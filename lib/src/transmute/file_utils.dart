import 'dart:io';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:chalkdart/chalkstrings.dart';


/// Prints a message with each character colored in a rainbow hue cycle using HSL.
/// The hue changes smoothly across the full 0-360 range, with finer
/// gradations for longer messages.
void printRainbow(String message) {
  if (message.isEmpty) return;
  final runes = message.runes.toList();
  // Calculate visual width: emojis are typically 2 columns wide in the terminal
  int visualWidth = 0;
  for (final rune in runes) {
    visualWidth += _isWideChar(rune) ? 2 : 1;
  }
  final pad = (' ' * visualWidth).onDarkGrey;
  // Find leading/trailing padding boundaries
  int firstNonSpace = runes.indexWhere((r) => r != 0x20);
  int lastNonSpace = runes.lastIndexWhere((r) => r != 0x20);
  if (firstNonSpace == -1) firstNonSpace = 0;
  if (lastNonSpace == -1) lastNonSpace = runes.length - 1;
  final buffer = StringBuffer();
  for (int i = 0; i < runes.length; i++) {
    final char = String.fromCharCode(runes[i]);
    final hue = (i / runes.length) * 360;
    final isPadSpace = char == ' ' && (i < firstNonSpace || i > lastNonSpace);
    final useGrey = _isWideChar(runes[i]) || isPadSpace;
    final bg = useGrey ? char.onDarkGrey : char.onBlack;
    buffer.write(bg.hsl(hue, 1, 0.5));
  }
  print(pad);
  print(buffer.toString());
  print(pad);
}

/// Returns true if a Unicode code point is likely displayed as a wide (2-column) character
/// in the terminal, such as emojis and CJK characters.
bool _isWideChar(int rune) {
  return rune > 0x1F000 || // Emojis (Supplementary Symbols, Emoticons, etc.)
      (rune >= 0x2600 && rune <= 0x27BF) || // Misc symbols, Dingbats
      (rune >= 0x2B50 && rune <= 0x2B55) || // Stars, circles
      (rune >= 0xFE00 && rune <= 0xFE0F) || // Variation selectors
      (rune >= 0x2702 && rune <= 0x27B0) || // Dingbats
      (rune >= 0x3000 && rune <= 0x9FFF) || // CJK
      (rune >= 0xF900 && rune <= 0xFAFF); // CJK Compatibility
}

class FileUtils {
  static void replaceInFile(String path, oldPackage, newPackage) async {
    String? contents = readFileAsString(path);
    if (contents == null) {
      print('ERROR:: file at $path not found'.brightRed);
      return;
    }
    contents = contents.replaceAll(oldPackage, newPackage);
    writeStringToFilename(path, contents);
  }

  static void replaceInFileRegex(String replacementTitle, String path, RegExp regex, String replacement) {
    String? contents = readFileAsString(path);

    if (contents == null) {
      print('ERROR:: file at $path not found'.brightRed);
      return;
    }
    
    //OBSOLETE//contents = contents.replaceAll(regex, replacement);

    var match = regex.firstMatch(contents);
    if (match == null) {
      print('NOTE:: $match not found in file $path'.red);
    } else {

      // NAMESPACE FOUND - REPLACE THE NAMESPACE
      final previousValue = match.group(1) ?? 'NO match found in $path';

      //OBSOLETE//print('Previous value: $previousValue');

      int occurrences = 0;
      contents = contents.replaceAllMapped(regex, (match) {
        if(FlutterAppTransmuter.verboseDebug>0) {
          print('Replacing ${match.group(0)!.brightBlue} with ${replacement.brightGreen}');
        }        
        occurrences++;
        return replacement;
      });
      print('Replaced $occurrences occurrence${(occurrences==0 || occurrences>1) ? 's':''} of $replacementTitle value: ${previousValue.blue} with ${replacement.green}'.limeGreen);
    }


    writeStringToFilename(path, contents);
  }

  static String? readFileAsString(String path) {
    var file = File(path);
    String? contents;

    if (file.existsSync()) {
      contents = file.readAsStringSync();
    }
    return contents;
  }

  static void writeAsStringSync(File file, String contents) {
    if(FlutterAppTransmuter.executingDryRun) {
      print('..dry run - skipping writing ${file.path}'.brightYellow);
    } else {
      file.writeAsStringSync(contents,flush:true);
    }
  }

  static void writeStringToFilename(String path, String contents) {
    if(FlutterAppTransmuter.executingDryRun) {
      print('..dry run - skipping writing ${path}'.brightYellow);
    } else {
      var file = File(path);
      file.writeAsStringSync(contents,flush:true);
    }
  }

  static bool rebrandJSONExist() {
    const filePath = Constants.transmuteDefintionFile;
    final File rebrandFile = File(filePath);
    return rebrandFile.existsSync();
  }

  static bool fileExists(String path) {
    return File(path).existsSync();
  }

  static void copyFile(String sourcePath, String destPath) {
    if (FlutterAppTransmuter.executingDryRun) {
      print('..dry run - skipping copy $sourcePath -> $destPath'.brightYellow);
      return;
    }
    final destFile = File(destPath);
    final destDir = destFile.parent;
    if (!destDir.existsSync()) {
      destDir.createSync(recursive: true);
    }
    File(sourcePath).copySync(destPath);
  }

  static bool compareFiles(String pathA, String pathB) {
    final fileA = File(pathA);
    final fileB = File(pathB);
    if (!fileA.existsSync() || !fileB.existsSync()) {
      return false;
    }
    final bytesA = fileA.readAsBytesSync();
    final bytesB = fileB.readAsBytesSync();
    if (bytesA.length != bytesB.length) {
      return false;
    }
    for (int i = 0; i < bytesA.length; i++) {
      if (bytesA[i] != bytesB[i]) {
        return false;
      }
    }
    return true;
  }
}
