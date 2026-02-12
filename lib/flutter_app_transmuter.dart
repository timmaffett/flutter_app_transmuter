library flutter_app_transmuter;

import 'dart:convert';
import 'dart:io';
import 'package:chalkdart/chalkstrings.dart';
import '/src/transmute/constants.dart';
import '/src/transmute/file_utils.dart';
import '/src/transmute/brand_file_operations.dart';
import '/src/transmute/transmute_operations.dart';

/// [FlutterAppTransmuter]
class FlutterAppTransmuter {

  static bool executingDryRun = false;
  static int verboseDebug = 0;

  /// Start the process to rebrand application with
  /// the provided transmute.json file
  static void run({required bool executeDryRun, required int verboseDebugLevel}) {

    // All writing checks [FlutterAppTransmuter.executingDryRun] flag before writing to disk
    executingDryRun = executeDryRun;
    verboseDebug = verboseDebugLevel;

    // Check if transmute.json file exists
    final bool fileExist = FileUtils.rebrandJSONExist();
    if (!fileExist) {
      print('Error: ${Constants.transmuteDefintionFile} file not found.');
      return;
    }

    try {
      // Parse the JSON
      final String contents = File(Constants.transmuteDefintionFile).readAsStringSync();
      final data = jsonDecode(contents) as Map<String, dynamic>;

      _printBrandBanner(data);

      assert(data[TransmuterKeys.packageName.key] is String,
          Constants.packageNameStringError);
      assert(data[TransmuterKeys.appName.key] is String,
          Constants.appNameStringError);
      assert(data[TransmuterKeys.iosBundleIdentifierName.key]==null || (data[TransmuterKeys.iosBundleIdentifierName.key] is String),
          Constants.iosBundleIdentifierNameKeyStringError);
      assert(data[TransmuterKeys.iosBundleDisplayName.key]==null || (data[TransmuterKeys.iosBundleDisplayName.key] is String),
          Constants.iosBundleDisplayNameKeyStringError);

      // Prepare resolved data map with fallback keys pre-resolved
      // so the operation runner can look up by json_key directly
      final resolvedData = Map<String, dynamic>.from(data);
      // Pre-resolve iosBundleIdentifier fallback to packageName
      if (resolvedData[TransmuterKeys.iosBundleIdentifierName.key] == null) {
        resolvedData[TransmuterKeys.iosBundleIdentifierName.key] = resolvedData[TransmuterKeys.packageName.key];
      }
      // Pre-resolve iosBundleDisplayName fallback to appName
      if (resolvedData[TransmuterKeys.iosBundleDisplayName.key] == null) {
        resolvedData[TransmuterKeys.iosBundleDisplayName.key] = resolvedData[TransmuterKeys.appName.key];
      }

      // Load, merge, and execute operations from YAML
      final operations = TransmuteOperationRunner.loadAndMergeOperations();
      TransmuteOperationRunner.executeAll(operations, resolvedData);
    } catch (ex,stackTrace) {
      print('Error reading or parsing JSON: $ex'.brightRed);
      print(stackTrace);
    }
  }

  static void copyBrand({required bool executeDryRun, required int verboseDebugLevel, required String brandDir}) {
    executingDryRun = executeDryRun;
    verboseDebug = verboseDebugLevel;
    BrandFileOperations.copyBrandFiles(brandDir);
  }

  static void diffBrand({required bool executeDryRun, required int verboseDebugLevel, required String brandDir}) {
    executingDryRun = executeDryRun;
    verboseDebug = verboseDebugLevel;
    BrandFileOperations.diffBrandFiles(brandDir);
  }

  static void updateBrand({required bool executeDryRun, required int verboseDebugLevel, required String brandDir, bool autoConfirm = false}) {
    executingDryRun = executeDryRun;
    verboseDebug = verboseDebugLevel;
    BrandFileOperations.updateBrandFiles(brandDir, autoConfirm: autoConfirm);

    // Run interactive transmute check
    print('');
    print('Checking transmute values against project files...'.brightGreen);
    _runTransmuteCheckInteractive(autoConfirm: autoConfirm);
  }

  static void statusBrand({required bool executeDryRun, required int verboseDebugLevel}) {
    executingDryRun = executeDryRun;
    verboseDebug = verboseDebugLevel;

    if (!FileUtils.rebrandJSONExist()) {
      print('Error: ${Constants.transmuteDefintionFile} file not found.'.brightRed);
      return;
    }

    try {
      final contents = File(Constants.transmuteDefintionFile).readAsStringSync();
      final data = jsonDecode(contents) as Map<String, dynamic>;

      _printBrandBanner(data);

      final brandDir = data[Constants.brandSourceDirectoryKey];

      if (brandDir == null || brandDir is! String || brandDir.isEmpty) {
        print('No "${Constants.brandSourceDirectoryKey}" key found in ${Constants.transmuteDefintionFile}.'.brightYellow);
        print('This key is automatically set when using --copy. You can also add it manually.'.brightYellow);
      } else {
        print('Brand source directory: ${brandDir.brightCyan}'.brightGreen);

        if (!Directory(brandDir).existsSync()) {
          print('Error: Brand directory "$brandDir" does not exist.'.brightRed);
        } else {
          print('Running diff against brand source directory...'.brightGreen);
          print('');
          BrandFileOperations.diffBrandFiles(brandDir);
        }
      }

      // Also run transmute check
      print('');
      print('Checking transmute values against project files...'.brightGreen);
      _runTransmuteCheck(data);
    } catch (ex) {
      print('Error reading ${Constants.transmuteDefintionFile}: $ex'.brightRed);
    }
  }

  static void checkTransmute({required bool executeDryRun, required int verboseDebugLevel}) {
    executingDryRun = executeDryRun;
    verboseDebug = verboseDebugLevel;

    if (!FileUtils.rebrandJSONExist()) {
      print('Error: ${Constants.transmuteDefintionFile} file not found.'.brightRed);
      return;
    }

    try {
      final contents = File(Constants.transmuteDefintionFile).readAsStringSync();
      final data = jsonDecode(contents) as Map<String, dynamic>;

      _printBrandBanner(data);

      print('Checking transmute values against project files...'.brightGreen);
      _runTransmuteCheck(data);
    } catch (ex) {
      print('Error reading ${Constants.transmuteDefintionFile}: $ex'.brightRed);
    }
  }

  static void verifyTransmute({required bool executeDryRun, required int verboseDebugLevel}) {
    executingDryRun = executeDryRun;
    verboseDebug = verboseDebugLevel;

    print('Verifying transmute values against project files...'.brightGreen);
    _runTransmuteCheckInteractive(autoConfirm: false);
  }

  static void _runTransmuteCheck(Map<String, dynamic> data) {
    final resolvedData = _resolveTransmuteData(data);
    final operations = TransmuteOperationRunner.loadAndMergeOperations();
    TransmuteOperationRunner.checkAll(operations, resolvedData);
  }

  static void _runTransmuteCheckInteractive({bool autoConfirm = false}) {
    if (!FileUtils.rebrandJSONExist()) {
      print('Error: ${Constants.transmuteDefintionFile} file not found.'.brightRed);
      return;
    }

    try {
      final contents = File(Constants.transmuteDefintionFile).readAsStringSync();
      final data = jsonDecode(contents) as Map<String, dynamic>;

      _printBrandBanner(data);

      final resolvedData = _resolveTransmuteData(data);
      final operations = TransmuteOperationRunner.loadAndMergeOperations();
      TransmuteOperationRunner.checkAllInteractive(operations, resolvedData, autoConfirm: autoConfirm);
    } catch (ex) {
      print('Error reading ${Constants.transmuteDefintionFile}: $ex'.brightRed);
    }
  }

  static void _printBrandBanner(Map<String, dynamic> data) {
    final brandName = data[Constants.brandNameKey];
    if (brandName != null && brandName is String && brandName.isNotEmpty) {
      printRainbow('  \u{1FA84}\u{2728} Operating on ${Constants.transmuteDefintionFile} for $brandName \u{1F680}\u{1F4AB}  ');
    }
  }

  static Map<String, dynamic> _resolveTransmuteData(Map<String, dynamic> data) {
    final resolvedData = Map<String, dynamic>.from(data);
    if (resolvedData[TransmuterKeys.iosBundleIdentifierName.key] == null) {
      resolvedData[TransmuterKeys.iosBundleIdentifierName.key] = resolvedData[TransmuterKeys.packageName.key];
    }
    if (resolvedData[TransmuterKeys.iosBundleDisplayName.key] == null) {
      resolvedData[TransmuterKeys.iosBundleDisplayName.key] = resolvedData[TransmuterKeys.appName.key];
    }
    return resolvedData;
  }
}
