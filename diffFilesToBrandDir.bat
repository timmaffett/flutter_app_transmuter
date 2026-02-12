@echo off

rem Windows CMD script to DIFF specific files from a given directory to the appropriate directories.

if "%1"=="" (
    echo Usage: %0 ^<source_directory^>
    exit /b 1
)

set "source_dir=%1"

if not exist "%source_dir%\" (
    echo Error: Diff directory "%source_dir%" does not exist.
    exit /b 1
)

echo Diffing brand files from "%source_dir%" using master_transmute.yaml...
@echo on
cmd /C dart run flutter_app_transmuter:main --diff "%source_dir%"
@echo off

exit /b 0