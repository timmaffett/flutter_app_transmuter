import 'dart:convert';
import 'dart:io';
import 'package:test/test.dart';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/brand_file_operations.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';

void main() {
  // -----------------------------------------------------------
  // compareVersions
  // -----------------------------------------------------------
  group('compareVersions', () {
    test('equal versions return 0', () {
      expect(BrandFileOperations.compareVersions('1.0.0', '1.0.0'), 0);
    });

    test('equal versions with build numbers return 0', () {
      expect(BrandFileOperations.compareVersions('1.0.0+1', '1.0.0+1'), 0);
    });

    test('higher major version returns positive', () {
      expect(BrandFileOperations.compareVersions('2.0.0', '1.0.0'), greaterThan(0));
    });

    test('lower major version returns negative', () {
      expect(BrandFileOperations.compareVersions('1.0.0', '2.0.0'), lessThan(0));
    });

    test('higher minor version returns positive', () {
      expect(BrandFileOperations.compareVersions('1.2.0', '1.1.0'), greaterThan(0));
    });

    test('lower minor version returns negative', () {
      expect(BrandFileOperations.compareVersions('1.1.0', '1.2.0'), lessThan(0));
    });

    test('higher patch version returns positive', () {
      expect(BrandFileOperations.compareVersions('1.0.2', '1.0.1'), greaterThan(0));
    });

    test('higher build number returns positive', () {
      expect(BrandFileOperations.compareVersions('1.0.0+2', '1.0.0+1'), greaterThan(0));
    });

    test('version with build number greater than without', () {
      expect(BrandFileOperations.compareVersions('1.0.0+1', '1.0.0'), greaterThan(0));
    });

    test('version without build number less than with', () {
      expect(BrandFileOperations.compareVersions('1.0.0', '1.0.0+1'), lessThan(0));
    });

    test('shorter version treated as zero-padded', () {
      expect(BrandFileOperations.compareVersions('1.0', '1.0.1'), lessThan(0));
    });

    test('handles extra segments as zeros', () {
      expect(BrandFileOperations.compareVersions('1.0.0.0', '1.0.0'), 0);
    });

    test('compares multi-digit version numbers', () {
      expect(BrandFileOperations.compareVersions('1.10.0', '1.9.0'), greaterThan(0));
    });

    test('compares large build numbers', () {
      expect(BrandFileOperations.compareVersions('1.0.0+100', '1.0.0+99'), greaterThan(0));
    });

    test('equal semver different build numbers', () {
      expect(BrandFileOperations.compareVersions('1.2.3+4', '1.2.3+5'), lessThan(0));
    });

    test('handles non-numeric segments gracefully', () {
      // Non-numeric parts are parsed as 0
      expect(BrandFileOperations.compareVersions('1.abc.0', '1.0.0'), 0);
    });
  });

  // -----------------------------------------------------------
  // brand_source_directory path normalization
  // -----------------------------------------------------------
  group('brand_source_directory path normalization', () {
    late Directory tempDir;
    late String originalDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmuter_test_');
      originalDir = Directory.current.path;
      Directory.current = tempDir;

      // Create a minimal transmute.json
      File('transmute.json').writeAsStringSync(jsonEncode({
        'packageName': 'com.test.app',
        'appName': 'Test App',
      }));

      // Create a master_transmute.yaml with one file mapping
      File('master_transmute.yaml').writeAsStringSync('files:\n  - lib/config.dart\n');

      // Create a brand directory with the required file
      Directory('brands/acme').createSync(recursive: true);
      Directory('lib').createSync(recursive: true);
      File('lib/config.dart').writeAsStringSync('// config');
      File('brands/acme/config.dart').writeAsStringSync('// config');

      FlutterAppTransmuter.executingDryRun = false;
    });

    tearDown(() {
      Directory.current = originalDir;
      tempDir.deleteSync(recursive: true);
    });

    test('brand_source_directory is written with forward slashes', () {
      BrandFileOperations.copyBrandFiles('brands/acme');

      final contents = File('transmute.json').readAsStringSync();
      final data = jsonDecode(contents) as Map<String, dynamic>;
      final savedPath = data[Constants.brandSourceDirectoryKey] as String;

      // Must not contain backslashes
      expect(savedPath.contains(r'\'), isFalse,
          reason: 'brand_source_directory should use forward slashes');
    });
  });
}
