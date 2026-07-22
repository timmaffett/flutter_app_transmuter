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

import 'package:flutter_app_transmuter/src/provision/provision.dart';
import 'package:test/test.dart';

class FakeRunner implements ProcessRunner {
  final Map<String, ProcRes> results; // key: "exe args-joined"
  final List<List<String>> interactiveCalls = [];
  final int interactiveExit;
  FakeRunner(this.results, {this.interactiveExit = 0});
  @override
  Future<ProcRes> run(String exe, List<String> args) async =>
      results['$exe ${args.join(' ')}'] ?? ProcRes(9009, '', 'not found');
  @override
  Future<int> runInteractive(
      String exe, List<String> args, Map<String, String> env) async {
    interactiveCalls.add([exe, ...args, env['TRANSMUTER_PROJECT_ROOT'] ?? '']);
    return interactiveExit;
  }
}

void main() {
  test('findPythonAsync rejects broken candidates and picks a real one',
      () async {
    final runner = FakeRunner({
      'py -3 --version': ProcRes(9009, '', ''),
      // Windows Store alias: exits non-zero with an install hint
      'python3 --version': ProcRes(49, '', 'was not found'),
      'python --version': ProcRes(0, 'Python 3.12.4', ''),
    });
    expect(await findPythonAsync(runner), 'python');
  });

  test('findPythonAsync returns null when nothing works', () async {
    final runner = FakeRunner({});
    expect(await findPythonAsync(runner), isNull);
  });

  test('runProvision fails clearly with no python', () async {
    final code = await runProvision(['audit'], runner: FakeRunner({}));
    expect(code, isNot(0));
  });

  test('runProvision fails clearly when pip deps are missing', () async {
    final runner = FakeRunner({
      'python --version': ProcRes(0, 'Python 3.12.4', ''),
      'python -c $depProbeSnippet':
          ProcRes(1, '', "ModuleNotFoundError: No module named 'yaml'"),
    });
    final code = await runProvision(['audit'],
        runner: runner, packageRootOverride: '/pkg');
    expect(code, isNot(0));
    expect(runner.interactiveCalls, isEmpty);
  });

  test('runProvision passes verb+args through and sets project root env',
      () async {
    final runner = FakeRunner({
      'python --version': ProcRes(0, 'Python 3.12.4', ''),
      'python -c $depProbeSnippet': ProcRes(0, '', ''),
    });
    final code = await runProvision(['audit', 'active', '--noprompt'],
        runner: runner, packageRootOverride: '/pkg');
    expect(code, 0);
    final call = runner.interactiveCalls.single;
    expect(call[0], 'python');
    expect(call[1].replaceAll('\\', '/'),
        '/pkg/lib/python/brandtool/brandtool.py');
    expect(call.sublist(2, 5), ['audit', 'active', '--noprompt']);
    expect(call.last, isNotEmpty); // TRANSMUTER_PROJECT_ROOT set to cwd
  });

  test('bare provision without python falls back to short usage, nonzero',
      () async {
    expect(await runProvision([], runner: FakeRunner({})), isNot(0));
  });

  test('bare provision with python delegates to the engine usage guide',
      () async {
    final runner = FakeRunner({
      'python --version': ProcRes(0, 'Python 3.12.4', ''),
      'python -c $depProbeSnippet': ProcRes(0, '', ''),
    });
    expect(
        await runProvision([], runner: runner, packageRootOverride: '/pkg'), 0);
    final call = runner.interactiveCalls.single;
    expect(call[1], endsWith('brandtool.py'));
    expect(call.length, 3); // exe, engine, env marker - no extra args
  });
}
