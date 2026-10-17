@echo off
rem ============================================================
rem  Tech Lead Kit for Claude Code - uninstaller (Windows)
rem  Usage:  uninstall.cmd "C:\path\to\project"
rem  Removes kit files and the import line from .claude\CLAUDE.md.
rem  Project memory (.claude\tl-memory - ADRs, designs, tech debt)
rem  is KEPT. Delete it manually if you no longer need it.
rem ============================================================
setlocal EnableExtensions

set "IMPORT_LINE=@tech-lead-kit/CORE.md"

set "TARGET=%~1"
if not defined TARGET set /p "TARGET=Project folder path: "
if not defined TARGET (
    echo [ERROR] No project folder given.
    goto :fail
)
set "TARGET=%TARGET:"=%"
if not defined TARGET (
    echo [ERROR] No project folder given.
    goto :fail
)
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"
if not exist "%TARGET%\.claude\" (
    echo [ERROR] No .claude folder in: "%TARGET%"
    goto :fail
)

set "C=%TARGET%\.claude"
if exist "%C%\tech-lead-kit\" rmdir /s /q "%C%\tech-lead-kit"
for /d %%D in ("%C%\skills\tl-*") do rmdir /s /q "%%D"
if exist "%C%\skills\oleg-skill-hesber\" rmdir /s /q "%C%\skills\oleg-skill-hesber"
del /q "%C%\commands\tl-*.md" 2>nul
del /q "%C%\agents\tl-*.md" 2>nul
echo [OK] Kit files removed

set "CLAUDE_MD=%C%\CLAUDE.md"
if exist "%CLAUDE_MD%" (
    findstr /L /V /X /C:"%IMPORT_LINE%" "%CLAUDE_MD%" > "%CLAUDE_MD%.tmp"
    move /y "%CLAUDE_MD%.tmp" "%CLAUDE_MD%" >nul
    echo [OK] Import line removed from .claude\CLAUDE.md
)

echo.
echo Done. Project memory kept in .claude\tl-memory\
endlocal
exit /b 0

:fail
echo.
echo Uninstall aborted.
endlocal
exit /b 1
