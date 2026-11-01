param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$ExpectedSha256,
    [Parameter(Mandatory=$true)][string]$TestRoot,
    [string]$Version = '0.4.0-alpha.1',
    [string]$LocalAIModelSource,
    # A Content folder holding Classic's freeware Red Alert files (Content\ra\v2); without it Classic's skirmish is not run.
    [string]$ClassicContent
)
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^\d+\.\d+\.\d+(?:-[a-z]+\.\d+)?$') { throw 'Invalid release version.' }
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$TestRoot = [IO.Path]::GetFullPath($TestRoot)
# Task working folders live only in F:\work\<topic>-<YYYYMMDD>\ (owner rule, 31 October 2026).
if ($TestRoot -notmatch '^F:\\work\\[^\\]+-\d{8}\\') { throw 'TestRoot must be inside a task folder F:\work\<topic>-<YYYYMMDD>\.' }
if ((Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash -ne $ExpectedSha256) { throw 'Downloaded installer hash mismatch.' }
# A space in the path, like the default install folder (%LOCALAPPDATA%\Programs\RTS AI).
$install = Join-Path $TestRoot 'RTS AI'
if (Test-Path -LiteralPath $install) { throw 'Acceptance install directory already exists; preserve the previous run.' }
$backup = Join-Path $TestRoot 'previous-registration'
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$keys = @('HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\RTSAI', "HKCU\Software\Classes\openra-rtsai-$Version")
$saved = @()
for ($i=0; $i -lt $keys.Count; $i++) {
    $file = Join-Path $backup "registry-$i.reg"
    if (Test-Path -LiteralPath ($keys[$i] -replace '^HKCU\\','HKCU:\')) { & reg.exe export $keys[$i] $file /y *> $null; if ($LASTEXITCODE -ne 0) { throw 'Cannot preserve previous game registration.' }; $saved += $file }
}
$programs = [Environment]::GetFolderPath('Programs')
$desktop = [Environment]::GetFolderPath('Desktop')
$browserLink = Join-Path $desktop 'RTS AI.lnk'
$browserLinkHash = if (Test-Path -LiteralPath $browserLink) { (Get-FileHash -LiteralPath $browserLink -Algorithm SHA256).Hash } else { $null }
$browserLinkBackup = Join-Path $backup 'browser-shortcut.lnk'
if ($browserLinkHash) { Copy-Item -LiteralPath $browserLink -Destination $browserLinkBackup }
function Assert-BrowserShortcutPreserved {
    $hash = if (Test-Path -LiteralPath $browserLink) { (Get-FileHash -LiteralPath $browserLink -Algorithm SHA256).Hash } else { $null }
    if ($hash -ne $browserLinkHash) { throw 'Installer or uninstaller changed the browser app desktop shortcut.' }
}
$links = @((Join-Path $programs 'RTS AI/RTS AI.lnk'), (Join-Path $programs 'RTS AI/Uninstall RTS AI.lnk'), (Join-Path $desktop 'RTS AI (Windows).lnk'))
for ($i=0; $i -lt $links.Count; $i++) { if (Test-Path -LiteralPath $links[$i]) { Copy-Item -LiteralPath $links[$i] -Destination (Join-Path $backup "shortcut-$i.lnk") } }
$uninstalled = $false
try {
    $p = Start-Process -FilePath $Installer -ArgumentList "/AI=none /S /D=$install" -WindowStyle Hidden -PassThru
    $p.WaitForExit()
    if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $install 'RTSAI.exe'))) { throw 'Silent installer failed.' }
    Assert-BrowserShortcutPreserved
    $config = Get-Content -LiteralPath (Join-Path $install 'rtsai-install.json') -Raw | ConvertFrom-Json
    if ($config.ai_mode -ne 'none' -or $config.version -ne $Version) { throw 'Installer selection was not recorded correctly.' }
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($links[0])
    if ($shortcut.TargetPath -ne (Join-Path $install 'RTSAI.exe')) { throw 'Start menu shortcut targets the wrong game.' }
    if (-not (Test-Path -LiteralPath $links[2])) { throw 'Windows desktop shortcut is missing.' }
    $desktopShortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($links[2])
    if ($desktopShortcut.TargetPath -ne (Join-Path $install 'RTSAI.exe')) { throw 'Windows desktop shortcut targets the wrong game.' }
    if ((Get-Content -LiteralPath (Join-Path $install 'mods/rtsai-library/mod.yaml') -Raw) -notmatch "Version: $([regex]::Escape($Version))") { throw 'The installed Library is not this version.' }
    # The Library's three games (OpenRA.Mods.RTSAI/Library/NativeGameLibrary.cs): a bot skirmish in each, started
    # from the installed RTSAI.exe in its own fresh support directory, with window grabs and a per-bot census.
    $artTools = Join-Path (Split-Path $workspace -Parent) 'RTSAI-Art/tools'
    $games = @(
        @{ Mod = 'rtsai-classic-core'; Map = 'a-nuclear-winter'; Bots = 'Multi0:normal:england,Multi1:normal:russia' },
        @{ Mod = 'rtsai-ra2'; Map = 'ra2-defcon-6'; Bots = 'Multi0:normal:america,Multi1:normal:russia' },
        @{ Mod = 'rtsai'; Map = 'ra2-defcon-6'; Bots = 'Multi0:normal:china,Multi1:normal:iran' })
    $skirmishes = [ordered]@{}
    foreach ($game in $games) {
        if ($game.Mod -eq 'rtsai-classic-core' -and -not $ClassicContent) { $skirmishes[$game.Mod] = 'not-run (no -ClassicContent)'; continue }
        $out = Join-Path $TestRoot "installed-skirmish-$($game.Mod)"
        $smoke = @('--engine', $install, '--packaged', '--mod', $game.Mod, '--map', $game.Map, '--bots', $game.Bots, '--seconds', '70', '--out', $out, '--art-tools', $artTools)
        if ($game.Mod -eq 'rtsai-classic-core') { $smoke += @('--content', [IO.Path]::GetFullPath($ClassicContent)) }
        & python (Join-Path $workspace 'tools/recovery-smoke.py') @smoke
        if ($LASTEXITCODE -ne 0) { throw "Installed $($game.Mod) skirmish failed; see $out." }
        $skirmishes[$game.Mod] = 'passed'
    }
    if ($LocalAIModelSource) {
        $modelSource = [IO.Path]::GetFullPath($LocalAIModelSource)
        $companion = Join-Path $install 'companion'
        if (-not (Test-Path -LiteralPath (Join-Path $companion 'rtsai-companion.exe'))) { throw 'Local AI acceptance requires a bundled companion.' }
        Copy-Item -LiteralPath (Join-Path $modelSource 'models') -Destination (Join-Path $companion 'ai') -Recurse
        Copy-Item -LiteralPath (Join-Path $modelSource 'pack.json') -Destination (Join-Path $companion 'ai/pack.json')
        & (Join-Path $companion 'rtsai-companion.exe') pack status --root $companion --profile recommended
        if ($LASTEXITCODE -ne 0) { throw 'Seeded local AI model verification failed.' }
        $config.ai_mode = 'local'
        $config.stamp = 'acceptance-local-' + [guid]::NewGuid().ToString('N')
        $config | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $install 'rtsai-install.json')
        & python (Join-Path $workspace 'tools/packaged-companion-smoke.py') --install $install --out (Join-Path $TestRoot 'installed-local-companion')
        if ($LASTEXITCODE -ne 0) { throw 'Installed local companion acceptance failed.' }
    }
    Set-Content -LiteralPath (Join-Path $install 'keep-this-test-file.txt') -Value 'Uninstaller must preserve unrelated user files.'
    # The absolute install target above has been checked; the generated uninstaller removes only its payload.
    $u = Start-Process -FilePath (Join-Path $install 'Uninstall RTS AI.exe') -ArgumentList '/S' -WindowStyle Hidden -PassThru
    $u.WaitForExit()
    for ($i=0; $i -lt 30 -and (Test-Path -LiteralPath (Join-Path $install 'RTSAI.exe')); $i++) { Start-Sleep -Seconds 1 }
    if (Test-Path -LiteralPath (Join-Path $install 'RTSAI.exe')) { throw 'Uninstaller left the game payload behind.' }
    Assert-BrowserShortcutPreserved
    if (Test-Path -LiteralPath $links[2]) { throw 'Uninstaller left the Windows desktop shortcut behind.' }
    if (-not (Test-Path -LiteralPath (Join-Path $install 'keep-this-test-file.txt'))) { throw 'Uninstaller removed an unrelated file.' }
    $uninstalled = $true
    @{ version=$Version; scope='Fresh support directory on this Windows host; not a fresh OS'; installerHashVerified=$true; installer='passed'; skirmishes=$skirmishes; localCompanion=$(if ($LocalAIModelSource) { 'passed' } else { 'not-run' }); uninstall='passed'; unrelatedFilePreserved=$true; existingRegistrationRestored=$true } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $TestRoot 'installer-acceptance.json')
    Write-Output 'Packaged installer: install, configuration, shortcuts, gameplay and uninstall passed.'
} finally {
    # Restore the specific pre-existing registration and shortcut files touched by this installer.
    # An older installer under test can still damage the shared name before the assertion fails.
    if ($browserLinkHash) { Copy-Item -LiteralPath $browserLinkBackup -Destination $browserLink -Force }
    elseif (Test-Path -LiteralPath $browserLink) { Remove-Item -LiteralPath $browserLink }
    foreach ($key in $keys) { if (Test-Path -LiteralPath ($key -replace '^HKCU\\','HKCU:\')) { & reg.exe delete $key /f *> $null } }
    foreach ($file in $saved) { & reg.exe import $file *> $null; if ($LASTEXITCODE -ne 0) { Write-Warning "Restore failed: $file" } }
    for ($i=0; $i -lt $links.Count; $i++) {
        $file = Join-Path $backup "shortcut-$i.lnk"
        if (Test-Path -LiteralPath $file) { New-Item -ItemType Directory -Path (Split-Path $links[$i]) -Force | Out-Null; Copy-Item -LiteralPath $file -Destination $links[$i] -Force }
        elseif (Test-Path -LiteralPath $links[$i]) { Remove-Item -LiteralPath $links[$i] }
    }
    if (-not $uninstalled) { Write-Warning "Acceptance files retained at $install; previous game registration restored." }
}
