# Flutter App Transmuter — Example: Three Branded Apps on One Device

This example walks you through building and installing **three differently
branded versions** of the same Flutter app on a single device. Because each
brand has a unique package name / bundle ID, all three coexist side by side
in your app drawer — each with its own name, icon, and splash screen.

## The Three Brands

| | Acme Corp | Globex Industries | Initech Solutions |
|---|---|---|---|
| **Package Name** | `com.acmecorp.flutterapp` | `com.globexindustries.flutterapp` | `com.initechsolutions.flutterapp` |
| **App Name** | Acme App | Globex App | Initech App |
| **Icon** | Red diamond on charcoal | Blue rings on navy | Green grid on dark gray |
| **Splash Color** | `#333333` | `#1A1A2E` | `#2A2A2A` |

Each brand directory (`brands/<name>/`) contains:
- `transmute.json` — package name, app name, bundle IDs, version
- `appicon_square.png` — square app icon for `flutter_launcher_icons`
- `logo_wide.png` — wide logo for in-app branding
- `splash.png` — splash screen image for `flutter_native_splash`
- `flutter_launcher_icons.yaml` — config for the `flutter_launcher_icons` package
- `flutter_native_splash.yaml` — config for the `flutter_native_splash` package

---

## Setup

### 1. Create the Flutter project scaffolding

From the parent directory of `example/`, generate the platform directories:

```bash
cd example
flutter create --org com.acmecorp --project-name flutterapp .
```

The initial org doesn't matter much — the transmuter will overwrite it — but
using the first brand's org avoids an unnecessary rename on the first run.

### 2. Install dependencies and create asset directories

```bash
flutter pub get
mkdir -p assets/images/brand
```

---

## Step 1: Build and Run as Acme Corp

### Apply the brand

Use `--copy` to copy the Acme Corp brand files into the project, then
`--transmute` to rewrite package names, bundle IDs, and app names across all
platform files:

```bash
dart run flutter_app_transmuter:main --copy brands/acme_corp
dart run flutter_app_transmuter:main --transmute
```

This sets up:
- Android package: `com.acmecorp.flutterapp`
- iOS bundle ID: `com.acmecorp.flutterapp`
- App display name: **Acme App**
- Red diamond app icon and charcoal splash screen

### Run it

```bash
flutter run
```

You now have **Acme App** installed on your device. You'll see:
- A **red diamond** launcher icon in your app drawer
- A **charcoal** splash screen with a red diamond on launch
- The branded logo (`logo_wide.png`) available as an in-app asset

**Leave it installed** — we're going to add more apps alongside it.

---

## Step 2: Switch to Globex Industries, Build and Run

The `--switch` command does everything in one step: it saves any changes back
to the current brand (Acme Corp), copies the new brand's files in, and runs
the full transmute + post-switch pipeline (launcher icons, native splash,
clean, pub get):

```bash
dart run flutter_app_transmuter:main --switch brands/globex_industries
```

The project is now branded as **Globex Industries**:
- Android package: `com.globexindustries.flutterapp`
- iOS bundle ID: `com.globexindustries.flutterapp`
- App display name: **Globex App**
- Blue concentric rings icon and navy splash screen

### Run it

```bash
flutter run
```

Because the package name changed from `com.acmecorp.flutterapp` to
`com.globexindustries.flutterapp`, this installs as a **separate app**.
You'll see a **navy** splash screen with blue concentric rings on launch.

Check your device — you should now see **two apps** side by side in your
app drawer: Acme App (red diamond icon) and Globex App (blue rings icon),
each with their own distinct splash screen and in-app logo.

---

## Step 3: Switch to Initech Solutions, Build and Run

```bash
dart run flutter_app_transmuter:main --switch brands/initech_solutions
```

The project is now:
- Android package: `com.initechsolutions.flutterapp`
- iOS bundle ID: `com.initechsolutions.flutterapp`
- App display name: **Initech App**
- Green 3x3 grid icon and dark gray splash screen

### Run it

```bash
flutter run
```

You'll see a **dark gray** splash screen with a green grid emblem on launch.

**All three branded apps are now installed on your device.** Open your app
drawer (or home screen) and you'll see three distinct apps side by side:

| | Acme App | Globex App | Initech App |
|---|----------|-----------|-------------|
| **Icon** | Red diamond | Blue rings | Green grid |
| **Splash** | Charcoal + red | Navy + blue | Dark gray + green |
| **Logo** | Red bar w/ diamond | Blue bar w/ rings | Green bar w/ grid |
| **Package** | `com.acmecorp.flutterapp` | `com.globexindustries.flutterapp` | `com.initechsolutions.flutterapp` |

Each app has its own launcher icon, splash screen, and in-app logo — all
generated from the brand asset PNGs in each brand's directory.

This works because each brand uses a different `packageName` /
`iosBundleIdentifier`. Android and iOS treat each unique identifier as a
separate application, so they install side by side rather than replacing
each other.

---

## Switching Back

You can switch to any brand at any time. The current brand's files are always
saved back before switching, so no work is lost:

```bash
dart run flutter_app_transmuter:main --switch brands/acme_corp
```

---

## What `--switch` Does Under the Hood

A single `--switch` command runs this pipeline automatically:

1. **Update** — saves current project files back to the outgoing brand directory
2. **Copy** — copies the incoming brand's files into the project
3. **Transmute** — rewrites package names, bundle IDs, and app names in platform files
4. **Post-switch operations** — runs `flutter_launcher_icons`, `flutter_native_splash:create`, `flutter clean`, and `flutter pub get`

### Files that get rewritten

| File | What Changes |
|------|-------------|
| `android/app/build.gradle.kts` | `namespace` and `applicationId` |
| `android/app/src/main/AndroidManifest.xml` | `android:label` |
| `android/app/src/main/kotlin/.../MainActivity.kt` | `package` declaration + directory path |
| `ios/Runner.xcodeproj/project.pbxproj` | `PRODUCT_BUNDLE_IDENTIFIER` |
| `ios/Runner/Info.plist` | `CFBundleDisplayName` |
| `pubspec.yaml` | `version` |
| `assets/images/brand/*` | App icon, logo, splash screen images |
| `flutter_launcher_icons.yaml` | Icon generation config |
| `flutter_native_splash.yaml` | Splash screen config |
| `lib/main.dart` | AppBar title text (custom operation — see below) |

---

## Custom Transmute Operations: Branding Your Own Source Files

The built-in operations handle platform files (manifests, plists, pbxproj,
build.gradle.kts), but you can add your own regex-based transformations for
**any text file** in your project. This example includes one to demonstrate.

### How it works in this example

The AppBar title in `lib/main.dart` includes a marker comment:

```dart
title: const Text('Acme Corp Brand Demo'), //BRANDNAME
```

Each brand's `transmute.json` has a `brand_title` key:

```json
{
  "brand_title": "Acme Corp Brand Demo",
  ...
}
```

And `transmute_operations.yaml` in the project root defines a custom operation
that ties them together:

```yaml
operations:
  - id: main_dart_brand_title
    description: "Brand title in main.dart AppBar"
    type: regex_replace
    platform: both
    file: "lib/main.dart"
    json_key: brand_title
    regex: "const Text\\('([^']*)'\\),\\s*//BRANDNAME"
    replacement: "const Text('$value'), //BRANDNAME"
```

When `--transmute` or `--switch` runs, it finds this operation, reads the
`brand_title` value from `transmute.json`, and replaces the text between the
quotes — while preserving the `//BRANDNAME` marker so it works again next time.

### Writing your own custom operations

You can use this same pattern to brand **any text in any file**:

1. Add a marker comment (e.g. `//BRANDNAME`, `<!-- BRAND -->`, `# BRAND`)
   next to the text you want to change
2. Add a key to your `transmute.json` with the replacement value
3. Add an operation to `transmute_operations.yaml` with a regex that matches
   the line (including the marker) and a replacement that inserts `$value`

The regex just needs to match the **current** text (whatever it was set to
by the last brand), and the replacement writes the **new** brand's value.
The marker comment anchors the regex so it doesn't accidentally match
similar text elsewhere in the file.

To see all the built-in default operations as a starting point:

```bash
dart run flutter_app_transmuter:main --showdefaultyaml
```

---

## Inspecting the Current Brand

```bash
# Show the active brand and brand_source_directory
dart run flutter_app_transmuter:main --status

# Diff brand directory files against the project
dart run flutter_app_transmuter:main --diff

# Verify transmute.json values match what's in the platform files
dart run flutter_app_transmuter:main --check

# Interactive verification with fix prompts
dart run flutter_app_transmuter:main --verify
```

---

## Dry Run

Preview any operation without modifying files:

```bash
dart run flutter_app_transmuter:main --switch brands/globex_industries --dryrun
```

---

## Further Customization

Export the full set of built-in default operations to a file you can customize:

```bash
dart run flutter_app_transmuter:main --writedefaultyaml transmute_operations.yaml
```

Operations are merged by `id` — to override a built-in operation, use the same
`id` in your `transmute_operations.yaml`. You can also disable operations by
adding `enabled: false`. See the main [README](../README.md) for full
documentation.
