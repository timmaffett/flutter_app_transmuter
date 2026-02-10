
# Flutter App Rebranding Made Easy

**Flutter App Transmuter** automates the process of rebranding a Flutter application by updating the package name, launcher icon, and app name across both Android and iOS platforms. It ensures a smooth transition when you need to rebrand an app for new clients, products, or design overhauls.

## Features

- **Package Name Update**: Automatically updates the package name for both Android and iOS.
- **App Name Update**: Changes the app name that is displayed on the device.
- **Directory Structure Refactoring**: Moves the `MainActivity` to the correct new package directory and deletes the old one.
- **iOS Bundle Identifier Update**: Updates the iOS product bundle identifier (`Runner.xcodeproj`).
- **Launcher Icon Update**: Replaces the app’s launcher icon with a new one, updating for both platforms.  Optional if flutter_launcher_icons package is not being used.


## What It does?
- [x] Updates AndroidManifest.xml, build.gradle and MainActivity in both Java and Kotlin
- [x] Moves MainActivity to the new package directory structure and deletes old one
- [x] Generate & updates old ic_launcher icons with new ones
- [x] Updates Product Bundle Identifier in iOS (Runner.xcodeproj)
- [x] Generate & updates AppIcons and ImageSets


## How It Works

This package uses a configuration file (`transmute.json`) to automatically apply all the necessary changes to your Flutter app. Once the configuration file is set up, the rebranding process runs smoothly without the need for manual edits to each platform-specific file.

### Configuration File (`transmute.json`)

Create a file called `transmute.json` in your Flutter project's root directory. This file should include the following keys with valid values:
- `packageName`: The new package name (e.g., `com.newcompany.newapp`).
- `iosBundleIdentifier` Optional if IOS bundle identifier is different than the `packageName` on Android
- `appName`: The new app name (e.g., `NewApp`).
- `iosBundleDisplayName` Optional if the IOS bundle display name is different than the `appName` for android
- `launcherIconPath`: Path to the new launcher icon (e.g., `assets/icons/new_launcher_icon.png`).  Do not specify if flutter_laucher_icons package is being used.

### Example `transmute.json`:
```json
{
  "packageName": "com.newcompany.newapp",         <<<< This changes the android <manfest package=XXXX > name and also BundleIdentifer unless "iosBundleIdentifier" is specified
  "iosBundleIdentifier": "com.newcompany.newapp.BundleIDForIOS",   <<<< Optional if IOS bundle identifier is different than the "packageName" on Android
  "appName": "NewApp",    <<< This changes the android:label in the AndroidManifest.xml (and BundleDisplayName on IOS if "iosBundleDisplayName" is not specified)
  "iosBundleDisplayName": "NewBundleDisplayName",   <<<<< Optional if the IOS bundle display name is different than the "appName" on android
  "launcherIconPath": "assets/icons/new_launcher_icon.png",   <<< DO NOT specify if flutter_launcher_icons package is being used
}
```


## How to Use?

Add Flutter App Rebrand to your `pubspec.yaml` in `dev_dependencies:` section.
```yaml
dev_dependencies: 
  flutter_app_transmuter: ^1.0.3
```
or run this command
```bash
flutter pub add -d flutter_app_transmuter
```


Update dependencies
```
flutter pub get
```
Run this command to change the package configurations for both the platforms.

```
dart run flutter_app_transmuter:main transmute.json
```

where `transmute.json` is the JSON file that contains the new package name, path to the new launcher icon, and the updated app name.

## Meta

Distributed under the MIT license.

[https://github.com/timmaffett/flutter_app_transmuter](https://github.com/timmaffett/flutter_app_transmuter)

## Contributing

1. Fork the repository: (<https://github.com/timmaffett/flutter_app_transmuter/fork>)
2. Create a new feature branch (`git checkout -b feature/your-feature-name`)
3. Commit your changes with a descriptive message (`git commit -am 'Add new feature: your-feature-name''`)
4. Push to the branch (`git push origin feature/your-feature-name`)
5. Open a Pull Request and submit it for review.

## Acknowledgements

The launcher icon code within FAR was originally extracted from version XYZ of the [flutter_launcher_icon package](https://pub.dev/packages/flutter_launcher_icons).

The basis for this package was originally [https://github.com/sarj33t/flutter_app_rebrand](https://github.com/sarj33t/flutter_app_rebrand)

