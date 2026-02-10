import 'dart:io';

void copyFileWithMetadataBROKEN(String sourcePath, String destinationPath) {
  try {
    final sourceFile = File(sourcePath);
    final destinationFile = File(destinationPath);

    if (!sourceFile.existsSync()) {
      throw FileSystemException("Source file not found", sourcePath);
    }

    // Copy the file content.
    sourceFile.copySync(destinationPath);

    // Get the source file's metadata.
    final sourceStat = sourceFile.statSync();

    // Set the destination file's metadata.
    destinationFile.setLastModifiedSync(sourceStat.modified);
    destinationFile.setLastAccessedSync(sourceStat.accessed); //Often not relevant, but included for completeness.
    //Note: Dart's File class does not provide a direct method to set the file's creation time.
    //On some operating systems, and file systems, creation time may not be available or modifiable.

    print('File copied successfully with metadata.');

  } catch (e) {
    print('Error copying file: $e');
    rethrow; // Optionally rethrow the exception if needed.
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

    print('File copied successfully with metadata.');

  } catch (e) {
    print('Error copying file: $e');
    rethrow;
  }
}
// Example usage:
Future<void> main() async {
  final sourceFilePath = 'source.txt'; // Replace with your source file path.
  final destinationFilePath = 'destination.txt'; // Replace with your destination file path.

  // Create a dummy source file for testing.
  final sourceFile = File(sourceFilePath);
  sourceFile.writeAsStringSync('This is a test file.',flush:true);
  sourceFile.setLastModifiedSync(DateTime.now().subtract(Duration(days: 1))); //set modification time to yesterday.

  try {
    copyFileWithMetadata(sourceFilePath, destinationFilePath);

    final destinationFile = File(destinationFilePath);
    final destinationStat = destinationFile.statSync();
    final sourceStat = sourceFile.statSync();

    print("Source modified: ${sourceStat.modified}");
    print("Destination modified: ${destinationStat.modified}");

    if(sourceStat.modified == destinationStat.modified){
      print("Modified dates match!");
    } else {
      print("Modified dates DO NOT match!");
    }

    //Clean up test files.
    //await sourceFile.delete();
    //await destinationFile.delete();

  } catch (e) {
    print('An error occurred during the example: $e');
  }
}