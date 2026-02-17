@echo off

rem Windows CMD script to switch to a brand using flutter_app_transmuter --switch.
rem This replaces the old manual copy/transmute/rebuild pipeline with a single --switch command.
rem
rem Usage:
rem   copyBrandFilesInFromDir <source_directory> [/BUILD] [/FLUTTERFIRE]
rem
rem Flags are passed through to --switch as +build and +flutterfire.

if "%1"=="" (
    echo Usage: %0 ^<source_directory^> [/BUILD] [/FLUTTERFIRE]
    exit /b 1
)

set "SOURCE_DIR=%1"

if not exist "%SOURCE_DIR%\" (
    echo Error: Source directory "%SOURCE_DIR%" does not exist.
    exit /b 1
)

rem Collect +flags from remaining arguments
set "FLAGS="
shift

:parse_flags
if "%1"=="" goto done_flags
if /i "%1"=="/BUILD" (
    set "FLAGS=%FLAGS% +build"
)
if /i "%1"=="/FLUTTERFIRE" (
    set "FLAGS=%FLAGS% +flutterfire"
)
shift
goto parse_flags

:done_flags

echo Switching to brand from "%SOURCE_DIR%"...
@echo on
cmd /C dart run flutter_app_transmuter:main --switch="%SOURCE_DIR%" --projectfile --transmutevalue%FLAGS%
@echo off

if errorlevel 1 (
    echo Error: Brand switch failed.
    exit /b 1
)

echo Brand switch COMPLETE.

exit /b 0
