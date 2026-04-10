# 🪄 Flutter App Transmuter

**Automate Flutter app rebranding across Android and iOS — driven by JSON configuration and customizable YAML operations.**

Flutter App Transmuter updates package names, bundle identifiers, app display names, Google API keys, pubspec versions, and more — all from a single `transmute.json` file. It also provides a complete **brand management workflow** for maintaining multiple branded variants of the same app.

Because all operations are defined as regex-based transformations in YAML, the built-in defaults are just a starting point — you can add, override, or disable operations to perform virtually **any text-based transformation** on any file in your Flutter project. If a value lives in a config file, manifest, plist, or source file and can be matched with a regex, Flutter App Transmuter can update it. The post-switch operations pipeline can also **run arbitrary shell commands and Dart packages** as part of the workflow — for example, the defaults include running `flutter_launcher_icons` for app icons, `flutter_native_splash` for splash screens, `flutterfire configure` for Firebase setup, and platform builds — all orchestrated as a single brand-switch operation.

---

## ✨ Features

- 🔄 **Brand Switching** — Switch between branded app variants with full file management
- 📄 **Whole-File Swapping** — Replace entire source files, configs, and assets per brand via `master_transmute.yaml`
- 📦 **Package Name & Bundle ID** — Change Android package name and iOS bundle identifiers (where-ever that may reside within different flutter version's platform files (AndroidManifest.xml/build.gradle.kts/etc.))
- 🏷️ **App Display Name** — Change the app name on both platforms simultaneously
- 📂 **MainActivity Relocation** — Automatically moves/renames `MainActivity.java`/`.kt` to the correct package directories
- 🔑 **API Key Management** — Swap API keys per brand across platform config files, such as Google Maps SDK keys in `AndroidManifest.xml` and `AppDelegate.swift`
- 📋 **Version Management** — Set `pubspec.yaml` version from your brand configuration
- 🔧 **Customizable Operations** — Override, extend, or disable any operation via YAML
- 🏃 **Dry Run Mode** — Preview all changes/differences without modifying any files
- ✅ **Verification** — When switching between brands check that project files match your transmute configuration and/or changes made to brand files within the 'live' source project are copied back to the brand directory

---

## 📥 Installation

Add to your `pubspec.yaml` under `dev_dependencies`:

```yaml
dev_dependencies:
  flutter_app_transmuter:
    path: ../path/to/flutter_app_transmuter
```

Then run:

```bash
dart pub get
```

---

## 🚀 Quick Start

1. Create a `transmute.json` in your Flutter project root:

```json
{
  "packageName": "com.example.myapp",
  "appName": "My App"
}
```

2. Run the transmuter:

```bash
dart run flutter_app_transmuter:main --transmute
```

That's it! All Android and iOS configuration files will be updated to match.

> **Want to see brand switching in action?** Check out the [`example/`](example/) directory, which includes 3 complete brand variants (Acme Corp, Globex Industries, Initech Solutions) — each with its own app icon, splash screen, logo, and configuration. The [example README](example/README.md) walks you through switching between brands.  You can switch between brands and run each brand's app version side by side from your IDE.

---

## 📄 Configuration File (`transmute.json`)

Place this file in your Flutter project's root directory. It defines the values that the transmuter will apply to your project files.

### Keys

| Key | Required | Description |
|-----|----------|-------------|
| `packageName` | **Yes** | Android package name and default iOS bundle identifier |
| `appName` | **Yes** | Android label and default iOS display name |
| `iosBundleIdentifier` | No | Override iOS bundle identifier (defaults to `packageName`) |
| `iosBundleDisplayName` | No | Override iOS display name (defaults to `appName`) |
| `androidGoogleMapsSDKApiKey` | No | Google Maps API key for Android (`AndroidManifest.xml`) |
| `iosGoogleMapsSDKApiKey` | No | Google Maps API key for iOS (`AppDelegate.swift`) |
| `pubspec_version` | No | Version string for `pubspec.yaml` (e.g., `1.2.3+4`) |
| `brand_name` | No | Display name shown in the rainbow banner during operations |
| `brand_source_directory` | No | Path to the brand files directory (set automatically by `--copy`) |

### Example

```json
{
  "brand_name": "Acme Corp",
  "brand_source_directory": "../brands/acme",
  "packageName": "com.acmecorp.superapp",
  "appName": "Acme Super App",
  "iosBundleIdentifier": "com.acmecorp.superapp.ios",
  "iosBundleDisplayName": "Acme App",
  "androidGoogleMapsSDKApiKey": "AIza...",
  "iosGoogleMapsSDKApiKey": "AIza...",
  "pubspec_version": "2.1.0+5"
}
```

> 🌈 When `brand_name` is set, a colorful rainbow banner is displayed at the start of every operation showing which brand is active.

---

## 🛠️ Command Line Reference

All commands are run from your Flutter project root:

```bash
dart run flutter_app_transmuter:main <options>
```

Operations are **mutually exclusive** — only one can be specified per invocation. (Operations: `--status`, `--check`, `--verify`, `--transmute`, `--copy`, `--diff`, `--update`, `--switch`, `--executepostprocess`)

---

### `--status`

Show the current brand status: diffs brand files against the project and checks transmute values.

```bash
dart run flutter_app_transmuter:main --status
```

This is a read-only operation. It displays:
- The current `brand_source_directory` from `transmute.json`
- File differences between the brand directory and the project
- Whether transmute values in the JSON match the actual project files

---

### `--check`

Check that all project files match the values defined in `transmute.json`. No files are modified.

```bash
dart run flutter_app_transmuter:main --check
```

Each operation is reported as **MATCH**, **MISMATCH**, or **SKIP**:

```
  MATCH:    [build_gradle_kts_namespace] namespace in build.gradle.kts
  MISMATCH: [android_label] android:label in AndroidManifest.xml
              file has:  Old App Name
              transmute.json specifies:  My New App
  SKIP:     [ios_google_maps_api_key] no value for json_key "iosGoogleMapsSDKApiKey"
```

---

### `--verify`

Interactive verification — like `--check`, but offers to fix mismatches.

```bash
dart run flutter_app_transmuter:main --verify
```

For each mismatch, you're prompted:

```
  MISMATCH: [android_label] android:label in AndroidManifest.xml
              file has:  Old App Name
              transmute.json specifies:  My New App
              (T) transmute.json -> file, (F) file -> transmute.json, or (N) no change (default N):
```

- **T** — Apply the `transmute.json` value to the project file
- **F** — Update `transmute.json` to match the current file value
- **N** — Skip (no change)

For missing keys, you're offered to add them to `transmute.json` from the current file values.

---

### `--transmute`

Run all transmute operations — applies values from `transmute.json` to project files.

```bash
dart run flutter_app_transmuter:main --transmute
```

This is the main operation. It reads `transmute.json`, loads the operations from the built-in defaults (and merges any user `transmute_operations.yaml`), then executes each operation in order.

```bash
# Dry run to preview changes
dart run flutter_app_transmuter:main --transmute --dryrun

# With debug output
dart run flutter_app_transmuter:main --transmute --debug
```

---

### `--copy=<brand_dir>`

Copy brand files from a directory into the project using the mappings defined in `master_transmute.yaml`.

```bash
dart run flutter_app_transmuter:main --copy ../brands/acme
```

This:
1. Reads `master_transmute.yaml` for file mapping definitions
2. Copies each mapped file from `<brand_dir>` into the project
3. Records the brand directory in `transmute.json` as `brand_source_directory`

The brand directory is a flat folder containing all brand-specific files (icons, config files, `transmute.json`, etc.).

---

### `--diff` / `--diff=<brand_dir>`

Compare brand files against current project files.

```bash
# Use the brand_source_directory from transmute.json
dart run flutter_app_transmuter:main --diff

# Or specify a directory explicitly
dart run flutter_app_transmuter:main --diff=../brands/acme
```

Files are reported as **identical**, **different**, or **missing**. No files are modified.

When specifying an explicit directory, it is checked against the `brand_source_directory` in `transmute.json` and a warning is shown if they don't match.

---

### `--update` / `--update=<brand_dir>`

Interactively update brand files from changed project files.

```bash
# Use the brand_source_directory from transmute.json
dart run flutter_app_transmuter:main --update

# Specify a directory explicitly
dart run flutter_app_transmuter:main --update=../brands/acme

# Auto-confirm all prompts (copy project->brand for all diffs)
dart run flutter_app_transmuter:main --update --yes

# Non-interactive: use project files, apply transmute values
dart run flutter_app_transmuter:main --update --projectfile --transmutevalue
```

For each changed file, you're prompted whether to update the brand copy. If the brand file is **newer** than the project file, a timestamp warning is shown with options:

```
  WARNING: Brand file is NEWER than project file!
    Brand:   2025-01-15 14:30:00
    Project: 2025-01-10 09:15:00
  (B) use brand file -> project, (P) use project file -> brand, or (N) skip:
```

After file updates, a transmute check runs to verify values and optionally update `transmute.json`.

---

### `--switch=<new_brand_dir>`

Switch from the current brand to a new one. This is the most comprehensive operation.

```bash
# Basic switch (interactive prompts)
dart run flutter_app_transmuter:main --switch ../brands/newbrand

# Non-interactive: use project files, apply transmute values
dart run flutter_app_transmuter:main --switch ../brands/newbrand --projectfile --transmutevalue

# With post-switch flags
dart run flutter_app_transmuter:main --switch ../brands/newbrand --projectfile --transmutevalue +flutterfire +build

# Exclude specific post-switch steps
dart run flutter_app_transmuter:main --switch ../brands/newbrand --projectfile --transmutevalue -clean -pub_get

# Auto-confirm everything (yes to all prompts, project->brand for file diffs)
dart run flutter_app_transmuter:main --switch ../brands/newbrand --yes
```

The switch performs these steps in order:

1. **Step 1: Update current brand** — Saves any project changes back to the current brand directory (same as `--update`)
2. **Step 2: Copy new brand** — Copies files from the new brand directory into the project (same as `--copy`)
3. **Step 3: Post-switch operations** — Runs the post-switch pipeline (transmute, rebuild icons, clean, etc.)

> ⚠️ Requires `brand_source_directory` to be set in `transmute.json` (automatically set by `--copy`).

#### Post-Switch Flags (`+flag`)

Use `+` prefix to enable optional post-switch steps:

| Flag | Description |
|------|-------------|
| `+flutterfire` | Run `flutterfire configure --yes --overwrite-firebase-options` |
| `+build` | Run platform build (`flutter build apk` on Windows/Linux, `flutter build ipa` on macOS) |

#### Excluding Steps (`-stepname`)

Use `-` prefix to skip specific post-switch steps:

| Example | Effect |
|---------|--------|
| `-clean` | Skip `flutter clean` |
| `-pub_get` | Skip `flutter pub get` |
| `-native_splash` | Skip `flutter_native_splash:create` |
| `-remove_derived_data` | Skip `ios_remove_derived_data` (macOS only step) |
| `-ios_remove_derived_data` | Same as above (full name also works) |
| `-transmute_command` | Skip the internal transmute step |

---

### `--executepostprocess` / `--executepostprocess=<brand_dir>`

Run only the post-switch operations pipeline without performing a full brand switch. This skips the "update current brand" and "copy new brand" steps, and goes straight to executing the post-switch operations (transmute, rebuild icons, clean, etc.).

```bash
# Run post-switch pipeline (uses brand_source_directory from transmute.json for $brand_dir)
dart run flutter_app_transmuter:main --executepostprocess

# Specify a brand directory explicitly (for $brand_dir substitution in commands)
dart run flutter_app_transmuter:main --executepostprocess=../brands/acme

# With flags and step exclusions (same syntax as --switch)
dart run flutter_app_transmuter:main --executepostprocess +flutterfire -clean

# Skip the transmute step, only run launcher icons and clean
dart run flutter_app_transmuter:main --executepostprocess -transmute_command -native_splash -pub_get
```

This is useful when:
- You need to re-run the post-switch pipeline after a failed or interrupted `--switch`
- You want to run specific post-switch steps (e.g., regenerate launcher icons) without switching brands
- You're debugging or testing the post-switch pipeline

The same `+flag` and `-stepname` options used with `--switch` work here. See [Post-Switch Flags](#post-switch-flags-flag) and [Excluding Steps](#excluding-steps--stepname) above.

---

### `--showdefaultyaml`

Print the built-in default transmute operations YAML to stdout.

```bash
dart run flutter_app_transmuter:main --showdefaultyaml
```

Useful for reviewing the default operations, piping to a file, or copying specific sections.

---

### `--writedefaultyaml` / `--writedefaultyaml=<filename>`

Write the default operations YAML to a file as a starting point for customization.

```bash
# Write to transmute_operations.yaml (default)
dart run flutter_app_transmuter:main --writedefaultyaml

# Write to a custom filename
dart run flutter_app_transmuter:main --writedefaultyaml=my_operations.yaml
```

If the file already exists, you'll be prompted before overwriting. This is the recommended way to create a starting point for your own customized operations file.

---

### Modifier Options

These options modify the behavior of the primary operations:

| Option | Description |
|--------|-------------|
| `--yes` | Auto-confirm all prompts (answer Y to yes/no, copy project->brand for file diffs) |
| `--skip` | Auto-answer N (skip/no change) to any prompt |
| `--brandfile` | Auto-answer B (use brand file) for brand/project file conflict prompts |
| `--projectfile` | Auto-answer P (use project file) for brand/project file conflict prompts |
| `--transmutevalue` | Auto-answer T (use transmute.json value) for transmute/file mismatch prompts |
| `--filevalue` | Auto-answer F (use file value) for transmute/file mismatch prompts |
| `--fatal-prompts` | Exit with error if any interactive prompt is encountered |
| `--dryrun` | Preview mode — no files are written to disk |
| `--debug` | Enable debug output (equivalent to `--verbose=1`) |
| `--verbose=<N>` | Set verbose debug level (0=off, 1+=debug detail) |
| `--help` / `--usage` | Show command line help |

#### Auto-Answer Prompt Options

The auto-answer options give you fine-grained control over how interactive prompts are handled:

**File conflict prompts** (B/P/N) — shown when brand and project files differ during `--update`:
- `--brandfile` — Always use the brand file (answer B)
- `--projectfile` — Always use the project file (answer P)
- `--skip` — Always skip (answer N)

**Transmute mismatch prompts** (T/F/N) — shown when file values don't match transmute.json during `--verify`:
- `--transmutevalue` — Always use the transmute.json value (answer T)
- `--filevalue` — Always use the current file value (answer F)
- `--skip` — Always skip (answer N)

**General behavior:**
- `--yes` — Auto-confirm yes/no prompts and copy project->brand for all file diffs
- `--skip` — Answer N/skip to any prompt that has a skip option
- `--fatal-prompts` — Exit with error code 1 if any prompt would be shown that isn't already auto-answered by another option

**Mutually exclusive pairs:**
- `--yes` and `--skip` cannot be used together
- `--brandfile` and `--projectfile` cannot be used together
- `--transmutevalue` and `--filevalue` cannot be used together

**Precedence:** More specific options take priority. For example, `--yes --transmutevalue` will auto-confirm yes/no prompts (via `--yes`) but answer T to mismatch prompts (via `--transmutevalue`, overriding `--yes`'s default of N for mismatches). `--fatal-prompts` only triggers for prompts not already handled by another auto-answer option.

---

## 📐 YAML Operations System

The transmuter's operations are defined in YAML and are fully customizable. There are two layers:

1. **Built-in defaults** — Always loaded from `default_transmute_operations.dart` (14 operations covering all standard Android and iOS configuration files)
2. **User overrides** — Optional `transmute_operations.yaml` in the project root can override, extend, or disable default operations

### Viewing the Defaults

```bash
# Print to terminal
dart run flutter_app_transmuter:main --showdefaultyaml

# Write to a file for customization
dart run flutter_app_transmuter:main --writedefaultyaml
```

### Operation Types

#### `regex_replace`

Finds regex matches in a file and replaces them with a template string.

```yaml
- id: android_label
  description: "android:label in AndroidManifest.xml"
  type: regex_replace
  platform: android
  file: "android/app/src/main/AndroidManifest.xml"
  json_key: appName
  regex: 'android:label\s*=\s*"([^"]*(\\"[^"]*)*)"'
  replacement: 'android:label="$value"'
```

#### `extract_and_replace`

Extracts the current value via regex group(1), then replaces all occurrences throughout the file.

```yaml
- id: ios_bundle_identifier
  description: "Bundle identifier in project.pbxproj"
  type: extract_and_replace
  platform: ios
  file: "ios/Runner.xcodeproj/project.pbxproj"
  json_key: iosBundleIdentifier
  fallback_key: packageName
  regex: 'PRODUCT_BUNDLE_IDENTIFIER\s*=?\s*(.*);'
  replacement: '$value'
```

#### `move_activity`

Moves `MainActivity.java`/`.kt` to the correct package directory structure. This is a specialized operation with hardcoded procedural logic.

```yaml
- id: move_main_activity
  description: "Move MainActivity to new package directory"
  type: move_activity
  platform: android
  json_key: packageName
```

### Operation Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier for merge/override matching |
| `description` | Yes | Human-readable label printed during execution |
| `type` | Yes | `regex_replace`, `extract_and_replace`, or `move_activity` |
| `platform` | Yes | `android`, `ios`, or `both` (affects logging color) |
| `file` | For regex/extract | Path to the file to modify (relative to project root) |
| `optional` | No | If `true`, skip silently when file doesn't exist (default: `false`) |
| `json_key` | Yes | The `transmute.json` key that provides the replacement value |
| `fallback_key` | No | Fallback `transmute.json` key if `json_key` is missing |
| `regex` | For regex/extract | Regular expression pattern (use single quotes in YAML) |
| `multiline` | No | Enable multiline regex matching (default: `false`) |
| `replacement` | For regex/extract | Template string — `$value` is replaced with the JSON value |

### Customizing with `transmute_operations.yaml`

Create a `transmute_operations.yaml` in your project root to customize operations. Use `--writedefaultyaml` to generate a starting point:

```bash
dart run flutter_app_transmuter:main --writedefaultyaml
```

Then edit the file. The merge rules are:

- **Override** — A user operation with the same `id` as a default replaces it in-place
- **Disable** — Set `disabled: true` on an operation `id` to remove it
- **Extend** — Operations with new `id` values are appended at the end

#### Example: Custom `transmute_operations.yaml`

```yaml
operations:
  # Override: change the regex for namespace
  - id: build_gradle_kts_namespace
    description: "custom namespace in build.gradle.kts"
    type: regex_replace
    platform: android
    file: "android/app/build.gradle.kts"
    optional: true
    json_key: packageName
    regex: 'namespace\s*=\s*"(.*)"'
    replacement: 'namespace = "$value"'

  # Disable: skip the profile manifest update
  - id: profile_manifest_package
    disabled: true

  # Extend: add a custom operation
  - id: custom_splash_config
    description: "Update splash screen app title"
    type: regex_replace
    platform: both
    file: "lib/config/splash.dart"
    json_key: appName
    regex: 'appTitle\s*=\s*"(.*)"'
    replacement: 'appTitle = "$value"'

post_switch_operations:
  # Override: use a different clean command
  clean: "flutter clean && flutter pub cache clean"

  # Disable a step
  native_splash: disabled

  # Add a custom step
  build_runner: "dart run build_runner build --delete-conflicting-outputs"
```

---

## 🔄 Post-Switch Operations

When using `--switch`, a pipeline of shell commands runs automatically after the brand copy. These are defined in the `post_switch_operations` section of the YAML.

### Default Post-Switch Pipeline

| Step | Command | Platform | Condition |
|------|---------|----------|-----------|
| `transmute_command` | `--transmute` (internal) | All | Always |
| `launcher_icons` | `dart run flutter_launcher_icons` | All | Always |
| `native_splash` | `dart run flutter_native_splash:create` | All | Always |
| `clean` | `flutter clean` | All | Always |
| `ios_remove_derived_data` | `rm -rf ~/Library/.../DerivedData/Runner-*` | macOS only | Always |
| `ios_xcode_reminder` | Prints Xcode reminder message | macOS only | Always |
| `pub_get` | `flutter pub get` | All | Always |
| `requireflag_flutterfire` | `flutterfire configure --yes --overwrite-firebase-options` | All | `+flutterfire` |
| `android_requireflag_build` | `flutter build apk --target-platform android-arm64` | Windows/Linux | `+build` |
| `ios_requireflag_build` | `flutter build ipa` | macOS | `+build` |

### Step Name Prefixes

The step name (YAML key) uses prefixes to control behavior:

| Prefix | Effect |
|--------|--------|
| `ios_` | Step only runs on macOS |
| `android_` | Step only runs on Windows/Linux |
| `requireflag_` | Step only runs when `+flagname` is on the command line |
| *(none)* | Step runs on all platforms unconditionally |

Prefixes can combine: `ios_requireflag_build` runs only on macOS and only when `+build` is specified.

### Special Step: `transmute_command`

The `transmute_command` step name invokes the transmuter internally (no new process spawned). The value specifies which options to use:

```yaml
post_switch_operations:
  transmute_command: "--transmute"
```

Only these options are allowed in the value: `--transmute`, `--yes`, `--debug`, `--verbose[=N]`. Invalid options cause an error at startup before any work begins.

### `$brand_dir` Variable

Shell commands can use `$brand_dir` which is replaced with the new brand directory path:

```yaml
post_switch_operations:
  copy_apk: "cp build/app/outputs/flutter-apk/app-release.apk $brand_dir/release_builds/"
```

---

## 📁 Brand Management

### Directory Structure

A typical multi-brand project setup:

```
my_flutter_app/
├── transmute.json              # Current brand configuration
├── master_transmute.yaml       # File mapping definitions
├── transmute_operations.yaml   # Optional custom operations
├── pubspec.yaml
├── lib/
│   └── client/
│       ├── config.dart         # ← swapped per brand (different API endpoints, feature flags)
│       └── theme.dart          # ← swapped per brand (different colors, fonts, spacing)
├── android/
│   └── app/
│       └── google-services.json  # ← swapped per brand (different Firebase project)
├── ios/
│   └── Runner/
│       └── GoogleService-Info.plist  # ← swapped per brand
└── brands/
    ├── acme/
    │   ├── transmute.json
    │   ├── appicon_square_1024x1024.png
    │   ├── google-services.json
    │   ├── GoogleService-Info.plist
    │   ├── config.dart          # Acme's API endpoints, feature flags
    │   ├── theme.dart           # Acme's colors, fonts
    │   └── ...
    └── globex/
        ├── transmute.json
        ├── appicon_square_1024x1024.png
        ├── google-services.json
        ├── GoogleService-Info.plist
        ├── config.dart          # Globex's API endpoints, feature flags
        ├── theme.dart           # Globex's colors, fonts
        └── ...
```

### Swapping Entire Source Files Per Brand

While regex-based transmute operations are great for changing individual values
in config files, many real-world projects need to swap **entire files** per brand.
This is one of the most powerful features of the brand management system.

Common files to swap per brand:

- **Dart source files** — `config.dart`, `theme.dart`, `constants.dart`, `routes.dart`
  with brand-specific API endpoints, feature flags, color themes, or navigation
- **Firebase configs** — `google-services.json` (Android) and `GoogleService-Info.plist`
  (iOS) pointing at different Firebase projects
- **Image assets** — app icons, splash screens, logos, onboarding images
- **Platform configs** — `flutter_launcher_icons.yaml`, `flutter_native_splash.yaml`
  with brand-specific settings
- **Entitlements / provisioning** — iOS entitlements files with different app group or
  keychain access group identifiers

All of this is managed through `master_transmute.yaml` — the brand directory
is flat (all files at the top level), and the YAML maps each file to one or
more destinations in the project tree.

### `master_transmute.yaml`

This file defines how brand files map to project locations. Place it in your project root.

```yaml
# Files where the source filename differs from the destination,
# or needs to be copied to multiple locations
file_mappings:
  - source: appicon_square_1024x1024.png
    destinations:
      - android/app/src/main/res/mipmap-hdpi/ic_launcher_background.png
      - android/app/src/main/res/mipmap-mdpi/ic_launcher_foreground.png
      - assets/images/brand/app_icon.png

# Files where the brand file has the same basename as the destination.
# The brand directory is flat — the basename is used to locate the
# source file, and the full path is the destination in the project.
files:
  - transmute.json
  - android/app/google-services.json
  - ios/Runner/GoogleService-Info.plist
  - assets/images/brand/logo.png
  - lib/client/config.dart
  - lib/client/theme.dart
  - flutter_launcher_icons.yaml
  - flutter_native_splash.yaml
```

The brand directory is **flat** — all source files are in one directory. The `files` section uses the basename of each path to find the source file in the brand directory.

The combination of **whole-file swapping** (via `master_transmute.yaml`) and
**regex-based value replacement** (via transmute operations) means you can
handle everything from swapping an entire config module to changing a single
string deep in a platform manifest — all as part of the same `--switch`
command.

### Workflow Example

```bash
# 1. Initial setup: copy brand files into a fresh project
dart run flutter_app_transmuter:main --copy ../brands/acme

# 2. Apply all transmute operations
dart run flutter_app_transmuter:main --transmute

# 3. Check status at any time
dart run flutter_app_transmuter:main --status

# 4. After making project changes, update the brand directory
dart run flutter_app_transmuter:main --update

# 5. Switch to a different brand (updates current brand first)
dart run flutter_app_transmuter:main --switch ../brands/globex +flutterfire

# 6. Quick switch without cleaning
dart run flutter_app_transmuter:main --switch ../brands/acme -clean -pub_get
```

---

## 🎨 Default Transmute Operations

The transmuter ships with 14 built-in operations. Use `--showdefaultyaml` to see the full YAML.

### Android Operations

| ID | Description | JSON Key |
|----|-------------|----------|
| `build_gradle_application_id` | applicationId in build.gradle | `packageName` |
| `build_gradle_kts_namespace` | namespace in build.gradle.kts | `packageName` |
| `build_gradle_kts_application_id` | applicationId in build.gradle.kts | `packageName` |
| `main_manifest_package` | package in main AndroidManifest.xml | `packageName` |
| `debug_manifest_package` | package in debug AndroidManifest.xml | `packageName` |
| `profile_manifest_package` | package in profile AndroidManifest.xml | `packageName` |
| `move_main_activity` | Move MainActivity to new package dir | `packageName` |
| `android_label` | android:label in AndroidManifest.xml | `appName` |
| `android_google_maps_api_key` | Google Maps API key in manifest | `androidGoogleMapsSDKApiKey` |

### iOS Operations

| ID | Description | JSON Key |
|----|-------------|----------|
| `ios_bundle_identifier` | Bundle identifier in project.pbxproj | `iosBundleIdentifier` → `packageName` |
| `ios_display_name_info_plist` | CFBundleDisplayName in Info.plist | `iosBundleDisplayName` → `appName` |
| `ios_display_name_pbxproj` | CFBundleDisplayName in project.pbxproj | `iosBundleDisplayName` → `appName` |
| `ios_google_maps_api_key` | Google Maps API key in AppDelegate.swift | `iosGoogleMapsSDKApiKey` |

### Both Platforms

| ID | Description | JSON Key |
|----|-------------|----------|
| `pubspec_version` | version in pubspec.yaml | `pubspec_version` |

> The `→` notation indicates a fallback: `iosBundleIdentifier → packageName` means it uses `iosBundleIdentifier` if present, otherwise falls back to `packageName`.

---

## 🧪 Tips & Tricks

### Preview Before Applying

Always use `--dryrun` when trying something new:

```bash
dart run flutter_app_transmuter:main --transmute --dryrun
```

### Create a Custom Operations File

```bash
# Generate a starting point with all defaults
dart run flutter_app_transmuter:main --writedefaultyaml

# Edit transmute_operations.yaml to add your custom operations
# Then run with your customizations active
dart run flutter_app_transmuter:main --transmute
```

### Verify After Changes

```bash
# Quick read-only check
dart run flutter_app_transmuter:main --check

# Interactive fix-up
dart run flutter_app_transmuter:main --verify
```

### Automate in CI/Scripts

```bash
# Non-interactive brand switch for CI (use project files, apply transmute values)
dart run flutter_app_transmuter:main --switch ../brands/release_brand --projectfile --transmutevalue +build

# Strict CI mode: fail if any unexpected prompt is encountered
dart run flutter_app_transmuter:main --switch ../brands/release_brand --projectfile --transmutevalue --fatal-prompts +build

# Or use --yes for full auto-confirm
dart run flutter_app_transmuter:main --switch ../brands/release_brand --yes +build
```

---

## 🤖 AI / Agent Support

This repository includes an [`AGENTS.md`](AGENTS.md) file — a structured guide
designed for AI coding assistants (Claude Code, GitHub Copilot, Gemini, etc.)
and autonomous agents. It provides the context an AI needs to help you set up
brands, write custom transmute operations, configure `master_transmute.yaml`,
and run the correct commands — without you having to explain the tool from
scratch each time.

If you use an AI assistant in your workflow, having `AGENTS.md` in the repo
means it can understand the transmuter's concepts, commands, and pitfalls
out of the box.

---

## 📜 License

Distributed under the MIT license.

## 🔗 Links

- Repository: [https://github.com/timmaffett/flutter_app_transmuter](https://github.com/timmaffett/flutter_app_transmuter)

## 🙏 Acknowledgements

Originally forked from [flutter_app_rebrand](https://github.com/sarj33t/flutter_app_rebrand) by sarj33t, it no
longer shares much of the original code, but flutter_app_rebrand was the tool that inspired me to create
`flutter_app_transmuter` in the first place.

## Dev Notes

- to activate from local copy of repo, allowing you to use 'transmute' command using the current source
    `dart pub global activate --source path .`
