#!/bin/bash

# Bash script to switch to a brand using flutter_app_transmuter --switch.
# This replaces the old manual copy/transmute/rebuild pipeline with a single --switch command.
#
# Usage:
#   copyBrandFilesInFromDir.sh <source_directory> [/build] [/flutterfire]
#
# Flags are passed through to --switch as +build and +flutterfire.

# Check if a directory argument is provided
if [ $# -lt 1 ]; then
  echo "Usage: $0 <source_directory> [/build] [/flutterfire]"
  exit 1
fi

source_dir="$1"
shift

# Check if the source directory exists and is a directory
if [ ! -d "$source_dir" ]; then
  echo "Error: Source directory '$source_dir' does not exist or is not a directory."
  exit 1
fi

# Collect +flags from remaining arguments
flags=""
for arg in "$@"; do
  case "${arg,,}" in
    /build|--build|-build)
      flags="$flags +build"
      ;;
    /flutterfire|--flutterfire|-flutterfire)
      flags="$flags +flutterfire"
      ;;
    *)
      echo "Warning: Unknown flag '$arg' ignored."
      ;;
  esac
done

echo "Switching to brand from '$source_dir'..."
dart run flutter_app_transmuter:main --switch="$source_dir" --projectfile --transmutevalue $flags

if [ $? -ne 0 ]; then
  echo "Error: Brand switch failed."
  exit 1
fi

printf "\e[1;35mXCODE \e[1;33mBe sure to close Xcode and reopen Runner.xcworkspace and CLEAN build folder\n"
printf "\e[1;35mXCODE \e[1;36mThen make sure that the correct TEAM is set in Signing & Capabilities\n"

echo -e "\e[1;32mBrand switch COMPLETE.\e[0m"

exit 0
