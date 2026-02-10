import 'dart:convert';
import 'dart:io';
import 'package:yaml/yaml.dart';
import 'package:yaml_writer/yaml_writer.dart';

void main() async {
  try {
    // Read pubspec.yaml
    final pubspecContent = File('fli_pubspec.yaml').readAsStringSync();
    final pubspecYaml = loadYaml(pubspecContent);

    // Extract flutter_launcher_icons section
    if (pubspecYaml.containsKey('flutter_launcher_icons')) {
      final iconsConfig = pubspecYaml['flutter_launcher_icons'];

      Map<String, dynamic> fullConfig = <String, dynamic>{ 'flutter_launcher_icons' : iconsConfig };


      // Convert to JSON
      final myJsonEncoder = JsonEncoder.withIndent('  ');
      final iconsJson = myJsonEncoder.convert(fullConfig);

      // Write JSON file
      File('launcher_icons.json').writeAsStringSync(iconsJson,flush:true);
      print('launcher_icons.json created.');

      // Read JSON and create new YAML
      createYamlFromIconsJson('launcher_icons.json', 'new_pubspec.yaml');
    } else {
      print('flutter_launcher_icons section not found in pubspec.yaml.');
    }
  } catch (e) {
    print('Error: $e');
  }
}
void createYamlFromIconsJson(String jsonFilePath, String outputYamlPath) {
  try {
    final jsonContent = File(jsonFilePath).readAsStringSync();
    final iconsConfig = jsonDecode(jsonContent);

    // Create YAML map
    final yamlMap = iconsConfig; //{'flutter_launcher_icons': iconsConfig};

    // Convert to YAML string using yaml_writer for proper indentation
    final yamlWriter = YamlWriter(indentSize :4, allowUnquotedStrings: false);
    final yamlString = yamlWriter.write(yamlMap);

    // Write YAML file
    File(outputYamlPath).writeAsStringSync(yamlString,flush:true);
    print('$outputYamlPath created.');
  } catch (e) {
    print('Error creating YAML: $e');
  }
}


void createYamlFromIconsJsonORIG(String jsonFilePath, String outputYamlPath) {
  try {
    final jsonContent = File(jsonFilePath).readAsStringSync();
    final iconsConfig = jsonDecode(jsonContent);

    // Create YAML map
    final yamlMap = {'flutter_launcher_icons': iconsConfig};

    // Convert to YAML string using yaml package
    final yamlString = jsonEncode(yamlMap)
        .replaceAll('{', '')
        .replaceAll('}', '')
        .replaceAll('"', '')
        .replaceAll(',', '\n')
        .replaceAll(':', ': '); //basic yaml conversion

    // Write YAML file
    File(outputYamlPath).writeAsStringSync('flutter_launcher_icons:\n' + yamlString,flush:true);
    print('$outputYamlPath created.');
  } catch (e) {
    print('Error creating YAML: $e');
  }
}

// Example pubspec.yaml creation for testing
void createExamplePubspec() {
  final pubspecContent = '''
name: my_app
description: A new Flutter project.

version: 1.0.0+1

environment:
  sdk: ">=3.0.0 <4.0.0"

dependencies:
  flutter:
    sdk: flutter

dev_dependencies:
  flutter_test:
    sdk: flutter

flutter:
  uses-material-design: true

flutter_launcher_icons:
  android: "launcher_icon"
  ios: true
  image_path: "assets/icon/icon.png"
  min_sdk_android: 21
  web:
    generate: true
    image_path: "assets/icon/icon.png"
    background_color: "#hexcode"
    theme_color: "#hexcode"
  windows:
    generate: true
    image_path: "assets/icon/icon.png"
    icon_size: 48
  macos:
    generate: true
    image_path: "assets/icon/icon.png"
''';

  File('pubspec.yaml').writeAsStringSync(pubspecContent,flush:true);
  print('Example pubspec.yaml created.');
}

void setup(){
  createExamplePubspec();
}

void runTests(){
  main();
}

void test(){
  setup();
  runTests();
}