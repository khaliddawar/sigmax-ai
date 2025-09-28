@echo off
echo ========================================
echo    SignalScope Distribution Builder
echo ========================================
echo.

REM Create distribution directories
if not exist "dist\portable" mkdir "dist\portable"
if not exist "dist\chrome-extension" mkdir "dist\chrome-extension"
if not exist "dist\installer" mkdir "dist\installer"

echo Building Chrome Extension...
call npm run build
if %errorlevel% neq 0 (
    echo ERROR: Extension build failed
    pause
    exit /b 1
)

echo Copying extension files...
xcopy /E /I /Y "dist\content\*" "dist\chrome-extension\"
xcopy /E /I /Y "dist\background\*" "dist\chrome-extension\"
xcopy /E /I /Y "dist\popup\*" "dist\chrome-extension\"
xcopy /E /I /Y "dist\options\*" "dist\chrome-extension\"
xcopy /E /I /Y "dist\sidebar\*" "dist\chrome-extension\"
copy "manifest.json" "dist\chrome-extension\"

echo Copying portable files...
xcopy /E /I /Y "dist\portable\*" "dist\portable\"
xcopy /E /I /Y "servers\*" "dist\portable\servers\"
copy "README.md" "dist\portable\"
copy "LICENSE.txt" "dist\portable\"

echo Creating portable package...
cd dist\portable
powershell Compress-Archive -Path ".\*" -DestinationPath "..\SignalScope-Portable.zip" -Force
cd ..\..

echo Building Electron app...
cd electron-app
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Electron dependencies failed
    pause
    exit /b 1
)

call npm run build-win
if %errorlevel% neq 0 (
    echo ERROR: Electron build failed
    pause
    exit /b 1
)
cd ..

echo Building Docker image...
docker build -t signalScope:latest .
if %errorlevel% neq 0 (
    echo WARNING: Docker build failed (Docker may not be installed)
)

echo.
echo ========================================
echo    Build Complete!
echo ========================================
echo.
echo Distribution files created:
echo - dist\SignalScope-Portable.zip
echo - dist\chrome-extension\ (Chrome extension)
echo - electron-app\dist\ (Electron app)
echo - Docker image: signalScope:latest
echo.
echo Next steps:
echo 1. Test the portable package
echo 2. Create installer with NSIS
echo 3. Test Docker container
echo.
pause
