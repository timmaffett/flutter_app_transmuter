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

import 'dart:convert';
import 'dart:io';
import 'package:chalkdart/chalkstrings.dart';
import 'package:path/path.dart' as path;
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

  /// Build from `master_transmute.yaml` in the current directory, merged over
  /// the shipped defaults. Missing file or missing `tag_release:` -> defaults.
  factory TagReleaseConfig.fromMasterTransmute() {
    final f = File('master_transmute.yaml');
    if (!f.existsSync()) return TagReleaseConfig.fromDefaults();
    try {
      final doc = loadYaml(f.readAsStringSync());
      final user = (doc is YamlMap) ? doc['tag_release'] : null;
      return fromMergedMap(_defaultMap(), _toPlain(user) as Map?);
    } catch (_) {
      return TagReleaseConfig.fromDefaults();
    }
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

class RunResult {
  final String tag;
  final bool success;
  final String message;
  RunResult({required this.tag, required this.success, required this.message});
}

class TagReleaseRunner {
  final TagReleaseConfig config;
  final String workingDir;

  TagReleaseRunner(this.config, {this.workingDir = '.'});

  /// Derive the slug from a brand directory: take the basename, then
  /// repeatedly strip a trailing match of [stripPattern] until none remains.
  static String deriveSlug(String brandDir, String stripPattern) {
    var slug = path.basename(brandDir.endsWith('/') || brandDir.endsWith('\\')
        ? brandDir.substring(0, brandDir.length - 1)
        : brandDir);
    final re = RegExp(stripPattern);
    while (re.hasMatch(slug)) {
      final next = slug.replaceFirst(re, '');
      if (next == slug) break; // guard against zero-width match loops
      slug = next;
    }
    return slug;
  }

  /// Replace `{token}` occurrences using [tokens]; unknown tokens become
  /// the literal string `unknown` (mirrors the shell script's `:-unknown`).
  static String renderTemplate(String template, Map<String, String> tokens) {
    return template.replaceAllMapped(RegExp(r'\{(\w+)\}'), (m) {
      final key = m.group(1)!;
      final v = tokens[key];
      return (v == null || v.isEmpty) ? 'unknown' : v;
    });
  }

  /// ISO-8601 local timestamp with a numeric timezone offset, e.g.
  /// `2026-06-05T14:30:00-0700` (replaces the shell `date +%Y-%m-%dT%H:%M:%S%z`).
  static String formatTagDate(DateTime now) {
    final off = now.timeZoneOffset;
    final sign = off.isNegative ? '-' : '+';
    final hh = off.inHours.abs().toString().padLeft(2, '0');
    final mm = (off.inMinutes.abs() % 60).toString().padLeft(2, '0');
    final base = now.toIso8601String().split('.').first; // drop milliseconds
    return '$base$sign$hh$mm';
  }

  /// Canonical platform values, keyed by their prompt letter.
  static const Map<String, String> platformLetters = {
    'i': 'ios',
    'a': 'android',
    'w': 'windows',
    'm': 'macosx',
    'l': 'linux',
  };

  static String? platformForLetter(String letter) => platformLetters[letter.trim().toLowerCase()];

  /// Map Dart's `Platform.operatingSystem` value to a `default_platform_by_os`
  /// key (`macos` -> `macosx`; others pass through).
  static String hostOsKey(String dartOs) => dartOs == 'macos' ? 'macosx' : dartOs;

  /// Resolve platform without prompting. Returns null if unresolved (the
  /// caller then prompts, or errors under --fatal-prompts).
  /// Order: cliPlatform > default_platform_by_os[hostOs] > default_platform.
  static String? resolvePlatformNonInteractive(
    TagReleaseConfig cfg, {
    required String? cliPlatform,
    required String hostOs,
  }) {
    if (cliPlatform != null && cliPlatform.isNotEmpty) {
      return cliPlatform.toLowerCase();
    }
    final byOs = cfg.defaultPlatformByOs[hostOsKey(hostOs)];
    if (byOs != null && byOs.isNotEmpty) return byOs;
    final def = cfg.defaultPlatform;
    if (def != null && def.isNotEmpty) return def.toLowerCase();
    return null;
  }

  /// Resolve a single metadata entry to its string value.
  /// - value:        render template against [tokens]
  /// - json_key:     look up in [jsonData] (missing -> 'unknown')
  /// - file+yaml_key: read key from a YAML file under [brandDir]
  /// - command:      stdout of the command run in [workingDir] (failure -> 'unknown')
  static String resolveMetadataEntry(
    TagReleaseMetadataEntry e, {
    required Map<String, dynamic> jsonData,
    required String brandDir,
    required String workingDir,
    required Map<String, String> tokens,
  }) {
    if (e.value != null) {
      return renderTemplate(e.value!, tokens);
    }
    if (e.jsonKey != null) {
      final v = jsonData[e.jsonKey];
      return (v == null || v.toString().isEmpty) ? 'unknown' : v.toString();
    }
    if (e.file != null && e.yamlKey != null) {
      final f = File(path.join(brandDir, e.file!));
      if (!f.existsSync()) return 'unknown';
      try {
        final doc = loadYaml(f.readAsStringSync());
        final v = (doc is YamlMap) ? doc[e.yamlKey] : null;
        return (v == null || v.toString().isEmpty) ? 'unknown' : v.toString();
      } catch (_) {
        return 'unknown';
      }
    }
    if (e.command != null && e.command!.isNotEmpty) {
      try {
        final result = Process.runSync(
          e.command!.first,
          e.command!.skip(1).toList(),
          runInShell: true,
          workingDirectory: workingDir,
        );
        if (result.exitCode != 0) return 'unknown';
        var out = (result.stdout as String).trim();
        if (out.isEmpty) return 'unknown';
        if (e.firstLine) out = out.split('\n').first.trim();
        return out;
      } catch (_) {
        return 'unknown';
      }
    }
    return 'unknown';
  }

  /// Parse a transmute.json file into a plain map of string-ish values.
  static Map<String, dynamic> readTransmuteJson(String brandDir) {
    final f = File(path.join(brandDir, 'transmute.json'));
    if (!f.existsSync()) return {};
    try {
      return jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
    } catch (_) {
      return {};
    }
  }

  ProcessResult _git(List<String> args) =>
      Process.runSync('git', args, workingDirectory: workingDir);

  bool _isGitRepo() => _git(['rev-parse', '--git-dir']).exitCode == 0;

  bool _isClean() {
    final r = _git(['status', '--porcelain']);
    return r.exitCode == 0 && (r.stdout as String).trim().isEmpty;
  }

  bool _tagExists(String tag) =>
      _git(['rev-parse', '-q', '--verify', 'refs/tags/$tag']).exitCode == 0;

  String _gitUser() {
    final name = (_git(['config', 'user.name']).stdout as String).trim();
    final email = (_git(['config', 'user.email']).stdout as String).trim();
    if (name.isEmpty && email.isEmpty) return 'unknown';
    return '$name <$email>';
  }

  /// Orchestrate the whole tag-release flow. Pure-ish: side effects are git
  /// calls + (optionally) a stdout prompt provided by [promptPlatform].
  RunResult run({
    required String brandDir,
    required String? cliPlatform,
    required List<String> notes,
    required bool push,
    required bool force,
    required bool dryRun,
    required bool fatalPrompts,
    required String hostOs,
    required DateTime now,
    required String Function() promptPlatform,
  }) {
    if (!_isGitRepo()) {
      return RunResult(tag: '', success: false, message: 'not inside a git repository');
    }
    final brandPath = Directory(path.join(workingDir, brandDir));
    if (!brandPath.existsSync()) {
      return RunResult(tag: '', success: false, message: 'brand dir not found: $brandDir');
    }
    for (final required in config.requiredFiles) {
      if (!File(path.join(brandPath.path, required)).existsSync()) {
        return RunResult(tag: '', success: false, message: 'missing $brandDir/$required');
      }
    }

    final jsonData = readTransmuteJson(brandPath.path);
    final version = jsonData[config.versionField]?.toString() ?? '';
    if (version.isEmpty) {
      return RunResult(
          tag: '', success: false, message: 'no ${config.versionField} in $brandDir/transmute.json');
    }

    // Resolve platform.
    var platform = resolvePlatformNonInteractive(config, cliPlatform: cliPlatform, hostOs: hostOs);
    if (platform == null) {
      if (fatalPrompts) {
        return RunResult(tag: '', success: false, message: 'platform unresolved (--fatal-prompts)');
      }
      platform = promptPlatform();
    }

    final slug = deriveSlug(brandDir, config.slugStripPattern);

    // Build the base token map: all transmute.json string values + built-ins.
    final tokens = <String, String>{};
    jsonData.forEach((k, v) {
      if (v != null) tokens[k] = v.toString();
    });
    tokens['slug'] = slug;
    tokens['platform'] = platform;
    tokens['version'] = version;
    tokens['brand_dir'] = brandDir;
    tokens['commit'] = (_git(['rev-parse', 'HEAD']).stdout as String).trim();
    tokens['git_user'] = _gitUser();
    tokens['date'] = formatTagDate(now);
    if ((tokens['appName'] ?? '').isEmpty) tokens['appName'] = slug; // title fallback (matches script)

    final tag = renderTemplate(config.tagTemplate, tokens);

    // Safety checks. In a real run these are hard refusals; in a dry run they
    // are warnings so the preview (tag name + annotation) is still shown.
    if (!_isClean()) {
      const msg =
          'working tree is not clean. Switch back to your canonical brand and commit first.';
      if (!dryRun) {
        return RunResult(tag: tag, success: false, message: msg);
      }
      print('[dry run] Warning: $msg'.brightYellow);
    }
    if (_tagExists(tag) && !force) {
      final msg = 'tag already exists: $tag (use --force to overwrite)';
      if (!dryRun) {
        return RunResult(tag: tag, success: false, message: msg);
      }
      print('[dry run] Warning: $msg'.brightYellow);
    }

    // Build annotation message.
    final buf = StringBuffer();
    buf.writeln(renderTemplate(config.title, tokens));
    for (final n in notes) {
      if (n.trim().isNotEmpty) {
        buf.writeln();
        buf.writeln('Note: $n');
      }
    }
    buf.writeln();
    for (final entry in config.metadata) {
      final value = resolveMetadataEntry(
        entry,
        jsonData: jsonData,
        brandDir: brandPath.path,
        workingDir: workingDir,
        tokens: tokens,
      );
      buf.writeln('${entry.label.padRight(15)} $value');
    }
    final message = buf.toString();

    if (dryRun) {
      print('[dry run] Would create tag: $tag'.brightCyan);
      print(message);
      return RunResult(tag: tag, success: true, message: 'dry run');
    }

    // Create the tag via a temp message file (cross-platform; avoids stdin pipe).
    final tmpFile = File(
        path.join(Directory.systemTemp.path, 'tagrelease_msg_${tag.replaceAll('/', '_')}.txt'));
    tmpFile.writeAsStringSync(message);
    try {
      final args = force
          ? ['tag', '-a', '-f', tag, '-F', tmpFile.path]
          : ['tag', '-a', tag, '-F', tmpFile.path];
      final r = _git(args);
      if (r.exitCode != 0) {
        return RunResult(tag: tag, success: false, message: 'git tag failed: ${r.stderr}');
      }
    } finally {
      if (tmpFile.existsSync()) tmpFile.deleteSync();
    }

    print('Created annotated tag: $tag'.brightGreen);
    final shown = _git(['tag', '-n99', '-l', tag]).stdout as String;
    print(shown);

    if (push) {
      print('Pushing tag to origin...'.brightGreen);
      final pr = _git(['push', 'origin', tag]);
      if (pr.exitCode != 0) {
        return RunResult(tag: tag, success: false, message: 'git push failed: ${pr.stderr}');
      }
    } else {
      print('To publish this tag, run:\n    git push origin $tag'.brightYellow);
    }

    return RunResult(tag: tag, success: true, message: 'created');
  }
}
