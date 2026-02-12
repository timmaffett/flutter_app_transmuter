import 'dart:io';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:flutter_app_transmuter/src/transmute/file_utils.dart';
import 'package:chalkdart/chalkstrings.dart';


/// [IOSTransmute]
///
class IOSTransmute {
  static final Chalk iosColor = Chalk().cyan;

/* OBSOLETE UNUSED
  static void process(String newPackageName) {
    print(iosColor('Running for ios'));
    if (!File(Constants.iOSProjectPbxprojFile).existsSync()) {
      print('ERROR:: project.pbxproj file not found, '
          'Check if you have a correct ios directory present in your project'
          '\n\nrun " flutter create . " to regenerate missing files.'.brightRed);
      return;
    }
    String? contents = FileUtils.readFileAsString(Constants.iOSProjectPbxprojFile);

    var match = RegExConstants.bundleIdentifierInProjectPbxproj.firstMatch(contents!);
    if (match == null) {
      print('ERROR:: Bundle Identifier not found in project.pbxproj file, '
          'Please file an issue on github with ${Constants.iOSProjectPbxprojFile} '
          'file attached.'.brightRed);
      return;
    }
    var name = match.group(1);
    final String? oldPackageName = name;

    print(iosColor('Old Package Name: $oldPackageName'));

    print(iosColor('Updating project.pbxproj File'));

    _replace(Constants.iOSProjectPbxprojFile, newPackageName, oldPackageName);

    print(iosColor('Finished updating ios bundle identifier'));
  }

  static void _replace(
      String path, String newPackageName, String? oldPackageName) {
    FileUtils.replaceInFile(path, oldPackageName, newPackageName);
  }

  /// Updates CFBundleName
  static void overwriteInfoPlist(String name) {
    final File file = File(Constants.iOSInfoPlistFile);
    if (!file.existsSync()) {
      print('File "${Constants.iOSInfoPlistFile}" does not exist'.brightRed);
      return;
    }

    String contents = file.readAsStringSync();

    const String keyToUpdate = 'CFBundleDisplayName';
    final String newValue = name;

    final RegExp keyRegEx = RegExp('<key>$keyToUpdate</key>\\s*<string>(.*?)</string>');

    int occurrences=0;
    contents = contents.replaceAllMapped(keyRegEx, (match) {
      final String replacement = '<key>$keyToUpdate</key>\n\t<string>$newValue</string>';
      if(FlutterAppTransmuter.verboseDebug>0) {
        print('Replacing ${match.group(0)!.brightBlue} with ${replacement.brightGreen}'.lime);
      }
      occurrences++;
      return replacement;
    });
    print(iosColor('Replaced $occurrences occurrence${(occurrences==0 || occurrences>1) ? 's':''} of ${keyToUpdate.green}'.lime));

    FileUtils.writeAsStringSync(file,contents);
    print(iosColor('${Constants.iOSInfoPlistFile.brightBlue} file updated successfully.'));

    makeChangesInPbxProj(name);
  }

  /// Updates CFBundleDisplayName in PbxProj file
  static void makeChangesInPbxProj(String newAppName) {
    if (!File(Constants.iOSProjectPbxprojFile).existsSync()) {
      print('ERROR:: project.pbxproj file not found, '
          'Check if you have a correct ios directory present in your project'
          '\n\nrun " flutter create . " to regenerate missing files.'.brightRed);
      return;
    }
    String? contents =
    FileUtils.readFileAsString(Constants.iOSProjectPbxprojFile);

    var match = RegExConstants.bundleDisplayNameInInfoPList.firstMatch(contents!);
    if (match != null) {
      var name = match.group(1);
      final String? oldDisplayName = name;

      print(iosColor('Match ${match.group(0)} Found Old Display Name: $oldDisplayName'));

      print(iosColor('Updating project.pbxproj File'));

      _replace(Constants.iOSProjectPbxprojFile, '\"$newAppName\"', oldDisplayName);

      print(iosColor('Finished updating CFBundleDisplayName'));
    } else {
      print(
          'WARNING: CFBundleDisplayName was not found in project.pbxproj file.\n'
              'Skipping Changes...'.brightYellow);
    }
  }

   static void updateGoogleMapsSDKApiKey(String googleMapsSDKApiKey) {
    var manifestFile = File(Constants.iOSAppDelegateSwiftFile);
    if (!manifestFile.existsSync()) {
      print(
          'ERROR:: "$Constants.iOSAppDelegateFile" file not found, Check if you have an ios directory present in your project'
          '\n\nrun ${'flutter create --platforms=ios .'.cyan} to regenerate missing files.'.brightRed);
      return;
    }
    String? contents = manifestFile.readAsStringSync();

    var match = RegExConstants.gmsServicesProvideApiKeyInInfoPList.firstMatch(contents);
    if (match == null) {
      print('ERROR:: GMSServices.provideAPIKey() call not found in AppDelegate.swift file.\n  Transmuter requires the ${'GMSServices.provideAPIKey("...")'.green}\n  line to already be present within the file.'.brightRed);
      return;
    }

    final String? previousGoogleMapAPIKey = match.group(1);

    if(previousGoogleMapAPIKey==null) {
      print('ERROR - match found for regular expression ${RegExConstants.gmsServicesProvideApiKeyInInfoPList} but group(1) was null'.brightRed);
      return;
    }

    print(iosColor('Previous iosGoogleMapAPIKey: $previousGoogleMapAPIKey  changing it to $googleMapsSDKApiKey'));

    int occurrences=0;
    contents = contents.replaceAllMapped(RegExConstants.gmsServicesProvideApiKeyInInfoPList, (match) {
      final String replacement = 'GMSServices.provideAPIKey("$googleMapsSDKApiKey")';
      if(FlutterAppTransmuter.verboseDebug>0) {
        print('Replacing ${match.group(0)!.brightBlue} with ${replacement.brightGreen}'.lime);
      }
      occurrences++;
      return replacement;
    });
    print(iosColor('Replaced $occurrences occurrence${(occurrences==0 || occurrences>1) ? 's':''} of GMSServices.provideAPIKey(): ${previousGoogleMapAPIKey.blue} with ${googleMapsSDKApiKey.green}'.lime));

    FileUtils.writeAsStringSync(manifestFile,contents);
    print(iosColor('Updated Google API Key in AppDelegate.swift File'));
  }
OBSOLETE UNUSED */
}
