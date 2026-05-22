# AGENTS.md — AI/Agent Guide to flutter_app_transmuter

This file helps AI assistants and coding agents understand and use `flutter_app_transmuter` when helping users rebrand Flutter apps or manage multi-brand projects.

## What This Tool Does

`flutter_app_transmuter` is a Dart CLI tool that automates rebranding Flutter applications. It has two complementary mechanisms:

1. **Regex-based value replacement** (`--transmute`) — Rewrites specific values (package names, bundle IDs, app names, API keys, versions) inside platform config files using regex patterns defined in YAML.
2. **Whole-file swapping** (`--copy`, `--switch`) — Replaces entire files (source code, images, Firebase configs, YAML configs) per brand using mappings defined in `master_transmute.yaml`.

Together these let a single Flutter project produce multiple branded app variants — each with a different package name, app icon, splash screen, API keys, Firebase project, theme, feature flags, and even entirely different Dart source files.

## When to Use This Tool

Use `flutter_app_transmuter` when the user needs to:
- Rebrand a Flutter app (change package name, bundle ID, app name, icons)
- Maintain multiple branded variants of the same Flutter app
- Switch between brand configurations during development
- Set up a new brand variant from an existing project
- Automate post-rebrand tasks (icon generation, splash screens, clean builds)

## Key Concepts

### Brand Directory
A flat directory containing all brand-specific files. No subdirectories — just files at the top level. The `master_transmute.yaml` maps these flat files to their destinations in the project tree.

### Three Config Files (in the Flutter project root)

| File | Purpose |
|------|---------|
| `transmute.json` | **Required.** Key-value pairs consumed by transmute operations (package name, app name, bundle ID, API keys, version, plus any custom keys) |
| `master_transmute.yaml` | **Required for brand switching.** Maps brand directory files to project destinations. Defines which files get copied/diffed/updated when switching brands |
| `transmute_operations.yaml` | **Optional.** User-defined regex operations that extend or override the 14 built-in defaults. Also can customize the post-switch pipeline |

### transmute.json Keys

Standard keys consumed by built-in operations:

| Key | Used By | Fallback |
|-----|---------|----------|
| `packageName` | Android namespace, applicationId, manifest package, MainActivity | — |
| `appName` | Android label, iOS display name | — |
| `iosBundleIdentifier` | iOS bundle ID in pbxproj | `packageName` |
| `iosBundleDisplayName` | iOS display name in Info.plist, pbxproj | `appName` |
| `androidGoogleMapsSDKApiKey` | Google Maps key in AndroidManifest.xml | — |
| `iosGoogleMapsSDKApiKey` | Google Maps key in AppDelegate.swift | — |
| `pubspec_version` | version in pubspec.yaml | — |
| `brand_name` | Display name in rainbow banner (cosmetic) | — |
| `brand_source_directory` | Path to current brand dir (set by `--copy`) | — |

Users can add **any custom keys** and reference them from custom operations in `transmute_operations.yaml` via the `json_key` field.

### master_transmute.yaml Structure

```yaml
# 1:N mappings — one source file copied to multiple destinations
file_mappings:
  - source: appicon_square.png
    destinations:
      - assets/images/brand/app_icon.png
      - android/app/src/main/res/drawable/app_icon.png

  # 1:1 mapping variant
  - source: splash_logo.png
    destination: assets/images/brand/splash_logo.png

# Same-basename mappings — source basename matches destination basename
# Brand dir has "config.dart", it goes to "lib/client/config.dart"
files:
  - transmute.json
  - lib/client/config.dart
  - lib/client/theme.dart
  - android/app/google-services.json
  - ios/Runner/GoogleService-Info.plist
  - flutter_launcher_icons.yaml
  - flutter_native_splash.yaml
```

## Commands Reference (Quick)

All commands run from the Flutter project root:

```bash
# Core operations
--transmute                    # Apply transmute.json values to project files
--copy <brand_dir>             # Copy brand files into project, set as active brand
--switch <brand_dir>           # Save current brand, copy new brand, run full pipeline
--diff [brand_dir]             # Compare brand files vs project (read-only)
--update [brand_dir]           # Sync changed project files back to brand dir
--status                       # Show current brand + diffs + value checks (read-only)
--check                        # Verify project files match transmute.json (read-only)
--verify                       # Interactive check with fix prompts
--executepostprocess           # Re-run post-switch pipeline without switching

# Utilities
--showdefaultyaml              # Print built-in default operations
--writedefaultyaml [file]      # Export defaults to a file for customization
--dryrun                       # Add to any command to preview without writing
--debug                        # Verbose output

# CI/automation flags
--yes                          # Auto-confirm all prompts
--skip                         # Auto-skip all prompts
--projectfile                  # Auto-answer "use project file" for diffs
--brandfile                    # Auto-answer "use brand file" for diffs
--transmutevalue               # Auto-answer "use transmute.json value" for mismatches
--fatal-prompts                # Error if any prompt would appear (CI safety)

# Post-switch step control
+flutterfire                   # Enable flutterfire configure step
+build                         # Enable platform build step
-clean                         # Skip flutter clean
-native_splash                 # Skip native splash generation
-pub_get                       # Skip flutter pub get
```

## Common Workflows

### Workflow 1: Simple rebrand (no brand management)

For a one-time rebrand, only `transmute.json` is needed:

```json
{
  "packageName": "com.newcompany.myapp",
  "appName": "New App Name"
}
```

```bash
dart run flutter_app_transmuter:main --transmute
```

### Workflow 2: Set up multi-brand project from scratch

1. Create `master_transmute.yaml` mapping brand files to project destinations
2. Create brand directories (flat) with all brand-specific files
3. Copy the first brand: `--copy brands/brand_a`
4. Apply values: `--transmute`
5. Switch to another: `--switch brands/brand_b`

### Workflow 3: Switch between existing brands

```bash
dart run flutter_app_transmuter:main --switch brands/target_brand
```

This single command: saves current brand -> copies new brand -> transmutes -> runs launcher_icons -> runs native_splash -> cleans -> pub gets.

### Workflow 4: Add a custom regex operation

When the user needs to change a value in a source file per brand:

1. Add a marker comment in the source file (e.g., `//BRANDNAME`, `//BRAND_API_URL`)
2. Add a custom key to each brand's `transmute.json`
3. Add an operation to `transmute_operations.yaml`:

```yaml
operations:
  - id: my_custom_operation
    description: "API URL in config.dart"
    type: regex_replace
    platform: both
    file: "lib/config.dart"
    json_key: api_url
    regex: "apiUrl\\s*=\\s*'([^']*)'.*//BRAND_API_URL"
    replacement: "apiUrl = '$value' //BRAND_API_URL"
```

Key rules for custom operations:
- The regex MUST have a capture group `()` around the old value — the transmuter uses `group(1)` for logging
- The `//MARKER` comment anchors the regex and survives across brand switches
- `$value` in the replacement is substituted with the `json_key` value from `transmute.json`

### Workflow 5: Swap entire source files per brand

For files that differ too much for regex (different implementations, different Firebase projects):

1. Add the file to `master_transmute.yaml` under `files:` (same basename) or `file_mappings:` (different name)
2. Place each brand's version in their brand directory
3. `--switch` will copy the right version automatically

Common files to swap whole: `config.dart`, `theme.dart`, `google-services.json`, `GoogleService-Info.plist`, app icons, splash images, `flutter_launcher_icons.yaml`, `flutter_native_splash.yaml`.

## Writing Custom Operations — Rules

| Rule | Detail |
|------|--------|
| Regex must have a capture group | `group(1)` is used to extract the old value for logging. Without it, you get a `RangeError` |
| Use `$value` in replacement | Substituted with the value from `transmute.json` at the key specified by `json_key` |
| Use `git_restore` for deterministic baselines | Resets a file to git `HEAD` before other transforms; ideal for `ios/Runner/Info.plist` when switching brands |
| Use marker comments | Anchor regexes with comments like `//BRANDNAME` so they don't accidentally match elsewhere |
| `id` must be unique | Used for merge/override matching. Reusing a built-in `id` overrides that operation |
| `disabled: true` removes an operation | Use this to turn off a built-in default you don't need |
| `optional: true` silences missing files | Without it, a missing file is an error |
| `fallback_key` for optional keys | If `json_key` isn't in transmute.json, tries `fallback_key` before skipping |
| `platform` affects log color only | `android` = orange, `ios` = cyan, `both` = green. Does not restrict execution |

## Operation Types

| Type | Behavior |
|------|----------|
| `regex_replace` | Match regex, replace with template. Good for single-value changes in a known location |
| `extract_and_replace` | Extract current value via `group(1)`, then replace ALL occurrences of that value in the file. Good for values that appear many times (like bundle ID in pbxproj) |
| `move_activity` | Special: moves `MainActivity.java`/`.kt` to the package directory matching `packageName` |
| `git_restore` | Special: restores `file` to git `HEAD` baseline using `git restore` (fallback: `git checkout --`). Runs unconditionally and does not require `json_key` |

Execution order for operations is two-pass:
1. All `git_restore` operations run first
2. All value-driven operations run next (`regex_replace`, `extract_and_replace`, `move_activity`)

This guarantees deterministic starting state for files that many brands mutate over time.

## Post-Switch Pipeline

The default `--switch` pipeline runs these steps in order:

1. `transmute_command` — internal `--transmute`
2. `launcher_icons` — `dart run flutter_launcher_icons`
3. `native_splash` — `dart run flutter_native_splash:create`
4. `clean` — `flutter clean`
5. `ios_remove_derived_data` — rm DerivedData (macOS only)
6. `ios_xcode_reminder` — print Xcode reminder (macOS only)
7. `pub_get` — `flutter pub get`

Steps can be customized in `transmute_operations.yaml` under `post_switch_operations:`. Use the step name as key, `"disabled"` as value to skip, or a shell command string to override.

Step name prefixes: `ios_` = macOS only, `android_` = Windows/Linux only, `requireflag_` = needs `+flag` on command line.

## Important Pitfalls

- **Always `--dryrun` first** when unsure — it previews all changes without writing files
- **`brand_source_directory`** must be set before `--switch` or `--update` works — `--copy` sets it automatically
- **`brand_source_directory` is stored as a POSIX path** (forward slashes) in transmute.json, even on Windows
- **New Flutter templates** don't have `package=` in AndroidManifest.xml — the "pattern not matched" warnings for manifest package operations are normal and expected
- **`--switch` is interactive by default** — it prompts when files differ. Use `--projectfile --transmutevalue` or `--yes` for non-interactive CI usage
- **Operation `id` values are sacred** — the built-in IDs are part of the public API. Users override operations by matching `id`, so changing them in the source breaks user customizations
- **The `files:` section uses basenames** — `lib/client/config.dart` means "find `config.dart` in the brand directory, copy to `lib/client/config.dart`"
- **Do not rely on append order for `git_restore`** — user operations are appended during merge, but `git_restore` still executes first due to the dedicated pre-pass

## Example Project

The `example/` directory contains a working multi-brand demo with 3 brands (Acme Corp, Globex Industries, Initech Solutions). Each has distinct package names, icons, splash screens, and a custom transmute operation that changes the AppBar title and color. See `example/README.md` for a step-by-step walkthrough.
