# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flutter App Transmuter is a Dart CLI tool that automates rebranding Flutter applications. It modifies package names, bundle identifiers, app names, Google Maps API keys, and related configuration across both Android and iOS platforms. Forked from `flutter_app_rebrand`.

## Build & Run Commands

```bash
# Get dependencies
dart pub get

# Run the tool against a Flutter project (from the target project's root)
dart run flutter_app_transmuter:main transmute.json

# Dry run (no files written to disk)
dart run flutter_app_transmuter:main --dryrun transmute.json

# Verbose/debug output
dart run flutter_app_transmuter:main --debug transmute.json
dart run flutter_app_transmuter:main --verbose=2 transmute.json

# Static analysis
dart analyze
```

There are no unit tests in this repository. CI testing is done via GitHub Actions (`.github/workflows/test_main.yml`) which creates a fresh Flutter project, runs the transmuter against it, and verifies the output with grep checks.

## Architecture

**Entry flow:** `bin/main.dart` → `bin/flutter_app_transmuter.dart` (CLI arg parsing) → `lib/flutter_app_transmuter.dart` (`FlutterAppTransmuter.run()`) → delegates to platform-specific transmuters.

### Key source files

- `lib/flutter_app_transmuter.dart` — Main orchestrator. Reads `transmute.json`, validates fields, dispatches to `AndroidTransmuter` and `IOSTransmute`.
- `lib/src/transmute/android_transmute.dart` — Android platform: updates `build.gradle`/`.kts`, `AndroidManifest.xml` (main/debug/profile), moves `MainActivity` to new package directory.
- `lib/src/transmute/ios_transmute.dart` — iOS platform: updates `project.pbxproj` bundle identifiers, `Info.plist` display name, `AppDelegate.swift` Google Maps key.
- `lib/src/transmute/constants.dart` — `TransmuterKeys` enum (JSON config keys), `RegExConstants` (all regex patterns for matching config values), `Constants` (file paths, error messages).
- `lib/src/transmute/file_utils.dart` — File I/O utilities (`replaceInFile`, `replaceInFileRegex`, `readFileAsString`, `writeStringToFilename`). All writes check the global `FlutterAppTransmuter.executingDryRun` flag.

### Design patterns

- **Regex-based replacement strategy**: All config file modifications use compiled `RegExp` patterns from `RegExConstants` to find and replace values, with occurrence counting for verification.
- **Global dry-run flag**: `FlutterAppTransmuter.executingDryRun` is checked before every file write, enabling safe preview mode.
- **Configuration-driven**: All rebranding parameters come from `transmute.json` with `TransmuterKeys` enum mapping JSON keys.

## Configuration File (`transmute.json`)

Placed in the target Flutter project root:

| Key | Required | Description |
|-----|----------|-------------|
| `packageName` | Yes | Android package name and default iOS bundle ID |
| `appName` | Yes | Android label and default iOS display name |
| `iosBundleIdentifier` | No | Override iOS bundle ID if different from `packageName` |
| `iosBundleDisplayName` | No | Override iOS display name if different from `appName` |
| `androidGoogleMapsSDKApiKey` | No | Update Google Maps API key in AndroidManifest.xml |
| `iosGoogleMapsSDKApiKey` | No | Update Google Maps API key in AppDelegate.swift |

## Code Style

- Formatter page width: 120 characters
- Prefer single quotes
- `avoid_print` is disabled (this is a CLI tool)
- Uses `chalkdart` for colored terminal output (orange for Android operations, cyan for iOS)
- Dart SDK constraint: `^3.5.3`
