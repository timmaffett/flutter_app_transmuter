#!/bin/bash

# Bash script to copy specific files from a given directory to the current directory.

# Check if a directory argument is provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <source_directory>"
  exit 1
fi

source_dir="$1"

# Check if the source directory exists and is a directory
if [ ! -d "$source_dir" ]; then
  echo "Error: Source directory '$source_dir' does not exist or is not a directory."
  exit 1
fi

build_flag=false
fluttefire_flag=false

# Check if the /build argument is provided
if [ "$2" == "/build" ]; then
  build_flag=true
fi

# Check if the /fluttefire argument is provided
if [ "$2" == "/fluttefire" ]; then
  fluttefire_flag=true
fi


echo "Copying brand files from '$source_dir' using master_transmute.yaml..."
dart run flutter_app_transmuter:main --copy "$source_dir"

echo "Running Transmuter Tool to Rebrand"
dart run flutter_app_transmuter:main transmute.json

echo "Running Launcher Icon Rebuild Tool"
dart run flutter_launcher_icons

echo "Running Native Splash Screen Rebuild Tool"
dart run flutter_native_splash:create

echo "Running flutter clean"
flutter clean

echo "Removing Xcode Derived Data"
rm -rf ~/Library/Developer/Xcode/DerivedData/Runner-* 

printf "\e[1;35mXCODE \e[1;33mBe sure to close xcode and reopen Runner.xcworkspace and CLEAN build folder\n"
printf "\e[1;35mXCODE \e[1;36mThen make sure that the correct TEAM is set in Signing & Capabilities\n"

echo "Running flutter pub get"
flutter pub get

if "$fluttefire_flag" == true; then
  echo "Running flutterfire configure to SET Firebase configuration"
  flutterfire configure --yes --overwrite-firebase-options
fi

if "$build_flag" == true; then
  echo "Running Release Build for IOS ipa file"
  flutter build ipa 
fi

echo -e "\e[1;32mCopying files for new brand COMPLETE.\e[0m"

exit 0
