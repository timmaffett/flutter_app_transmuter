import 'dart:io';
import 'package:test/test.dart';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/transmute_operations.dart';
import 'package:flutter_app_transmuter/src/transmute/default_transmute_operations.dart';

void main() {
  // -----------------------------------------------------------
  // TransmuteOperation data class
  // -----------------------------------------------------------
  group('TransmuteOperation.fromYamlMap', () {
    test('parses all fields from YAML', () {
      final yaml = '''
operations:
  - id: test_op
    description: "Test operation"
    type: regex_replace
    platform: android
    file: "some/file.txt"
    optional: true
    disabled: false
    json_key: packageName
    fallback_key: appName
    regex: 'pattern(.*)'
    multiline: true
    replacement: 'replaced \$value'
''';
      final ops = TransmuteOperationRunner.parseOperationsYaml(yaml);
      expect(ops.length, 1);
      final op = ops[0];
      expect(op.id, 'test_op');
      expect(op.description, 'Test operation');
      expect(op.type, 'regex_replace');
      expect(op.platform, 'android');
      expect(op.file, 'some/file.txt');
      expect(op.optional, true);
      expect(op.disabled, false);
      expect(op.jsonKey, 'packageName');
      expect(op.fallbackKey, 'appName');
      expect(op.regex, 'pattern(.*)');
      expect(op.multiline, true);
      expect(op.replacement, r'replaced $value');
    });

    test('uses defaults for optional fields', () {
      final yaml = '''
operations:
  - id: minimal_op
    json_key: someKey
''';
      final ops = TransmuteOperationRunner.parseOperationsYaml(yaml);
      expect(ops.length, 1);
      final op = ops[0];
      expect(op.id, 'minimal_op');
      expect(op.description, '');
      expect(op.type, '');
      expect(op.platform, 'both');
      expect(op.file, isNull);
      expect(op.optional, false);
      expect(op.disabled, false);
      expect(op.jsonKey, 'someKey');
      expect(op.fallbackKey, isNull);
      expect(op.regex, isNull);
      expect(op.multiline, false);
      expect(op.replacement, isNull);
    });
  });

  // -----------------------------------------------------------
  // parseOperationsYaml
  // -----------------------------------------------------------
  group('parseOperationsYaml', () {
    test('parses multiple operations', () {
      final yaml = '''
operations:
  - id: op1
    description: "First"
    type: regex_replace
    platform: android
    json_key: packageName
  - id: op2
    description: "Second"
    type: extract_and_replace
    platform: ios
    json_key: appName
''';
      final ops = TransmuteOperationRunner.parseOperationsYaml(yaml);
      expect(ops.length, 2);
      expect(ops[0].id, 'op1');
      expect(ops[1].id, 'op2');
    });

    test('returns empty list for empty YAML', () {
      expect(TransmuteOperationRunner.parseOperationsYaml(''), isEmpty);
    });

    test('returns empty list for YAML without operations key', () {
      expect(TransmuteOperationRunner.parseOperationsYaml('some_key: value'), isEmpty);
    });
  });

  // -----------------------------------------------------------
  // Default YAML parsing
  // -----------------------------------------------------------
  group('default YAML', () {
    test('default operations YAML parses without errors', () {
      final ops = TransmuteOperationRunner.parseOperationsYaml(defaultTransmuteOperationsYaml);
      expect(ops, isNotEmpty);
      for (final op in ops) {
        expect(op.id, isNotEmpty);
        expect(op.type, isNotEmpty);
      }
    });

    test('default post-switch YAML parses without errors', () {
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(defaultTransmuteOperationsYaml);
      expect(ops, isNotEmpty);
      for (final op in ops) {
        expect(op.id, isNotEmpty);
      }
    });

    test('default post-switch operations pass validation', () {
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(defaultTransmuteOperationsYaml);
      expect(TransmuteOperationRunner.validatePostSwitchOperations(ops), isNull);
    });

    test('default operations have unique ids', () {
      final ops = TransmuteOperationRunner.parseOperationsYaml(defaultTransmuteOperationsYaml);
      final ids = ops.map((op) => op.id).toSet();
      expect(ids.length, ops.length, reason: 'All operation ids should be unique');
    });

    test('default post-switch operations have unique ids', () {
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(defaultTransmuteOperationsYaml);
      final ids = ops.map((op) => op.id).toSet();
      expect(ids.length, ops.length, reason: 'All post-switch operation ids should be unique');
    });
  });

  // -----------------------------------------------------------
  // mergeOperations
  // -----------------------------------------------------------
  group('mergeOperations', () {
    test('overrides existing operation by id', () {
      final defaults = [
        TransmuteOperation(id: 'op1', description: 'Original', type: 'regex_replace', platform: 'android', jsonKey: 'key1'),
        TransmuteOperation(id: 'op2', description: 'Keep', type: 'regex_replace', platform: 'ios', jsonKey: 'key2'),
      ];
      final overrides = [
        TransmuteOperation(id: 'op1', description: 'Overridden', type: 'regex_replace', platform: 'both', jsonKey: 'key1_new'),
      ];

      final merged = TransmuteOperationRunner.mergeOperations(defaults, overrides);
      expect(merged.length, 2);
      expect(merged[0].id, 'op1');
      expect(merged[0].description, 'Overridden');
      expect(merged[0].jsonKey, 'key1_new');
      expect(merged[1].id, 'op2');
    });

    test('disables operation by id', () {
      final defaults = [
        TransmuteOperation(id: 'op1', description: 'D1', type: 't', platform: 'p', jsonKey: 'k1'),
        TransmuteOperation(id: 'op2', description: 'D2', type: 't', platform: 'p', jsonKey: 'k2'),
        TransmuteOperation(id: 'op3', description: 'D3', type: 't', platform: 'p', jsonKey: 'k3'),
      ];
      final overrides = [
        TransmuteOperation(id: 'op2', description: '', type: '', platform: '', disabled: true, jsonKey: ''),
      ];

      final merged = TransmuteOperationRunner.mergeOperations(defaults, overrides);
      expect(merged.length, 2);
      expect(merged[0].id, 'op1');
      expect(merged[1].id, 'op3');
    });

    test('appends new operations', () {
      final defaults = [
        TransmuteOperation(id: 'op1', description: 'D1', type: 't', platform: 'p', jsonKey: 'k1'),
      ];
      final overrides = [
        TransmuteOperation(id: 'op_new', description: 'New', type: 't', platform: 'p', jsonKey: 'k_new'),
      ];

      final merged = TransmuteOperationRunner.mergeOperations(defaults, overrides);
      expect(merged.length, 2);
      expect(merged[0].id, 'op1');
      expect(merged[1].id, 'op_new');
    });

    test('mixed override, disable, and append', () {
      final defaults = [
        TransmuteOperation(id: 'a', description: 'A', type: 't', platform: 'p', jsonKey: 'k'),
        TransmuteOperation(id: 'b', description: 'B', type: 't', platform: 'p', jsonKey: 'k'),
        TransmuteOperation(id: 'c', description: 'C', type: 't', platform: 'p', jsonKey: 'k'),
      ];
      final overrides = [
        TransmuteOperation(id: 'b', description: '', type: '', platform: '', disabled: true, jsonKey: ''),
        TransmuteOperation(id: 'a', description: 'A-new', type: 't', platform: 'p', jsonKey: 'k'),
        TransmuteOperation(id: 'd', description: 'D', type: 't', platform: 'p', jsonKey: 'k'),
      ];

      final merged = TransmuteOperationRunner.mergeOperations(defaults, overrides);
      expect(merged.length, 3);
      expect(merged[0].id, 'a');
      expect(merged[0].description, 'A-new');
      expect(merged[1].id, 'c');
      expect(merged[2].id, 'd');
    });

    test('preserves order on override', () {
      final defaults = [
        TransmuteOperation(id: 'first', description: '1st', type: 't', platform: 'p', jsonKey: 'k'),
        TransmuteOperation(id: 'second', description: '2nd', type: 't', platform: 'p', jsonKey: 'k'),
        TransmuteOperation(id: 'third', description: '3rd', type: 't', platform: 'p', jsonKey: 'k'),
      ];
      final overrides = [
        TransmuteOperation(id: 'second', description: '2nd-new', type: 't', platform: 'p', jsonKey: 'k'),
      ];

      final merged = TransmuteOperationRunner.mergeOperations(defaults, overrides);
      expect(merged.length, 3);
      expect(merged[0].id, 'first');
      expect(merged[1].id, 'second');
      expect(merged[1].description, '2nd-new');
      expect(merged[2].id, 'third');
    });

    test('empty overrides returns defaults unchanged', () {
      final defaults = [
        TransmuteOperation(id: 'op1', description: 'D1', type: 't', platform: 'p', jsonKey: 'k'),
      ];
      final merged = TransmuteOperationRunner.mergeOperations(defaults, []);
      expect(merged.length, 1);
      expect(merged[0].id, 'op1');
    });

    test('disabled override for non-existent id is ignored', () {
      final defaults = [
        TransmuteOperation(id: 'op1', description: 'D1', type: 't', platform: 'p', jsonKey: 'k'),
      ];
      final overrides = [
        TransmuteOperation(id: 'nonexistent', description: '', type: '', platform: '', disabled: true, jsonKey: ''),
      ];
      final merged = TransmuteOperationRunner.mergeOperations(defaults, overrides);
      expect(merged.length, 1);
    });
  });

  // -----------------------------------------------------------
  // resolveValue
  // -----------------------------------------------------------
  group('resolveValue', () {
    test('returns primary key value', () {
      final op = TransmuteOperation(id: 'op', description: '', type: '', platform: '', jsonKey: 'primary');
      expect(TransmuteOperationRunner.resolveValue(op, {'primary': 'value1'}), 'value1');
    });

    test('falls back to fallback key when primary is missing', () {
      final op = TransmuteOperation(id: 'op', description: '', type: '', platform: '', jsonKey: 'primary', fallbackKey: 'fallback');
      expect(TransmuteOperationRunner.resolveValue(op, {'fallback': 'fb_val'}), 'fb_val');
    });

    test('falls back when primary is empty string', () {
      final op = TransmuteOperation(id: 'op', description: '', type: '', platform: '', jsonKey: 'primary', fallbackKey: 'fallback');
      expect(TransmuteOperationRunner.resolveValue(op, {'primary': '', 'fallback': 'fb_val'}), 'fb_val');
    });

    test('returns null when both keys missing', () {
      final op = TransmuteOperation(id: 'op', description: '', type: '', platform: '', jsonKey: 'primary', fallbackKey: 'fallback');
      expect(TransmuteOperationRunner.resolveValue(op, <String, dynamic>{}), isNull);
    });

    test('returns null when no fallback defined and primary missing', () {
      final op = TransmuteOperation(id: 'op', description: '', type: '', platform: '', jsonKey: 'primary');
      expect(TransmuteOperationRunner.resolveValue(op, <String, dynamic>{}), isNull);
    });

    test('prefers primary over fallback when both present', () {
      final op = TransmuteOperation(id: 'op', description: '', type: '', platform: '', jsonKey: 'primary', fallbackKey: 'fallback');
      expect(TransmuteOperationRunner.resolveValue(op, {'primary': 'prim', 'fallback': 'fb'}), 'prim');
    });

    test('returns null for non-string value', () {
      final op = TransmuteOperation(id: 'op', description: '', type: '', platform: '', jsonKey: 'primary');
      expect(TransmuteOperationRunner.resolveValue(op, {'primary': 123}), isNull);
    });
  });

  // -----------------------------------------------------------
  // reverseTemplate
  // -----------------------------------------------------------
  group('reverseTemplate', () {
    test('extracts value from quoted template', () {
      expect(TransmuteOperationRunner.reverseTemplate(r'"$value"', '"MyApp"'), 'MyApp');
    });

    test('extracts value from bare template', () {
      expect(TransmuteOperationRunner.reverseTemplate(r'$value', 'MyApp'), 'MyApp');
    });

    test('returns raw value when no marker', () {
      expect(TransmuteOperationRunner.reverseTemplate('no_marker', 'raw'), 'raw');
    });

    test('handles prefix only', () {
      expect(TransmuteOperationRunner.reverseTemplate(r'prefix_$value', 'prefix_MyApp'), 'MyApp');
    });

    test('handles suffix only', () {
      expect(TransmuteOperationRunner.reverseTemplate(r'$value_suffix', 'MyApp_suffix'), 'MyApp');
    });

    test('handles complex template', () {
      expect(
        TransmuteOperationRunner.reverseTemplate(r'namespace = "$value"', 'namespace = "com.example"'),
        'com.example',
      );
    });
  });

  // -----------------------------------------------------------
  // Post-switch operation parsing
  // -----------------------------------------------------------
  group('parsePostSwitchOpsYaml', () {
    test('parses basic steps', () {
      final yaml = '''
post_switch_operations:
  clean: "flutter clean"
  pub_get: "flutter pub get"
''';
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(yaml);
      expect(ops.length, 2);
      expect(ops[0].id, 'clean');
      expect(ops[0].stepName, 'clean');
      expect(ops[0].command, 'flutter clean');
      expect(ops[0].platform, 'both');
      expect(ops[0].requireFlag, isNull);
      expect(ops[0].isTransmuteCommand, false);
    });

    test('extracts ios_ platform prefix', () {
      final yaml = '''
post_switch_operations:
  ios_remove_data: "rm -rf ~/data"
''';
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(yaml);
      expect(ops[0].id, 'ios_remove_data');
      expect(ops[0].stepName, 'remove_data');
      expect(ops[0].platform, 'ios');
    });

    test('extracts android_ platform prefix', () {
      final yaml = '''
post_switch_operations:
  android_requireflag_build: "flutter build apk"
''';
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(yaml);
      expect(ops[0].id, 'android_requireflag_build');
      expect(ops[0].platform, 'android');
      expect(ops[0].requireFlag, 'build');
      expect(ops[0].stepName, 'build');
    });

    test('extracts requireflag_ prefix', () {
      final yaml = '''
post_switch_operations:
  requireflag_flutterfire: "flutterfire configure"
''';
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(yaml);
      expect(ops[0].requireFlag, 'flutterfire');
      expect(ops[0].stepName, 'flutterfire');
    });

    test('detects transmute_command', () {
      final yaml = '''
post_switch_operations:
  transmute_command: "--transmute"
''';
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(yaml);
      expect(ops[0].isTransmuteCommand, true);
      expect(ops[0].command, '--transmute');
    });

    test('detects disabled steps', () {
      final yaml = '''
post_switch_operations:
  clean: disabled
  empty_step: ""
''';
      final ops = TransmuteOperationRunner.parsePostSwitchOpsYaml(yaml);
      expect(ops[0].disabled, true);
      expect(ops[1].disabled, true);
    });

    test('returns empty list for YAML without post_switch_operations', () {
      expect(TransmuteOperationRunner.parsePostSwitchOpsYaml('operations: []'), isEmpty);
    });
  });

  // -----------------------------------------------------------
  // mergePostSwitchOperations
  // -----------------------------------------------------------
  group('mergePostSwitchOperations', () {
    test('overrides by id', () {
      final defaults = [
        PostSwitchOperation(id: 'clean', stepName: 'clean', command: 'flutter clean'),
        PostSwitchOperation(id: 'pub_get', stepName: 'pub_get', command: 'flutter pub get'),
      ];
      final overrides = [
        PostSwitchOperation(id: 'clean', stepName: 'clean', command: 'flutter clean && echo done'),
      ];

      final merged = TransmuteOperationRunner.mergePostSwitchOperations(defaults, overrides);
      expect(merged.length, 2);
      expect(merged[0].command, 'flutter clean && echo done');
      expect(merged[1].id, 'pub_get');
    });

    test('disables by id', () {
      final defaults = [
        PostSwitchOperation(id: 'clean', stepName: 'clean', command: 'flutter clean'),
        PostSwitchOperation(id: 'pub_get', stepName: 'pub_get', command: 'flutter pub get'),
      ];
      final overrides = [
        PostSwitchOperation(id: 'clean', stepName: 'clean', command: '', disabled: true),
      ];

      final merged = TransmuteOperationRunner.mergePostSwitchOperations(defaults, overrides);
      expect(merged.length, 1);
      expect(merged[0].id, 'pub_get');
    });

    test('appends new steps', () {
      final defaults = [
        PostSwitchOperation(id: 'clean', stepName: 'clean', command: 'flutter clean'),
      ];
      final overrides = [
        PostSwitchOperation(id: 'build_runner', stepName: 'build_runner', command: 'dart run build_runner build'),
      ];

      final merged = TransmuteOperationRunner.mergePostSwitchOperations(defaults, overrides);
      expect(merged.length, 2);
      expect(merged[1].id, 'build_runner');
    });
  });

  // -----------------------------------------------------------
  // validatePostSwitchOperations
  // -----------------------------------------------------------
  group('validatePostSwitchOperations', () {
    test('returns null for valid operations', () {
      final ops = [
        PostSwitchOperation(id: 'tc', stepName: 'transmute_command', command: '--transmute', isTransmuteCommand: true),
        PostSwitchOperation(id: 'clean', stepName: 'clean', command: 'flutter clean'),
      ];
      expect(TransmuteOperationRunner.validatePostSwitchOperations(ops), isNull);
    });

    test('allows --yes --debug with transmute_command', () {
      final ops = [
        PostSwitchOperation(id: 'tc', stepName: 'transmute_command', command: '--transmute --yes --debug', isTransmuteCommand: true),
      ];
      expect(TransmuteOperationRunner.validatePostSwitchOperations(ops), isNull);
    });

    test('allows --verbose=2 with transmute_command', () {
      final ops = [
        PostSwitchOperation(id: 'tc', stepName: 'transmute_command', command: '--transmute --verbose=2', isTransmuteCommand: true),
      ];
      expect(TransmuteOperationRunner.validatePostSwitchOperations(ops), isNull);
    });

    test('rejects invalid option in transmute_command', () {
      final ops = [
        PostSwitchOperation(id: 'tc', stepName: 'transmute_command', command: '--transmute --badopt', isTransmuteCommand: true),
      ];
      final error = TransmuteOperationRunner.validatePostSwitchOperations(ops);
      expect(error, isNotNull);
      expect(error!, contains('--badopt'));
    });

    test('rejects transmute_command missing --transmute', () {
      final ops = [
        PostSwitchOperation(id: 'tc', stepName: 'transmute_command', command: '--yes', isTransmuteCommand: true),
      ];
      final error = TransmuteOperationRunner.validatePostSwitchOperations(ops);
      expect(error, isNotNull);
      expect(error!, contains('must include --transmute'));
    });

    test('skips disabled transmute_command', () {
      final ops = [
        PostSwitchOperation(id: 'tc', stepName: 'transmute_command', command: '--badopt', isTransmuteCommand: true, disabled: true),
      ];
      expect(TransmuteOperationRunner.validatePostSwitchOperations(ops), isNull);
    });

    test('returns null for non-transmute-command operations', () {
      final ops = [
        PostSwitchOperation(id: 'clean', stepName: 'clean', command: 'anything --invalid works here'),
      ];
      expect(TransmuteOperationRunner.validatePostSwitchOperations(ops), isNull);
    });

    test('rejects invalid --verbose format', () {
      final ops = [
        PostSwitchOperation(id: 'tc', stepName: 'transmute_command', command: '--transmute --verbose=abc', isTransmuteCommand: true),
      ];
      final error = TransmuteOperationRunner.validatePostSwitchOperations(ops);
      expect(error, isNotNull);
      expect(error!, contains('--verbose=abc'));
    });
  });

  // -----------------------------------------------------------
  // File-based: executeRegexReplace
  // -----------------------------------------------------------
  group('executeRegexReplace', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
      FlutterAppTransmuter.executingDryRun = false;
      FlutterAppTransmuter.verboseDebug = 0;
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('replaces single regex match', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('applicationId = "com.old.app"');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'packageName',
        regex: r'applicationId\s*=\s*"(.*)"',
        replacement: r'applicationId = "$value"',
      );

      TransmuteOperationRunner.executeRegexReplace(op, 'com.new.app');
      expect(File(filePath).readAsStringSync(), 'applicationId = "com.new.app"');
    });

    test('replaces multiple matches', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('package="com.old"\npackage="com.old"');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'key',
        regex: r'package="(.*?)"',
        replacement: r'package="$value"',
      );

      TransmuteOperationRunner.executeRegexReplace(op, 'com.new.app');
      expect(File(filePath).readAsStringSync(), 'package="com.new.app"\npackage="com.new.app"');
    });

    test('skips optional file when not found', () {
      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: '${tempDir.path}/nonexistent.txt',
        optional: true, jsonKey: 'key',
        regex: 'pattern', replacement: 'replacement',
      );
      // Should not throw
      TransmuteOperationRunner.executeRegexReplace(op, 'value');
    });

    test('handles multiline regex', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('version: 1.0.0+1\nname: app');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'both', file: filePath, jsonKey: 'version',
        regex: r'^version:\s*(.+)$', multiline: true,
        replacement: r'version: $value',
      );

      TransmuteOperationRunner.executeRegexReplace(op, '2.0.0+5');
      expect(File(filePath).readAsStringSync(), 'version: 2.0.0+5\nname: app');
    });

    test('preserves surrounding content', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('before\napplicationId = "old"\nafter');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'key',
        regex: r'applicationId\s*=\s*"(.*)"',
        replacement: r'applicationId = "$value"',
      );

      TransmuteOperationRunner.executeRegexReplace(op, 'new');
      expect(File(filePath).readAsStringSync(), 'before\napplicationId = "new"\nafter');
    });
  });

  // -----------------------------------------------------------
  // File-based: executeExtractAndReplace
  // -----------------------------------------------------------
  group('executeExtractAndReplace', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
      FlutterAppTransmuter.executingDryRun = false;
      FlutterAppTransmuter.verboseDebug = 0;
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('extracts and replaces all occurrences', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync(
        'PRODUCT_BUNDLE_IDENTIFIER = com.old.app;\n'
        'other = com.old.app\n'
        'again = com.old.app;',
      );

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'extract_and_replace',
        platform: 'ios', file: filePath, jsonKey: 'key',
        regex: r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*(.*);',
        replacement: r'$value',
      );

      TransmuteOperationRunner.executeExtractAndReplace(op, 'com.new.app');
      final result = File(filePath).readAsStringSync();
      expect(result, contains('com.new.app'));
      expect(result, isNot(contains('com.old.app')));
    });

    test('skips optional file when not found', () {
      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'extract_and_replace',
        platform: 'ios', file: '${tempDir.path}/nope.txt',
        optional: true, jsonKey: 'key',
        regex: 'pattern', replacement: r'$value',
      );
      // Should not throw
      TransmuteOperationRunner.executeExtractAndReplace(op, 'value');
    });
  });

  // -----------------------------------------------------------
  // File-based: checkRegexReplace
  // -----------------------------------------------------------
  group('checkRegexReplace', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('returns true when value matches', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('applicationId = "com.expected"');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'key',
        regex: r'applicationId\s*=\s*"(.*)"',
        replacement: r'applicationId = "$value"',
      );
      expect(TransmuteOperationRunner.checkRegexReplace(op, 'com.expected'), true);
    });

    test('returns false when value mismatches', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('applicationId = "com.different"');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'key',
        regex: r'applicationId\s*=\s*"(.*)"',
        replacement: r'applicationId = "$value"',
      );
      expect(TransmuteOperationRunner.checkRegexReplace(op, 'com.expected'), false);
    });

    test('returns null when file not found', () {
      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: '${tempDir.path}/nope.txt',
        jsonKey: 'key', regex: 'pattern', replacement: 'r',
      );
      expect(TransmuteOperationRunner.checkRegexReplace(op, 'value'), isNull);
    });

    test('returns null when pattern not matched', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('no match here');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'key',
        regex: r'applicationId\s*=\s*"(.*)"', replacement: r'applicationId = "$value"',
      );
      expect(TransmuteOperationRunner.checkRegexReplace(op, 'value'), isNull);
    });

    test('returns null when file path is null', () {
      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', jsonKey: 'key',
        regex: 'pattern', replacement: 'r',
      );
      expect(TransmuteOperationRunner.checkRegexReplace(op, 'value'), isNull);
    });
  });

  // -----------------------------------------------------------
  // File-based: checkExtractAndReplace
  // -----------------------------------------------------------
  group('checkExtractAndReplace', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('returns true when extracted value matches expected', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('PRODUCT_BUNDLE_IDENTIFIER = com.expected;');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'extract_and_replace',
        platform: 'ios', file: filePath, jsonKey: 'key',
        regex: r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*(.*);',
        replacement: r'$value',
      );
      expect(TransmuteOperationRunner.checkExtractAndReplace(op, 'com.expected'), true);
    });

    test('returns false when extracted value mismatches', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('PRODUCT_BUNDLE_IDENTIFIER = com.old;');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'extract_and_replace',
        platform: 'ios', file: filePath, jsonKey: 'key',
        regex: r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*(.*);',
        replacement: r'$value',
      );
      expect(TransmuteOperationRunner.checkExtractAndReplace(op, 'com.new'), false);
    });

    test('returns null for missing file', () {
      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'extract_and_replace',
        platform: 'ios', file: '${tempDir.path}/nope.txt', jsonKey: 'key',
        regex: 'pattern', replacement: r'$value',
      );
      expect(TransmuteOperationRunner.checkExtractAndReplace(op, 'value'), isNull);
    });
  });

  // -----------------------------------------------------------
  // File-based: extractCurrentFileValue
  // -----------------------------------------------------------
  group('extractCurrentFileValue', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('extracts capture group from file', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('applicationId = "com.example.app"');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'key',
        regex: r'applicationId\s*=\s*"(.*)"',
      );
      expect(TransmuteOperationRunner.extractCurrentFileValue(op), 'com.example.app');
    });

    test('returns null for missing file', () {
      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: '${tempDir.path}/nope.txt', jsonKey: 'key',
        regex: 'pattern',
      );
      expect(TransmuteOperationRunner.extractCurrentFileValue(op), isNull);
    });

    test('returns null when pattern not matched', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('no match');

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'key',
        regex: r'applicationId\s*=\s*"(.*)"',
      );
      expect(TransmuteOperationRunner.extractCurrentFileValue(op), isNull);
    });

    test('returns null when no regex defined', () {
      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', jsonKey: 'key',
      );
      expect(TransmuteOperationRunner.extractCurrentFileValue(op), isNull);
    });
  });

  // -----------------------------------------------------------
  // value_is_flag detection
  // -----------------------------------------------------------
  group('valueIsFlag', () {
    test('parses explicit value_is_flag true from YAML', () {
      final yaml = '''
operations:
  - id: flag_op
    type: regex_replace
    json_key: someFlag
    regex: 'pattern'
    replacement: 'fixed \$value text'
    value_is_flag: true
''';
      final ops = TransmuteOperationRunner.parseOperationsYaml(yaml);
      expect(ops[0].valueIsFlag, true);
    });

    test('explicit value_is_flag false overrides auto-detection', () {
      final yaml = '''
operations:
  - id: not_flag_op
    type: regex_replace
    json_key: someKey
    regex: 'pattern'
    replacement: 'fixed text with no marker'
    value_is_flag: false
''';
      final ops = TransmuteOperationRunner.parseOperationsYaml(yaml);
      expect(ops[0].valueIsFlag, false);
    });

    test('auto-detects flag when replacement has no value marker', () {
      final yaml = '''
operations:
  - id: removal_op
    type: regex_replace
    json_key: someRemovalFlag
    regex: '(<key>Something</key>)'
    replacement: ""
''';
      final ops = TransmuteOperationRunner.parseOperationsYaml(yaml);
      expect(ops[0].valueIsFlag, true);
    });

    test('does not auto-detect flag when replacement uses value marker', () {
      final yaml = '''
operations:
  - id: normal_op
    type: regex_replace
    json_key: packageName
    regex: 'applicationId = "(.*)"'
    replacement: 'applicationId = "\$value"'
''';
      final ops = TransmuteOperationRunner.parseOperationsYaml(yaml);
      expect(ops[0].valueIsFlag, false);
    });

    test('does not auto-detect flag when there is no replacement', () {
      final op = TransmuteOperation(
        id: 'move', description: '', type: 'move_activity', platform: 'android', jsonKey: 'packageName');
      expect(op.valueIsFlag, false);
    });

    test('no default operation is a flag operation', () {
      final ops = TransmuteOperationRunner.parseOperationsYaml(defaultTransmuteOperationsYaml);
      for (final op in ops) {
        expect(op.valueIsFlag, false, reason: 'default op ${op.id} should not be flag-gated');
      }
    });
  });

  // -----------------------------------------------------------
  // isFlagValueDisabled
  // -----------------------------------------------------------
  group('isFlagValueDisabled', () {
    test('recognizes disabled flag values', () {
      for (final v in ['false', 'FALSE', 'False', 'no', 'NO', '0', 'off', 'OFF']) {
        expect(TransmuteOperationRunner.isFlagValueDisabled(v), true, reason: '"$v" should disable a flag op');
      }
    });

    test('treats other values as enabled', () {
      for (final v in ['true', 'yes', '1', 'on', 'anything else']) {
        expect(TransmuteOperationRunner.isFlagValueDisabled(v), false, reason: '"$v" should not disable a flag op');
      }
    });
  });

  // -----------------------------------------------------------
  // checkRegexReplace flag semantics
  // -----------------------------------------------------------
  group('checkRegexReplace flag ops', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    TransmuteOperation flagOp(String filePath) => TransmuteOperation(
          id: 'remove_block', description: 'Remove block', type: 'regex_replace',
          platform: 'ios', file: filePath, jsonKey: 'someRemovalFlag',
          regex: r'(<key>Something</key>)', replacement: '',
        );

    test('returns true (applied) when pattern no longer matches', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('block already removed');
      expect(TransmuteOperationRunner.checkRegexReplace(flagOp(filePath), 'true'), true);
    });

    test('returns false (not applied) when pattern still matches', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('<key>Something</key>');
      expect(TransmuteOperationRunner.checkRegexReplace(flagOp(filePath), 'true'), false);
    });
  });

  // -----------------------------------------------------------
  // executeAll flag gating
  // -----------------------------------------------------------
  group('executeAll flag ops', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
      FlutterAppTransmuter.executingDryRun = false;
      FlutterAppTransmuter.verboseDebug = 0;
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    TransmuteOperation flagOp(String filePath) => TransmuteOperation(
          id: 'remove_block', description: 'Remove block', type: 'regex_replace',
          platform: 'ios', file: filePath, jsonKey: 'someRemovalFlag',
          regex: r'(<key>Something</key>\n)', replacement: '',
        );

    test('runs flag op when value is true', () {
      final filePath = '${tempDir.path}/test.txt';
      File(filePath).writeAsStringSync('<key>Something</key>\nkeep this');

      TransmuteOperationRunner.executeAll([flagOp(filePath)], {'someRemovalFlag': 'true'});
      expect(File(filePath).readAsStringSync(), 'keep this');
    });

    test('skips flag op when value is false', () {
      final filePath = '${tempDir.path}/test.txt';
      const original = '<key>Something</key>\nkeep this';
      File(filePath).writeAsStringSync(original);

      TransmuteOperationRunner.executeAll([flagOp(filePath)], {'someRemovalFlag': 'false'});
      expect(File(filePath).readAsStringSync(), original);
    });
  });

  // -----------------------------------------------------------
  // checkAllInteractive flag ops: never adopt regex match as json value
  // -----------------------------------------------------------
  group('checkAllInteractive flag ops', () {
    late Directory tempDir;
    late String jsonPath;
    late String plistPath;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
      jsonPath = '${tempDir.path}/transmute.json';
      plistPath = '${tempDir.path}/info.plist';
      FlutterAppTransmuter.executingDryRun = false;
      FlutterAppTransmuter.verboseDebug = 0;
      FlutterAppTransmuter.autoSkip = false;
      FlutterAppTransmuter.autoTransmuteValue = false;
      FlutterAppTransmuter.autoFileValue = false;
      FlutterAppTransmuter.fatalPrompts = false;
    });

    tearDown(() {
      FlutterAppTransmuter.autoSkip = false;
      FlutterAppTransmuter.autoTransmuteValue = false;
      FlutterAppTransmuter.autoFileValue = false;
      FlutterAppTransmuter.fatalPrompts = false;
      tempDir.deleteSync(recursive: true);
    });

    TransmuteOperation flagOp() => TransmuteOperation(
          id: 'remove_block', description: 'Remove block', type: 'regex_replace',
          platform: 'ios', file: plistPath, jsonKey: 'someRemovalFlag',
          regex: r'(<key>Something</key>\n)', replacement: '',
        );

    test('missing flag key is skipped, not adopted from file, even with --yes', () {
      const jsonContents = '{\n  "other": "x"\n}\n';
      File(jsonPath).writeAsStringSync(jsonContents);
      File(plistPath).writeAsStringSync('<key>Something</key>\nkeep this');

      TransmuteOperationRunner.checkAllInteractive([flagOp()], {'other': 'x'},
          autoConfirm: true, transmuteJsonPath: jsonPath);

      expect(File(jsonPath).readAsStringSync(), jsonContents,
          reason: 'flag key must not be added to transmute.json from a regex match');
    });

    test('missing flag key does not trigger --fatal-prompts', () {
      const jsonContents = '{\n  "other": "x"\n}\n';
      File(jsonPath).writeAsStringSync(jsonContents);
      File(plistPath).writeAsStringSync('<key>Something</key>\nkeep this');
      FlutterAppTransmuter.fatalPrompts = true;

      // Would call exit(1) if a prompt were shown - reaching the expect proves it skipped.
      TransmuteOperationRunner.checkAllInteractive([flagOp()], {'other': 'x'}, transmuteJsonPath: jsonPath);

      expect(File(jsonPath).readAsStringSync(), jsonContents);
    });

    test('missing non-flag key still adopts file value with --yes', () {
      final gradlePath = '${tempDir.path}/build.gradle';
      File(jsonPath).writeAsStringSync('{\n  "other": "x"\n}\n');
      File(gradlePath).writeAsStringSync('applicationId = "com.example.app"');

      final op = TransmuteOperation(
        id: 'pkg', description: 'Package name', type: 'regex_replace',
        platform: 'android', file: gradlePath, jsonKey: 'packageName',
        regex: r'applicationId\s*=\s*"(.*)"', replacement: r'applicationId = "$value"',
      );

      TransmuteOperationRunner.checkAllInteractive([op], {'other': 'x'},
          autoConfirm: true, transmuteJsonPath: jsonPath);

      expect(File(jsonPath).readAsStringSync(), contains('"packageName": "com.example.app"'));
    });

    test('mismatched flag op with --filevalue does not write regex match to transmute.json', () {
      const jsonContents = '{\n  "someRemovalFlag": "true"\n}\n';
      File(jsonPath).writeAsStringSync(jsonContents);
      const plist = '<key>Something</key>\nkeep this';
      File(plistPath).writeAsStringSync(plist);
      FlutterAppTransmuter.autoFileValue = true;

      TransmuteOperationRunner.checkAllInteractive([flagOp()], {'someRemovalFlag': 'true'},
          transmuteJsonPath: jsonPath);

      expect(File(jsonPath).readAsStringSync(), jsonContents,
          reason: 'flag key must not be overwritten with a regex match');
      expect(File(plistPath).readAsStringSync(), plist, reason: 'file must not be modified either');
    });

    test('mismatched flag op with --transmutevalue applies the operation to the file', () {
      const jsonContents = '{\n  "someRemovalFlag": "true"\n}\n';
      File(jsonPath).writeAsStringSync(jsonContents);
      File(plistPath).writeAsStringSync('<key>Something</key>\nkeep this');
      FlutterAppTransmuter.autoTransmuteValue = true;

      TransmuteOperationRunner.checkAllInteractive([flagOp()], {'someRemovalFlag': 'true'},
          transmuteJsonPath: jsonPath);

      expect(File(plistPath).readAsStringSync(), 'keep this');
      expect(File(jsonPath).readAsStringSync(), jsonContents);
    });

    test('flag op with disabled value is skipped without prompting', () {
      const jsonContents = '{\n  "someRemovalFlag": "false"\n}\n';
      File(jsonPath).writeAsStringSync(jsonContents);
      const plist = '<key>Something</key>\nkeep this';
      File(plistPath).writeAsStringSync(plist);
      FlutterAppTransmuter.fatalPrompts = true;

      // Would call exit(1) if a prompt were shown.
      TransmuteOperationRunner.checkAllInteractive([flagOp()], {'someRemovalFlag': 'false'},
          transmuteJsonPath: jsonPath);

      expect(File(plistPath).readAsStringSync(), plist);
      expect(File(jsonPath).readAsStringSync(), jsonContents);
    });
  });

  // -----------------------------------------------------------
  // Dry run mode
  // -----------------------------------------------------------
  group('dry run mode', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_test_');
      FlutterAppTransmuter.executingDryRun = true;
      FlutterAppTransmuter.verboseDebug = 0;
    });

    tearDown(() {
      FlutterAppTransmuter.executingDryRun = false;
      tempDir.deleteSync(recursive: true);
    });

    test('executeRegexReplace does not modify file in dry run', () {
      final filePath = '${tempDir.path}/test.txt';
      const original = 'applicationId = "com.old.app"';
      File(filePath).writeAsStringSync(original);

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'regex_replace',
        platform: 'android', file: filePath, jsonKey: 'key',
        regex: r'applicationId\s*=\s*"(.*)"',
        replacement: r'applicationId = "$value"',
      );

      TransmuteOperationRunner.executeRegexReplace(op, 'com.new.app');
      expect(File(filePath).readAsStringSync(), original);
    });

    test('executeExtractAndReplace does not modify file in dry run', () {
      final filePath = '${tempDir.path}/test.txt';
      const original = 'PRODUCT_BUNDLE_IDENTIFIER = com.old.app;';
      File(filePath).writeAsStringSync(original);

      final op = TransmuteOperation(
        id: 'test', description: 'test', type: 'extract_and_replace',
        platform: 'ios', file: filePath, jsonKey: 'key',
        regex: r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*(.*);',
        replacement: r'$value',
      );

      TransmuteOperationRunner.executeExtractAndReplace(op, 'com.new.app');
      expect(File(filePath).readAsStringSync(), original);
    });
  });
}
