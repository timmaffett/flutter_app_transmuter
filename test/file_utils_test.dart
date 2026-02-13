import 'dart:io';
import 'package:test/test.dart';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/file_utils.dart';

void main() {
  // -----------------------------------------------------------
  // readFileAsString
  // -----------------------------------------------------------
  group('readFileAsString', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('file_utils_test_');
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('reads existing file', () {
      final path = '${tempDir.path}/test.txt';
      File(path).writeAsStringSync('hello world');
      expect(FileUtils.readFileAsString(path), 'hello world');
    });

    test('returns null for non-existent file', () {
      expect(FileUtils.readFileAsString('${tempDir.path}/nope.txt'), isNull);
    });

    test('reads empty file', () {
      final path = '${tempDir.path}/empty.txt';
      File(path).writeAsStringSync('');
      expect(FileUtils.readFileAsString(path), '');
    });

    test('reads file with unicode content', () {
      final path = '${tempDir.path}/unicode.txt';
      File(path).writeAsStringSync('Hello \u{1F600} World');
      expect(FileUtils.readFileAsString(path), 'Hello \u{1F600} World');
    });

    test('reads multiline file', () {
      final path = '${tempDir.path}/multi.txt';
      File(path).writeAsStringSync('line1\nline2\nline3');
      expect(FileUtils.readFileAsString(path), 'line1\nline2\nline3');
    });
  });

  // -----------------------------------------------------------
  // writeStringToFilename
  // -----------------------------------------------------------
  group('writeStringToFilename', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('file_utils_test_');
      FlutterAppTransmuter.executingDryRun = false;
    });

    tearDown(() {
      FlutterAppTransmuter.executingDryRun = false;
      tempDir.deleteSync(recursive: true);
    });

    test('writes content to file', () {
      final path = '${tempDir.path}/out.txt';
      FileUtils.writeStringToFilename(path, 'written content');
      expect(File(path).readAsStringSync(), 'written content');
    });

    test('overwrites existing file', () {
      final path = '${tempDir.path}/out.txt';
      File(path).writeAsStringSync('old content');
      FileUtils.writeStringToFilename(path, 'new content');
      expect(File(path).readAsStringSync(), 'new content');
    });

    test('skips writing in dry run mode', () {
      FlutterAppTransmuter.executingDryRun = true;
      final path = '${tempDir.path}/out.txt';
      File(path).writeAsStringSync('original');
      FileUtils.writeStringToFilename(path, 'should not be written');
      expect(File(path).readAsStringSync(), 'original');
    });
  });

  // -----------------------------------------------------------
  // fileExists
  // -----------------------------------------------------------
  group('fileExists', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('file_utils_test_');
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('returns true for existing file', () {
      final path = '${tempDir.path}/exists.txt';
      File(path).writeAsStringSync('');
      expect(FileUtils.fileExists(path), true);
    });

    test('returns false for non-existent file', () {
      expect(FileUtils.fileExists('${tempDir.path}/nope.txt'), false);
    });

    test('returns false for directory path', () {
      expect(FileUtils.fileExists(tempDir.path), false);
    });
  });

  // -----------------------------------------------------------
  // compareFiles
  // -----------------------------------------------------------
  group('compareFiles', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('file_utils_test_');
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('returns true for identical files', () {
      final pathA = '${tempDir.path}/a.txt';
      final pathB = '${tempDir.path}/b.txt';
      File(pathA).writeAsStringSync('identical content');
      File(pathB).writeAsStringSync('identical content');
      expect(FileUtils.compareFiles(pathA, pathB), true);
    });

    test('returns false for different content', () {
      final pathA = '${tempDir.path}/a.txt';
      final pathB = '${tempDir.path}/b.txt';
      File(pathA).writeAsStringSync('content A');
      File(pathB).writeAsStringSync('content B');
      expect(FileUtils.compareFiles(pathA, pathB), false);
    });

    test('returns false for different lengths', () {
      final pathA = '${tempDir.path}/a.txt';
      final pathB = '${tempDir.path}/b.txt';
      File(pathA).writeAsStringSync('short');
      File(pathB).writeAsStringSync('much longer content');
      expect(FileUtils.compareFiles(pathA, pathB), false);
    });

    test('returns false when file A does not exist', () {
      final pathB = '${tempDir.path}/b.txt';
      File(pathB).writeAsStringSync('content');
      expect(FileUtils.compareFiles('${tempDir.path}/nope.txt', pathB), false);
    });

    test('returns false when file B does not exist', () {
      final pathA = '${tempDir.path}/a.txt';
      File(pathA).writeAsStringSync('content');
      expect(FileUtils.compareFiles(pathA, '${tempDir.path}/nope.txt'), false);
    });

    test('returns true for empty files', () {
      final pathA = '${tempDir.path}/a.txt';
      final pathB = '${tempDir.path}/b.txt';
      File(pathA).writeAsStringSync('');
      File(pathB).writeAsStringSync('');
      expect(FileUtils.compareFiles(pathA, pathB), true);
    });

    test('compares same file against itself', () {
      final path = '${tempDir.path}/same.txt';
      File(path).writeAsStringSync('self compare');
      expect(FileUtils.compareFiles(path, path), true);
    });

    test('detects single byte difference', () {
      final pathA = '${tempDir.path}/a.txt';
      final pathB = '${tempDir.path}/b.txt';
      File(pathA).writeAsStringSync('abcdef');
      File(pathB).writeAsStringSync('abcdeF');
      expect(FileUtils.compareFiles(pathA, pathB), false);
    });
  });

  // -----------------------------------------------------------
  // copyFile
  // -----------------------------------------------------------
  group('copyFile', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('file_utils_test_');
      FlutterAppTransmuter.executingDryRun = false;
    });

    tearDown(() {
      FlutterAppTransmuter.executingDryRun = false;
      tempDir.deleteSync(recursive: true);
    });

    test('copies file to destination', () {
      final src = '${tempDir.path}/src.txt';
      final dst = '${tempDir.path}/dst.txt';
      File(src).writeAsStringSync('copy me');
      FileUtils.copyFile(src, dst);
      expect(File(dst).readAsStringSync(), 'copy me');
    });

    test('creates destination directories', () {
      final src = '${tempDir.path}/src.txt';
      final dst = '${tempDir.path}/sub/dir/dst.txt';
      File(src).writeAsStringSync('deep copy');
      FileUtils.copyFile(src, dst);
      expect(File(dst).readAsStringSync(), 'deep copy');
    });

    test('overwrites existing destination', () {
      final src = '${tempDir.path}/src.txt';
      final dst = '${tempDir.path}/dst.txt';
      File(src).writeAsStringSync('new content');
      File(dst).writeAsStringSync('old content');
      FileUtils.copyFile(src, dst);
      expect(File(dst).readAsStringSync(), 'new content');
    });

    test('skips copy in dry run mode', () {
      FlutterAppTransmuter.executingDryRun = true;
      final src = '${tempDir.path}/src.txt';
      final dst = '${tempDir.path}/dst.txt';
      File(src).writeAsStringSync('content');
      FileUtils.copyFile(src, dst);
      expect(File(dst).existsSync(), false);
    });
  });

  // -----------------------------------------------------------
  // replaceInFileRegex
  // -----------------------------------------------------------
  group('replaceInFileRegex', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('file_utils_test_');
      FlutterAppTransmuter.executingDryRun = false;
      FlutterAppTransmuter.verboseDebug = 0;
    });

    tearDown(() {
      FlutterAppTransmuter.executingDryRun = false;
      tempDir.deleteSync(recursive: true);
    });

    test('replaces regex match in file', () {
      final path = '${tempDir.path}/test.txt';
      File(path).writeAsStringSync('version: 1.0.0+1');
      final regex = RegExp(r'^version:\s*(.+)$', multiLine: true);
      FileUtils.replaceInFileRegex('version', path, regex, 'version: 2.0.0+5');
      expect(File(path).readAsStringSync(), 'version: 2.0.0+5');
    });

    test('replaces multiple occurrences', () {
      final path = '${tempDir.path}/test.txt';
      File(path).writeAsStringSync('package="old"\npackage="old"');
      final regex = RegExp(r'package="(.*?)"');
      FileUtils.replaceInFileRegex('package', path, regex, 'package="new"');
      expect(File(path).readAsStringSync(), 'package="new"\npackage="new"');
    });

    test('skips writing in dry run mode', () {
      FlutterAppTransmuter.executingDryRun = true;
      final path = '${tempDir.path}/test.txt';
      File(path).writeAsStringSync('version: 1.0.0');
      final regex = RegExp(r'^version:\s*(.+)$', multiLine: true);
      FileUtils.replaceInFileRegex('version', path, regex, 'version: 2.0.0');
      expect(File(path).readAsStringSync(), 'version: 1.0.0');
    });
  });
}
