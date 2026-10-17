# ============================================================
#  Tech Lead Kit - installer test (Windows: cmd.exe, robocopy, git)
#  Usage:  pwsh tests\test-install.ps1 [-Installer path\to\install.cmd]
#  Runs install.cmd against throw-away projects and checks that every
#  case reaches the git exclude step, prints "Done" and leaves no kit
#  files in the project's git status. Exit code 1 if any check fails.
# ============================================================
param(
    [string]$Installer = (Join-Path $PSScriptRoot '..\install.cmd')
)

$ErrorActionPreference = 'Stop'
$Installer = (Resolve-Path -LiteralPath $Installer).Path
$ImportLine = '@tech-lead-kit/CORE.md'
$KitExcludes = @(
    '# tech-lead-kit (local only, not committed)',
    '.claude/tech-lead-kit/',
    '.claude/skills/tl-*/',
    '.claude/skills/oleg-skill-hesber/',
    '.claude/commands/tl-*.md',
    '.claude/agents/tl-*.md',
    '.claude/tl-memory/'
)
$TempBase = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }
# space and parentheses in the path also check quoting inside install.cmd
$Root = Join-Path $TempBase "tlk test (install) $PID"
$script:Failures = 0

function Check([bool]$Ok, [string]$What) {
    if ($Ok) { Write-Host "  ok    $What" }
    else { Write-Host "  FAIL  $What"; $script:Failures++ }
}

function Read-Lines([string]$Path) {
    # the comma keeps a one-line file an array
    if (Test-Path -LiteralPath $Path) { , @(Get-Content -LiteralPath $Path) } else { , @() }
}

function Count-Line([string[]]$Lines, [string]$Line) {
    @($Lines | Where-Object { $_ -ceq $Line }).Count
}

function Invoke-Git([string]$Dir) {
    $out = & git -C $Dir @args 2>&1
    if ($LASTEXITCODE) { throw "git $args failed in ${Dir}: $out" }
    $out
}

function New-Project([string]$Name, [switch]$NoGit) {
    $dir = Join-Path $Root $Name
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    if (-not $NoGit) {
        Invoke-Git $dir -c init.defaultBranch=main init -q | Out-Null
        Invoke-Git $dir config core.autocrlf false | Out-Null
    }
    $dir
}

function Add-TrackedClaudeMd([string]$Dir, [string]$Text) {
    New-Item -ItemType Directory -Path (Join-Path $Dir '.claude') -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $Dir '.claude\CLAUDE.md'), $Text)
    Invoke-Git $Dir add .claude/CLAUDE.md | Out-Null
    Invoke-Git $Dir -c user.name=test -c user.email=test@example.com commit -q -m init | Out-Null
}

function Invoke-Installer([string]$Dir) {
    $out = & $Installer $Dir 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $out | ForEach-Object { Write-Host "    | $_" }
    [pscustomobject]@{ Code = $code; Out = ($out -join "`n") }
}

# Checks shared by every case with a .git folder.
#   $ClaudeMdExcluded - how many times .claude/CLAUDE.md must be in .git\info\exclude
#   $Status           - expected `git status --porcelain` lines (kit files must not appear)
function Assert-Installed($Result, [string]$Dir, [int]$ClaudeMdExcluded, [string[]]$Status = @()) {
    Check ($Result.Code -eq 0) "exit code 0 (got $($Result.Code))"
    Check ($Result.Out.Contains('[OK] Kit hidden from git via .git\info\exclude')) 'reached the git exclude step'
    Check ($Result.Out.Contains('Done. Next steps:')) 'printed Done'
    Check (Test-Path -LiteralPath (Join-Path $Dir '.claude\tech-lead-kit\CORE.md')) 'kit files copied'
    Check (Test-Path -LiteralPath (Join-Path $Dir '.claude\tl-memory\adr')) 'memory folder created'

    $md = Read-Lines (Join-Path $Dir '.claude\CLAUDE.md')
    $n = Count-Line $md $ImportLine
    Check ($n -eq 1) "CLAUDE.md has the import line once (found $n)"

    $exclude = Read-Lines (Join-Path $Dir '.git\info\exclude')
    foreach ($line in $KitExcludes) {
        $n = Count-Line $exclude $line
        Check ($n -eq 1) "exclude has '$line' once (found $n)"
    }
    $n = Count-Line $exclude '.claude/CLAUDE.md'
    Check ($n -eq $ClaudeMdExcluded) "exclude has '.claude/CLAUDE.md' $ClaudeMdExcluded time(s) (found $n)"

    $actual = @(Invoke-Git $Dir status --porcelain --untracked-files=all | Where-Object { $_ } | ForEach-Object { "$_" })
    Check (($actual -join '|') -ceq ($Status -join '|')) "git status is [$($Status -join ', ')] (got [$($actual -join ', ')])"
}

function Start-Case([string]$Title) { Write-Host ''; Write-Host "== $Title" }

Write-Host "Installer: $Installer"
Write-Host "Projects:  $Root"
if (Test-Path -LiteralPath $Root) { Remove-Item -LiteralPath $Root -Recurse -Force }

try {
    Start-Case '(a) no .claude\CLAUDE.md'
    $a = New-Project 'case-a'
    $r = Invoke-Installer $a
    Assert-Installed $r $a -ClaudeMdExcluded 1
    Check ($r.Out.Contains('[OK] Created .claude\CLAUDE.md')) 'created CLAUDE.md'

    Start-Case '(b) tracked .claude\CLAUDE.md without the import line'
    $b = New-Project 'case-b'
    Add-TrackedClaudeMd $b "# Company rules`r`n`r`nUse tabs.`r`n"
    $r = Invoke-Installer $b
    Assert-Installed $r $b -ClaudeMdExcluded 0 -Status @(' M .claude/CLAUDE.md')
    Check ($r.Out.Contains('[OK] Added the kit import line')) 'added the import line'
    Check ($r.Out.Contains('[WARN] .claude\CLAUDE.md is tracked by git')) 'warned that CLAUDE.md is tracked'
    $md = Read-Lines (Join-Path $b '.claude\CLAUDE.md')
    Check ($md.Count -gt 0 -and $md[0] -ceq '# Company rules') 'kept the original CLAUDE.md content'

    Start-Case '(c) tracked .claude\CLAUDE.md that already imports the kit'
    $c = New-Project 'case-c'
    Add-TrackedClaudeMd $c "# Company rules`r`n`r`n$ImportLine`r`n"
    $before = (Get-FileHash -LiteralPath (Join-Path $c '.claude\CLAUDE.md')).Hash
    $r = Invoke-Installer $c
    Assert-Installed $r $c -ClaudeMdExcluded 0
    Check ($r.Out.Contains('[OK] .claude\CLAUDE.md already imports the kit')) 'reported the existing import'
    $after = (Get-FileHash -LiteralPath (Join-Path $c '.claude\CLAUDE.md')).Hash
    Check ($before -eq $after) 'CLAUDE.md unchanged'

    Start-Case '(d) re-install over (a): nothing duplicated'
    $r = Invoke-Installer $a
    Assert-Installed $r $a -ClaudeMdExcluded 1
    Check ($r.Out.Contains('[OK] .claude\CLAUDE.md already imports the kit')) 'reported the existing import'

    Start-Case '(d) re-install over (b): nothing duplicated'
    $r = Invoke-Installer $b
    Assert-Installed $r $b -ClaudeMdExcluded 0 -Status @(' M .claude/CLAUDE.md')
    Check ($r.Out.Contains('[OK] .claude\CLAUDE.md already imports the kit')) 'reported the existing import'

    Start-Case '(e) project without a .git folder'
    $e = New-Project 'case-e' -NoGit
    $r = Invoke-Installer $e
    Check ($r.Code -eq 0) "exit code 0 (got $($r.Code))"
    Check ($r.Out.Contains('[INFO] No .git folder found')) 'skipped the git exclude step'
    Check ($r.Out.Contains('Done. Next steps:')) 'printed Done'
    Check (Test-Path -LiteralPath (Join-Path $e '.claude\CLAUDE.md')) 'created CLAUDE.md'
}
finally {
    if (Test-Path -LiteralPath $Root) { Remove-Item -LiteralPath $Root -Recurse -Force }
}

Write-Host ''
if ($script:Failures) { Write-Host "$($script:Failures) check(s) FAILED"; exit 1 }
Write-Host 'All installer checks passed'
exit 0
