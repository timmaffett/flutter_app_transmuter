import 'dart:convert';
import 'dart:io';

void main() {

  //setup();

  try {
    final Map<String, dynamic> mainJson =
        jsonDecode(File('main.json').readAsStringSync());

    processIncludes(mainJson);

    print('Processed JSON:');
    final myJsonEncoder =JsonEncoder.withIndent(' ');
    print(myJsonEncoder.convert(mainJson)); // Print the modified mainJson with indentation

  } catch (e) {
    print('Error: $e');
  }
}

void processIncludes(Map<String, dynamic> jsonObject) {
  final keys = jsonObject.keys.toList(); // Create a copy of the keys

  print('processIncludes entered - keys to be examined are $keys');

  for (final key in keys) {
    if (key.startsWith('include')) {
      final includePath = jsonObject[key];
      try {
        final includeJsonString = File(includePath).readAsStringSync();
        final includeJson = jsonDecode(includeJsonString);

        if (includeJson is Map<String, dynamic>) {
          jsonObject.addAll(includeJson); // Merge the included JSON
        } else {
          print('Error: Included JSON file "$includePath" does not contain a JSON object.');
        }

        //jsonObject.remove(key); // Remove the "include" key after processing

      } catch (e) {
        print('Error processing include "$includePath": $e');
      }
    } else if (jsonObject[key] is Map<String, dynamic>) {
      print('SUB processing nested OBJECT key=$key');
      processIncludes(jsonObject[key]); // Recurse for nested objects
    } else if (jsonObject[key] is List) {
      print('SUB processing nested LIST key=$key');
      for (var item in jsonObject[key]) {
        print('Examining item=$item to see if it is a OBJECT we need to SUB PROCESS');
        if(item is Map<String, dynamic>){
          processIncludes(item);
        }
      }
    }
  }
}

// Example usage and file creation
void createExampleFiles() {
  final mainJsonContent = {
    'name': 'Main Object',
    'include_config': 'config.json',
    'nested': {
      'include_nested': 'nested.json',
      'other': 'value'
    },
    'array': [
      {'include_array': 'array.json', 'array_value': 'test'},
      {'array_value_2':'test2'}
    ]
  };

  final configJsonContent = {'setting1': 'value1', 'setting2': 123};
  final nestedJsonContent = {'nestedSetting': true};
  final arrayJsonContent = {'arraySetting': 'arrayValue'};

  final myJsonEncoder =JsonEncoder.withIndent(' ');
  File('main.json').writeAsStringSync(myJsonEncoder.convert(mainJsonContent),flush:true);
  File('config.json').writeAsStringSync(myJsonEncoder.convert(configJsonContent),flush:true);
  File('nested.json').writeAsStringSync(myJsonEncoder.convert(nestedJsonContent),flush:true);
  File('array.json').writeAsStringSync(myJsonEncoder.convert(arrayJsonContent),flush:true);

  print('Example JSON files created.');
}

void setup() {
  createExampleFiles();
}

void runTests(){
  main();
}

void test(){
  setup();
  runTests();
}