# Tech Lead Kit - installer window (Windows PowerShell 5.1, Windows Forms; no internet, no modules).
# Started by install.cmd without arguments. A table of projects (installed version, status, documents
# mode); projects are added by folder dialog, by scanning a root folder for git repositories, from the
# recent folders of VS Code, by drag and drop or by pasting a path. Runs install.cmd / uninstall.cmd
# for the checked projects and writes .claude\tl-memory\publish.json.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$KitRoot = Split-Path -Parent $PSScriptRoot
$InstallCmd = Join-Path $KitRoot 'install.cmd'
$UninstallCmd = Join-Path $KitRoot 'uninstall.cmd'
$NewVersion = (Get-Content -LiteralPath (Join-Path $KitRoot 'kit\.claude\tech-lead-kit\VERSION') -Raw).Trim()
$RegistryDir = Join-Path $env:LOCALAPPDATA 'TechLeadKit'
$Registry = Join-Path $RegistryDir 'projects.txt'
$SettingsFile = Join-Path $RegistryDir 'settings.json'
$SkipDirs = @('node_modules', 'bin', 'obj', '.vs', '.vscode', '.idea', 'packages', 'dist', 'build', 'venv', '.venv', '__pycache__')

# ---------------------------------------------------------------- data
function Get-KnownProjects {
    if (-not (Test-Path -LiteralPath $Registry)) { return @() }
    Get-Content -LiteralPath $Registry | Where-Object { $_.Trim() -and (Test-Path -LiteralPath $_) } |
        Sort-Object -Unique
}

function Save-Registry([string[]]$Projects) {
    if (-not (Test-Path -LiteralPath $RegistryDir)) { New-Item -ItemType Directory -Path $RegistryDir | Out-Null }
    [System.IO.File]::WriteAllLines($Registry, [string[]]($Projects | Sort-Object -Unique))
}

function Read-UiSettings {
    if (Test-Path -LiteralPath $SettingsFile) {
        try { return Get-Content -LiteralPath $SettingsFile -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
    }
    return New-Object PSObject
}

function Save-UiSetting([string]$Name, $Value) {
    $cfg = Read-UiSettings
    $cfg | Add-Member -NotePropertyName $Name -NotePropertyValue $Value -Force
    if (-not (Test-Path -LiteralPath $RegistryDir)) { New-Item -ItemType Directory -Path $RegistryDir | Out-Null }
    [System.IO.File]::WriteAllText($SettingsFile, ($cfg | ConvertTo-Json), (New-Object System.Text.UTF8Encoding $false))
}

function Get-InstalledVersion([string]$Project) {
    $v = Join-Path $Project '.claude\tech-lead-kit\VERSION'
    if (Test-Path -LiteralPath $v) { return (Get-Content -LiteralPath $v -Raw).Trim() }
    return $null
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

function Get-Status([string]$Project) {
    $v = Get-InstalledVersion $Project
    if (-not $v) { $s = 'не установлен' }
    elseif ($v -eq $NewVersion) { $s = 'актуально' }
    else { $s = "обновить до $NewVersion" }
    if (-not (Test-Path -LiteralPath (Join-Path $Project '.git'))) { $s += ' · нет .git' }
    return $s
}

function Get-DocsMode([string]$Project) {
    $cfg = Read-PublishSettings $Project
    if (-not $cfg) { return '—' }
    $root = if ($cfg.docs_root) { $cfg.docs_root } else { 'docs' }
    if ($cfg.auto_publish) { return "$root\ авто" }
    return "$root\ вручную"
}

function Find-GitProjects([string]$Root, [int]$Depth) {
    $found = New-Object System.Collections.ArrayList
    $queue = New-Object System.Collections.Queue
    $queue.Enqueue(@($Root, 0))
    while ($queue.Count -gt 0) {
        $item = $queue.Dequeue()
        $dir = $item[0]; $level = $item[1]
        if (Test-Path -LiteralPath (Join-Path $dir '.git')) { [void]$found.Add($dir); continue }
        if ($level -ge $Depth) { continue }
        try { $children = Get-ChildItem -LiteralPath $dir -Directory -ErrorAction Stop } catch { continue }
        foreach ($c in $children) {
            if ($SkipDirs -notcontains $c.Name -and -not $c.Name.StartsWith('.')) { $queue.Enqueue(@($c.FullName, $level + 1)) }
        }
    }
    return $found
}

function Get-VsCodeRecent {
    $result = New-Object System.Collections.ArrayList
    $files = @((Join-Path $env:APPDATA 'Code\User\globalStorage\storage.json'),
               (Join-Path $env:APPDATA 'Code\storage.json'))
    foreach ($f in $files) {
        if (-not (Test-Path -LiteralPath $f)) { continue }
        $text = Get-Content -LiteralPath $f -Raw -Encoding UTF8
        foreach ($m in [regex]::Matches($text, 'file:///([^"\\]+)')) {
            try { $p = [Uri]::UnescapeDataString($m.Groups[1].Value) -replace '/', '\' } catch { continue }
            $p = $p.TrimEnd('\')
            if ($p -match '^[a-zA-Z]:' -and (Test-Path -LiteralPath $p -PathType Container) -and $result -notcontains $p) {
                [void]$result.Add($p)
            }
        }
    }
    return $result
}

# ---------------------------------------------------------------- window
$font = New-Object System.Drawing.Font('Segoe UI', 9.5)
$form = New-Object System.Windows.Forms.Form
$form.Text = "Tech Lead Kit $NewVersion - установка и обновление"
$form.Size = New-Object System.Drawing.Size(1000, 740)
$form.MinimumSize = New-Object System.Drawing.Size(900, 640)
$form.StartPosition = 'CenterScreen'
$form.Font = $font
$form.AllowDrop = $true

$header = New-Object System.Windows.Forms.Panel
$header.Dock = 'Top'
$header.Height = 64
$header.BackColor = [System.Drawing.Color]::FromArgb(30, 64, 175)
$form.Controls.Add($header)

$title = New-Object System.Windows.Forms.Label
$title.Text = "Tech Lead Kit $NewVersion"
$title.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 15)
$title.ForeColor = [System.Drawing.Color]::White
$title.Location = New-Object System.Drawing.Point(16, 8)
$title.AutoSize = $true
$header.Controls.Add($title)

$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Text = 'Отметь проекты и нажми «Установить / обновить». Проекты можно перетащить в окно.'
$subtitle.ForeColor = [System.Drawing.Color]::FromArgb(219, 234, 254)
$subtitle.Location = New-Object System.Drawing.Point(18, 40)
$subtitle.AutoSize = $true
$header.Controls.Add($subtitle)

$news = New-Object System.Windows.Forms.Button
$news.Text = "Что нового в $NewVersion"
$news.Size = New-Object System.Drawing.Size(190, 30)
$news.Anchor = 'Top, Right'
$news.Location = New-Object System.Drawing.Point(($form.ClientSize.Width - 206), 17)
$news.FlatStyle = 'Flat'
$news.ForeColor = [System.Drawing.Color]::White
$header.Controls.Add($news)

function New-Button([string]$Text, [int]$X, [int]$Y, [int]$W) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $Text
    $b.Location = New-Object System.Drawing.Point($X, $Y)
    $b.Size = New-Object System.Drawing.Size($W, 30)
    $form.Controls.Add($b)
    return $b
}

$addFolder = New-Button 'Добавить папку...' 16 76 150
$scan = New-Button 'Найти проекты...' 172 76 150
$recent = New-Button 'Недавние из VS Code' 328 76 170

$pathBox = New-Object System.Windows.Forms.TextBox
$pathBox.Location = New-Object System.Drawing.Point(510, 79)
$pathBox.Size = New-Object System.Drawing.Size(360, 26)
$pathBox.Anchor = 'Top, Left, Right'
$form.Controls.Add($pathBox)
$addPath = New-Button 'Добавить' 876 76 92
$addPath.Anchor = 'Top, Right'

$view = New-Object System.Windows.Forms.ListView
$view.View = 'Details'
$view.CheckBoxes = $true
$view.FullRowSelect = $true
$view.GridLines = $true
$view.HideSelection = $false
$view.AllowDrop = $true
$view.Location = New-Object System.Drawing.Point(16, 114)
$view.Size = New-Object System.Drawing.Size(952, 250)
$view.Anchor = 'Top, Left, Right'
[void]$view.Columns.Add('Проект', 170)
[void]$view.Columns.Add('Путь', 380)
[void]$view.Columns.Add('Установлено', 100)
[void]$view.Columns.Add('Статус', 170)
[void]$view.Columns.Add('Документы', 120)
$form.Controls.Add($view)

$selUpdates = New-Button 'Отметить с обновлением' 16 370 190
$openDir = New-Button 'Открыть папку' 212 370 130
$forget = New-Button 'Убрать из списка' 348 370 150
$uninstall = New-Button 'Удалить kit из проекта' 504 370 180

$group = New-Object System.Windows.Forms.GroupBox
$group.Text = 'Документы kit (אפיון, ADR, дизайн, документ проекта, отчёты) — для отмеченных проектов'
$group.Location = New-Object System.Drawing.Point(16, 408)
$group.Size = New-Object System.Drawing.Size(952, 92)
$group.Anchor = 'Top, Left, Right'
$form.Controls.Add($group)

$auto = New-Object System.Windows.Forms.CheckBox
$auto.Text = 'Утверждённые документы сразу становятся частью проекта (папка docs + AGENTS.md), commit делаешь ты'
$auto.Location = New-Object System.Drawing.Point(14, 24)
$auto.Size = New-Object System.Drawing.Size(900, 24)
$auto.Checked = $true
$group.Controls.Add($auto)

$docsLabel = New-Object System.Windows.Forms.Label
$docsLabel.Text = 'Папка документов внутри проекта:'
$docsLabel.Location = New-Object System.Drawing.Point(14, 58)
$docsLabel.Size = New-Object System.Drawing.Size(230, 22)
$group.Controls.Add($docsLabel)

$docs = New-Object System.Windows.Forms.TextBox
$docs.Text = 'docs'
$docs.Location = New-Object System.Drawing.Point(250, 55)
$docs.Size = New-Object System.Drawing.Size(200, 24)
$group.Controls.Add($docs)

$hint = New-Object System.Windows.Forms.Label
$hint.Text = 'Черновики и сам kit остаются локальными и скрыты от git.'
$hint.Location = New-Object System.Drawing.Point(470, 58)
$hint.Size = New-Object System.Drawing.Size(460, 20)
$hint.ForeColor = [System.Drawing.Color]::DimGray
$group.Controls.Add($hint)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(16, 508)
$progress.Size = New-Object System.Drawing.Size(952, 12)
$progress.Anchor = 'Top, Left, Right'
$form.Controls.Add($progress)

$log = New-Object System.Windows.Forms.TextBox
$log.Multiline = $true
$log.ReadOnly = $true
$log.ScrollBars = 'Vertical'
$log.Font = New-Object System.Drawing.Font('Consolas', 9)
$log.Location = New-Object System.Drawing.Point(16, 526)
$log.Size = New-Object System.Drawing.Size(952, 116)
$log.Anchor = 'Top, Bottom, Left, Right'
$form.Controls.Add($log)

$run = New-Button 'Установить / обновить' 642 652 200
$run.Anchor = 'Bottom, Right'
$run.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 9.5)
$form.AcceptButton = $run
$close = New-Button 'Закрыть' 848 652 120
$close.Anchor = 'Bottom, Right'
$form.CancelButton = $close

function Write-Log([string]$Text) {
    $log.AppendText($Text + [Environment]::NewLine)
    [System.Windows.Forms.Application]::DoEvents()
}

function Update-Row($Item) {
    $p = $Item.Tag
    $v = Get-InstalledVersion $p
    $Item.SubItems[2].Text = $(if ($v) { $v } else { '—' })
    $Item.SubItems[3].Text = Get-Status $p
    $Item.SubItems[4].Text = Get-DocsMode $p
    if ($Item.SubItems[3].Text -like 'актуально*') { $Item.ForeColor = [System.Drawing.Color]::DarkGreen }
    elseif ($Item.SubItems[3].Text -like 'обновить*') { $Item.ForeColor = [System.Drawing.Color]::DarkOrange }
    else { $Item.ForeColor = [System.Drawing.SystemColors]::WindowText }
}

function Add-Project([string]$Path, [bool]$Check) {
    $p = $Path.Trim().Trim('"').TrimEnd('\')
    if (-not $p) { return }
    if (-not (Test-Path -LiteralPath $p -PathType Container)) { Write-Log "Нет такой папки: $p"; return }
    foreach ($it in $view.Items) { if ($it.Tag -eq $p) { $it.Checked = $true; return } }
    $item = New-Object System.Windows.Forms.ListViewItem((Split-Path -Leaf $p))
    [void]$item.SubItems.Add($p)
    [void]$item.SubItems.Add('')
    [void]$item.SubItems.Add('')
    [void]$item.SubItems.Add('')
    $item.Tag = $p
    [void]$view.Items.Add($item)
    Update-Row $item
    $item.Checked = $Check
    if (-not (Test-Path -LiteralPath (Join-Path $p '.git'))) {
        Write-Log "Внимание: в $p нет папки .git - kit не сможет скрыть свои файлы от git."
    }
}

function Select-Folders([string]$Caption, $Paths) {
    if (-not $Paths -or $Paths.Count -eq 0) { Write-Log "$Caption - ничего не найдено."; return }
    $dlg = New-Object System.Windows.Forms.Form
    $dlg.Text = $Caption
    $dlg.Size = New-Object System.Drawing.Size(720, 460)
    $dlg.StartPosition = 'CenterParent'
    $dlg.Font = $font
    $box = New-Object System.Windows.Forms.CheckedListBox
    $box.Location = New-Object System.Drawing.Point(12, 12)
    $box.Size = New-Object System.Drawing.Size(680, 350)
    $box.CheckOnClick = $true
    foreach ($p in $Paths) { [void]$box.Items.Add($p) }
    $dlg.Controls.Add($box)
    $ok = New-Object System.Windows.Forms.Button
    $ok.Text = 'Добавить отмеченные'
    $ok.Location = New-Object System.Drawing.Point(452, 372)
    $ok.Size = New-Object System.Drawing.Size(240, 32)
    $ok.DialogResult = 'OK'
    $dlg.Controls.Add($ok)
    $dlg.AcceptButton = $ok
    if ($dlg.ShowDialog($form) -eq 'OK') {
        foreach ($p in $box.CheckedItems) { Add-Project ([string]$p) $true }
    }
}

function Checked-Projects { return @($view.CheckedItems | ForEach-Object { $_ }) }

foreach ($p in Get-KnownProjects) {
    Add-Project $p ((Get-InstalledVersion $p) -ne $NewVersion)
}

# ---------------------------------------------------------------- actions
$addFolder.Add_Click({
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = 'Папка проекта (где лежит .git)'
    $last = (Read-UiSettings).last_folder
    if ($last -and (Test-Path -LiteralPath $last)) { $dlg.SelectedPath = $last }
    if ($dlg.ShowDialog() -eq 'OK') {
        Save-UiSetting 'last_folder' (Split-Path -Parent $dlg.SelectedPath)
        Add-Project $dlg.SelectedPath $true
    }
})

$scan.Add_Click({
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = 'Где искать проекты (например C:\dev). Ищутся папки с .git до глубины 3.'
    $last = (Read-UiSettings).scan_root
    if ($last -and (Test-Path -LiteralPath $last)) { $dlg.SelectedPath = $last }
    if ($dlg.ShowDialog() -eq 'OK') {
        Save-UiSetting 'scan_root' $dlg.SelectedPath
        Write-Log "Поиск проектов в $($dlg.SelectedPath)..."
        $form.Cursor = [System.Windows.Forms.Cursors]::WaitCursor
        $found = Find-GitProjects $dlg.SelectedPath 3
        $form.Cursor = [System.Windows.Forms.Cursors]::Default
        Select-Folders "Найдено проектов: $($found.Count)" $found
    }
})

$recent.Add_Click({ Select-Folders 'Недавние папки VS Code' (Get-VsCodeRecent) })

$addPath.Add_Click({ Add-Project $pathBox.Text $true; $pathBox.Clear() })
$pathBox.Add_KeyDown({ if ($_.KeyCode -eq 'Enter') { Add-Project $pathBox.Text $true; $pathBox.Clear(); $_.SuppressKeyPress = $true } })

$dragEnter = {
    if ($_.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) { $_.Effect = 'Copy' } else { $_.Effect = 'None' }
}
$dragDrop = {
    foreach ($p in $_.Data.GetData([System.Windows.Forms.DataFormats]::FileDrop)) {
        if (Test-Path -LiteralPath $p -PathType Container) { Add-Project $p $true }
    }
}
$view.Add_DragEnter($dragEnter)
$view.Add_DragDrop($dragDrop)
$form.Add_DragEnter($dragEnter)
$form.Add_DragDrop($dragDrop)

$view.Add_SelectedIndexChanged({
    if ($view.SelectedItems.Count -ne 1) { return }
    $cfg = Read-PublishSettings $view.SelectedItems[0].Tag
    if ($cfg -and $cfg.docs_root) { $docs.Text = $cfg.docs_root }
    if ($cfg -and ($null -ne $cfg.auto_publish)) { $auto.Checked = [bool]$cfg.auto_publish }
})

$selUpdates.Add_Click({
    foreach ($it in $view.Items) { $it.Checked = ($it.SubItems[3].Text -like 'обновить*') }
})

$openDir.Add_Click({
    foreach ($it in $view.SelectedItems) { Start-Process explorer.exe -ArgumentList "`"$($it.Tag)`"" }
})

$forget.Add_Click({
    foreach ($it in @($view.SelectedItems | ForEach-Object { $_ })) { $view.Items.Remove($it) }
    Save-Registry @($view.Items | ForEach-Object { $_.Tag })
})

$uninstall.Add_Click({
    $targets = @($view.SelectedItems | ForEach-Object { $_ })
    if ($targets.Count -eq 0) { Write-Log 'Выдели строку проекта, из которого удалить kit.'; return }
    $names = ($targets | ForEach-Object { $_.Tag }) -join [Environment]::NewLine
    $answer = [System.Windows.Forms.MessageBox]::Show("Удалить файлы kit из проектов?`n`n$names`n`nПамять проекта (.claude\tl-memory) и опубликованные документы останутся.",
        'Удалить kit', 'YesNo', 'Question')
    if ($answer -ne 'Yes') { return }
    foreach ($it in $targets) {
        Write-Log "=== удаление: $($it.Tag)"
        $ErrorActionPreference = 'Continue'
        $out = & $UninstallCmd $it.Tag 2>&1
        $ErrorActionPreference = 'Stop'
        foreach ($line in $out) { Write-Log ("  " + $line) }
        Update-Row $it
    }
})

$news.Add_Click({
    $changelog = Join-Path $KitRoot 'kit\.claude\tech-lead-kit\CHANGELOG.md'
    if (-not (Test-Path -LiteralPath $changelog)) { Write-Log 'CHANGELOG.md не найден.'; return }
    $text = Get-Content -LiteralPath $changelog -Raw -Encoding UTF8
    $parts = $text -split '(?m)^## '
    if ($parts.Count -gt 1) { $shown = '== ' + $parts[1].TrimEnd() } else { $shown = $text }
    [System.Windows.Forms.MessageBox]::Show($shown, "Что нового в $NewVersion", 'OK', 'Information') | Out-Null
})

$close.Add_Click({ $form.Close() })

$run.Add_Click({
    $docsRoot = $docs.Text.Trim().Trim('\', '/')
    if (-not $docsRoot) { $docsRoot = 'docs' }
    $targets = Checked-Projects
    if ($targets.Count -eq 0) { Write-Log 'Ничего не отмечено.'; return }
    $run.Enabled = $false
    $progress.Maximum = $targets.Count
    $progress.Value = 0
    $env:TLK_FROM_GUI = '1'
    $failed = 0
    foreach ($it in $targets) {
        $p = $it.Tag
        Write-Log "=== $p"
        $ErrorActionPreference = 'Continue'  # stderr of install.cmd must not stop the window
        $out = & $InstallCmd $p 2>&1
        $code = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        foreach ($line in $out) { Write-Log ("  " + $line) }
        if ($code -ne 0) { $failed++; Write-Log '  ОШИБКА: установка не выполнена' }
        else {
            Write-PublishSettings $p $docsRoot $auto.Checked
            $mode = 'по команде /tl-publish'
            if ($auto.Checked) { $mode = 'автоматически после утверждения' }
            Write-Log "  Документы: $docsRoot\ ($mode)"
            $it.Checked = $false
        }
        Update-Row $it
        $progress.Value++
    }
    Remove-Item Env:\TLK_FROM_GUI -ErrorAction SilentlyContinue
    Save-Registry @($view.Items | ForEach-Object { $_.Tag })
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
