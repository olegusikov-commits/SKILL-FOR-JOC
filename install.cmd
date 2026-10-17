@echo off
rem ============================================================
rem  Tech Lead Kit for Claude Code - installer (Windows)
rem  Usage:  install.cmd "C:\path\to\project"
rem          (without argument the script asks for the path)
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
if not defined TARGET set /p "TARGET=Project folder path: "
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
robocopy "%SRC%" "%TARGET%\.claude" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo [ERROR] robocopy failed to copy the files.
    goto :fail
)
echo [OK] Kit files copied to .claude\

rem ---- 2. memory folders (created once, content preserved) ----
if not exist "%TARGET%\.claude\tl-memory\adr\"    mkdir "%TARGET%\.claude\tl-memory\adr"
if not exist "%TARGET%\.claude\tl-memory\design\" mkdir "%TARGET%\.claude\tl-memory\design"
echo [OK] Project memory folder: .claude\tl-memory\

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
if not exist "%EXCLUDE%" type nul > "%EXCLUDE%"
findstr /L /C:"# tech-lead-kit" "%EXCLUDE%" >nul 2>&1
if not errorlevel 1 (
    echo [OK] git exclude already configured
    goto :exclude_claude_md
)
>>"%EXCLUDE%" echo.
>>"%EXCLUDE%" echo # tech-lead-kit (local only, not committed)
>>"%EXCLUDE%" echo .claude/tech-lead-kit/
>>"%EXCLUDE%" echo .claude/skills/tl-*/
>>"%EXCLUDE%" echo .claude/commands/tl-*.md
>>"%EXCLUDE%" echo .claude/agents/tl-*.md
>>"%EXCLUDE%" echo .claude/tl-memory/
echo [OK] Kit hidden from git via .git\info\exclude (local, not committed)

:exclude_claude_md
if "%CREATED_CLAUDE_MD%"=="1" (
    findstr /L /X /C:".claude/CLAUDE.md" "%EXCLUDE%" >nul 2>&1
    if errorlevel 1 >>"%EXCLUDE%" echo .claude/CLAUDE.md
)

:done
echo.
echo Done. Next steps:
echo   1. Open the project in VS Code and start a new Claude Code session.
echo   2. Type /  - you should see /tl-init, /tl-design, /tl-implement, /tl-review, /tl-sql, /tl-debt
echo   3. Run /tl-init once to build the project map (.claude\tl-memory\PROJECT_CONTEXT.md).
echo.
endlocal
exit /b 0

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
