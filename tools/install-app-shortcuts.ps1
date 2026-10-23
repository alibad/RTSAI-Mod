param()
$ErrorActionPreference = 'Stop'
$modRoot = Split-Path $PSScriptRoot -Parent
$games = Split-Path $modRoot -Parent
$state = Join-Path $env:LOCALAPPDATA 'RTSAI/app-shortcuts'
$backup = Join-Path $state ('backups/' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $backup | Out-Null
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$programs = Join-Path ([Environment]::GetFolderPath('Programs')) 'RTS AI'
New-Item -ItemType Directory -Force -Path $programs | Out-Null
$studioLink = Join-Path $desktop 'Faction Studio.lnk'
if (Test-Path -LiteralPath $studioLink) {
    $old = $shell.CreateShortcut($studioLink)
    if ($old.Arguments -match '--app-id=') {
        @{ target = $old.TargetPath; arguments = $old.Arguments } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $state 'installed-studio.json') -Encoding UTF8
    }
}
$apps = @(
    @{name='RTS AI'; script="$modRoot/tools/launch-desktop.ps1"; args=''; icon="$modRoot/packaging/artwork/rtsai.ico"; description='RTS AI native desktop game'},
    @{name='Faction Studio'; script="$games/RTSAI-Web/scripts/launch-app.ps1"; args='-App Studio'; icon="$games/RTSAI-Web/public/brand/faction-studio/favicon.ico"; description='Local Faction Studio — units, artwork and encounters'},
    @{name='RTS AI Website'; script="$games/RTSAI-Web/scripts/launch-app.ps1"; args='-App Website'; icon="$games/RTSAI-Web/public/favicon.ico"; description='RTS AI website in its own local app window'},
    @{name='RTS AI Web Game'; script="$games/RTSAI-WebGame/tools/launch-web-game.ps1"; args=''; icon="$games/RTSAI-WebGame/web/public/favicon.ico"; description='Verified local RTS AI browser game in its own app window'}
)
foreach ($app in $apps) {
    if (!(Test-Path -LiteralPath $app.icon)) { throw "Missing approved icon: $($app.icon)" }
    foreach ($directory in @($desktop,$programs)) {
        $destination = Join-Path $directory ($app.name + '.lnk')
        if (Test-Path -LiteralPath $destination) { Copy-Item -LiteralPath $destination -Destination (Join-Path $backup (([guid]::NewGuid().ToString()) + '.lnk')) }
        $link = $shell.CreateShortcut($destination)
        $link.TargetPath = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
        $link.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$($app.script)`" $($app.args)"
        $link.IconLocation = "$($app.icon),0"
        $link.WorkingDirectory = Split-Path (Split-Path $app.script -Parent) -Parent
        $link.Description = $app.description
        $link.Save()
        Write-Output "Installed $destination"
    }
}
$installedIcon = Join-Path $env:LOCALAPPDATA 'Programs/RTS AI/rtsai.ico'
if (Test-Path -LiteralPath $installedIcon) {
    Copy-Item -LiteralPath $installedIcon -Destination (Join-Path $backup 'installed-native-icon.ico')
    Copy-Item -LiteralPath "$modRoot/packaging/artwork/rtsai.ico" -Destination $installedIcon -Force
}
Write-Output "Previous shortcuts preserved in $backup"
