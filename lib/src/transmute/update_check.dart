import 'dart:convert';
import 'dart:io';
import 'package:chalkdart/chalkstrings.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:flutter_app_transmuter/src/transmute/brand_file_operations.dart';

/// Checks pub.dev for a newer published version of flutter_app_transmuter.
///
/// Regular commands call [maybeCheckForUpdate] which consults a small cache
/// file so the network is hit at most once every [cacheDuration]; the
/// `--check_pubdev` command calls [forcedCheck] which always queries pub.dev.
/// All failures (offline, timeout, bad response) are silent for the cached
/// check - the tool must never break or slow down because pub.dev is
/// unreachable.
class UpdateCheck {
  static final Uri pubDevUrl = Uri.parse('https://pub.dev/api/packages/flutter_app_transmuter');
  static const Duration cacheDuration = Duration(hours: 24);
  static const Duration networkTimeout = Duration(seconds: 3);

  static String get updateCommand => 'dart pub global activate flutter_app_transmuter';

  static String defaultCacheFilePath() =>
      '${Directory.systemTemp.path}${Platform.pathSeparator}flutter_app_transmuter_update_check.json';

  /// Extracts `latest.version` from a pub.dev package-API JSON body.
  /// Returns null on any parse problem.
  static String? parseLatestVersion(String jsonBody) {
    try {
      final data = jsonDecode(jsonBody);
      final version = (data as Map<String, dynamic>)['latest']?['version'];
      if (version is String && version.isNotEmpty) return version;
    } catch (_) {}
    return null;
  }

  /// Returns a user-facing update notice when [latest] is newer than
  /// [current], or null when up to date (or ahead, e.g. a local dev build).
  static String? buildUpdateMessage({required String current, required String latest}) {
    if (BrandFileOperations.compareVersions(current, latest) >= 0) return null;
    return 'A newer version of flutter_app_transmuter is available: '
        '${latest.brightGreen} (current: $current)\n'
        'Update with: ${updateCommand.brightCyan}';
  }

  /// Fetches the latest published version from pub.dev (or [url] override).
  /// Returns null on any failure - never throws.
  static Future<String?> fetchLatestVersion({Uri? url, Duration timeout = networkTimeout}) async {
    final client = HttpClient()..connectionTimeout = timeout;
    try {
      final request = await client.getUrl(url ?? pubDevUrl).timeout(timeout);
      final response = await request.close().timeout(timeout);
      if (response.statusCode != HttpStatus.ok) return null;
      final body = await response.transform(utf8.decoder).join().timeout(timeout);
      return parseLatestVersion(body);
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  /// Reads the cache file: {"checkedAtMs": int, "latest": String}.
  /// Returns null if missing or unreadable.
  static Map<String, dynamic>? readCache(String cacheFilePath) {
    try {
      final file = File(cacheFilePath);
      if (!file.existsSync()) return null;
      final data = jsonDecode(file.readAsStringSync());
      if (data is Map<String, dynamic> && data['checkedAtMs'] is int && data['latest'] is String) {
        return data;
      }
    } catch (_) {}
    return null;
  }

  static void writeCache(String cacheFilePath, {required int checkedAtMs, required String latest}) {
    try {
      File(cacheFilePath).writeAsStringSync(jsonEncode({'checkedAtMs': checkedAtMs, 'latest': latest}));
    } catch (_) {}
  }

  /// Cached update check used on normal command runs. Queries pub.dev at most
  /// once every [cacheDuration]; between checks the cached latest version is
  /// still compared so an available update keeps being reported until
  /// installed. Returns the update notice, or null (up to date / any failure).
  static Future<String?> maybeCheckForUpdate({
    String? cacheFilePath,
    Uri? url,
    String? currentVersion,
  }) async {
    final current = currentVersion ?? Constants.packageVersion;
    final cachePath = cacheFilePath ?? defaultCacheFilePath();

    final cache = readCache(cachePath);
    if (cache != null) {
      final age = DateTime.now().millisecondsSinceEpoch - (cache['checkedAtMs'] as int);
      if (age >= 0 && age < cacheDuration.inMilliseconds) {
        return buildUpdateMessage(current: current, latest: cache['latest'] as String);
      }
    }

    final latest = await fetchLatestVersion(url: url);
    if (latest == null) return null;
    writeCache(cachePath, checkedAtMs: DateTime.now().millisecondsSinceEpoch, latest: latest);
    return buildUpdateMessage(current: current, latest: latest);
  }

  /// Forced check for the `--check_pubdev` command: always queries pub.dev
  /// and always prints an outcome (newer / up to date / unreachable).
  static Future<void> forcedCheck({Uri? url, String? currentVersion}) async {
    final current = currentVersion ?? Constants.packageVersion;
    print('flutter_app_transmuter $current');
    print('Checking pub.dev for the latest published version...');

    final latest = await fetchLatestVersion(url: url);
    if (latest == null) {
      print('Could not reach pub.dev (offline?). Try again later.'.brightYellow);
      return;
    }
    writeCache(defaultCacheFilePath(), checkedAtMs: DateTime.now().millisecondsSinceEpoch, latest: latest);

    final message = buildUpdateMessage(current: current, latest: latest);
    if (message != null) {
      print(message);
    } else if (BrandFileOperations.compareVersions(current, latest) > 0) {
      print('Your version ($current) is ahead of the latest published version ($latest).'.brightYellow);
    } else {
      print('You are running the latest published version ($latest).'.brightGreen);
      print('(Re-running "$updateCommand" always installs the latest release.)');
    }
  }
}
