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

/// Default, general-purpose `tag_release` configuration shipped with the tool.
///
/// Reproduces the `release/{slug}/{platform}/{version}` tag shape with zero
/// config. Project-specific fields (e.g. a Shorebird `app_id` or an Apple
/// `DEVELOPMENT_TEAM`) are added by a project's own `tag_release:` block in
/// `master_transmute.yaml`. Platform defaults are intentionally unset so the
/// tool prompts when `--platform` is omitted.
const String defaultTagReleaseYaml = r'''
tag_release:
  tag_template: "release/{slug}/{platform}/{version}"
  slug_strip_pattern: '_[0-9]+$'
  version_field: pubspec_version
  required_files:
    - transmute.json
  title: "Release: {appName}"
  metadata:
    - { label: "Brand dir",   value: "{brand_dir}" }
    - { label: "Version",     json_key: pubspec_version }
    - { label: "Platform",    value: "{platform}" }
    - { label: "Bundle ID",   json_key: iosBundleIdentifier }
    - { label: "Base commit", value: "{commit}" }
    - { label: "Flutter",     command: ["flutter", "--version"], first_line: true }
    - { label: "Tagged by",   value: "{git_user}" }
    - { label: "Date",        value: "{date}" }
''';
