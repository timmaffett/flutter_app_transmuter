import 'dart:io';
import 'dart:isolate';
import 'package:test/test.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';

void main() {
  // -----------------------------------------------------------
  // packageVersion drift guard
  //
  // Constants.packageVersion is what `--version` prints. It is hardcoded
  // (so it works when run via `dart run`, global activation, or a compiled
  // exe) and must be bumped alongside pubspec.yaml on every release.
  // This test fails CI if the two ever drift apart.
  // -----------------------------------------------------------
  group('packageVersion', () {
    test('matches the version in pubspec.yaml', () async {
      // Resolve pubspec.yaml from the package root rather than the working
      // directory: Directory.current is process-global, and other test files
      // (e.g. brand_file_operations_test.dart) temporarily change it while
      // running concurrently in the same process.
      final libUri = await Isolate.resolvePackageUri(Uri.parse('package:flutter_app_transmuter/'));
      expect(libUri, isNotNull, reason: 'could not resolve package root');
      final pubspec = File.fromUri(libUri!.resolve('../pubspec.yaml')).readAsStringSync();
      final match = RegExConstants.versionInPubspecYaml.firstMatch(pubspec);
      expect(match, isNotNull, reason: 'no version: field found in pubspec.yaml');

      final pubspecVersion = match!.group(1)!.trim();
      expect(
        Constants.packageVersion,
        pubspecVersion,
        reason: 'Constants.packageVersion is out of sync with pubspec.yaml. '
            'Update Constants.packageVersion to "$pubspecVersion".',
      );
    });
  });
}
