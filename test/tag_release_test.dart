import 'package:test/test.dart';
import 'package:yaml/yaml.dart';
import 'package:flutter_app_transmuter/src/transmute/default_tag_release.dart';
import 'package:flutter_app_transmuter/src/transmute/tag_release.dart';

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

  group('TagReleaseConfig', () {
    test('loads from default YAML', () {
      final cfg = TagReleaseConfig.fromDefaults();
      expect(cfg.tagTemplate, 'release/{slug}/{platform}/{version}');
      expect(cfg.versionField, 'pubspec_version');
      expect(cfg.requiredFiles, ['transmute.json']);
      expect(cfg.defaultPlatform, isNull);
      expect(cfg.metadata.length, 8);
      expect(cfg.metadata.first.label, 'Brand dir');
      expect(cfg.metadata.first.value, '{brand_dir}');
    });

    test('user scalar keys override defaults; metadata replaces wholesale', () {
      const userYaml = '''
tag_release:
  tag_template: "rel/{slug}/{version}"
  default_platform: ios
  metadata:
    - { label: "Version", json_key: pubspec_version }
''';
      final cfg = TagReleaseConfig.fromYamlString(userYaml);
      expect(cfg.tagTemplate, 'rel/{slug}/{version}'); // overridden
      expect(cfg.versionField, 'pubspec_version'); // fell back to default
      expect(cfg.defaultPlatform, 'ios'); // from user
      expect(cfg.metadata.length, 1); // replaced wholesale
      expect(cfg.metadata.first.label, 'Version');
    });

    test('parses all four metadata source types', () {
      const userYaml = '''
tag_release:
  metadata:
    - { label: "V", value: "{version}" }
    - { label: "B", json_key: iosBundleIdentifier }
    - { label: "S", file: shorebird.yaml, yaml_key: app_id }
    - { label: "F", command: ["flutter", "--version"], first_line: true }
''';
      final cfg = TagReleaseConfig.fromYamlString(userYaml);
      expect(cfg.metadata[0].value, '{version}');
      expect(cfg.metadata[1].jsonKey, 'iosBundleIdentifier');
      expect(cfg.metadata[2].file, 'shorebird.yaml');
      expect(cfg.metadata[2].yamlKey, 'app_id');
      expect(cfg.metadata[3].command, ['flutter', '--version']);
      expect(cfg.metadata[3].firstLine, isTrue);
    });
  });

  group('TagReleaseRunner pure helpers', () {
    test('deriveSlug strips trailing _<digits> groups repeatedly', () {
      expect(TagReleaseRunner.deriveSlug('fine_335_1535_2185_2190', r'_[0-9]+$'), 'fine');
      expect(TagReleaseRunner.deriveSlug('mke_smartpark_1495', r'_[0-9]+$'), 'mke_smartpark');
      expect(TagReleaseRunner.deriveSlug('netpark_demo_Loyalty', r'_[0-9]+$'), 'netpark_demo_Loyalty');
    });

    test('deriveSlug uses basename of a path', () {
      expect(TagReleaseRunner.deriveSlug('branded/fine_335', r'_[0-9]+$'), 'fine');
    });

    test('renderTemplate substitutes tokens, unknown -> unknown', () {
      final tokens = {'slug': 'fine', 'platform': 'ios', 'version': '2.0.6+22'};
      expect(
        TagReleaseRunner.renderTemplate('release/{slug}/{platform}/{version}', tokens),
        'release/fine/ios/2.0.6+22',
      );
      expect(TagReleaseRunner.renderTemplate('x={missing}', tokens), 'x=unknown');
    });

    test('formatTagDate produces ISO-8601 with numeric offset', () {
      final dt = DateTime(2026, 6, 5, 14, 30, 0);
      final out = TagReleaseRunner.formatTagDate(dt);
      expect(out, matches(r'^2026-06-05T14:30:00[+-]\d{4}$'));
    });
  });
}
