param([string]$EngineSource)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (!$EngineSource) { $EngineSource = (Get-Content -LiteralPath (Join-Path $projectRoot 'recovery.local.json') -Raw | ConvertFrom-Json).engineDirectory }
$utility = Join-Path $EngineSource 'bin/OpenRA.Utility.exe'
$env:ENGINE_DIR = $EngineSource
$env:MOD_SEARCH_PATHS = if (Test-Path -LiteralPath (Join-Path $EngineSource 'recovery-build.json')) { "$EngineSource/mods" } else { "$projectRoot/mods,$EngineSource/mods" }
function Check([string]$mode, [string[]]$arguments) {
 & $utility $mode @arguments
 if ($LASTEXITCODE -ne 0) { throw "Native verification failed: $mode $arguments" }
}
foreach ($profile in @('ai-assistant-only','world-war-iii','layered-defense','campaign-authoring','combined-arms-laboratory')) {
 $env:OPENRA_UTILITY_EXPERIENCE_PROFILE = $profile
 Check 'rtsai-classic-core' @('--check-native-recovery')
}
foreach ($profile in @('ra2-modern','ra2-original-combined-arms','ra2-classic')) {
 $env:OPENRA_UTILITY_EXPERIENCE_PROFILE = $profile
 Check 'rtsai' @('--check-native-recovery')
}
$env:OPENRA_UTILITY_EXPERIENCE_PROFILE = $null
foreach ($mode in @('rtsai-library','rtsai-ra2','rtsai','rtsai-classic-core')) {
 Check $mode @('--check-game-library')
}
foreach ($profile in @('ra2-classic','ra2-original-combined-arms','ra2-modern')) {
 $env:OPENRA_UTILITY_EXPERIENCE_PROFILE = $profile
 Check 'rtsai-ra2' @('--check-native-recovery')
}
$env:OPENRA_UTILITY_EXPERIENCE_PROFILE = $null
Check 'rtsai' @('--check-desktop-settings')
Check 'rtsai' @('--check-standalone','--strict')
Check 'rtsai' @('--check-yaml')
Check 'rtsai-classic-core' @('--check-yaml')
Check 'rtsai-ra2' @('--check-yaml')
Check 'rtsai-library' @('--check-yaml')
Write-Host 'Native rules, settings and standalone checks passed. Rendered acceptance is tools/recovery-smoke.py.'
