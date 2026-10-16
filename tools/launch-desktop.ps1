param([Parameter(ValueFromRemainingArguments=$true)][string[]]$GameArguments)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$configPath = Join-Path $projectRoot 'recovery.local.json'
if (!(Test-Path -LiteralPath $configPath)) { throw 'Build the local desktop with tools/build-desktop-recovery.ps1 first.' }
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$runtimeRoot = $config.engineDirectory
$runtimeExe = Join-Path $runtimeRoot 'bin/OpenRA.exe'
if (!(Test-Path -LiteralPath $runtimeExe)) { throw "Local native runtime missing: $runtimeExe" }
# Reuse the project's local companion. Its settings and lifetime stay owned by the game.
$companionRoot = Join-Path (Split-Path $projectRoot -Parent) 'OpenRA-AI'
if (Test-Path -LiteralPath (Join-Path $companionRoot '.venv/Scripts/python.exe')) { $env:OPENRA_AI_ROOT = $companionRoot }
$env:MOD_SEARCH_PATHS = "$runtimeRoot/mods"
$env:RTSAI_RECOVERY_SCREEN = $null
$env:RTSAI_VERIFY_MODE_SWITCH = $null
$env:OPENRA_UTILITY_EXPERIENCE_PROFILE = $null
$env:RTSAI_LIBRARY_SUPPORT = $config.supportDirectory
$hubSupport = Join-Path $config.supportDirectory 'Games/rtsai-library'
New-Item -ItemType Directory -Path $hubSupport -Force | Out-Null
$launchArgs = @('Game.Mod=rtsai-library', "Engine.EngineDir=$runtimeRoot", "Engine.ModSearchPaths=$runtimeRoot/mods", "Engine.SupportDir=$hubSupport", 'Game.FetchNews=false', "Engine.LaunchPath=$projectRoot/launch-game.cmd") + $GameArguments
Push-Location $runtimeRoot
try { & $runtimeExe @launchArgs; exit $LASTEXITCODE }
finally { Pop-Location }
