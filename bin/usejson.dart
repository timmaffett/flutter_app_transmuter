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
      final sourceFilePath = p.join(jsonDirectory, sourceFileName);
      var fullDestinationPath = p.join(p.current, destinationPath); // paths from JSON are relative to project root.

      // Check if the destination path already has a filename.
      if (p.extension(fullDestinationPath).isNotEmpty) {
        // Destination path includes a filename. Use it as is.
      } else {
        // Destination path is a directory. Append the source filename.
        fullDestinationPath = p.join(fullDestinationPath, sourceFileName);
      }

      final destinationDirectory = p.dirname(fullDestinationPath);

      // Create destination directory if it doesn't exist.
      Directory(destinationDirectory).createSync(recursive: true);

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

    // Copy the file content.
    sourceFile.copySync(destinationPath);

    // Get the source file's metadata.
    final sourceStat = sourceFile.statSync();

    // Get the destination file object *after* it's created.
    final destinationFile = File(destinationPath);

    // Set the destination file's metadata.
    destinationFile.setLastModifiedSync(sourceStat.modified);
    destinationFile.setLastAccessedSync(sourceStat.accessed);

  } catch (e) {
    print('Error copying file: $e');
    rethrow;
  }
}

// Example usage:
void main() {
  // Create a dummy JSON file for testing.
  final jsonFilePath = 'copy_config.json';
  final jsonContent = {
    'copyfiles': {
      'source1.txt': 'destination_dir/copied_file.txt',
      'source2.txt': 'another_dir/',
      'source3.txt': 'another_dir/source3.txt'
    },
  };
  
  File(jsonFilePath).writeAsStringSync(json.encode(jsonContent),flush:true);

  // Create dummy source files.
  File('source1.txt').writeAsStringSync('Source 1 content',flush:true);
  File('source2.txt').writeAsStringSync('Source 2 content',flush:true);
  File('source3.txt').writeAsStringSync('Source 3 content',flush:true);

  //Create destination directories.
  Directory('destination_dir').createSync(recursive: true);
  Directory('another_dir').createSync(recursive: true);

  try {
    copyFilesFromJson(jsonFilePath);

    // Verify files were copied (optional)
    print("Files copied, verifying...");
    final destinationFile1 = File('destination_dir/copied_file.txt');
    final destinationFile2 = File('another_dir/source2.txt');
    final destinationFile3 = File('another_dir/source3.txt');

    if(destinationFile1.existsSync()){
      print("destination_dir/copied_file.txt exists");
    }
    if(destinationFile2.existsSync()){
      print("another_dir/source2.txt exists");
    }
    if(destinationFile3.existsSync()){
      print("another_dir/source3.txt exists");
    }

    print("Test Complete. Results remain in destination_dir and another_dir.");

  } catch (e) {
    print('An error occurred: $e');
  } finally {
    //Clean up only the test json and source files.
    //await File(jsonFilePath).delete();
    //await File('source1.txt').delete();
    //await File('source2.txt').delete();
    //await File('source3.txt').delete();
  }
}