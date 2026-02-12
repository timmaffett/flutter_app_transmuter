//  Copyright 2025 Tim Maffett
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      https://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.

import 'dart:convert';
import 'dart:io';
import 'package:chalkdart/chalkstrings.dart';
import 'package:args/args.dart';
import 'package:glob/glob.dart';
import 'package:glob/list_local_fs.dart';
import 'package:path/path.dart' as path;
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:flutter_app_transmuter/src/transmute/file_utils.dart';
import 'package:flutter_app_transmuter/src/transmute/transmute_operations.dart';
import 'package:flutter_app_transmuter/src/transmute/default_transmute_operations.dart';

enum Options {
  transmute('transmute'),
  dryrun('dryrun'),
  verbose('verbose'),
  usage('usage'),
  help('help'),
  //OBSOLETE//path('path')
  debug('debug'),
  copy('copy'),
  diff('diff'),
  update('update'),
  switchBrand('switch'),
  status('status'),
  check('check'),
  verify('verify'),
  yes('yes'),
  showDefaultYaml('showdefaultyaml'),
  writeDefaultYaml('writedefaultyaml');

  const Options(this.name);

  final String name;
}

bool executeDryRun = false;
bool debugScripts = false;
String rootDir = './bin';

//NOTAPPLICABLE//// We need to get to the files of the LATEST material_symbols_icons package that is in the pub cache
//NOTAPPLICABLE//String getRootPathsToLatestInstalledPackage() {
//NOTAPPLICABLE//  final pathToScript = Platform.script.toFilePath();
//NOTAPPLICABLE//  rootDir = path.dirname(pathToScript);
//NOTAPPLICABLE//
//NOTAPPLICABLE//  // following for testing
//NOTAPPLICABLE//  if (!rootDir.contains('global_packages')) {
//NOTAPPLICABLE//    rootDir =
//NOTAPPLICABLE//        r"C:\Users\Tim\AppData\Local\Pub\Cache\global_packages\dart_frog_cli\bin";
//NOTAPPLICABLE//  }
//NOTAPPLICABLE//
//NOTAPPLICABLE//  String pubDevPackagesDir =
//NOTAPPLICABLE//      path.join(rootDir, '..', '..', '..', 'hosted', 'pub.dev');
//NOTAPPLICABLE//
//NOTAPPLICABLE//  if (debugScripts) print('pubDevPackagesDir=$pubDevPackagesDir');
//NOTAPPLICABLE//
//NOTAPPLICABLE//  final packageDirs =
//NOTAPPLICABLE//      Glob('material_symbols_icons-*', caseSensitive: false, recursive: false);
//NOTAPPLICABLE//  final baseToChop = 'material_symbols_icons-';
//NOTAPPLICABLE//
//NOTAPPLICABLE//  final listFSE = packageDirs.listSync(root: pubDevPackagesDir);
//NOTAPPLICABLE//  String highestVersion = '4.2600.0';
//NOTAPPLICABLE//  String latestPackageDir = '';
//NOTAPPLICABLE//
//NOTAPPLICABLE//  for (final fse in listFSE) {
//NOTAPPLICABLE//    String dirName = fse.basename;
//NOTAPPLICABLE//    String version = dirName.substring(baseToChop.length);
//NOTAPPLICABLE//    if (debugScripts) print('Found directory $dirName version=$version');
//NOTAPPLICABLE//    if (version.length >= 8) {
//NOTAPPLICABLE//      if (version.compareTo(highestVersion) > 0) {
//NOTAPPLICABLE//        highestVersion = version;
//NOTAPPLICABLE//        latestPackageDir = fse.path;
//NOTAPPLICABLE//      }
//NOTAPPLICABLE//    }
//NOTAPPLICABLE//  }
//NOTAPPLICABLE//  if (debugScripts) print('Highest Version = $highestVersion');
//NOTAPPLICABLE//  if (debugScripts) print('latestPackageDir = $latestPackageDir');
//NOTAPPLICABLE//  return path.join(latestPackageDir, 'bin');
//NOTAPPLICABLE//}

void main(List<String> args) async {
  final parser = ArgParser()
    ..addFlag(
      Options.status.name,
      defaultsTo: false,
      negatable: false,
      help: 'Diff brand files and check transmute values against project files',
    )
    ..addFlag(
      Options.check.name,
      defaultsTo: false,
      negatable: false,
      help: 'Check that project files match transmute.json values (no files changed)',
    )
    ..addFlag(
      Options.verify.name,
      defaultsTo: false,
      negatable: false,
      help: 'Check transmute values and interactively resolve mismatches',
    )
    ..addFlag(
      Options.transmute.name,
      defaultsTo: false,
      negatable: false,
      help: 'Run transmute operations using transmute.json (and optional transmute_operations.yaml)',
    )
    ..addOption(
      Options.copy.name,
      help: 'Copy brand files from <brand_dir> into the project using master_transmute.yaml',
      valueHelp: 'brand_dir',
    )
    ..addOption(
      Options.diff.name,
      help: 'Diff brand files against project files (uses brand_source_directory from transmute.json if no dir given)',
      valueHelp: 'brand_dir',
      defaultsTo: '',
    )
    ..addOption(
      Options.update.name,
      help: 'Diff and interactively update brand files from changed project files (uses brand_source_directory from transmute.json if no dir given)',
      valueHelp: 'brand_dir',
      defaultsTo: '',
    )
    ..addOption(
      Options.switchBrand.name,
      help: 'Update current brand files from project, then switch to <new_brand_dir> (requires brand_source_directory in transmute.json)',
      valueHelp: 'new_brand_dir',
    )
    ..addFlag(
      Options.showDefaultYaml.name,
      defaultsTo: false,
      negatable: false,
      help: 'Print the default transmute operations YAML to stdout',
    )
    ..addOption(
      Options.writeDefaultYaml.name,
      help: 'Write default transmute operations YAML to file (default: ${Constants.transmuteOperationsFile})',
      valueHelp: 'filename',
      defaultsTo: '',
    )
    ..addFlag(
      Options.yes.name,
      defaultsTo: false,
      negatable: false,
      help: 'Auto-confirm all prompts (use with --update to skip interactive questions)',
    )
    ..addFlag(
      Options.dryrun.name,
      defaultsTo: false,
      negatable: false,
      help:
          'Execute a "dry run" - No files are changed/written to disk.',
    )
    ..addFlag(
      Options.debug.name,
      defaultsTo: false,
      negatable: false,
      help: 'Debug flag (defaults to --verbose=1)',
    )
    ..addOption(
      Options.verbose.name,
      defaultsTo: '0',
      help: 'Verbose Debug Level (>1 sets --debug mode)',
    )
    ..addFlag(
      Options.help.name,
      defaultsTo: false,
      negatable: false,
      help:
          'Prints help on how to use the command. The same as --${Options.usage.name}.',
    )
    ..addFlag(
      Options.usage.name,
      defaultsTo: false,
      negatable: false,
      help:
          'Prints help on how to use the command. The same as --${Options.help.name}.',
    )
//UNUSED FLAGFS//    ..addFlag(
//UNUSED FLAGFS//      Options.global.name,
//UNUSED FLAGFS//      defaultsTo: false,
//UNUSED FLAGFS//      negatable: false,
//UNUSED FLAGFS//      help:
//UNUSED FLAGFS//          'MacOS specific flag to specify installing the fonts globally in /Library/Fonts instead of ~/Library/Fonts .',
//UNUSED FLAGFS//    )
//UNUSED FLAGFS//    ..addFlag(
//UNUSED FLAGFS//      Options.usefontbook.name,
//UNUSED FLAGFS//      defaultsTo: false,
//UNUSED FLAGFS//      negatable: false,
//UNUSED FLAGFS//      help:
//UNUSED FLAGFS//          'MacOS specific flag to additionally validate fonts using FontBook.',
//UNUSED FLAGFS//    )
//UNUSED FLAGFS//    ..addFlag(
//UNUSED FLAGFS//      Options.uninstall.name,
//UNUSED FLAGFS//      defaultsTo: false,
//UNUSED FLAGFS//      negatable: false,
//UNUSED FLAGFS//      help: 'Uninstall the material symbols icons fonts.',
//UNUSED FLAGFS//    )
    ;

  // Extract +flag and -exclude arguments (e.g. +flutterfire, -clean) before arg parsing
  final enabledFlags = <String>{};
  final excludedSteps = <String>{};
  final argsWithoutFlags = <String>[];
  for (final arg in args) {
    if (arg.startsWith('+')) {
      enabledFlags.add(arg.substring(1));
    } else if (arg.startsWith('-') && !arg.startsWith('--') && arg.length > 1) {
      excludedSteps.add(arg.substring(1));
    } else {
      argsWithoutFlags.add(arg);
    }
  }

  // Preprocess args: allow --diff and --update to be used without a value
  // by inserting an empty value when no argument follows
  final processedArgs = _preprocessOptionalValueArgs(argsWithoutFlags, ['--diff', '--update', '--writedefaultyaml']);

  late final ArgResults parsedArgs;
  int verboseDebugLevel = 0;

  try {
    parsedArgs = parser.parse(processedArgs);
  } on FormatException catch (e) {
    print(e.message);
    print(parser.usage);
    return;
  }

  if (parsedArgs[Options.debug.name] == true) {
    debugScripts = true;
    verboseDebugLevel = 1;
  }
  if (parsedArgs[Options.dryrun.name] == true) {
    executeDryRun = true;
  }
  //NOTUSED//if (parsedArgs[Options.usefontbook.name] == true) {
  //NOTUSED//  macOSUseFontBook = true;
  //NOTUSED//}

  if (parsedArgs[Options.usage.name] == true ||
      parsedArgs[Options.help.name] == true) {
    print(parser.usage);
    print('');
    print('Post-switch flags (used with --switch):');
    print('  +flutterfire   Run flutterfire configure after switch');
    print('  +build         Run platform build (apk/ipa) after switch');
    print('  -stepname      Exclude a post-switch step (e.g. -clean, -pub_get)');
    return;
  }

  // Handle --showdefaultyaml (utility command, exits immediately)
  if (parsedArgs[Options.showDefaultYaml.name] == true) {
    print(defaultTransmuteOperationsYaml);
    return;
  }

  // Handle --writedefaultyaml (utility command, exits immediately)
  if (parsedArgs.wasParsed(Options.writeDefaultYaml.name)) {
    final String filenameArg = parsedArgs[Options.writeDefaultYaml.name] as String;
    final String filename = filenameArg.isEmpty ? Constants.transmuteOperationsFile : filenameArg;
    final file = File(filename);
    if (file.existsSync()) {
      stdout.write('File "$filename" already exists. Overwrite? (y/N): '.brightYellow);
      final response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
      if (response != 'y' && response != 'yes') {
        print('Aborted.'.brightYellow);
        return;
      }
    }
    file.writeAsStringSync(defaultTransmuteOperationsYaml);
    print('Default operations YAML written to "$filename".'.brightGreen);
    return;
  }

  if (parsedArgs[Options.verbose.name] != '0') {
    verboseDebugLevel = int.tryParse( parsedArgs[Options.verbose.name], radix:10 ) ?? 0;
  }

  if(verboseDebugLevel>0) {
    print('verbose debug level: $verboseDebugLevel'.brightYellow);
  }

  if (enabledFlags.isNotEmpty) {
    print('Enabled flags: ${enabledFlags.map((f) => '+$f').join(', ')}'.brightCyan);
  }
  if (excludedSteps.isNotEmpty) {
    print('Excluded steps: ${excludedSteps.map((s) => '-$s').join(', ')}'.brightYellow);
  }

  //NOTUSED//rootDir = getRootPathsToLatestInstalledPackage();
  //NOTUSED//
  //NOTUSED//if (parsedArgs[Options.uninstall.name] == true) {
  //NOTUSED//  print(chalk.yellowBright('Uninstalling Material Symbols Icons fonts...'));
  //NOTUSED//  uninstallMaterialSymbolsIconsFonts();
  //NOTUSED//} else {
  //NOTUSED//  print(chalk.greenBright('Installing Material Symbols Icons fonts...'));
  //NOTUSED//  installMaterialSymbolsIconsFonts();
  //NOTUSED//}

  final bool doTransmute = parsedArgs[Options.transmute.name] == true;
  final bool doStatus = parsedArgs[Options.status.name] == true;
  final bool doCheck = parsedArgs[Options.check.name] == true;
  final bool doVerify = parsedArgs[Options.verify.name] == true;
  final String? copyDir = parsedArgs[Options.copy.name];
  final bool doDiff = parsedArgs.wasParsed(Options.diff.name);
  final String diffDirArg = parsedArgs[Options.diff.name] as String;
  final bool doUpdate = parsedArgs.wasParsed(Options.update.name);
  final String updateDirArg = parsedArgs[Options.update.name] as String;
  final String? switchDir = parsedArgs[Options.switchBrand.name];

  final int opCount = (doTransmute ? 1 : 0) + (doStatus ? 1 : 0) + (doCheck ? 1 : 0) + (doVerify ? 1 : 0) + (copyDir != null ? 1 : 0) + (doDiff ? 1 : 0) + (doUpdate ? 1 : 0) + (switchDir != null ? 1 : 0);
  if (opCount > 1) {
    print('Error: --status, --check, --verify, --transmute, --copy, --diff, --update, and --switch are mutually exclusive.'.brightRed);
    print(parser.usage);
    return;
  }

  if (opCount == 0) {
    print('Flutter App Transmuter - No operation specified.\n'.brightYellow);
    print(parser.usage);
    return;
  }

  // Print brand banner at the very start of any operation
  final transmuteFile = File(Constants.transmuteDefintionFile);
  if (transmuteFile.existsSync()) {
    try {
      final data = jsonDecode(transmuteFile.readAsStringSync()) as Map<String, dynamic>;
      final brandName = data[Constants.brandNameKey];
      if (brandName != null && brandName is String && brandName.isNotEmpty) {
        printRainbow('  \u{1FA84}\u{2728} Operating on ${Constants.transmuteDefintionFile} for $brandName \u{1F680}\u{1F4AB}  ');
        print('');
      }
    } catch (_) {
      // Ignore errors reading transmute.json for the banner
    }
  }

  if (doTransmute) {
    FlutterAppTransmuter.run(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel);
  } else if (doStatus) {
    FlutterAppTransmuter.statusBrand(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel);
  } else if (doCheck) {
    FlutterAppTransmuter.checkTransmute(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel);
  } else if (doVerify) {
    FlutterAppTransmuter.verifyTransmute(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel);
  } else if (copyDir != null) {
    if (!Directory(copyDir).existsSync()) {
      print('Error: Brand directory "$copyDir" does not exist.'.brightRed);
      return;
    }
    FlutterAppTransmuter.copyBrand(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel, brandDir: copyDir);
  } else if (doDiff) {
    final diffDir = _resolveBrandDir(diffDirArg);
    if (diffDir == null) return;
    FlutterAppTransmuter.diffBrand(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel, brandDir: diffDir);
  } else if (doUpdate) {
    final updateDir = _resolveBrandDir(updateDirArg);
    if (updateDir == null) return;
    final bool autoConfirm = parsedArgs[Options.yes.name] == true;
    FlutterAppTransmuter.updateBrand(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel, brandDir: updateDir, autoConfirm: autoConfirm);
  } else if (switchDir != null) {
    if (!Directory(switchDir).existsSync()) {
      print('Error: New brand directory "$switchDir" does not exist.'.brightRed);
      return;
    }

    // Load and validate post-switch operations before starting any work
    final postOps = TransmuteOperationRunner.loadAndMergePostSwitchOperations();
    final validationError = TransmuteOperationRunner.validatePostSwitchOperations(postOps);
    if (validationError != null) {
      print('Error in post_switch_operations: $validationError'.brightRed);
      return;
    }

    final bool autoConfirm = parsedArgs[Options.yes.name] == true;
    FlutterAppTransmuter.switchBrand(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel, newBrandDir: switchDir, autoConfirm: autoConfirm, enabledFlags: enabledFlags, excludedSteps: excludedSteps, postSwitchOperations: postOps);
  }
}

/// Allows certain options to be used as bare flags (no value).
/// If --flag appears without a following value, inserts --flag= so the
/// parser sees it as an option with an empty string value.
List<String> _preprocessOptionalValueArgs(List<String> args, List<String> optionNames) {
  final result = <String>[];
  for (int i = 0; i < args.length; i++) {
    final arg = args[i];
    if (optionNames.contains(arg) && !arg.contains('=')) {
      // Check if next arg is a value (not a flag)
      if (i + 1 < args.length && !args[i + 1].startsWith('-')) {
        result.add(arg);
      } else {
        result.add('$arg=');
      }
    } else {
      result.add(arg);
    }
  }
  return result;
}

/// Resolves the brand directory from the command-line argument or from
/// the brand_source_directory key in transmute.json. Returns null on error.
String? _resolveBrandDir(String argValue) {
  String brandDir = argValue;

  if (brandDir.isEmpty) {
    // Try to read from transmute.json
    final transmuteFile = File(Constants.transmuteDefintionFile);
    if (!transmuteFile.existsSync()) {
      print('Error: No brand directory specified and ${Constants.transmuteDefintionFile} not found.'.brightRed);
      return null;
    }
    try {
      final data = jsonDecode(transmuteFile.readAsStringSync()) as Map<String, dynamic>;
      final saved = data[Constants.brandSourceDirectoryKey];
      if (saved == null || saved is! String || saved.isEmpty) {
        print('Error: No brand directory specified and no "${Constants.brandSourceDirectoryKey}" key found in ${Constants.transmuteDefintionFile}.'.brightRed);
        print('Use --copy first to set it, or provide a directory: --diff=<brand_dir>'.brightYellow);
        return null;
      }
      brandDir = saved;
      print('Using brand directory from ${Constants.transmuteDefintionFile}: ${brandDir.brightCyan}'.brightGreen);
    } catch (ex) {
      print('Error reading ${Constants.transmuteDefintionFile}: $ex'.brightRed);
      return null;
    }
  } else {
    // Brand dir was explicitly provided — check against brand_source_directory in transmute.json
    if (!_checkBrandDirConsistency(brandDir)) return null;
  }

  if (!Directory(brandDir).existsSync()) {
    print('Error: Brand directory "$brandDir" does not exist.'.brightRed);
    return null;
  }

  return brandDir;
}

/// Checks if the command-line brand directory matches the brand_source_directory
/// in transmute.json. Returns false if the user chooses not to continue on mismatch.
bool _checkBrandDirConsistency(String cmdBrandDir) {
  final transmuteFile = File(Constants.transmuteDefintionFile);
  if (!transmuteFile.existsSync()) return true;

  try {
    final data = jsonDecode(transmuteFile.readAsStringSync()) as Map<String, dynamic>;
    final saved = data[Constants.brandSourceDirectoryKey];

    if (saved == null || saved is! String || saved.isEmpty) {
      print('Warning: No "${Constants.brandSourceDirectoryKey}" key found in ${Constants.transmuteDefintionFile}.'.brightYellow);
      return true;
    }

    // Normalize paths for comparison
    final normalizedCmd = path.normalize(cmdBrandDir);
    final normalizedSaved = path.normalize(saved);

    if (normalizedCmd == normalizedSaved) {
      print('Brand directory matches ${Constants.brandSourceDirectoryKey} in ${Constants.transmuteDefintionFile}.'.brightGreen);
    } else {
      print('Mismatch: command-line brand directory does not match ${Constants.brandSourceDirectoryKey} in ${Constants.transmuteDefintionFile}.'.brightRed);
      print('  command-line: ${cmdBrandDir.brightCyan}'.brightRed);
      print('  transmute.json: ${saved.toString().brightCyan}'.brightRed);
      stdout.write('Continue anyway? (y/N): '.brightYellow);
      final response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
      if (response != 'y' && response != 'yes') {
        print('Aborted.'.brightYellow);
        return false;
      }
    }
  } catch (_) {
    // Ignore errors reading transmute.json for this check
  }

  return true;
}

/*
void installMaterialSymbolsIconsFonts() {
  print(chalk.cyanBright('running on ${Platform.operatingSystem}'));
  switch (Platform.operatingSystem) {
    case 'windows':
      installMaterialSymbolsIconsFontWindows();
      break;
    case 'macos':
      installMaterialSymbolsIconsFontMacOS();
      break;
    case 'linux':
      installMaterialSymbolsIconsFontLinux();
      break;
    default:
      print(chalk.brightRedBright(
          'Unsupported operating system: ${Platform.operatingSystem}'));
  }
}

void uninstallMaterialSymbolsIconsFonts() {
  print(chalk.cyanBright('running on ${Platform.operatingSystem}'));
  switch (Platform.operatingSystem) {
    case 'windows':
      uninstallMaterialSymbolsIconsFontWindows();
      break;
    case 'macos':
      print(chalk.brightRedBright(
          'Uninstalling Material Symbols Icons fonts is not supported on MacOS yet.'));
      //uninstallMaterialSymbolsIconsFontMacOS();
      break;
    case 'linux':
      print(chalk.brightRedBright(
          'Uninstalling Material Symbols Icons fonts is not supported on Linux yet.'));
      //uninstallMaterialSymbolsIconsFontLinux();
      break;
    default:
      print(chalk.brightRedBright(
          'Unsupported operating system: ${Platform.operatingSystem}'));
  }
}

//Windows specific functions
void installMaterialSymbolsIconsFontWindows() {
  print(chalk.cyanBright(
      'running powershell scripts to install Material Symbols Icons fonts...'));
  runPowerShellInstallFont(r'..\lib\fonts\MaterialSymbolsOutlined.ttf');
  runPowerShellInstallFont(r'..\lib\fonts\MaterialSymbolsRounded.ttf');
  runPowerShellInstallFont(r'..\lib\fonts\MaterialSymbolsSharp.ttf');
}

void uninstallMaterialSymbolsIconsFontWindows() {
  print(chalk.cyanBright(
      'running powershell scripts to UNINSTALL Material Symbols Icons fonts...'));
  runPowerShellUninstallFont(r'..\lib\fonts\MaterialSymbolsOutlined.ttf');
  runPowerShellUninstallFont(r'..\lib\fonts\MaterialSymbolsRounded.ttf');
  runPowerShellUninstallFont(r'..\lib\fonts\MaterialSymbolsSharp.ttf');
}

void runPowerShellInstallFont(String fontNameWithRelativePath) {
  var result = runPowerShellScriptOneArg(
      r'.\Install-Font.ps1', fontNameWithRelativePath);
  final fontname =
      path.basename(path.withoutExtension(fontNameWithRelativePath));
  final numberFacesInstalled = int.tryParse(result);
  if (numberFacesInstalled != null && numberFacesInstalled > 0) {
    print(chalk.greenBright(
        '$fontname font was successfully installed ($numberFacesInstalled faces installed).'));
  } else {
    print(chalk.brightRedBright(
        '$fontname font was not installed likely because the font $fontNameWithRelativePath was not found.'));
  }
}

void runPowerShellUninstallFont(String fontNameWithRelativePath) {
  var result = runPowerShellScriptOneArg(
      r'.\Uninstall-Font.ps1', fontNameWithRelativePath);
  final fontname =
      path.basename(path.withoutExtension(fontNameWithRelativePath));
  if (result.toLowerCase().contains('True'.toLowerCase())) {
    print(chalk.greenBright('$fontname font was successfully uninstalled.'));
  } else {
    print(chalk.brightRedBright(
        '$fontname font was not uninstalled because it was not currently installed.'));
  }
}

String runPowerShellScriptOneArg(String scriptPath, String argumentToScript) {
  return runPowerShellScript(scriptPath, [argumentToScript]);
}

String runPowerShellScript(String scriptPath, List<String> argumentsToScript) {
  final processResult = Process.runSync('Powershell.exe',
      ['-executionpolicy', 'bypass', '-File', scriptPath, ...argumentsToScript],
      workingDirectory: rootDir //path.join(Directory.current.path, 'bin')
      );
  if (debugScripts) {
    print(chalk.yellowBright('Executing $scriptPath with $argumentsToScript'));
    print(chalk.brightRedBright(processResult.stderr as String));
    print(chalk.blueBright(processResult.stdout as String));
  }
  return processResult.stdout as String;
}

void runShellInstallFontsScriptLinux() {
  String scriptName = 'install-fonts.sh';
  if (macOSUseFontBook) {
    scriptName = 'install-fonts-withFontBook.sh';
  }
  final scriptPath = path.join(
      rootDir, scriptName); //path.join('..', '..', 'bin', scriptName);
  final fontWorkingDir = path.join(rootDir, '..', 'lib', 'fonts');
  //print(chalk.brightRed('scriptPath=$scriptPath  fontWorkingDir=$fontWorkingDir'));
  final processResult =
      Process.runSync('sh', [scriptPath], workingDirectory: fontWorkingDir);
  if (debugScripts) {
    print(chalk.yellowBright('Executed $scriptName'));
    print(chalk.brightRedBright(processResult.stderr as String));
    print(chalk.blueBright(processResult.stdout as String));
  }
}

void runShellInstallFontsScriptGloballyOnMacOS() {
  String scriptName = 'install-fonts-macAlt.sh';
  if (macOSUseFontBook) {
    scriptName = 'install-fonts-macAlt-withFontBook.sh';
  }
  final scriptPath = path.join(
      rootDir, scriptName); //path.join('..', '..', 'bin', scriptName);
  final fontWorkingDir = path.join(rootDir, '..', 'lib', 'fonts');
  //print(chalk.brightRed('scriptPath=$scriptPath  fontWorkingDir=$fontWorkingDir'));
  final processResult =
      Process.runSync('sh', [scriptPath], workingDirectory: fontWorkingDir);
  if (debugScripts) {
    print(chalk.yellowBright('Executed $scriptName'));
    print(chalk.brightRedBright(processResult.stderr as String));
    print(chalk.blueBright(processResult.stdout as String));
  }
}

//MacOS specific functions
void installMaterialSymbolsIconsFontMacOS() {
  if (globalMacOSInstall) {
    print(chalk.greenBright(
        'Install Material Symbols Icons fonts globally${(macOSUseFontBook) ? ' and validating with FontBook.' : '.'}'));
    runShellInstallFontsScriptGloballyOnMacOS();
  } else {
    print(chalk.greenBright(
        'Install Material Symbols Icons fonts for current user${(macOSUseFontBook) ? ' and validating with FontBook.' : '.'}...'));
    runShellInstallFontsScriptLinux();
  }
}

void uninstallMaterialSymbolsIconsFontMacOS() {
  print(chalk.brightRedBright(
      'UNINSTALLING Material Symbols Icons fonts not supported on MacOS.'));
}

//Linux specific functions
void installMaterialSymbolsIconsFontLinux() {
  print(chalk.greenBright(
      'Install Material Symbols Icons fonts for current user using Linux script...'));
  runShellInstallFontsScriptLinux();
}

void uninstallMaterialSymbolsIconsFontLinux() {
  print(chalk.brightRedBright(
      'UNINSTALLING Material Symbols Icons fonts not supported on Linux.'));
}



*/