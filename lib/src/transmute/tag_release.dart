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

import 'package:yaml/yaml.dart';
import 'default_tag_release.dart';

/// One line in the tag annotation. Exactly one source is set.
class TagReleaseMetadataEntry {
  final String label;
  final String? value; // template string, e.g. "{brand_dir}"
  final String? jsonKey; // key read from the brand's transmute.json
  final String? file; // YAML file in the brand dir
  final String? yamlKey; // key read from [file]
  final List<String>? command; // shell command; stdout captured
  final bool firstLine; // keep only first line of command output

  TagReleaseMetadataEntry({
    required this.label,
    this.value,
    this.jsonKey,
    this.file,
    this.yamlKey,
    this.command,
    this.firstLine = false,
  });

  factory TagReleaseMetadataEntry.fromMap(Map map) {
    final cmd = map['command'];
    return TagReleaseMetadataEntry(
      label: map['label'] as String,
      value: map['value'] as String?,
      jsonKey: map['json_key'] as String?,
      file: map['file'] as String?,
      yamlKey: map['yaml_key'] as String?,
      command: cmd == null ? null : (cmd as List).map((e) => e.toString()).toList(),
      firstLine: map['first_line'] == true,
    );
  }
}

class TagReleaseConfig {
  final String tagTemplate;
  final String slugStripPattern;
  final String versionField;
  final List<String> requiredFiles;
  final String title;
  final String? defaultPlatform;
  final Map<String, String> defaultPlatformByOs; // host-os-key -> platform
  final List<TagReleaseMetadataEntry> metadata;

  TagReleaseConfig({
    required this.tagTemplate,
    required this.slugStripPattern,
    required this.versionField,
    required this.requiredFiles,
    required this.title,
    required this.defaultPlatform,
    required this.defaultPlatformByOs,
    required this.metadata,
  });

  /// Build from the shipped defaults only.
  factory TagReleaseConfig.fromDefaults() => fromMergedMap(_defaultMap(), null);

  /// Build from a full YAML document string (test/helper convenience).
  /// The string may be just a `tag_release:` block; merged over defaults.
  factory TagReleaseConfig.fromYamlString(String yamlString) {
    final doc = loadYaml(yamlString);
    final user = (doc is YamlMap) ? doc['tag_release'] : null;
    return fromMergedMap(_defaultMap(), _toPlain(user) as Map?);
  }

  static Map<String, dynamic> _defaultMap() {
    final doc = loadYaml(defaultTagReleaseYaml) as YamlMap;
    return _toPlain(doc['tag_release']) as Map<String, dynamic>;
  }

  /// Merge: user scalar keys override defaults individually; if the user
  /// supplies `metadata`, it replaces the default list wholesale.
  static TagReleaseConfig fromMergedMap(Map defaults, Map? user) {
    final merged = Map<String, dynamic>.from(defaults);
    if (user != null) {
      for (final key in user.keys) {
        merged[key.toString()] = user[key];
      }
    }
    final metaList = (merged['metadata'] as List? ?? const [])
        .map((m) => TagReleaseMetadataEntry.fromMap(m as Map))
        .toList();
    return TagReleaseConfig(
      tagTemplate: merged['tag_template'] as String,
      slugStripPattern: merged['slug_strip_pattern'] as String,
      versionField: merged['version_field'] as String,
      requiredFiles: (merged['required_files'] as List).map((e) => e.toString()).toList(),
      title: merged['title'] as String,
      defaultPlatform: merged['default_platform'] as String?,
      defaultPlatformByOs: parsePlatformByOs(merged['default_platform_by_os'] as String?),
      metadata: metaList,
    );
  }

  /// Parse "windows=android, macosx=ios" into {windows: android, macosx: ios}.
  static Map<String, String> parsePlatformByOs(String? spec) {
    final result = <String, String>{};
    if (spec == null || spec.trim().isEmpty) return result;
    for (final part in spec.split(',')) {
      final kv = part.split('=');
      if (kv.length == 2) {
        result[kv[0].trim().toLowerCase()] = kv[1].trim().toLowerCase();
      }
    }
    return result;
  }

  /// Recursively convert YamlMap/YamlList to plain Map/List.
  static dynamic _toPlain(dynamic node) {
    if (node is YamlMap) {
      return node.map((k, v) => MapEntry(k.toString(), _toPlain(v)));
    }
    if (node is YamlList) {
      return node.map(_toPlain).toList();
    }
    return node;
  }
}
