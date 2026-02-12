const String defaultTransmuteOperationsYaml = r'''
operations:
  - id: build_gradle_application_id
    description: "applicationId in build.gradle"
    type: regex_replace
    platform: android
    file: "android/app/build.gradle"
    optional: true
    json_key: packageName
    regex: 'applicationId\s*=?\s*"(.*)"'
    replacement: 'applicationId = "$value"'

  - id: build_gradle_kts_namespace
    description: "namespace in build.gradle.kts"
    type: regex_replace
    platform: android
    file: "android/app/build.gradle.kts"
    optional: true
    json_key: packageName
    regex: 'namespace\s*=?\s*"(.*)"'
    replacement: 'namespace = "$value"'

  - id: build_gradle_kts_application_id
    description: "applicationId in build.gradle.kts"
    type: regex_replace
    platform: android
    file: "android/app/build.gradle.kts"
    optional: true
    json_key: packageName
    regex: 'applicationId\s*=?\s*"(.*)"'
    replacement: 'applicationId = "$value"'

  - id: main_manifest_package
    description: "package in main AndroidManifest.xml"
    type: regex_replace
    platform: android
    file: "android/app/src/main/AndroidManifest.xml"
    json_key: packageName
    regex: 'package\s*=\s*"([^"]*(\\"[^"]*)*)"'
    replacement: 'package="$value"'

  - id: debug_manifest_package
    description: "package in debug AndroidManifest.xml"
    type: regex_replace
    platform: android
    file: "android/app/src/debug/AndroidManifest.xml"
    json_key: packageName
    regex: 'package\s*=\s*"([^"]*(\\"[^"]*)*)"'
    replacement: 'package="$value"'

  - id: profile_manifest_package
    description: "package in profile AndroidManifest.xml"
    type: regex_replace
    platform: android
    file: "android/app/src/profile/AndroidManifest.xml"
    json_key: packageName
    regex: 'package\s*=\s*"([^"]*(\\"[^"]*)*)"'
    replacement: 'package="$value"'

  - id: move_main_activity
    description: "Move MainActivity to new package directory"
    type: move_activity
    platform: android
    json_key: packageName

  - id: android_label
    description: "android:label in AndroidManifest.xml"
    type: regex_replace
    platform: android
    file: "android/app/src/main/AndroidManifest.xml"
    json_key: appName
    regex: 'android:label\s*=\s*"([^"]*(\\"[^"]*)*)"'
    replacement: 'android:label="$value"'

  - id: ios_bundle_identifier
    description: "Bundle identifier in project.pbxproj"
    type: extract_and_replace
    platform: ios
    file: "ios/Runner.xcodeproj/project.pbxproj"
    json_key: iosBundleIdentifier
    fallback_key: packageName
    regex: 'PRODUCT_BUNDLE_IDENTIFIER\s*=?\s*(.*);'
    replacement: '$value'

  - id: ios_display_name_info_plist
    description: "CFBundleDisplayName in Info.plist"
    type: regex_replace
    platform: ios
    file: "ios/Runner/Info.plist"
    json_key: iosBundleDisplayName
    fallback_key: appName
    regex: '<key>CFBundleDisplayName</key>\s*<string>(.*?)</string>'
    replacement: "<key>CFBundleDisplayName</key>\n\t<string>$value</string>"

  - id: ios_display_name_pbxproj
    description: "CFBundleDisplayName in project.pbxproj"
    type: extract_and_replace
    platform: ios
    file: "ios/Runner.xcodeproj/project.pbxproj"
    json_key: iosBundleDisplayName
    fallback_key: appName
    regex: 'INFOPLIST_KEY_CFBundleDisplayName\s*=?\s*(.*);'
    replacement: '"$value"'

  - id: android_google_maps_api_key
    description: "Google Maps API key in AndroidManifest.xml"
    type: regex_replace
    platform: android
    file: "android/app/src/main/AndroidManifest.xml"
    json_key: androidGoogleMapsSDKApiKey
    multiline: true
    regex: 'android:name\s*=\s*"com.google.android.geo.API_KEY"\s*android:value="([^"]*(\\"[^"]*)*)"'
    replacement: 'android:name="com.google.android.geo.API_KEY" android:value="$value"'

  - id: ios_google_maps_api_key
    description: "Google Maps API key in AppDelegate.swift"
    type: regex_replace
    platform: ios
    file: "ios/Runner/AppDelegate.swift"
    json_key: iosGoogleMapsSDKApiKey
    multiline: true
    regex: 'GMSServices\.provideAPIKey\("([^"]+)"\)'
    replacement: 'GMSServices.provideAPIKey("$value")'

  - id: pubspec_version
    description: "version in pubspec.yaml"
    type: regex_replace
    platform: both
    file: "pubspec.yaml"
    json_key: pubspec_version
    multiline: true
    regex: '^version:\s*(.+)$'
    replacement: 'version: $value'

post_switch_operations:
  transmute_command: "--transmute"
  launcher_icons: "dart run flutter_launcher_icons"
  native_splash: "dart run flutter_native_splash:create"
  clean: "flutter clean"
  ios_remove_derived_data: "rm -rf ~/Library/Developer/Xcode/DerivedData/Runner-*"
  ios_xcode_reminder: "echo 'XCODE: Be sure to close Xcode, reopen Runner.xcworkspace, CLEAN build folder, and verify TEAM in Signing & Capabilities'"
  pub_get: "flutter pub get"
  requireflag_flutterfire: "flutterfire configure --yes --overwrite-firebase-options"
  android_requireflag_build: "flutter build apk --target-platform android-arm64"
  ios_requireflag_build: "flutter build ipa"
''';
