library flutter_app_transmuter;

import 'dart:convert';
import 'dart:io';
import 'package:chalkdart/chalkstrings.dart';
import '/src/transmute/android_transmute.dart';
import '/src/transmute/ios_transmute.dart';
import '/src/transmute/constants.dart';
import '/src/transmute/file_utils.dart';

/// [FlutterAppTransmuter]
class FlutterAppTransmuter {

  static bool executingDryRun = false;
  static int verboseDebug = 0;

  /// Start the process to rebrand application with
  /// the provided transmute.json file
  static void run({required bool executeDryRun, required int verboseDebugLevel, required List<String> args}) {    // Check if there are no arguments passed

    // All writing checks [FlutterAppTransmuter.executingDryRun] flag before writing to disk
    executingDryRun = executeDryRun;
    verboseDebug = verboseDebugLevel;

    if (args.isEmpty) {
      print('No arguments passed.');
      return;
    }

    // Check if transmute.json file exists
    final bool fileExist = FileUtils.rebrandJSONExist();
    if (!fileExist) {
      print('Error: ${Constants.transmuteDefintionFile} file not found.');
      return;
    }

    try {
      // Parse the JSON
      final String contents = File(Constants.transmuteDefintionFile).readAsStringSync();
      final data = jsonDecode(contents);

      assert(data[TransmuterKeys.packageName.key] is String,
          Constants.packageNameStringError);
      assert(data[TransmuterKeys.appName.key] is String,
          Constants.appNameStringError);
      assert(data[TransmuterKeys.iosBundleIdentifierName.key]==null || (data[TransmuterKeys.iosBundleIdentifierName.key] is String),
          Constants.iosBundleIdentifierNameKeyStringError);
      assert(data[TransmuterKeys.iosBundleDisplayName.key]==null || (data[TransmuterKeys.iosBundleDisplayName.key] is String),
          Constants.iosBundleDisplayNameKeyStringError);

      // Extract fields from JSON
      final String newPackageName = data[TransmuterKeys.packageName.key];
      final String newIOSBundleIdentifier = data[TransmuterKeys.iosBundleIdentifierName.key] ?? newPackageName;
      final String newAppName = data[TransmuterKeys.appName.key];
      final String iosBundleDisplayName = data[TransmuterKeys.iosBundleDisplayName.key] ?? newAppName;

      final String? androidGoogleMapsSDKApi = data[TransmuterKeys.androidGoogleMapsSDKApi.key];
      final String? iosGoogleMapsSDKApi = data[TransmuterKeys.iosGoogleMapsSDKApi.key];

      if (newPackageName.isNotEmpty) {
        AndroidTransmuter.process(newPackageName);
        IOSTransmute.process(newIOSBundleIdentifier);
      }
      if (newAppName.isNotEmpty) {
        AndroidTransmuter.updateAppName(newAppName);
        IOSTransmute.overwriteInfoPlist(iosBundleDisplayName);
      }
      if(androidGoogleMapsSDKApi!=null && androidGoogleMapsSDKApi.isNotEmpty) {
        AndroidTransmuter.updateGoogleMapsSDKApiKey(androidGoogleMapsSDKApi);
      }
      if(iosGoogleMapsSDKApi!=null && iosGoogleMapsSDKApi.isNotEmpty) {
        IOSTransmute.updateGoogleMapsSDKApiKey(iosGoogleMapsSDKApi);
      }
    } catch (ex,stackTrace) {
      print('Error reading or parsing JSON: $ex'.brightRed);
      print(stackTrace);
    }
  }
}
