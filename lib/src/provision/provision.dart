//  Copyright 2026 Tim Maffett
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

/// The `transmute provision <verb>` command family: a thin driver in front of
/// the bundled Python provisioning engine (lib/python/brandtool/). The driver
/// finds a working Python 3, verifies the required pip packages, resolves the
/// engine inside this package's pub-cache copy, and runs it with inherited
/// stdio so interactive prompts, colors, Ctrl-C, and exit codes pass through
/// untouched. Everything else in transmute works without Python.
library;

import 'dart:io';
import 'dart:isolate';

import 'package:path/path.dart' as path;

import 'starter_yaml.dart';

/// Result of a captured (non-interactive) process run.
class ProcRes {
  final int exitCode;
  final String stdout;
  final String stderr;
  ProcRes(this.exitCode, this.stdout, this.stderr);
}

/// Seam for tests: real implementation shells out, fakes record calls.
class ProcessRunner {
  Future<ProcRes> run(String exe, List<String> args) async {
    try {
      final r = await Process.run(exe, args, runInShell: true);
      return ProcRes(r.exitCode, r.stdout as String, r.stderr as String);
    } on ProcessException {
      return ProcRes(9009, '', 'not found');
    }
  }

  Future<int> runInteractive(
      String exe, List<String> args, Map<String, String> env) async {
    final p = await Process.start(exe, args,
        mode: ProcessStartMode.inheritStdio,
        environment: {...Platform.environment, ...env});
    return p.exitCode;
  }
}

const pipPackages =
    'google-api-python-client google-auth requests PyJWT cryptography pyyaml';

/// One-liner import probe; non-zero exit => something is missing.
const depProbeSnippet =
    'import googleapiclient, google.auth, requests, jwt, cryptography, yaml';

const provisionVerbs = [
  'init',
  'audit',
  'audit-unique',
  'create-project',
  'create-apps',
  'create-keys',
  'create',
  'create-apple',
  'add-asc-key',
  'check-agreements',
  'check-personal-ios-dev-certs',
];

/// Try candidates in order; each must run `--version` successfully AND print a
/// real Python 3 version. The Windows Store alias fails that probe (non-zero
/// exit / an install hint instead of a version string).
Future<String?> findPythonAsync(ProcessRunner runner) async {
  final candidates = Platform.isWindows
      ? ['py -3', 'python3', 'python']
      : ['python3', 'python'];
  for (final cand in candidates) {
    final parts = cand.split(' ');
    final r = await runner.run(parts.first, [...parts.skip(1), '--version']);
    if (r.exitCode == 0 &&
        (r.stdout.contains('Python 3') || r.stderr.contains('Python 3'))) {
      return cand;
    }
  }
  return null;
}

Future<String> _engineScript(String? packageRootOverride) async {
  if (packageRootOverride != null) {
    return path.join(
        packageRootOverride, 'lib', 'python', 'brandtool', 'brandtool.py');
  }
  final uri = await Isolate.resolvePackageUri(Uri.parse(
      'package:flutter_app_transmuter/python/brandtool/brandtool.py'));
  if (uri == null) {
    throw StateError('cannot locate the bundled provisioning engine');
  }
  return File.fromUri(uri).path;
}

Future<int> runProvision(List<String> args,
    {ProcessRunner? runner, String? packageRootOverride}) async {
  final r = runner ?? ProcessRunner();
  if (args.isEmpty || args.first == '--help' || args.first == '-h') {
    stdout.writeln('usage: transmute provision <verb> [args...]');
    stdout.writeln('verbs: ${provisionVerbs.join(', ')}');
    stdout.writeln('Configure a project with: transmute provision init '
        '(writes transmute_provisioning.yaml)');
    return args.isEmpty ? 64 : 0;
  }
  if (args.first == 'init') {
    return runProvisionInit(Directory.current.path);
  }
  final python = await findPythonAsync(r);
  if (python == null) {
    stderr.writeln('provision: Python 3 not found on PATH.');
    stderr.writeln('Install Python 3.10+ (https://www.python.org/downloads/) '
        'and re-run. The rest of transmute works without it.');
    return 1;
  }
  final pyParts = python.split(' ');
  final probe =
      await r.run(pyParts.first, [...pyParts.skip(1), '-c', depProbeSnippet]);
  if (probe.exitCode != 0) {
    stderr.writeln('provision: required Python packages are missing.');
    stderr.writeln('Install them with:');
    stderr.writeln('  $python -m pip install $pipPackages');
    final detail = probe.stderr.trim().split('\n');
    if (detail.isNotEmpty && detail.last.isNotEmpty) {
      stderr.writeln('(detail: ${detail.last})');
    }
    return 1;
  }
  final engine = await _engineScript(packageRootOverride);
  return r.runInteractive(pyParts.first, [...pyParts.skip(1), engine, ...args],
      {'TRANSMUTER_PROJECT_ROOT': Directory.current.path});
}

/// `provision init`: write the commented starter config (pure Dart - works
/// before Python is even installed). Refuses to overwrite.
int runProvisionInit(String projectDir) {
  final f = File(path.join(projectDir, 'transmute_provisioning.yaml'));
  if (f.existsSync()) {
    stderr.writeln(
        'transmute_provisioning.yaml already exists - not overwriting.');
    return 1;
  }
  f.writeAsStringSync(starterProvisioningYaml);
  stdout.writeln('wrote transmute_provisioning.yaml - fill in the marked '
      'values, then run: transmute provision audit');
  return 0;
}
