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

import 'dart:io';
import 'package:chalkdart/chalkstrings.dart';
import 'package:args/args.dart';
import 'package:glob/glob.dart';
import 'package:glob/list_local_fs.dart';
import 'package:path/path.dart' as path;
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';

enum Options {
  dryrun('dryrun'),
  verbose('verbose'),
  usage('usage'),
  help('help'),
  //OBSOLETE//path('path')
  debug('debug'),
  copy('copy'),
  diff('diff'),
  update('update'),
  yes('yes');

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
      Options.usage.name,
      defaultsTo: false,
      negatable: false,
      help:
          'Prints help on how to use the command. The same as --${Options.usage.name}.',
    )
    ..addFlag(
      Options.help.name,
      defaultsTo: false,
      negatable: false,
      help:
          'Prints help on how to use the command. The same as --${Options.help.name}.',
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
    ..addOption(
      Options.copy.name,
      help: 'Copy brand files from <brand_dir> into the project using master_transmute.yaml',
      valueHelp: 'brand_dir',
    )
    ..addOption(
      Options.diff.name,
      help: 'Diff brand files in <brand_dir> against project files using master_transmute.yaml',
      valueHelp: 'brand_dir',
    )
    ..addOption(
      Options.update.name,
      help: 'Diff and interactively update brand files in <brand_dir> from changed project files',
      valueHelp: 'brand_dir',
    )
    ..addFlag(
      Options.yes.name,
      defaultsTo: false,
      negatable: false,
      help: 'Auto-confirm all prompts (use with --update to skip interactive questions)',
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

  late final ArgResults parsedArgs;
  int verboseDebugLevel = 0;

  try {
    parsedArgs = parser.parse(args);
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
    return;
  }

  if (parsedArgs[Options.verbose.name] != '0') {
    verboseDebugLevel = int.tryParse( parsedArgs[Options.verbose.name], radix:10 ) ?? 0;
  }

  if(verboseDebugLevel>0) {
    print('verbose debug level: $verboseDebugLevel'.brightYellow);
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

  final String? copyDir = parsedArgs[Options.copy.name];
  final String? diffDir = parsedArgs[Options.diff.name];
  final String? updateDir = parsedArgs[Options.update.name];

  final int brandOpCount = (copyDir != null ? 1 : 0) + (diffDir != null ? 1 : 0) + (updateDir != null ? 1 : 0);
  if (brandOpCount > 1) {
    print('Error: --copy, --diff, and --update are mutually exclusive.'.brightRed);
    print(parser.usage);
    return;
  }

  if (copyDir != null) {
    if (!Directory(copyDir).existsSync()) {
      print('Error: Brand directory "$copyDir" does not exist.'.brightRed);
      return;
    }
    FlutterAppTransmuter.copyBrand(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel, brandDir: copyDir);
  } else if (diffDir != null) {
    if (!Directory(diffDir).existsSync()) {
      print('Error: Brand directory "$diffDir" does not exist.'.brightRed);
      return;
    }
    FlutterAppTransmuter.diffBrand(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel, brandDir: diffDir);
  } else if (updateDir != null) {
    if (!Directory(updateDir).existsSync()) {
      print('Error: Brand directory "$updateDir" does not exist.'.brightRed);
      return;
    }
    final bool autoConfirm = parsedArgs[Options.yes.name] == true;
    FlutterAppTransmuter.updateBrand(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel, brandDir: updateDir, autoConfirm: autoConfirm);
  } else {
    FlutterAppTransmuter.run(executeDryRun: executeDryRun, verboseDebugLevel: verboseDebugLevel, args: args);
  }
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