import 'dart:io';
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
    test('matches the version in pubspec.yaml', () {
      final pubspec = File('pubspec.yaml').readAsStringSync();
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
