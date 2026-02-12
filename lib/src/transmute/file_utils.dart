import 'dart:io';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:chalkdart/chalkstrings.dart';


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
