import 'package:test/test.dart';
import 'package:yaml/yaml.dart';
import 'package:flutter_app_transmuter/src/transmute/default_tag_release.dart';

void main() {
  group('defaultTagReleaseYaml', () {
    test('parses and exposes the general default keys', () {
      final doc = loadYaml(defaultTagReleaseYaml) as YamlMap;
      final tr = doc['tag_release'] as YamlMap;
      expect(tr['tag_template'], 'release/{slug}/{platform}/{version}');
      expect(tr['slug_strip_pattern'], r'_[0-9]+$');
      expect(tr['version_field'], 'pubspec_version');
      expect((tr['required_files'] as YamlList).toList(), ['transmute.json']);
      expect(tr['default_platform'], isNull);
      expect(tr['default_platform_by_os'], isNull);
      expect(tr['metadata'], isA<YamlList>());
    });
  });
}
