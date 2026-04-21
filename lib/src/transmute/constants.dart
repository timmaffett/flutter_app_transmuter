
enum TransmuterKeys {
  packageName('packageName'),
  iosBundleIdentifierName('iosBundleIdentifier'),
  appName('appName'),
  iosBundleDisplayName('iosBundleDisplayName'),

  androidGoogleMapsSDKApi('androidGoogleMapsSDKApiKey'),
  iosGoogleMapsSDKApi('iosGoogleMapsSDKApiKey'),
  pubspecVersion('pubspec_version'),
  unknownKey('unknownValue');
 
  const TransmuterKeys(this.jsonValue);

  final String jsonValue;

  String get key => jsonValue;

  @override
  String toString() {
    return jsonValue;
  }

}


class RegExConstants {
  static final packageInMainActivity = RegExp(r'^(package (?:\.|\w)+)',
            caseSensitive: true, multiLine: false);
  static final versionInPubspecYaml = RegExp(r'^version:\s*(.+)$',
        caseSensitive: true, multiLine: true);
}

class Constants {
  static const String transmuteDefintionFile = 'transmute.json';
  static const String transmuteOperationsFile = 'transmute_operations.yaml';
  static const String brandSourceDirectoryKey = 'brand_source_directory';
  static const String brandNameKey = 'brand_name';
  static const String masterTransmuteFile = 'master_transmute.yaml';
  static const String pubspecYamlFile = 'pubspec.yaml';

  /// iOS Specific
  static const String iOSProjectPbxprojFile = 'ios/Runner.xcodeproj/project.pbxproj';
  static const String iOSInfoPlistFile = 'ios/Runner/Info.plist';
  static const String iOSAppDelegateSwiftFile = 'ios/Runner/AppDelegate.swift';
  static const String iosAssetXcassetsFolder = 'ios/Runner/Assets.xcassets/';

  /// Android Specific
  static const String androidAppBuildGradleFile = 'android/app/build.gradle';
  static const String androidAppBuildGradleKTSFile = 'android/app/build.gradle.kts';
  static const String androidManifestXmlFile = 'android/app/src/main/AndroidManifest.xml';
  static const String androidDebugManifestXmlFile = 'android/app/src/debug/AndroidManifest.xml';
  static const String androidProfileManifestXmlFile = 'android/app/src/profile/AndroidManifest.xml';
  static const String androidActivityPath = 'android/app/src/main/';

  static const packageNameStringError = 'Package name must be String';
  static String iosBundleIdentifierNameKeyStringError =
       '${TransmuterKeys.iosBundleIdentifierName} must be MISSING or be String';
  static String iosBundleDisplayNameKeyStringError =
      '${TransmuterKeys.iosBundleDisplayName} must be MISSING or be String';

  static const appNameStringError = 'App Name must be String';
}
