import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;

void copyFilesFromJson(String jsonFilePath) {
  try {
    final jsonFile = File(jsonFilePath);
    if (!jsonFile.existsSync()) {
      throw FileSystemException('JSON file not found: $jsonFilePath');
    }

    final jsonString = jsonFile.readAsStringSync();
    final jsonData = json.decode(jsonString);

    if (jsonData is! Map || !jsonData.containsKey('copyfiles') || jsonData['copyfiles'] is! Map) {
      throw FormatException('Invalid JSON format');
    }

    final copyFiles = jsonData['copyfiles'] as Map<String, dynamic>;
    final jsonDirectory = p.dirname(jsonFilePath);

    for (final sourceFileName in copyFiles.keys) {
      final destinationPath = copyFiles[sourceFileName] as String;
      String sourceFilePath = sourceFileName; // Default to sourceFileName

      print('sourceFileName=$sourceFileName  absolute=${p.isAbsolute(sourceFileName)}  dirname=${p.dirname(sourceFileName)}');

      if (!p.isAbsolute(sourceFileName) && (p.dirname(sourceFileName) == "." && !sourceFilePath.startsWith('.')) ) { //if not absolute and no directory, prepend jsonDirectory
          sourceFilePath = p.join(jsonDirectory, sourceFileName);
      }

      String fullDestinationPath = p.join(p.current, destinationPath);

      if (p.extension(fullDestinationPath).isNotEmpty) {
        // Destination path includes a filename. Use it as is.
      } else {
        fullDestinationPath = p.join(fullDestinationPath, p.basename(sourceFileName)); //use basename of source.
      }

      final destinationDirectory = p.dirname(fullDestinationPath);

      if (!Directory(destinationDirectory).existsSync()) {
        Directory(destinationDirectory).createSync(recursive: true);
      }

      copyFileWithMetadata(sourceFilePath, fullDestinationPath);
    }

    print('Files copied successfully.');
  } catch (e) {
    print('Error processing JSON file: $e');
    rethrow;
  }
}

void copyFileWithMetadata(String sourcePath, String destinationPath) {
  try {
    final sourceFile = File(sourcePath);

    if (!sourceFile.existsSync()) {
      throw FileSystemException("Source file not found", sourcePath);
    }

    sourceFile.copySync(destinationPath);

    final sourceStat = sourceFile.statSync();
    final destinationFile = File(destinationPath);

    destinationFile.setLastModifiedSync(sourceStat.modified);
    destinationFile.setLastAccessedSync(sourceStat.accessed);

  } catch (e) {
    print('Error copying file: $e');
    rethrow;
  }
}

void main(List<String> arguments) {
  if (arguments.isEmpty) {
    print('Usage: dart copy_files.dart <copy_config.json>');
    return;
  }

  final jsonFilePath = arguments[0];

  try {
    copyFilesFromJson(jsonFilePath);
    print("Copy process completed.");

  } catch (e) {
    print('An error occurred: $e');
  }
}