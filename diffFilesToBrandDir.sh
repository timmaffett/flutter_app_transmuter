#!/bin/bash

# Bash script to DIFF specific files from a given directory to the appropriate directories.

# Check if a directory argument is provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <source_directory>"
  exit 1
fi

source_dir="$1"

# Check if the source directory exists and is a directory
if [ ! -d "$source_dir" ]; then
  echo "Error: Diff directory '$source_dir' does not exist or is not a directory."
  exit 1
fi

echo "Diffing brand files from '$source_dir' using master_transmute.yaml..."
dart run flutter_app_transmuter:main --diff "$source_dir"

exit 0