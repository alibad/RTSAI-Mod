param(
 [Parameter(ValueFromRemainingArguments=$true)][string[]]$GameArguments,
 [ValidateSet('rtsai-library', 'rtsai', 'rtsai-ra2', 'rtsai-classic-core')][string]$Mod = 'rtsai-library'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$configPath = Join-Path $projectRoot 'recovery.local.json'
if (!(Test-Path -LiteralPath $configPath)) { throw 'Build the local desktop with tools/build-desktop-recovery.ps1 first.' }
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$contentPointer = Join-Path $projectRoot '.recovery/content-current.json'
if (Test-Path -LiteralPath $contentPointer) {
 $reference = Get-Content -LiteralPath $contentPointer -Raw | ConvertFrom-Json
 if ((Get-FileHash -LiteralPath $reference.receipt -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reference.sha256) { throw 'Shared content receipt changed; build and verify again in Studio.' }
 $content = Get-Content -LiteralPath $reference.receipt -Raw | ConvertFrom-Json
 $saved = & python (Join-Path $projectRoot 'tools/unit-content.py') check | ConvertFrom-Json
 if ($LASTEXITCODE -ne 0 -or !$content.verified -or !$content.verification.passed -or $content.revision -ne $saved.revision) { throw 'Saved content needs a verified build. Open Studio and choose Build & test locally.' }
 foreach ($entry in $content.checksums) {
  if ((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Shared build file changed: $($entry.path)" }
 }
 $config.engineDirectory = $content.native
 $config.supportDirectory = $content.support
 Write-Host "Content $($content.revision.Substring(0,10)) - Built and verified in Classic/RA2 desktop/web - Local"
}
$runtimeRoot = $config.engineDirectory
$runtimeExe = Join-Path $runtimeRoot 'bin/RTSAI.exe'
if (!(Test-Path -LiteralPath $runtimeExe)) { $runtimeExe = Join-Path $runtimeRoot 'bin/OpenRA.exe' }
if (!(Test-Path -LiteralPath $runtimeExe)) { throw "Local native runtime missing: $runtimeExe" }
# Reuse the project's local companion. Its settings and lifetime stay owned by the game.
$companionRoot = Join-Path (Split-Path $projectRoot -Parent) 'OpenRA-AI'
if (Test-Path -LiteralPath (Join-Path $companionRoot '.venv/Scripts/python.exe')) { $env:OPENRA_AI_ROOT = $companionRoot }
$env:MOD_SEARCH_PATHS = "$runtimeRoot/mods"
$env:RTSAI_RECOVERY_SCREEN = $null
$env:RTSAI_VERIFY_MODE_SWITCH = $null
$env:OPENRA_UTILITY_EXPERIENCE_PROFILE = $null
$env:RTSAI_LIBRARY_SUPPORT = $config.supportDirectory
$modeSupport = Join-Path $config.supportDirectory "Games/$Mod"
New-Item -ItemType Directory -Path $modeSupport -Force | Out-Null
$launchArgs = @("Game.Mod=$Mod", "Engine.EngineDir=$runtimeRoot", "Engine.ModSearchPaths=$runtimeRoot/mods", "Engine.SupportDir=$modeSupport", 'Game.FetchNews=false', "Engine.LaunchPath=$projectRoot/launch-game.cmd") + $GameArguments
Push-Location $runtimeRoot
try { & $runtimeExe @launchArgs; exit $LASTEXITCODE }
finally { Pop-Location }
