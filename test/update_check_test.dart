import 'dart:convert';
import 'dart:io';
import 'package:test/test.dart';
import 'package:flutter_app_transmuter/src/transmute/update_check.dart';

void main() {
  // -----------------------------------------------------------
  // parseLatestVersion
  // -----------------------------------------------------------
  group('parseLatestVersion', () {
    test('extracts latest.version from pub.dev API JSON', () {
      const body = '{"name":"flutter_app_transmuter","latest":{"version":"2.2.0","pubspec":{}},"versions":[]}';
      expect(UpdateCheck.parseLatestVersion(body), '2.2.0');
    });

    test('returns null for malformed JSON', () {
      expect(UpdateCheck.parseLatestVersion('not json at all'), isNull);
    });

    test('returns null when latest.version is missing', () {
      expect(UpdateCheck.parseLatestVersion('{"name":"x","latest":{}}'), isNull);
    });
  });

  // -----------------------------------------------------------
  // buildUpdateMessage
  // -----------------------------------------------------------
  group('buildUpdateMessage', () {
    test('returns message with versions and activate command when newer', () {
      final msg = UpdateCheck.buildUpdateMessage(current: '2.1.6', latest: '2.2.0');
      expect(msg, isNotNull);
      expect(msg!, contains('2.2.0'));
      expect(msg, contains('2.1.6'));
      expect(msg, contains('dart pub global activate flutter_app_transmuter'));
    });

    test('returns null when versions are equal', () {
      expect(UpdateCheck.buildUpdateMessage(current: '2.1.6', latest: '2.1.6'), isNull);
    });

    test('returns null when local version is ahead of pub.dev', () {
      expect(UpdateCheck.buildUpdateMessage(current: '2.2.0', latest: '2.1.6'), isNull);
    });

    test('treats build number as part of the comparison', () {
      expect(UpdateCheck.buildUpdateMessage(current: '2.1.6', latest: '2.1.7'), isNotNull);
    });
  });

  // -----------------------------------------------------------
  // cache read/write
  // -----------------------------------------------------------
  group('cache', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_update_test_');
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('writeCache/readCache round trip', () {
      final cachePath = '${tempDir.path}/cache.json';
      UpdateCheck.writeCache(cachePath, checkedAtMs: 12345, latest: '2.2.0');
      final cache = UpdateCheck.readCache(cachePath);
      expect(cache, isNotNull);
      expect(cache!['checkedAtMs'], 12345);
      expect(cache['latest'], '2.2.0');
    });

    test('readCache returns null for missing file', () {
      expect(UpdateCheck.readCache('${tempDir.path}/nope.json'), isNull);
    });

    test('readCache returns null for corrupt file', () {
      final cachePath = '${tempDir.path}/cache.json';
      File(cachePath).writeAsStringSync('garbage');
      expect(UpdateCheck.readCache(cachePath), isNull);
    });
  });

  // -----------------------------------------------------------
  // fetchLatestVersion (against a local HTTP server)
  // -----------------------------------------------------------
  group('fetchLatestVersion', () {
    test('fetches latest version from a server', () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      server.listen((request) {
        request.response
          ..headers.contentType = ContentType.json
          ..write(jsonEncode({'name': 'flutter_app_transmuter', 'latest': {'version': '9.9.9'}}))
          ..close();
      });

      final url = Uri.parse('http://127.0.0.1:${server.port}/api/packages/flutter_app_transmuter');
      final latest = await UpdateCheck.fetchLatestVersion(url: url);
      await server.close(force: true);

      expect(latest, '9.9.9');
    });

    test('returns null when the server is unreachable', () async {
      // Bind and immediately close to get a port with nothing listening.
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final port = server.port;
      await server.close(force: true);

      final url = Uri.parse('http://127.0.0.1:$port/nope');
      expect(await UpdateCheck.fetchLatestVersion(url: url), isNull);
    });
  });

  // -----------------------------------------------------------
  // maybeCheckForUpdate (24h cache logic)
  // -----------------------------------------------------------
  group('maybeCheckForUpdate', () {
    late Directory tempDir;
    late String cachePath;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('transmute_update_test_');
      cachePath = '${tempDir.path}/cache.json';
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('fresh cache with newer version returns message without network', () async {
      UpdateCheck.writeCache(cachePath,
          checkedAtMs: DateTime.now().millisecondsSinceEpoch, latest: '9.9.9');

      // Unreachable URL proves the cached value is used instead of the network.
      final url = Uri.parse('http://127.0.0.1:1/nope');
      final msg = await UpdateCheck.maybeCheckForUpdate(
          cacheFilePath: cachePath, url: url, currentVersion: '2.1.6');

      expect(msg, isNotNull);
      expect(msg!, contains('9.9.9'));
    });

    test('fresh cache with same version returns null without network', () async {
      UpdateCheck.writeCache(cachePath,
          checkedAtMs: DateTime.now().millisecondsSinceEpoch, latest: '2.1.6');

      final url = Uri.parse('http://127.0.0.1:1/nope');
      final msg = await UpdateCheck.maybeCheckForUpdate(
          cacheFilePath: cachePath, url: url, currentVersion: '2.1.6');

      expect(msg, isNull);
    });

    test('stale cache triggers a network check and updates the cache', () async {
      UpdateCheck.writeCache(cachePath, checkedAtMs: 0, latest: '0.0.1');

      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      server.listen((request) {
        request.response
          ..headers.contentType = ContentType.json
          ..write(jsonEncode({'latest': {'version': '9.9.9'}}))
          ..close();
      });
      final url = Uri.parse('http://127.0.0.1:${server.port}/x');

      final msg = await UpdateCheck.maybeCheckForUpdate(
          cacheFilePath: cachePath, url: url, currentVersion: '2.1.6');
      await server.close(force: true);

      expect(msg, isNotNull);
      expect(msg!, contains('9.9.9'));
      final cache = UpdateCheck.readCache(cachePath);
      expect(cache!['latest'], '9.9.9');
    });

    test('no cache and unreachable network returns null silently', () async {
      final url = Uri.parse('http://127.0.0.1:1/nope');
      final msg = await UpdateCheck.maybeCheckForUpdate(
          cacheFilePath: cachePath, url: url, currentVersion: '2.1.6');
      expect(msg, isNull);
    });
  });
}
