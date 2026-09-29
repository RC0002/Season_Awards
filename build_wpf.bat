@echo off
REM Builds ScraperWPF.exe from ScraperWPF.cs using the .NET Framework compiler shipped with Windows
cd /d "%~dp0"
set FW=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319
"%FW%\csc.exe" /nologo /target:winexe /out:ScraperWPF.exe /win32icon:favicon.ico ^
  /r:"%FW%\WPF\PresentationFramework.dll" /r:"%FW%\WPF\PresentationCore.dll" ^
  /r:"%FW%\WPF\WindowsBase.dll" /r:"%FW%\System.Xaml.dll" ScraperWPF.cs
if errorlevel 1 (echo Build failed & exit /b 1)
echo Built ScraperWPF.exe
