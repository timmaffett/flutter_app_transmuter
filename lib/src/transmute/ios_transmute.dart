import 'dart:io';
import 'package:flutter_app_transmuter/flutter_app_transmuter.dart';
import 'package:flutter_app_transmuter/src/transmute/constants.dart';
import 'package:flutter_app_transmuter/src/transmute/file_utils.dart';
import 'package:chalkdart/chalkstrings.dart';


/// [IOSTransmute]
///
class IOSTransmute {
  static final Chalk iosColor = Chalk().cyan;

  static void process(String newPackageName) {
    print(iosColor('Running for ios'));
    if (!File(Constants.iOSProjectPbxprojFile).existsSync()) {
      print('ERROR:: project.pbxproj file not found, '
          'Check if you have a correct ios directory present in your project'
          '\n\nrun " flutter create . " to regenerate missing files.'.brightRed);
      return;
    }
    String? contents = FileUtils.readFileAsString(Constants.iOSProjectPbxprojFile);

    //OBSOLETE//var reg = RegExp(r'PRODUCT_BUNDLE_IDENTIFIER\s*=?\s*(.*);',
    //OBSOLETE//    caseSensitive: true, multiLine: false);
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

// KLUDGE FIX THIS

    print(iosColor('Updating project.pbxproj File'));

    //WE WANT THE MORE GENERAL BELOW BECAUSE OF XXYZ.RunnerTests, etc. //var replacement = 'PRODUCT_BUNDLE_IDENTIFIER = $newPackageName';
    //WE WANT THE MORE GENERAL BELOW BECAUSE OF XXYZ.RunnerTests, etc. //FileUtils.replaceInFileRegex('`PRODUCT_BUNDLE_IDENTIFIER=` in $Constants.iOSProjectPbxprojFile', Constants.iOSProjectPbxprojFile, RegExConstants.bundleIdentifierInProjectPbxproj, replacement);

    _replace(Constants.iOSProjectPbxprojFile, newPackageName, oldPackageName);

    print(iosColor('Finished updating ios bundle identifier'));
  }

  static void _replace(
      String path, String newPackageName, String? oldPackageName) {
    FileUtils.replaceInFile(path, oldPackageName, newPackageName);
  }

  /// Updates CFBundleName
  static void overwriteInfoPlist(String name) {
    // Read the file as a string
    final File file = File(Constants.iOSInfoPlistFile);
    if (!file.existsSync()) {
      print('File "${Constants.iOSInfoPlistFile}" does not exist'.brightRed);
      return;
    }

    String contents = file.readAsStringSync();

    // Find the key and replace the corresponding value
    const String keyToUpdate = 'CFBundleDisplayName';
    final String newValue = name;

    final RegExp keyRegEx = RegExp('<key>$keyToUpdate</key>\\s*<string>(.*?)</string>');

    //OBSOLETE//// Example: Search for the key and its value and replace the value
    //OBSOLETE//contents = contents.replaceAllMapped(
    //OBSOLETE//  RegExp('<key>$keyToUpdate</key>\\s*<string>(.*?)</string>'),
    //OBSOLETE//  (match) => '<key>$keyToUpdate</key>\n\t<string>$newValue</string>',
    //OBSOLETE//);

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



    // Write the updated content back to the file
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

    //OBSOLETE//var reg = RegExp(r'INFOPLIST_KEY_CFBundleDisplayName\s*=?\s*(.*);',
    //OBSOLETE//    caseSensitive: true, multiLine: false);
    var match = RegExConstants.bundleDisplayNameInInfoPList.firstMatch(contents!);
    if (match != null) {
      var name = match.group(1);
      final String? oldDisplayName = name;

      print(iosColor('Match ${match.group(0)} Found Old Display Name: $oldDisplayName'));

      print(iosColor('Updating project.pbxproj File'));
      
      //WE WANT THE MORE GENERAL BELOW//var replacement = 'INFOPLIST_KEY_CFBundleDisplayName = \"$newAppName\"';
      //WE WANT THE MORE GENERAL BELOW//FileUtils.replaceInFileRegex('`INFOPLIST_KEY_CFBundleDisplayName=` in $Constants.iOSProjectPbxprojFile', Constants.iOSProjectPbxprojFile, RegExConstants.bundleDisplayNameInInfoPList, replacement);

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

    //OBSOLETE//final regex = RegExp(r'GMSServices\.provideAPIKey\("([^"]+)"\)',
    //OBSOLETE//    caseSensitive: true, multiLine: true);
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

    //OBSOLETE//contents = contents.replaceAllMapped(regex, (match) {
    //OBSOLETE//  return 'GMSServices.provideAPIKey("$googleMapsSDKApiKey")';
    //OBSOLETE//});

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
}
