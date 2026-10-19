@echo off
rem ============================================================
rem  Tech Lead Kit for Claude Code - installer (Windows)
rem  Usage:  install.cmd "C:\path\to\project"
rem          (without argument: the installer window - pick projects,
rem           install or update; text mode if the window cannot start)
rem  Copies kit\.claude into <project>\.claude, connects CORE.md
rem  through .claude\CLAUDE.md and hides the kit from git
rem  (local .git\info\exclude - nothing is committed).
rem ============================================================
setlocal EnableExtensions

set "SRC=%~dp0kit\.claude"
set "IMPORT_LINE=@tech-lead-kit/CORE.md"

if not exist "%SRC%\tech-lead-kit\CORE.md" (
    echo [ERROR] Kit files not found next to this script: "%SRC%"
    echo         Run install.cmd from the unpacked kit folder.
    goto :fail
)

set "TARGET=%~1"
if defined TARGET goto :have_target
if defined TLK_NO_GUI goto :ask_target
rem no argument: open the installer window (Windows PowerShell, no internet needed)
powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0installer\install-gui.ps1"
if not errorlevel 1 exit /b 0
echo [INFO] The installer window could not start - continuing in text mode.
:ask_target
set /p "TARGET=Project folder path: "
:have_target
if not defined TARGET (
    echo [ERROR] No project folder given.
    goto :fail
)
rem strip quotes typed or pasted by the user
set "TARGET=%TARGET:"=%"
if not defined TARGET (
    echo [ERROR] No project folder given.
    goto :fail
)
rem strip a trailing backslash
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"

if not exist "%TARGET%\" (
    echo [ERROR] Folder does not exist: "%TARGET%"
    goto :fail
)

set /p KIT_VERSION=<"%SRC%\tech-lead-kit\VERSION"
echo.
echo Installing Tech Lead Kit %KIT_VERSION% into: "%TARGET%"
echo.

rem ---- 1. copy kit files (updates kit files, never touches tl-memory) ----
rem remove the previous kit files first, so renamed or removed parts do not stay behind
set "C=%TARGET%\.claude"
if exist "%C%\tech-lead-kit\" rmdir /s /q "%C%\tech-lead-kit"
for /d %%D in ("%C%\skills\tl-*") do rmdir /s /q "%%D"
if exist "%C%\skills\oleg-skill-hesber\" rmdir /s /q "%C%\skills\oleg-skill-hesber"
del /q "%C%\commands\tl-*.md" 2>nul
del /q "%C%\agents\tl-*.md" 2>nul
robocopy "%SRC%" "%TARGET%\.claude" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo [ERROR] robocopy failed to copy the files.
    goto :fail
)
echo [OK] Kit files copied to .claude\

rem ---- 2. memory folders (created once, content preserved) ----
if not exist "%TARGET%\.claude\tl-memory\adr\"    mkdir "%TARGET%\.claude\tl-memory\adr"
if not exist "%TARGET%\.claude\tl-memory\design\" mkdir "%TARGET%\.claude\tl-memory\design"
if not exist "%TARGET%\.claude\tl-memory\analysis\" mkdir "%TARGET%\.claude\tl-memory\analysis"
if not exist "%TARGET%\.claude\tl-memory\spec\" mkdir "%TARGET%\.claude\tl-memory\spec"
echo [OK] Project memory folder: .claude\tl-memory\

rem ---- 2b. how kit documents become part of the project (asked once per project) ----
set "PUBJ=%TARGET%\.claude\tl-memory\publish.json"
if exist "%PUBJ%" goto :publish_done
if defined TLK_FROM_GUI goto :publish_done
echo.
echo Approved kit documents (specs, ADRs, designs, reports) can become part of the
echo project automatically: moved to docs\ and listed in AGENTS.md. You commit them.
choice /C YN /M "Make approved documents part of the project automatically"
if errorlevel 2 goto :publish_manual
> "%PUBJ%" echo {"docs_root": "docs", "auto_publish": true}
echo [OK] Documents: docs\ automatically after approval
goto :publish_done
:publish_manual
> "%PUBJ%" echo {"docs_root": "docs", "auto_publish": false}
echo [OK] Documents: shared on request with /tl-publish
:publish_done

rem ---- 3. connect CORE.md via .claude\CLAUDE.md ----
set "CLAUDE_MD=%TARGET%\.claude\CLAUDE.md"
set "CREATED_CLAUDE_MD=0"
if not exist "%CLAUDE_MD%" (
    > "%CLAUDE_MD%" echo # Project instructions
    >>"%CLAUDE_MD%" echo.
    >>"%CLAUDE_MD%" echo %IMPORT_LINE%
    set "CREATED_CLAUDE_MD=1"
    echo [OK] Created .claude\CLAUDE.md with the kit import
) else (
    findstr /L /C:"%IMPORT_LINE%" "%CLAUDE_MD%" >nul 2>&1
    if errorlevel 1 (
        >>"%CLAUDE_MD%" echo.
        >>"%CLAUDE_MD%" echo %IMPORT_LINE%
        echo [OK] Added the kit import line to existing .claude\CLAUDE.md
        call :warn_if_tracked
    ) else (
        echo [OK] .claude\CLAUDE.md already imports the kit
    )
)

rem ---- 4. hide kit from git locally (.git\info\exclude) ----
if exist "%TARGET%\.git\info\" goto :do_exclude
if exist "%TARGET%\.git\" (
    mkdir "%TARGET%\.git\info" 2>nul
    goto :do_exclude
)
echo [INFO] No .git folder found - git exclude step skipped.
goto :done

:do_exclude
set "EXCLUDE=%TARGET%\.git\info\exclude"
set "EXCLUDE_HEADER=# tech-lead-kit (local only, not committed)"
if not exist "%EXCLUDE%" type nul > "%EXCLUDE%"
rem each line is added only if missing, so re-installs also add lines of new kit parts
findstr /L /X /C:"%EXCLUDE_HEADER%" "%EXCLUDE%" >nul 2>&1
if errorlevel 1 >>"%EXCLUDE%" echo.
call :add_exclude "%EXCLUDE_HEADER%"
call :add_exclude ".claude/tech-lead-kit/"
call :add_exclude ".claude/skills/tl-*/"
call :add_exclude ".claude/skills/oleg-skill-hesber/"
call :add_exclude ".claude/commands/tl-*.md"
call :add_exclude ".claude/agents/tl-*.md"
call :add_exclude ".claude/tl-memory/"
call :add_exclude ".claude/settings.local.json"
if "%CREATED_CLAUDE_MD%"=="1" call :add_exclude ".claude/CLAUDE.md"
echo [OK] Kit hidden from git via .git\info\exclude (local, not committed)

:done
call :register
echo.
echo Done. Next steps:
echo   1. Open the project in VS Code and start a NEW Claude Code session.
echo   2. Run /tl-init now - and after every kit update: kit check, time limits, project map, data sources.
echo   3. Then /tl-go - say what you want in your own words; it picks the route and asks you to confirm.
echo      /tl-go new ^<request^> - a new task from one line to code; /tl-go alone - where you stopped.
echo   What is new: .claude\tech-lead-kit\CHANGELOG.md
echo   Later updates: double-click install.cmd - known projects are listed in the window.
echo.
endlocal
exit /b 0

:register
if not defined LOCALAPPDATA goto :eof
if not exist "%LOCALAPPDATA%\TechLeadKit\" mkdir "%LOCALAPPDATA%\TechLeadKit"
set "REG=%LOCALAPPDATA%\TechLeadKit\projects.txt"
if not exist "%REG%" type nul > "%REG%"
findstr /L /X /I /C:"%TARGET%" "%REG%" >nul 2>&1
if errorlevel 1 >>"%REG%" echo %TARGET%
goto :eof

:add_exclude
findstr /L /X /C:"%~1" "%EXCLUDE%" >nul 2>&1
if errorlevel 1 >>"%EXCLUDE%" echo %~1
goto :eof

:warn_if_tracked
where git >nul 2>&1
if errorlevel 1 goto :eof
git -C "%TARGET%" ls-files --error-unmatch ".claude/CLAUDE.md" >nul 2>&1
if errorlevel 1 goto :eof
echo [WARN] .claude\CLAUDE.md is tracked by git, so it now shows as modified.
echo        To keep the change local only, run in the project folder:
echo        git update-index --skip-worktree .claude/CLAUDE.md
goto :eof

:fail
echo.
echo Installation aborted.
endlocal
exit /b 1
