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

import 'dart:io';

import 'package:flutter_app_transmuter/src/provision/provision.dart';
import 'package:path/path.dart' as path;
import 'package:test/test.dart';

void main() {
  test('init writes the starter yaml and refuses to overwrite', () {
    final tmp = Directory.systemTemp.createTempSync('prov_init');
    try {
      // NOTE: runProvisionInit takes the directory explicitly - mutating
      // Directory.current in a test races other concurrently-running suites
      // (cwd is process-global in the Dart VM).
      expect(runProvisionInit(tmp.path), 0);
      final f = File(path.join(tmp.path, 'transmute_provisioning.yaml'));
      expect(f.existsSync(), isTrue);
      final text = f.readAsStringSync();
      expect(text, contains('api_keys:'));
      expect(text, contains('customer_id_pattern'));
      expect(text, contains('required_apis:'));
      expect(text, contains('FILL_ME'));
      // second run must not clobber
      expect(runProvisionInit(tmp.path), 1);
    } finally {
      tmp.deleteSync(recursive: true);
    }
  });
}
