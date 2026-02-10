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
}
