#!/bin/bash

# Bash script to diff brand files and check transmute values against the project.
#
# Usage:
#   diffFilesToBrandDir.sh [source_directory]
#
# If no directory is given, uses --status which falls back to brand_source_directory in transmute.json.

if [ $# -eq 0 ]; then
  echo "No directory specified, using --status to diff brand files and check transmute values..."
  dart run flutter_app_transmuter:main --status
else
  source_dir="$1"

  # Check if the source directory exists and is a directory
  if [ ! -d "$source_dir" ]; then
    echo "Error: Diff directory '$source_dir' does not exist or is not a directory."
    exit 1
  fi

  echo "Diffing brand files from '$source_dir' and checking transmute values..."
  dart run flutter_app_transmuter:main --diff="$source_dir"
  dart run flutter_app_transmuter:main --check
fi

exit 0
