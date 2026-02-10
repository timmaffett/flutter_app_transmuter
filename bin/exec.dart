import 'dart:convert';
import 'dart:io';

void main() async {

  createSampleJson();

  final jsonString = File('commands.json').readAsStringSync(); // Read the JSON file
  final Map<String, dynamic> jsonData = jsonDecode(jsonString);

  if (jsonData.containsKey('exec') && jsonData['exec'] is List) {
    final List<String> commands = List<String>.from(jsonData['exec']);
    await executeCommands(commands);
  } else {
    print('JSON file does not contain a valid "exec" key.');
  }
}

Future<void> executeCommands(List<String> commands) async {
  for (final command in commands) {
    try {
      final process = await Process.run(
        command.split(' ')[0], // Command itself
        command.split(' ').skip(1).toList(), // Arguments
        runInShell: true, // Crucial for shell commands
      );

      if (process.exitCode == 0) {
        print('Command executed successfully: $command');
        if (process.stdout.isNotEmpty) {
          print(process.stdout);
        }
        if (process.stderr.isNotEmpty) {
          print(process.stderr);
        }
      } else {
        print('Command failed: $command');
        print(process.stderr);
        print(process.stdout);
        print('Exit code: ${process.exitCode}');
        break; // Stop execution on error, or remove to continue
      }
    } catch (e) {
      print('Error executing command "$command": $e');
      break; // Stop execution on error, or remove to continue
    }
  }
}

// Create a sample commands.json file for testing.
void createSampleJson() {
  final jsonContent = {
    'exec': ['dir', 'ls -l', "echo 'Hello from Dart'"]
  };
  File('commands.json').writeAsStringSync(jsonEncode(jsonContent),flush:true);
  print('Created sample commands.json file.');
}