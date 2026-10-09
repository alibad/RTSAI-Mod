param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$ExpectedSha256,
    [Parameter(Mandatory=$true)][string]$TestRoot,
    [string]$Version = '0.4.0-alpha.1'
)
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^\d+\.\d+\.\d+(?:-[a-z]+\.\d+)?$') { throw 'Invalid release version.' }
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$TestRoot = [IO.Path]::GetFullPath($TestRoot)
if (-not $TestRoot.StartsWith('D:\rtsai-release\online-e2e-', [StringComparison]::OrdinalIgnoreCase)) { throw 'TestRoot must be in the explicitly designated online acceptance directory.' }
if ((Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash -ne $ExpectedSha256) { throw 'Downloaded installer hash mismatch.' }
$install = Join-Path $TestRoot 'installed-game'
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
$links = @((Join-Path $programs 'RTS AI/RTS AI.lnk'), (Join-Path $programs 'RTS AI/Uninstall RTS AI.lnk'), (Join-Path $desktop 'RTS AI.lnk'))
for ($i=0; $i -lt $links.Count; $i++) { if (Test-Path -LiteralPath $links[$i]) { Copy-Item -LiteralPath $links[$i] -Destination (Join-Path $backup "shortcut-$i.lnk") } }
$uninstalled = $false
try {
    $p = Start-Process -FilePath $Installer -ArgumentList "/AI=none /S /D=$install" -WindowStyle Hidden -PassThru
    $p.WaitForExit()
    if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $install 'RTSAI.exe'))) { throw 'Silent installer failed.' }
    $config = Get-Content -LiteralPath (Join-Path $install 'rtsai-install.json') -Raw | ConvertFrom-Json
    if ($config.ai_mode -ne 'none' -or $config.version -ne $Version) { throw 'Installer selection was not recorded correctly.' }
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($links[0])
    if ($shortcut.TargetPath -ne (Join-Path $install 'RTSAI.exe')) { throw 'Start menu shortcut targets the wrong game.' }
    & python (Join-Path $workspace 'tools/standalone-smoke.py') menu --packaged --worktree $install --switch-mode rtsai-topdown --seconds 24 --out (Join-Path $TestRoot 'installed-mode-switch') --set Game.IntroductionPromptVersion=99 --set Debug.SystemInformationVersionPrompt=99
    if ($LASTEXITCODE -ne 0) { throw 'Installed game smoke command failed.' }
    $log = Get-Content -LiteralPath (Join-Path $TestRoot 'installed-mode-switch/stdout.log') -Raw
    if ($log -notmatch 'Loading mod: rtsai-topdown' -or $log -match 'Exception|Fatal') { throw 'Installed mode switch failed.' }
    foreach ($mode in @('rtsai', 'rtsai-topdown')) {
        $map = if ($mode -eq 'rtsai') { 'twin-fords' } else { 'classic-frontier' }
        $out = Join-Path $TestRoot "installed-skirmish-$mode"
        & python (Join-Path $workspace 'tools/standalone-smoke.py') skirmish --packaged --worktree $install --mod $mode --map $map --observe --seconds 55 --out $out --set Game.IntroductionPromptVersion=99 --set Debug.SystemInformationVersionPrompt=99
        if ($LASTEXITCODE -ne 0) { throw "Installed $mode skirmish command failed." }
        $result = Get-Content -LiteralPath (Join-Path $out 'report.json') -Raw | ConvertFrom-Json
        if ($result.exited_early -or $result.'exception.log' -or $result.missing_sounds.Count -gt 0 -or $result.replays.Count -eq 0 -or -not ($result.lua -match 'CENSUS\|')) { throw "Installed $mode skirmish acceptance failed." }
    }
    Set-Content -LiteralPath (Join-Path $install 'keep-this-test-file.txt') -Value 'Uninstaller must preserve unrelated user files.'
    # The absolute install target above has been checked; the generated uninstaller removes only its payload.
    $u = Start-Process -FilePath (Join-Path $install 'Uninstall RTS AI.exe') -ArgumentList '/S' -WindowStyle Hidden -PassThru
    $u.WaitForExit()
    for ($i=0; $i -lt 30 -and (Test-Path -LiteralPath (Join-Path $install 'RTSAI.exe')); $i++) { Start-Sleep -Seconds 1 }
    if (Test-Path -LiteralPath (Join-Path $install 'RTSAI.exe')) { throw 'Uninstaller left the game payload behind.' }
    if (-not (Test-Path -LiteralPath (Join-Path $install 'keep-this-test-file.txt'))) { throw 'Uninstaller removed an unrelated file.' }
    $uninstalled = $true
    @{ version=$Version; scope='Fresh support directory on this Windows host; not a fresh OS'; downloadedHashVerified=$true; installer='passed'; modeSwitch='passed'; classicSkirmish='passed'; isometricSkirmish='passed'; uninstall='passed'; unrelatedFilePreserved=$true; existingRegistrationRestored=$true } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $TestRoot 'installer-acceptance.json')
    Write-Output 'Downloaded installer: install, configuration, shortcut, rendered mode switch and uninstall passed.'
} finally {
    # Restore the specific pre-existing registration and shortcut files touched by this installer.
    foreach ($key in $keys) { if (Test-Path -LiteralPath ($key -replace '^HKCU\\','HKCU:\')) { & reg.exe delete $key /f *> $null } }
    foreach ($file in $saved) { & reg.exe import $file *> $null; if ($LASTEXITCODE -ne 0) { Write-Warning "Restore failed: $file" } }
    for ($i=0; $i -lt $links.Count; $i++) {
        $file = Join-Path $backup "shortcut-$i.lnk"
        if (Test-Path -LiteralPath $file) { New-Item -ItemType Directory -Path (Split-Path $links[$i]) -Force | Out-Null; Copy-Item -LiteralPath $file -Destination $links[$i] -Force }
        elseif (Test-Path -LiteralPath $links[$i]) { Remove-Item -LiteralPath $links[$i] }
    }
    if (-not $uninstalled) { Write-Warning "Acceptance files retained at $install; previous game registration restored." }
}
