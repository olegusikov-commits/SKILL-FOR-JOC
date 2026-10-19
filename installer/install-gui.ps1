# Tech Lead Kit - installer window (Windows PowerShell 5.1, Windows Forms; no internet, no modules).
# Started by install.cmd without arguments. Shows the projects where the kit is installed,
# lets the user add a project folder, choose how kit documents become part of the project,
# then runs install.cmd for every checked project and writes .claude\tl-memory\publish.json.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$KitRoot = Split-Path -Parent $PSScriptRoot
$InstallCmd = Join-Path $KitRoot 'install.cmd'
$NewVersion = (Get-Content -LiteralPath (Join-Path $KitRoot 'kit\.claude\tech-lead-kit\VERSION') -Raw).Trim()
$RegistryDir = Join-Path $env:LOCALAPPDATA 'TechLeadKit'
$Registry = Join-Path $RegistryDir 'projects.txt'

function Get-KnownProjects {
    if (-not (Test-Path -LiteralPath $Registry)) { return @() }
    Get-Content -LiteralPath $Registry | Where-Object { $_.Trim() -and (Test-Path -LiteralPath $_) } |
        Sort-Object -Unique
}

function Get-InstalledVersion([string]$Project) {
    $v = Join-Path $Project '.claude\tech-lead-kit\VERSION'
    if (Test-Path -LiteralPath $v) { return (Get-Content -LiteralPath $v -Raw).Trim() }
    return $null
}

function Format-Item([string]$Project) {
    $v = Get-InstalledVersion $Project
    if ($v) { return "$Project    (установлено $v)" }
    return "$Project    (не установлено)"
}

function Read-PublishSettings([string]$Project) {
    $p = Join-Path $Project '.claude\tl-memory\publish.json'
    if (Test-Path -LiteralPath $p) {
        try { return Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
    }
    return $null
}

function Write-PublishSettings([string]$Project, [string]$DocsRoot, [bool]$Auto) {
    $dir = Join-Path $Project '.claude\tl-memory'
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    $cfg = Read-PublishSettings $Project
    if (-not $cfg) { $cfg = New-Object PSObject }
    $cfg | Add-Member -NotePropertyName 'docs_root' -NotePropertyValue $DocsRoot -Force
    $cfg | Add-Member -NotePropertyName 'auto_publish' -NotePropertyValue $Auto -Force
    $json = $cfg | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText((Join-Path $dir 'publish.json'), $json, (New-Object System.Text.UTF8Encoding $false))
}

# ---------------------------------------------------------------- window
$form = New-Object System.Windows.Forms.Form
$form.Text = "Tech Lead Kit $NewVersion - установка и обновление"
$form.Size = New-Object System.Drawing.Size(820, 640)
$form.StartPosition = 'CenterScreen'
$form.Font = New-Object System.Drawing.Font('Segoe UI', 9.5)

$title = New-Object System.Windows.Forms.Label
$title.Text = "Проекты. Отметь, куда установить или где обновить kit $NewVersion."
$title.Location = New-Object System.Drawing.Point(16, 14)
$title.Size = New-Object System.Drawing.Size(770, 22)
$form.Controls.Add($title)

$list = New-Object System.Windows.Forms.CheckedListBox
$list.Location = New-Object System.Drawing.Point(16, 40)
$list.Size = New-Object System.Drawing.Size(770, 150)
$list.CheckOnClick = $true
$form.Controls.Add($list)
$paths = New-Object System.Collections.ArrayList
foreach ($p in Get-KnownProjects) {
    [void]$paths.Add($p)
    $i = $list.Items.Add((Format-Item $p))
    if ((Get-InstalledVersion $p) -ne $NewVersion) { $list.SetItemChecked($i, $true) }
}

$add = New-Object System.Windows.Forms.Button
$add.Text = 'Добавить проект...'
$add.Location = New-Object System.Drawing.Point(16, 198)
$add.Size = New-Object System.Drawing.Size(170, 30)
$form.Controls.Add($add)

$news = New-Object System.Windows.Forms.Button
$news.Text = "Что нового в $NewVersion"
$news.Location = New-Object System.Drawing.Point(196, 198)
$news.Size = New-Object System.Drawing.Size(200, 30)
$form.Controls.Add($news)

$group = New-Object System.Windows.Forms.GroupBox
$group.Text = 'Документы kit (אפיון, ADR, дизайн, документ проекта, отчёты)'
$group.Location = New-Object System.Drawing.Point(16, 238)
$group.Size = New-Object System.Drawing.Size(770, 112)
$form.Controls.Add($group)

$auto = New-Object System.Windows.Forms.CheckBox
$auto.Text = 'Утверждённые документы сразу становятся частью проекта (папка docs + AGENTS.md), commit делаешь ты'
$auto.Location = New-Object System.Drawing.Point(14, 26)
$auto.Size = New-Object System.Drawing.Size(740, 24)
$auto.Checked = $true
$group.Controls.Add($auto)

$docsLabel = New-Object System.Windows.Forms.Label
$docsLabel.Text = 'Папка документов внутри проекта:'
$docsLabel.Location = New-Object System.Drawing.Point(14, 62)
$docsLabel.Size = New-Object System.Drawing.Size(230, 22)
$group.Controls.Add($docsLabel)

$docs = New-Object System.Windows.Forms.TextBox
$docs.Text = 'docs'
$docs.Location = New-Object System.Drawing.Point(250, 59)
$docs.Size = New-Object System.Drawing.Size(200, 24)
$group.Controls.Add($docs)

$hint = New-Object System.Windows.Forms.Label
$hint.Text = 'Черновики и сам kit остаются локальными и скрыты от git.'
$hint.Location = New-Object System.Drawing.Point(14, 86)
$hint.Size = New-Object System.Drawing.Size(740, 20)
$hint.ForeColor = [System.Drawing.Color]::DimGray
$group.Controls.Add($hint)

$log = New-Object System.Windows.Forms.TextBox
$log.Multiline = $true
$log.ReadOnly = $true
$log.ScrollBars = 'Vertical'
$log.Font = New-Object System.Drawing.Font('Consolas', 9)
$log.Location = New-Object System.Drawing.Point(16, 360)
$log.Size = New-Object System.Drawing.Size(770, 180)
$form.Controls.Add($log)

$run = New-Object System.Windows.Forms.Button
$run.Text = 'Установить / обновить'
$run.Location = New-Object System.Drawing.Point(456, 552)
$run.Size = New-Object System.Drawing.Size(200, 34)
$form.Controls.Add($run)
$form.AcceptButton = $run

$close = New-Object System.Windows.Forms.Button
$close.Text = 'Закрыть'
$close.Location = New-Object System.Drawing.Point(666, 552)
$close.Size = New-Object System.Drawing.Size(120, 34)
$form.Controls.Add($close)
$form.CancelButton = $close

function Write-Log([string]$Text) {
    $log.AppendText($Text + [Environment]::NewLine)
    [System.Windows.Forms.Application]::DoEvents()
}

$add.Add_Click({
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = 'Папка проекта (где лежит .git)'
    if ($dlg.ShowDialog() -eq 'OK') {
        $p = $dlg.SelectedPath.TrimEnd('\')
        if ($paths -notcontains $p) {
            [void]$paths.Add($p)
            $i = $list.Items.Add((Format-Item $p))
            $list.SetItemChecked($i, $true)
            $cfg = Read-PublishSettings $p
            if ($cfg -and $cfg.docs_root) { $docs.Text = $cfg.docs_root }
            if ($cfg -and ($null -ne $cfg.auto_publish)) { $auto.Checked = [bool]$cfg.auto_publish }
            if (-not (Test-Path -LiteralPath (Join-Path $p '.git'))) {
                Write-Log "Внимание: в $p нет папки .git - kit не сможет скрыть свои файлы от git."
            }
        }
    }
})

$news.Add_Click({
    $changelog = Join-Path $KitRoot 'kit\.claude\tech-lead-kit\CHANGELOG.md'
    if (-not (Test-Path -LiteralPath $changelog)) { Write-Log 'CHANGELOG.md не найден.'; return }
    $text = Get-Content -LiteralPath $changelog -Raw -Encoding UTF8
    $parts = $text -split '(?m)^## '
    if ($parts.Count -gt 1) { Write-Log ('== ' + $parts[1].TrimEnd()) } else { Write-Log $text }
})

$close.Add_Click({ $form.Close() })

$run.Add_Click({
    $docsRoot = $docs.Text.Trim().Trim('\', '/')
    if (-not $docsRoot) { $docsRoot = 'docs' }
    if ($list.CheckedIndices.Count -eq 0) { Write-Log 'Ничего не отмечено.'; return }
    $run.Enabled = $false
    $env:TLK_FROM_GUI = '1'
    $failed = 0
    foreach ($i in @($list.CheckedIndices)) {
        $p = $paths[$i]
        Write-Log "=== $p"
        $ErrorActionPreference = 'Continue'  # stderr of install.cmd must not stop the window
        $out = & $InstallCmd $p 2>&1
        $code = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        foreach ($line in $out) { Write-Log ("  " + $line) }
        if ($code -ne 0) { $failed++; Write-Log '  ОШИБКА: установка не выполнена'; continue }
        Write-PublishSettings $p $docsRoot $auto.Checked
        $mode = 'по команде /tl-publish'
        if ($auto.Checked) { $mode = 'автоматически после утверждения' }
        Write-Log "  Документы: $docsRoot\ ($mode)"
        $list.Items[$i] = Format-Item $p
        $list.SetItemChecked($i, $false)
    }
    Remove-Item Env:\TLK_FROM_GUI -ErrorAction SilentlyContinue
    $run.Enabled = $true
    if ($failed -eq 0) {
        Write-Log ''
        Write-Log 'Готово. Дальше: открой проект в VS Code, начни НОВУЮ сессию Claude Code и запусти /tl-init'
        Write-Log '(после обновления тоже): проверка kit, лимиты времени, карта проекта, источники данных.'
        Write-Log 'Потом /tl-go: пиши своими словами, что нужно, - kit предложит маршрут и спросит подтверждение.'
    }
})

[void]$form.ShowDialog()
exit 0
