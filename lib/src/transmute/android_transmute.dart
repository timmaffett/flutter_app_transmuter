import 'dart:io';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:flutter_app_transmuter/src/transmute/file_utils.dart';
import 'package:chalkdart/chalkstrings.dart';

class AndroidTransmuter {
  static final Chalk androidColor = Chalk().orange;

  static void updateMainActivity(String newPackageName) {
    var path = findMainActivity(type: 'java');
    if (path != null) {
      processMainActivity(path, 'java', newPackageName);
    }

    path = findMainActivity(type: 'kotlin');
    if (path != null) {
      processMainActivity(path, 'kotlin', newPackageName);
    }
  }

  static void processMainActivity(File path, String type, String newPackageName) {
    var extension = type == 'java' ? 'java' : 'kt';
    print(androidColor('Project is using $type'));
    print(androidColor('Updating MainActivity.$extension'));
    FileUtils.replaceInFileRegex('`package XYZ` in ${path.path}', path.path, RegExConstants.packageInMainActivity, 'package $newPackageName');

    String newPackagePath = newPackageName.replaceAll('.', '/');
    String newPath = '${Constants.androidActivityPath}$type/$newPackagePath';
    String renamedMainActivityName = '$newPath/MainActivity.$extension';

    if(!FlutterAppTransmuter.executingDryRun) {
      print(androidColor('Creating New Directory Structure'));
      Directory(newPath).createSync(recursive: true);
      path.renameSync(renamedMainActivityName);

      print(androidColor('Deleting old (empty) directories'));

      deleteEmptyDirs(type);
    } else {
      print('dry run - Would Create Directory ${newPath.brightBlue}'.brightYellow);
      print('dry run - Would rename ${path.path.brightBlue} to ${renamedMainActivityName.brightGreen}'.brightYellow);
      print('dry run - Would delete empty directories of type ${type.brightCyan}'.brightYellow);
    }
  }

  /// Delete .DStore file for macOS & Empty dirs
  static void deleteEmptyDirs(String type) {
    if(FlutterAppTransmuter.executingDryRun) {
      print('Error deleteEmptyDirs() called when executing dry run'.brightRed);
      return;
    }

    var dirs = dirContents(Directory(Constants.androidActivityPath + type));
    dirs = dirs.reversed.toList();
    for (var dir in dirs) {
      if (dir is Directory) {
        // Recursively search for and delete .DS_Store files
        dir.listSync(recursive: true).forEach((entity) {
          if (entity is File && entity.uri.pathSegments.last == '.DS_Store') {
            try {
              entity.deleteSync();
              print('Deleted: ${entity.path}'.brightYellow);
            } catch (ex) {
              print('Error deleting file: ${entity.path.brightYellow}, Error: ${ex.toString().brightYellow.onRed}'.brightRed);
            }
          }
        });

        /// Proceed to delete empty dirs
        if (dir.listSync().isEmpty) {
          try {
            dir.deleteSync();
          } catch (ex) {
            print('Error deleting dir: ${dir.toString().brightYellow}, Error: ${ex.toString().brightYellow.onRed}'.brightRed);
          }
        }
      }
    }
  }

  static File? findMainActivity({String type = 'java'}) {
    var files = dirContents(Directory(Constants.androidActivityPath + type));
    String extension = type == 'java' ? 'java' : 'kt';
    for (var item in files) {
      if (item is File) {
        if (item.path.endsWith('MainActivity.$extension')) {
          return item;
        }
      }
    }
    return null;
  }

  static List<FileSystemEntity> dirContents(Directory dir) {
    if (!dir.existsSync()) return [];
    return dir.listSync(recursive: true);
  }
}
