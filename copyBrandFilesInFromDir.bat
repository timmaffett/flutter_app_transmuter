@echo off

rem Windows CMD script to copy specific files from a given directory to the current directory.

if "%1"=="" (
    echo Usage: %0 ^<source_directory^>
    exit /b 1
)

set "SOURCE_DIR=%1"
set BUILD_FLAG=false
set FLUTTERFIRE_FLAG=false

rem if /i "%2"=="/BUILD" OR /i "%2"=="--BUILD" OR /i "%2"=="-BUILD" (
if "%2"=="/BUILD" (
  echo Detected BUILD FLAG
    set BUILD_FLAG=true
)

if "%2"=="/FLUTTERFIRE" (
  echo Detected FLUTTERFIRE FLAG
    set FLUTTERFIRE_FLAG=true
)

if not exist "%SOURCE_DIR%\" (
    echo Error: Source directory "%SOURCE_DIR%" does not exist.
    exit /b 1
)
if "%BUILD_FLAG%"=="true" (
   echo BUILD flag has been set and APP WILL BE BUILT
)

echo Copying brand files from "%SOURCE_DIR%" using master_transmute.yaml...
@echo on
cmd /C dart run flutter_app_transmuter:main --copy "%SOURCE_DIR%"
@echo off

echo Running Transmuting Tool to Rebrand
@echo on
cmd /C dart run flutter_app_transmuter:main transmute.json
@echo off

echo Running Launcher Icon Rebuild Tool
@echo on
cmd /C dart run flutter_launcher_icons
@echo off

echo Running Native Splash Screen Rebuild Tool
@echo on
cmd /C dart run flutter_native_splash:create
@echo off


echo Running flutter clean
@echo on
cmd /C flutter clean
@echo off

echo Running flutter pub get
@echo on
cmd /C flutter pub get
@echo off

if "%FLUTTERFIRE_FLAG%"=="true" (
  echo Running flutterfire configure to RESET Firebase configuration
  @echo on
  cmd /C flutterfire configure --yes --overwrite-firebase-options
  @echo off
}

REM echo Running build_runner to generate code
REM echo Running flutter pub run build_runner build --delete-conflicting-outputs
REM @echo on
REM cmd /C flutter pub run build_runner build --delete-conflicting-outputs
REM @echo off

if "%BUILD_FLAG%"=="true" (
    echo Running Release Build for Android
    @echo on
    cmd /C flutter build apk --target-platform android-arm64
    @echo off
    if exist build\app\outputs\flutter-apk\app-release.apk (
      if not exist "%SOURCE_DIR%\release_builds" mkdir "%SOURCE_DIR%\release_builds"
      @echo on
      echo copying build\app\outputs\flutter-apk\app-release.apk to "%SOURCE_DIR%\release_builds\"
      copy /Y build\app\outputs\flutter-apk\app-release.apk "%SOURCE_DIR%\release_builds\"
      @echo off
    ) else (
      powershell -Command "Write-Host 'Error in Build!: app-release.apk not found in build\app\outputs\flutter-apk.' -ForegroundColor Red"
    )
)

@echo off

echo Copying files for new brand COMPLETE.

exit /b 0