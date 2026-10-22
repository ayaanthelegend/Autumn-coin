@echo off
setlocal enabledelayedexpansion

call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 (
    echo Failed to initialize MSVC environment.
    exit /b 1
)

set "PATH=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"

cd /d "%~dp0"

echo [Configuring CMake with Ninja...]
cmake -G Ninja -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
if errorlevel 1 (
    echo CMake configure failed.
    exit /b 1
)

echo [Building targets...]
cmake --build build --config Release
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo [Build Succeeded!]
