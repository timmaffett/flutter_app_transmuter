import 'dart:io';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:flutter_app_transmuter/src/transmute/file_utils.dart';
import 'package:chalkdart/chalkstrings.dart';
import 'package:chalkdart/chalk_X11.dart';
import 'package:path/path.dart' as path;
/*

GOOGLE MAPS API KEY Replace REGEX
var reg = RegExp(r'android:name="com.google.android.geo.API_KEY"\s*android:value="([^"]*(\\"[^"]*)*)"');


*/

class AndroidTransmuter {
  static final Chalk androidColor = Chalk().orange;

  //UNUSWED//// Path to your Flutter project's Android res directory
  //UNUSWED//static final Directory resDirectory =
  //UNUSWED//    Directory(Constants.androidDrawableResFolder);

/* OBSOLETE UNUSED
  static void processBuildGradleFile(String newPackageName) {
    final gradleFile = File(Constants.androidAppBuildGradleFile);
     if (!gradleFile.existsSync()) {
      print(
          'ERROR:: build.gradle file not found, Check if you have a correct android directory present in your project'
          '\n\nrun " flutter create . " to regenerate missing files.'.brightRed);
      return;
    }
    String? contents = gradleFile.readAsStringSync();

    var match = RegExConstants.applicationIdInBuildGradleKts.firstMatch(contents);
    if (match == null) {
      print('ERROR:: applicationId not found in build.gradle file'.brightRed);
      return;
    }
    final oldPackageName = match.group(1) ?? 'applicationId NOT FOUND';

    print(androidColor('Previous applicationId Package Name: $oldPackageName'));

    int occurrences = 0;
    contents = contents.replaceAllMapped(RegExConstants.applicationIdInBuildGradleKts, (match) {
      final String replacement = 'applicationId = "$newPackageName"';
      if(FlutterAppTransmuter.verboseDebug>0) {
        print('Replacing ${match.group(0)!.brightBlue} with ${replacement.brightGreen}');
      }
      occurrences++;
      return replacement;
    });

    FileUtils.writeAsStringSync(gradleFile,contents);

    print(androidColor('Updated $occurrences occurrence${(occurrences==0 || occurrences>1) ? 's':''} of applicationId Package Name: ${oldPackageName.blue} with ${newPackageName.green}'.lime));

    //OBSOLETE//await _replace(
    //OBSOLETE//    Constants.androidAppBuildGradle, newPackageName, oldPackageName);
  }


  // In build.gradle.kts file WE MUST CHANGE BOTH namespace= and applicationId=
  static void processBuildGradleFileKTS(String newPackageName) {
    final gradleKtsFile = File(Constants.androidAppBuildGradleKTSFile);
     if (!gradleKtsFile.existsSync()) {
      print(
          'ERROR:: ${Constants.androidAppBuildGradleKTSFile.green} file not found, Check if you have a correct android directory present in your project'
          '\n\nrun ${'flutter create --platform=android .'.blue} to regenerate missing files.'.brightRed);
      return;
    }
    String? contents = gradleKtsFile.readAsStringSync();

    int occurrences = 0;  // we use to find the number of things we replace

    // FIRST look for namespace and swap that
    var matchNamespace = RegExConstants.namespaceInBuildGradleKts.firstMatch(contents);
    if (matchNamespace == null) {
      print('NOTE:: namespace not found in build.gradle.kts file ${Constants.androidAppBuildGradleKTSFile}'.red);
    } else {
      // NAMESPACE FOUND - REPLACE THE NAMESPACE
      final oldNamespacePackageName = matchNamespace.group(1) ?? 'NO NAMESPACE found in ${Constants.androidAppBuildGradleKTSFile}';

      print(androidColor('Previous namespace Package Name: $oldNamespacePackageName'));

      occurrences = 0;
      contents = contents.replaceAllMapped(RegExConstants.namespaceInBuildGradleKts, (match) {
        final String replacement = 'namespace = "$newPackageName"';
        if(FlutterAppTransmuter.verboseDebug>0) {
          print('Replacing ${match.group(0)!.brightBlue} with ${replacement.brightGreen}');
        }
        occurrences++;
        return replacement;
      });
      print(androidColor('Replaced $occurrences occurrence${(occurrences==0 || occurrences>1) ? 's':''} of namespace Package Name: ${oldNamespacePackageName.blue} with ${newPackageName.green}'));
    }


    // Now Do applicationId
    var match = RegExConstants.applicationIdInBuildGradleKts.firstMatch(contents);
    if (match == null) {
      print('ERROR:: applicationId not found in build.gradle.kts file'.brightRed);
      return;
    }
    final oldPackageName = match.group(1) ?? 'NO applicationId found to replace';

    print(androidColor('Previous applicationId Package Name: $oldPackageName'));

    occurrences = 0;
    contents = contents.replaceAllMapped(RegExConstants.applicationIdInBuildGradleKts, (match) {
      final String replacement = 'applicationId = "$newPackageName"';
      if(FlutterAppTransmuter.verboseDebug>0) {
        print('Replacing ${match.group(0)!.brightBlue} with ${replacement.brightGreen}');
      }
      occurrences++;
      return replacement;
    });

    print(androidColor('Replaced $occurrences occurrence${(occurrences==0 || occurrences>1) ? 's':''} of applicationId Package Name: ${oldPackageName.blue} with ${newPackageName.green}'.lime));

    // Finally write out the new version of the file
    print(androidColor('Updating build.gradle.kts File'));

    FileUtils.writeAsStringSync(gradleKtsFile,contents);
  }

  static void process(String newPackageName) {
    print(androidColor('Running for android'));
    if (File(Constants.androidAppBuildGradleFile).existsSync()) {
      processBuildGradleFile(newPackageName);
    }

    if (File(Constants.androidAppBuildGradleKTSFile).existsSync()) {
      processBuildGradleFileKTS(newPackageName);
    }

    var mText = 'package="$newPackageName"';
    //OBSOLETE and not specific enough //var mRegex = '(package=.*)';

    print(androidColor('Updating Main Manifest file'));
    FileUtils.replaceInFileRegex('`package=` in Main AndroidManifest.xml', Constants.androidManifestXmlFile, RegExConstants.packageInAndroidManifest, mText);

    print(androidColor('Updating Debug Manifest file'));
    FileUtils.replaceInFileRegex('`package=` in Debug AndroidManifest.xml', Constants.androidDebugManifestXmlFile, RegExConstants.packageInAndroidManifest, mText);

    print(androidColor('Updating Profile Manifest file'));
    FileUtils.replaceInFileRegex('`package=` in Profile AndroidManifest.xml', Constants.androidProfileManifestXmlFile, RegExConstants.packageInAndroidManifest, mText);

    updateMainActivity(newPackageName);
    print(androidColor('Finished updating android package name'));
  }
OBSOLETE UNUSED */

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
    FileUtils.replaceInFileRegex('`package XYZ` in ${path.path}', path.path, RegExConstants.packageInMainActivity, "package $newPackageName");

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

  //NOT USED//static void _replace(
  //NOT USED//    String path, String newPackageName, String? oldPackageName) {
  //NOT USED//  FileUtils.replaceInFile(path, oldPackageName, newPackageName);
  //NOT USED//}

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

/* OBSOLETE UNUSED
  /// Updates App Label
  static void updateAppName(String newAndroidLabelName) {
    final File androidManifestFile = File(Constants.androidManifestXmlFile);
    final List<String> lines = androidManifestFile.readAsLinesSync();

    //print('updateAppName() read ${lines.length} lines from ${Constants.androidManifest}'.green);

    for (int x = 0; x < lines.length; x++) {
      String line = lines[x];

      //print(line.red);

      if (line.contains('android:label')) {
        // Get previous `android:label` so we can display it to user
        var match = RegExConstants.androidLabelInAndroidManifest.firstMatch(line);
        if (match == null) {
          print('ERROR:: android:label= line incorrectly matched'
              'Please file an issue on github with '
              '${Constants.androidManifestXmlFile} file attached.'.brightRed);
          return;
        }
        var previousName = match.group(1);
        final String? oldAndroidLabelName = previousName;

        print(androidColor('Previous `android:label` was "$oldAndroidLabelName"'));
        // END display previous `android:label` for user

        line = line.replaceAll(RegExConstants.androidLabelInAndroidManifest,'android:label="$newAndroidLabelName"');
        lines[x] = line;

        print(androidColor('NEW android:label line=`$line`'));

        lines.add('');
      }
    }
    FileUtils.writeAsStringSync(androidManifestFile,lines.join('\n'));
  }


 static void updateGoogleMapsSDKApiKey(String googleMapsSDKApiKey) async {

    print('Reading from ${Constants.androidManifestXmlFile}');

   // String manifestFullPath = path.absolute(Constants.androidManifest);

    //manifestFullPath = path.normalize(manifestFullPath);

    //print('Absolute path = $manifestFullPath');
    //final manifestFile = File(manifestFullPath); //Constants.androidManifest);

    final manifestFile = File(Constants.androidManifestXmlFile);
    if (!manifestFile.existsSync()) {
      print('ERROR ${Constants.androidManifestXmlFile} FILE NOT FOUND');
      print('ERROR:: AndroidManifest.xml file not found, Check if you have a correct android directory present in your project'
          '\n\nrun " flutter create . " to regenerate missing files.'.brightRed);
      return;
    }

    // KLUDGE weird bug where I HAVE TO MAKE A async file call to get the call to readAsStringSync() to work!!!!!!
    //final stat = await manifestFile.stat();
    //print('size = ${stat.size} changed = ${stat.changed} type=${stat.type}');


    String contents = manifestFile.readAsStringSync();

    //print('Contents are = "${contents.orangeRed}"');

    var match = RegExConstants.androidGoogleMapsAPIKey.firstMatch(contents);
    if (match == null) {
      print('ERROR:: com.google.android.geo.API_KEY not found in AndroidManifest.xml file.\n  Transmuter requires the ${'<meta-data android:name="com.google.android.geo.API_KEY" .../>'.green}\n  tag to already be present within the file.'.brightRed);

      return;
    }

    final String? previousGoogleMapAPIKey = match.group(1);

    if(previousGoogleMapAPIKey==null) {
      print('ERROR - match found for regular expression ${RegExConstants.androidGoogleMapsAPIKey} but group(1) was null'.brightRed);
      return;
    }
    print(androidColor('Previous GoogleMapAPIKey: $previousGoogleMapAPIKey  change it to $googleMapsSDKApiKey'));

    int occurrences = 0;
    contents = contents.replaceAllMapped(RegExConstants.androidGoogleMapsAPIKey, (match) {
      final String newKeyLine = 'android:name="com.google.android.geo.API_KEY" android:value="$googleMapsSDKApiKey"';
      if(FlutterAppTransmuter.verboseDebug>0) {
        print('updateGoogleMapsSDKApiKey() matched ${match.group(0)!.brightGreen}');
        print('   replacing with ${newKeyLine.brightCyan}');
      }
      occurrences++;
      return newKeyLine;
    });
    print(androidColor('Replaced $occurrences occurrence${(occurrences==0 || occurrences>1) ? 's':''} of android:name="com.google.android.geo.API_KEY": ${previousGoogleMapAPIKey.blue} with ${googleMapsSDKApiKey.green}'.lime));

    FileUtils.writeAsStringSync(manifestFile,contents);
    print(androidColor('Updated Google API Key in AndroidManifest.xml File'));
  }
OBSOLETE UNUSED */

}
