import 'dart:convert';
import 'dart:io';
import 'package:chalkdart/chalkstrings.dart';
import 'package:path/path.dart' as path;
import 'package:yaml/yaml.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:flutter_app_transmuter/src/transmute/file_utils.dart';

class BrandFileMapping {
  final String source;
  final String destination;

  const BrandFileMapping({required this.source, required this.destination});

  @override
  String toString() => '$source -> $destination';
}

class BrandFileOperations {
  static List<BrandFileMapping> _loadMappings() {
    final yamlPath = Constants.masterTransmuteFile;
    if (!FileUtils.fileExists(yamlPath)) {
      print('Error: ${Constants.masterTransmuteFile} file not found.'.brightRed);
      return [];
    }

    final contents = FileUtils.readFileAsString(yamlPath);
    if (contents == null || contents.isEmpty) {
      print('Error: ${Constants.masterTransmuteFile} is empty.'.brightRed);
      return [];
    }

    final yaml = loadYaml(contents);
    final List<BrandFileMapping> mappings = [];

    // Parse file_mappings section (source filename differs from destination)
    // Supports both singular 'destination' (string) and plural 'destinations' (list)
    if (yaml['file_mappings'] != null) {
      final fileMappings = yaml['file_mappings'] as YamlList;
      for (final mapping in fileMappings) {
        final source = mapping['source'] as String;
        if (mapping['destinations'] != null) {
          final destinations = mapping['destinations'] as YamlList;
          for (final dest in destinations) {
            mappings.add(BrandFileMapping(source: source, destination: dest as String));
          }
        } else if (mapping['destination'] != null) {
          mappings.add(BrandFileMapping(source: source, destination: mapping['destination'] as String));
        }
      }
    }

    // Parse files section (source filename matches destination basename)
    if (yaml['files'] != null) {
      final files = yaml['files'] as YamlList;
      for (final filePath in files) {
        final destination = filePath as String;
        final source = path.basename(destination);
        mappings.add(BrandFileMapping(source: source, destination: destination));
      }
    }

    return mappings;
  }

  static void copyBrandFiles(String brandDir) {
    final mappings = _loadMappings();
    if (mappings.isEmpty) {
      return;
    }

    print('Copying brand files from ${brandDir.brightCyan}...'.brightGreen);
    int copied = 0;
    int skipped = 0;
    int errors = 0;

    for (final mapping in mappings) {
      final sourcePath = path.join(brandDir, mapping.source);
      final destPath = mapping.destination;

      if (!FileUtils.fileExists(sourcePath)) {
        print('  MISSING: ${mapping.source} not found in brand directory'.brightRed);
        errors++;
        continue;
      }

      print('  ${mapping.source.brightCyan} -> ${destPath.brightGreen}');
      FileUtils.copyFile(sourcePath, destPath);
      copied++;
    }

    print('');
    print('Brand file copy complete: $copied copied, $skipped skipped, $errors errors.'.brightGreen);

    // Inject brand_source_directory into the local transmute.json
    _injectBrandSourceDirectory(brandDir);
  }

  static void _injectBrandSourceDirectory(String brandDir) {
    final transmuteJsonPath = Constants.transmuteDefintionFile;
    if (!FileUtils.fileExists(transmuteJsonPath)) {
      return;
    }

    try {
      final contents = FileUtils.readFileAsString(transmuteJsonPath);
      if (contents == null) return;

      final data = jsonDecode(contents) as Map<String, dynamic>;
      final relativeBrandDir = path.relative(brandDir);
      data[Constants.brandSourceDirectoryKey] = relativeBrandDir;

      final encoder = JsonEncoder.withIndent('  ');
      final updatedJson = encoder.convert(data);
      FileUtils.writeStringToFilename(transmuteJsonPath, '$updatedJson\n');
      print('Set ${Constants.brandSourceDirectoryKey} to "${relativeBrandDir.brightCyan}" in $transmuteJsonPath'.brightGreen);
    } catch (ex) {
      print('Warning: Could not inject ${Constants.brandSourceDirectoryKey} into $transmuteJsonPath: $ex'.brightYellow);
    }
  }

  static void diffBrandFiles(String brandDir) {
    final mappings = _loadMappings();
    if (mappings.isEmpty) {
      return;
    }

    print('Diffing brand files from ${brandDir.brightCyan}...'.brightGreen);
    int identical = 0;
    int different = 0;
    int missing = 0;

    for (final mapping in mappings) {
      final sourcePath = path.join(brandDir, mapping.source);
      final destPath = mapping.destination;

      if (!FileUtils.fileExists(sourcePath)) {
        print('  MISSING SOURCE: ${mapping.source} not found in brand directory'.brightRed);
        missing++;
        continue;
      }

      if (!FileUtils.fileExists(destPath)) {
        print('  MISSING DEST:   $destPath does not exist in project'.brightRed);
        missing++;
        continue;
      }

      if (FileUtils.compareFiles(sourcePath, destPath)) {
        print('  IDENTICAL: ${mapping.source} == $destPath'.brightGreen);
        identical++;
      } else {
        print('  DIFFERENT: ${mapping.source} != $destPath'.brightRed);
        different++;
      }
    }

    print('');
    print('Brand file diff complete: $identical identical, $different different, $missing missing.'.brightGreen);
  }

  static void updateBrandFiles(String brandDir, {bool autoConfirm = false}) {
    final mappings = _loadMappings();
    if (mappings.isEmpty) {
      return;
    }

    print('Checking brand files from ${brandDir.brightCyan} for updates...'.brightGreen);
    if (autoConfirm) {
      print('Auto-confirm mode enabled (--yes): all changed files will be updated automatically.'.brightYellow);
    }
    int identical = 0;
    int different = 0;
    int updated = 0;
    int skipped = 0;
    int missing = 0;

    for (final mapping in mappings) {
      final brandPath = path.join(brandDir, mapping.source);
      final projectPath = mapping.destination;

      if (!FileUtils.fileExists(brandPath)) {
        print('  MISSING SOURCE: ${mapping.source} not found in brand directory'.brightRed);
        missing++;
        continue;
      }

      if (!FileUtils.fileExists(projectPath)) {
        print('  MISSING DEST:   $projectPath does not exist in project'.brightRed);
        missing++;
        continue;
      }

      if (FileUtils.compareFiles(brandPath, projectPath)) {
        print('  IDENTICAL: ${mapping.source} == $projectPath'.brightGreen);
        identical++;
      } else {
        print('  DIFFERENT: ${mapping.source} != $projectPath'.brightRed);
        different++;
        bool doUpdate = autoConfirm;
        if (!autoConfirm) {
          stdout.write('  Update brand file ${mapping.source.brightCyan} from $projectPath? (y/N): '.brightYellow);
          final response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
          doUpdate = response == 'y' || response == 'yes';
        }
        if (doUpdate) {
          FileUtils.copyFile(projectPath, brandPath);
          print('  UPDATED: $projectPath -> ${brandPath.brightGreen}'.brightGreen);
          updated++;
        } else {
          print('  SKIPPED'.brightYellow);
          skipped++;
        }
      }
    }

    print('');
    print('Brand file update complete: $identical identical, $different different, $updated updated, $skipped skipped, $missing missing.'
        .brightGreen);

    // Check if pubspec.yaml version is newer than transmute.json pubspec_version
    _checkAndUpdatePubspecVersion(brandDir, autoConfirm: autoConfirm);
  }

  static void _checkAndUpdatePubspecVersion(String brandDir, {bool autoConfirm = false}) {
    print('');
    print('Checking pubspec.yaml version against transmute.json pubspec_version...'.brightGreen);

    // Read version from project's pubspec.yaml
    final pubspecContents = FileUtils.readFileAsString(Constants.pubspecYamlFile);
    if (pubspecContents == null) {
      print('  Could not read ${Constants.pubspecYamlFile}'.brightRed);
      return;
    }
    final versionMatch = RegExConstants.versionInPubspecYaml.firstMatch(pubspecContents);
    if (versionMatch == null) {
      print('  No version: field found in ${Constants.pubspecYamlFile}'.brightRed);
      return;
    }
    final pubspecVersion = versionMatch.group(1)!.trim();

    // Read pubspec_version from transmute.json in the brand directory
    final transmuteJsonPath = path.join(brandDir, Constants.transmuteDefintionFile);
    if (!FileUtils.fileExists(transmuteJsonPath)) {
      print('  No ${Constants.transmuteDefintionFile} found in brand directory'.brightRed);
      return;
    }
    final transmuteContents = FileUtils.readFileAsString(transmuteJsonPath);
    if (transmuteContents == null) {
      print('  Could not read $transmuteJsonPath'.brightRed);
      return;
    }

    final transmuteData = jsonDecode(transmuteContents);
    final String? transmuteVersion = transmuteData[TransmuterKeys.pubspecVersion.key];

    if (transmuteVersion == null || transmuteVersion.isEmpty) {
      print('  No ${TransmuterKeys.pubspecVersion.key} found in $transmuteJsonPath'.brightYellow);
      print('  pubspec.yaml version is: ${pubspecVersion.brightCyan}'.brightYellow);
      return;
    }

    print('  pubspec.yaml version:              ${pubspecVersion.brightCyan}');
    print('  transmute.json pubspec_version:     ${transmuteVersion.brightCyan}');

    final comparison = _compareVersions(pubspecVersion, transmuteVersion);
    if (comparison > 0) {
      print('  pubspec.yaml version is NEWER'.brightGreen);
      bool doUpdate = autoConfirm;
      if (!autoConfirm) {
        stdout.write('  Update pubspec_version in $transmuteJsonPath to ${pubspecVersion.brightCyan}? (y/N): '.brightYellow);
        final response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
        doUpdate = response == 'y' || response == 'yes';
      }
      if (doUpdate) {
        transmuteData[TransmuterKeys.pubspecVersion.key] = pubspecVersion;
        final encoder = JsonEncoder.withIndent('  ');
        final updatedJson = encoder.convert(transmuteData);
        FileUtils.writeStringToFilename(transmuteJsonPath, '$updatedJson\n');
        print('  UPDATED: ${TransmuterKeys.pubspecVersion.key} in $transmuteJsonPath set to ${pubspecVersion.brightGreen}'.brightGreen);
      } else {
        print('  SKIPPED'.brightYellow);
      }
    } else if (comparison == 0) {
      print('  Versions are IDENTICAL - no update needed'.brightGreen);
    } else {
      print('  transmute.json version is newer or equal - no update needed'.brightYellow);
    }
  }

  /// Compares two Flutter version strings (e.g. "1.2.3+4").
  /// Returns positive if a > b, negative if a < b, 0 if equal.
  static int _compareVersions(String a, String b) {
    final aParts = a.split('+');
    final bParts = b.split('+');

    final aVersion = aParts[0].split('.');
    final bVersion = bParts[0].split('.');

    // Compare major.minor.patch
    final maxLen = aVersion.length > bVersion.length ? aVersion.length : bVersion.length;
    for (int i = 0; i < maxLen; i++) {
      final aNum = i < aVersion.length ? (int.tryParse(aVersion[i]) ?? 0) : 0;
      final bNum = i < bVersion.length ? (int.tryParse(bVersion[i]) ?? 0) : 0;
      if (aNum != bNum) return aNum - bNum;
    }

    // Compare build number if semver is equal
    final aBuild = aParts.length > 1 ? (int.tryParse(aParts[1]) ?? 0) : 0;
    final bBuild = bParts.length > 1 ? (int.tryParse(bParts[1]) ?? 0) : 0;
    return aBuild - bBuild;
  }
}
