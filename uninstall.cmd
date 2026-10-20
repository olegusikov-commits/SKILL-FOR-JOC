@echo off
rem ============================================================
rem  Tech Lead Kit for Claude Code - uninstaller (Windows)
rem  Usage:  uninstall.cmd "C:\path\to\project"
rem  Removes kit files and the import line from .claude\CLAUDE.md.
rem  Project memory (.claude\tl-memory - ADRs, designs, tech debt,
rem  what the kit learned) is KEPT. Project skills made by /tl-retro
rem  (skills\tlp-*) need the kit, so they move to
rem  tl-memory\skills-disabled and come back with the next install.
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
if not exist "%C%\tl-memory\skills-disabled\" mkdir "%C%\tl-memory\skills-disabled"
for /d %%D in ("%C%\skills\tlp-*") do move /y "%%D" "%C%\tl-memory\skills-disabled\" >nul
echo [OK] Kit files removed (project skills tlp-*, if any: .claude\tl-memory\skills-disabled\)

set "CLAUDE_MD=%C%\CLAUDE.md"
if exist "%CLAUDE_MD%" (
    findstr /L /V /X /C:"%IMPORT_LINE%" "%CLAUDE_MD%" > "%CLAUDE_MD%.tmp"
    move /y "%CLAUDE_MD%.tmp" "%CLAUDE_MD%" >nul
    echo [OK] Import line removed from .claude\CLAUDE.md
)

set "REG=%LOCALAPPDATA%\TechLeadKit\projects.txt"
if defined LOCALAPPDATA if exist "%REG%" (
    findstr /L /V /X /I /C:"%TARGET%" "%REG%" > "%REG%.tmp"
    move /y "%REG%.tmp" "%REG%" >nul
)

echo.
echo Done. Project memory kept in .claude\tl-memory\
echo Published documents in docs\ and the block in AGENTS.md belong to the project and stay.
endlocal
exit /b 0

:fail
echo.
echo Uninstall aborted.
endlocal
exit /b 1
