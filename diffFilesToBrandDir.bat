@echo off

rem Windows CMD script to diff brand files and check transmute values against the project.
rem
rem Usage:
rem   diffFilesToBrandDir [source_directory]
rem
rem If no directory is given, uses --status which falls back to brand_source_directory in transmute.json.

if "%1"=="" (
    echo No directory specified, using --status to diff brand files and check transmute values...
    @echo on
    cmd /C dart run flutter_app_transmuter:main --status
    @echo off
) else (
    set "SOURCE_DIR=%1"
    if not exist "%SOURCE_DIR%\" (
        echo Error: Diff directory "%SOURCE_DIR%" does not exist.
        exit /b 1
    )
    echo Diffing brand files from "%SOURCE_DIR%" and checking transmute values...
    @echo on
    cmd /C dart run flutter_app_transmuter:main --diff="%SOURCE_DIR%"
    cmd /C dart run flutter_app_transmuter:main --check
    @echo off
)

exit /b 0
