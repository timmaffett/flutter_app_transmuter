import 'dart:convert';
import 'dart:io';
import 'package:yaml/yaml.dart';
import 'package:chalkdart/chalkstrings.dart';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:flutter_app_transmuter/src/transmute/file_utils.dart';
import 'package:flutter_app_transmuter/src/transmute/android_transmute.dart';
import 'package:flutter_app_transmuter/src/transmute/default_transmute_operations.dart';

class TransmuteOperation {
  final String id;
  final String description;
  final String type;
  final String platform;
  final String? file;
  final bool optional;
  final bool disabled;
  final String jsonKey;
  final String? fallbackKey;
  final String? regex;
  final bool multiline;
  final String? replacement;

  TransmuteOperation({
    required this.id,
    required this.description,
    required this.type,
    required this.platform,
    this.file,
    this.optional = false,
    this.disabled = false,
    required this.jsonKey,
    this.fallbackKey,
    this.regex,
    this.multiline = false,
    this.replacement,
  });

  factory TransmuteOperation.fromYamlMap(YamlMap map) {
    return TransmuteOperation(
      id: map['id'] as String,
      description: (map['description'] as String?) ?? '',
      type: (map['type'] as String?) ?? '',
      platform: (map['platform'] as String?) ?? 'both',
      file: map['file'] as String?,
      optional: (map['optional'] as bool?) ?? false,
      disabled: (map['disabled'] as bool?) ?? false,
      jsonKey: (map['json_key'] as String?) ?? '',
      fallbackKey: map['fallback_key'] as String?,
      regex: map['regex'] as String?,
      multiline: (map['multiline'] as bool?) ?? false,
      replacement: map['replacement'] as String?,
    );
  }
}

class TransmuteOperationRunner {
  static final Chalk androidColor = Chalk().orange;
  static final Chalk iosColor = Chalk().cyan;
  static final Chalk bothColor = Chalk().green;

  static Chalk _colorForPlatform(String platform) {
    switch (platform) {
      case 'android':
        return androidColor;
      case 'ios':
        return iosColor;
      default:
        return bothColor;
    }
  }

  static List<TransmuteOperation> loadAndMergeOperations() {
    // 1. Load defaults
    final defaults = _parseOperationsYaml(defaultTransmuteOperationsYaml);
    print('Loaded ${defaults.length} default transmute operations'.limeGreen);

    // 2. Load user overrides if file exists
    final userFile = File(Constants.transmuteOperationsFile);
    if (!userFile.existsSync()) {
      if (FlutterAppTransmuter.verboseDebug > 0) {
        print('No user ${Constants.transmuteOperationsFile} found, using defaults only'.brightYellow);
      }
      return defaults;
    }

    print('Found user ${Constants.transmuteOperationsFile}, merging with defaults...'.limeGreen);
    final userYaml = userFile.readAsStringSync();
    final userOps = _parseOperationsYaml(userYaml);

    // 3. Merge
    return _mergeOperations(defaults, userOps);
  }

  static void executeAll(List<TransmuteOperation> operations, Map<String, dynamic> transmuteData) {
    for (final op in operations) {
      if (op.disabled) continue;

      final value = _resolveValue(op, transmuteData);
      if (value == null || value.isEmpty) {
        if (FlutterAppTransmuter.verboseDebug > 0) {
          print('Skipping ${op.id}: no value for json_key "${op.jsonKey}"'
              '${op.fallbackKey != null ? ' or fallback_key "${op.fallbackKey}"' : ''}'.brightYellow);
        }
        continue;
      }

      final color = _colorForPlatform(op.platform);
      print(color('>> ${op.description} [${op.id}]'));

      switch (op.type) {
        case 'regex_replace':
          _executeRegexReplace(op, value);
          break;
        case 'extract_and_replace':
          _executeExtractAndReplace(op, value);
          break;
        case 'move_activity':
          AndroidTransmuter.updateMainActivity(value);
          break;
        default:
          print('WARNING: Unknown operation type "${op.type}" for ${op.id}'.brightRed);
      }
    }
  }

  static void _executeRegexReplace(TransmuteOperation op, String value) {
    final filePath = op.file;
    if (filePath == null) {
      print('ERROR: regex_replace operation ${op.id} has no file path'.brightRed);
      return;
    }

    final file = File(filePath);
    if (!file.existsSync()) {
      if (op.optional) {
        if (FlutterAppTransmuter.verboseDebug > 0) {
          print('  Optional file $filePath not found, skipping'.brightYellow);
        }
        return;
      }
      print('ERROR: file $filePath not found for operation ${op.id}'.brightRed);
      return;
    }

    String contents = file.readAsStringSync();
    final regexPattern = RegExp(op.regex!, caseSensitive: true, multiLine: op.multiline);
    final replacementTemplate = op.replacement!.replaceAll(r'$value', value);

    final match = regexPattern.firstMatch(contents);
    if (match == null) {
      print('  NOTE: pattern not matched in $filePath'.red);
      return;
    }

    final previousValue = match.group(1) ?? '(no capture group)';

    int occurrences = 0;
    contents = contents.replaceAllMapped(regexPattern, (m) {
      if (FlutterAppTransmuter.verboseDebug > 0) {
        print('  Replacing ${m.group(0)!.brightBlue} with ${replacementTemplate.brightGreen}');
      }
      occurrences++;
      return replacementTemplate;
    });

    print('  Replaced $occurrences occurrence${occurrences != 1 ? 's' : ''}: ${previousValue.blue} -> ${value.green}'
        .limeGreen);

    FileUtils.writeStringToFilename(filePath, contents);
  }

  static void _executeExtractAndReplace(TransmuteOperation op, String value) {
    final filePath = op.file;
    if (filePath == null) {
      print('ERROR: extract_and_replace operation ${op.id} has no file path'.brightRed);
      return;
    }

    final file = File(filePath);
    if (!file.existsSync()) {
      if (op.optional) {
        if (FlutterAppTransmuter.verboseDebug > 0) {
          print('  Optional file $filePath not found, skipping'.brightYellow);
        }
        return;
      }
      print('ERROR: file $filePath not found for operation ${op.id}'.brightRed);
      return;
    }

    String contents = file.readAsStringSync();
    final regexPattern = RegExp(op.regex!, caseSensitive: true, multiLine: op.multiline);

    final match = regexPattern.firstMatch(contents);
    if (match == null) {
      print('  NOTE: pattern not matched in $filePath, skipping'.brightYellow);
      return;
    }

    final oldValue = match.group(1);
    if (oldValue == null || oldValue.isEmpty) {
      print('  WARNING: extracted empty value from $filePath for ${op.id}'.brightYellow);
      return;
    }

    final replacementTemplate = op.replacement!.replaceAll(r'$value', value);

    print('  Old value: ${oldValue.blue}');

    contents = contents.replaceAll(oldValue, replacementTemplate);

    print('  Replaced all occurrences of ${oldValue.blue} with ${replacementTemplate.green}'.limeGreen);

    FileUtils.writeStringToFilename(filePath, contents);
  }

  static void checkAll(List<TransmuteOperation> operations, Map<String, dynamic> transmuteData) {
    int matched = 0;
    int mismatched = 0;
    int skippedOps = 0;

    for (final op in operations) {
      if (op.disabled) continue;

      final value = _resolveValue(op, transmuteData);
      if (value == null || value.isEmpty) {
        print('  SKIP:     [${op.id}] no value for json_key "${op.jsonKey}"'
            '${op.fallbackKey != null ? ' or fallback_key "${op.fallbackKey}"' : ''}'.brightYellow);
        skippedOps++;
        continue;
      }

      final color = _colorForPlatform(op.platform);

      switch (op.type) {
        case 'regex_replace':
          final result = _checkRegexReplace(op, value);
          if (result == null) {
            skippedOps++;
          } else if (result) {
            print(color('  MATCH:    [${op.id}] ${op.description}'));
            matched++;
          } else {
            mismatched++;
          }
          break;
        case 'extract_and_replace':
          final result = _checkExtractAndReplace(op, value);
          if (result == null) {
            skippedOps++;
          } else if (result) {
            print(color('  MATCH:    [${op.id}] ${op.description}'));
            matched++;
          } else {
            mismatched++;
          }
          break;
        case 'move_activity':
          final result = _checkMoveActivity(value);
          if (result == null) {
            skippedOps++;
          } else if (result) {
            print(color('  MATCH:    [${op.id}] ${op.description}'));
            matched++;
          } else {
            mismatched++;
          }
          break;
        default:
          skippedOps++;
      }
    }

    print('');
    print('Transmute check complete: ${matched.toString().brightGreen} matched, '
        '${mismatched.toString().brightRed} mismatched, '
        '${skippedOps.toString().brightYellow} skipped.'.limeGreen);
  }

  static void checkAllInteractive(
      List<TransmuteOperation> operations,
      Map<String, dynamic> transmuteData,
      {bool autoConfirm = false}) {
    int matched = 0;
    int mismatched = 0;
    int skippedOps = 0;
    int updatedFiles = 0;
    int updatedJsonKeys = 0;

    // Collect changes to apply to transmute.json at the end
    final jsonUpdates = <String, String>{};

    for (final op in operations) {
      if (op.disabled) continue;

      final color = _colorForPlatform(op.platform);
      final value = _resolveValue(op, transmuteData);

      if (value == null || value.isEmpty) {
        // No value in transmute.json - try to extract from file and offer to add
        if (op.type == 'move_activity' || op.file == null || op.regex == null) {
          print('  SKIP:     [${op.id}] no value for json_key "${op.jsonKey}"'
              '${op.fallbackKey != null ? ' or fallback_key "${op.fallbackKey}"' : ''}'.brightYellow);
          skippedOps++;
          continue;
        }

        final file = File(op.file!);
        if (!file.existsSync()) {
          print('  SKIP:     [${op.id}] no value for json_key "${op.jsonKey}" '
              'and ${op.optional ? 'optional ' : ''}file ${op.file} not found'.brightYellow);
          skippedOps++;
          continue;
        }

        final rawValue = _extractCurrentFileValue(op);
        if (rawValue == null || rawValue.isEmpty) {
          print('  SKIP:     [${op.id}] no value for json_key "${op.jsonKey}" '
              'and pattern not matched in ${op.file}'.brightYellow);
          skippedOps++;
          continue;
        }

        // Determine the json-appropriate value (reverse-map template if needed)
        String jsonValue;
        if (op.type == 'extract_and_replace' && op.replacement != null) {
          jsonValue = _reverseTemplate(op.replacement!, rawValue);
        } else {
          jsonValue = rawValue;
        }

        print('  MISSING:  [${op.id}] ${op.description}'.brightYellow);
        print('              json_key "${op.jsonKey}" not in transmute.json');
        print('              current file value: ${jsonValue.brightCyan}');

        bool doAdd;
        if (autoConfirm) {
          doAdd = true;
          print('              Auto-adding to transmute.json (--yes)'.brightGreen);
        } else {
          stdout.write('              Add "${op.jsonKey}" = "$jsonValue" to transmute.json? (Y/N): '.brightYellow);
          final response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
          doAdd = response == 'y' || response == 'yes';
        }

        if (doAdd) {
          jsonUpdates[op.jsonKey] = jsonValue;
          updatedJsonKeys++;
        } else {
          skippedOps++;
        }
        continue;
      }

      // Value exists in transmute.json - check against the file
      if (op.type == 'move_activity') {
        final result = _checkMoveActivity(value);
        if (result == null) {
          skippedOps++;
        } else if (result) {
          print(color('  MATCH:    [${op.id}] ${op.description}'));
          matched++;
        } else {
          mismatched++;
        }
        continue;
      }

      if (op.file == null || op.regex == null) {
        skippedOps++;
        continue;
      }

      final file = File(op.file!);
      if (!file.existsSync()) {
        print('  SKIP:     [${op.id}] ${op.optional ? 'optional ' : ''}file ${op.file} not found'.brightYellow);
        skippedOps++;
        continue;
      }

      final rawValue = _extractCurrentFileValue(op);
      if (rawValue == null) {
        print('  SKIP:     [${op.id}] pattern not matched in ${op.file}'.brightYellow);
        skippedOps++;
        continue;
      }

      // Compare based on operation type
      String currentDisplayValue;
      String expectedDisplayValue;
      bool isMatch;

      if (op.type == 'extract_and_replace') {
        final expectedValue = op.replacement!.replaceAll(r'$value', value);
        currentDisplayValue = rawValue;
        expectedDisplayValue = expectedValue;
        isMatch = rawValue == expectedValue;
      } else {
        // regex_replace
        currentDisplayValue = rawValue;
        expectedDisplayValue = value;
        isMatch = rawValue == value;
      }

      if (isMatch) {
        print(color('  MATCH:    [${op.id}] ${op.description}'));
        matched++;
      } else {
        print('  MISMATCH: [${op.id}] ${op.description}'.brightRed);
        print('              file has:  ${currentDisplayValue.brightBlue}');
        print('              transmute.json specifies:  ${expectedDisplayValue.brightGreen}');

        String choice;
        if (autoConfirm) {
          choice = 'n';
          print('              Auto-skipping mismatch (--yes)'.brightYellow);
        } else {
          stdout.write('              (T) transmute.json -> file, (F) file -> transmute.json, or (N) no change (default N): '.brightYellow);
          choice = (stdin.readLineSync()?.trim().toLowerCase() ?? 'n');
        }

        if (choice == 't') {
          // Use transmute.json value -> update the file
          if (op.type == 'regex_replace') {
            _executeRegexReplace(op, value);
          } else if (op.type == 'extract_and_replace') {
            _executeExtractAndReplace(op, value);
          }
          updatedFiles++;
        } else if (choice == 'f') {
          // Use file value -> update transmute.json
          String jsonValue;
          if (op.type == 'extract_and_replace' && op.replacement != null) {
            jsonValue = _reverseTemplate(op.replacement!, rawValue);
          } else {
            jsonValue = rawValue;
          }
          jsonUpdates[op.jsonKey] = jsonValue;
          updatedJsonKeys++;
          print('              Will update "${op.jsonKey}" = "$jsonValue" in transmute.json'.brightGreen);
        } else {
          mismatched++;
        }
      }
    }

    // Apply accumulated json updates
    if (jsonUpdates.isNotEmpty) {
      _applyJsonUpdates(jsonUpdates);
    }

    print('');
    print('Transmute interactive check complete: '
        '${matched.toString().brightGreen} matched, '
        '${mismatched.toString().brightRed} mismatched, '
        '${updatedJsonKeys.toString().brightCyan} json keys updated, '
        '${updatedFiles.toString().brightCyan} files updated, '
        '${skippedOps.toString().brightYellow} skipped.'.limeGreen);
  }

  /// Extract current raw value from a file using the operation's regex.
  /// Returns group(1) from the first match, or null.
  static String? _extractCurrentFileValue(TransmuteOperation op) {
    if (op.file == null || op.regex == null) return null;
    final file = File(op.file!);
    if (!file.existsSync()) return null;
    final contents = file.readAsStringSync();
    final regexPattern = RegExp(op.regex!, caseSensitive: true, multiLine: op.multiline);
    final match = regexPattern.firstMatch(contents);
    if (match == null) return null;
    return match.group(1);
  }

  /// Given a replacement template like '"$value"' and a raw captured value like '"MyApp"',
  /// reverse-map to get the json value 'MyApp'.
  static String _reverseTemplate(String template, String rawValue) {
    const marker = r'$value';
    final idx = template.indexOf(marker);
    if (idx < 0) return rawValue;
    final prefix = template.substring(0, idx);
    final suffix = template.substring(idx + marker.length);
    var result = rawValue;
    if (prefix.isNotEmpty && result.startsWith(prefix)) {
      result = result.substring(prefix.length);
    }
    if (suffix.isNotEmpty && result.endsWith(suffix)) {
      result = result.substring(0, result.length - suffix.length);
    }
    return result;
  }

  /// Apply accumulated key updates to transmute.json on disk.
  static void _applyJsonUpdates(Map<String, String> updates) {
    final transmuteJsonPath = Constants.transmuteDefintionFile;
    if (!File(transmuteJsonPath).existsSync()) {
      print('ERROR: $transmuteJsonPath not found, cannot apply updates'.brightRed);
      return;
    }
    try {
      final contents = File(transmuteJsonPath).readAsStringSync();
      final data = jsonDecode(contents) as Map<String, dynamic>;
      for (final entry in updates.entries) {
        data[entry.key] = entry.value;
      }
      final encoder = JsonEncoder.withIndent('  ');
      final updatedJson = encoder.convert(data);
      FileUtils.writeStringToFilename(transmuteJsonPath, '$updatedJson\n');
      print('Updated ${updates.length} key${updates.length != 1 ? 's' : ''} in $transmuteJsonPath'.brightGreen);
    } catch (ex) {
      print('ERROR applying updates to $transmuteJsonPath: $ex'.brightRed);
    }
  }

  /// Returns true=match, false=mismatch, null=skipped
  static bool? _checkRegexReplace(TransmuteOperation op, String value) {
    final filePath = op.file;
    if (filePath == null) return null;

    final file = File(filePath);
    if (!file.existsSync()) {
      print('  SKIP:     [${op.id}] ${op.optional ? 'optional ' : ''}file $filePath not found'.brightYellow);
      return null;
    }

    final contents = file.readAsStringSync();
    final regexPattern = RegExp(op.regex!, caseSensitive: true, multiLine: op.multiline);
    final match = regexPattern.firstMatch(contents);

    if (match == null) {
      print('  SKIP:     [${op.id}] pattern not matched in $filePath'.brightYellow);
      return null;
    }

    final currentValue = match.group(1) ?? '';
    if (currentValue == value) {
      return true;
    } else {
      print('  MISMATCH: [${op.id}] ${op.description}'.brightRed);
      print('              file has:  ${currentValue.brightBlue}');
      print('              transmute.json specifies:  ${value.brightGreen}');
      return false;
    }
  }

  /// Returns true=match, false=mismatch, null=skipped
  static bool? _checkExtractAndReplace(TransmuteOperation op, String value) {
    final filePath = op.file;
    if (filePath == null) return null;

    final file = File(filePath);
    if (!file.existsSync()) {
      print('  SKIP:     [${op.id}] ${op.optional ? 'optional ' : ''}file $filePath not found'.brightYellow);
      return null;
    }

    final contents = file.readAsStringSync();
    final regexPattern = RegExp(op.regex!, caseSensitive: true, multiLine: op.multiline);
    final match = regexPattern.firstMatch(contents);

    if (match == null) {
      print('  SKIP:     [${op.id}] pattern not matched in $filePath'.brightYellow);
      return null;
    }

    final currentValue = match.group(1) ?? '';
    final expectedValue = op.replacement!.replaceAll(r'$value', value);

    if (currentValue == expectedValue) {
      return true;
    } else {
      print('  MISMATCH: [${op.id}] ${op.description}'.brightRed);
      print('              file has:  ${currentValue.brightBlue}');
      print('              transmute.json specifies:  ${expectedValue.brightGreen}');
      return false;
    }
  }

  /// Returns true=match, false=mismatch, null=skipped
  static bool? _checkMoveActivity(String packageName) {
    final packagePath = packageName.replaceAll('.', '/');
    for (final type in ['java', 'kotlin']) {
      final extension = type == 'java' ? 'java' : 'kt';
      final expectedPath = '${Constants.androidActivityPath}$type/$packagePath/MainActivity.$extension';
      if (File(expectedPath).existsSync()) {
        return true;
      }
    }
    // Check if any MainActivity exists at all
    final javaActivity = AndroidTransmuter.findMainActivity(type: 'java');
    final kotlinActivity = AndroidTransmuter.findMainActivity(type: 'kotlin');
    if (javaActivity == null && kotlinActivity == null) {
      print('  SKIP:     [move_main_activity] no MainActivity found'.brightYellow);
      return null;
    }
    final found = javaActivity ?? kotlinActivity;
    print('  MISMATCH: [move_main_activity] Move MainActivity to new package directory'.brightRed);
    print('              file at:   ${found!.path.brightBlue}');
    print('              transmute.json specifies:  .../$packagePath/MainActivity.*'.brightGreen);
    return false;
  }

  static String? _resolveValue(TransmuteOperation op, Map<String, dynamic> data) {
    final primary = data[op.jsonKey];
    if (primary is String && primary.isNotEmpty) return primary;

    if (op.fallbackKey != null) {
      final fallback = data[op.fallbackKey];
      if (fallback is String && fallback.isNotEmpty) return fallback;
    }

    return null;
  }

  static List<TransmuteOperation> _parseOperationsYaml(String yamlContent) {
    final doc = loadYaml(yamlContent);
    if (doc == null || doc['operations'] == null) return [];

    final YamlList opsList = doc['operations'] as YamlList;
    return opsList.map((item) => TransmuteOperation.fromYamlMap(item as YamlMap)).toList();
  }

  static List<TransmuteOperation> _mergeOperations(
      List<TransmuteOperation> defaults, List<TransmuteOperation> overrides) {
    // Build a mutable copy of defaults
    final merged = List<TransmuteOperation>.from(defaults);

    // Build an index of default ids to their positions
    final idToIndex = <String, int>{};
    for (int i = 0; i < merged.length; i++) {
      idToIndex[merged[i].id] = i;
    }

    final newOps = <TransmuteOperation>[];

    for (final userOp in overrides) {
      final idx = idToIndex[userOp.id];
      if (idx != null) {
        if (userOp.disabled) {
          // Mark the default as disabled by replacing with a disabled placeholder
          print('  Disabled default operation: ${userOp.id}'.brightYellow);
          merged[idx] = TransmuteOperation(
            id: userOp.id,
            description: merged[idx].description,
            type: merged[idx].type,
            platform: merged[idx].platform,
            disabled: true,
            jsonKey: merged[idx].jsonKey,
          );
        } else {
          // Override in-place
          print('  Overriding default operation: ${userOp.id}'.limeGreen);
          merged[idx] = userOp;
        }
      } else {
        if (!userOp.disabled) {
          // New operation, append
          print('  Adding new user operation: ${userOp.id}'.limeGreen);
          newOps.add(userOp);
        }
      }
    }

    merged.addAll(newOps);

    // Filter out disabled ops
    final active = merged.where((op) => !op.disabled).toList();
    print('Final operation count: ${active.length} (${merged.length - active.length} disabled)'.limeGreen);
    return active;
  }
}
