param([string]$EngineSource = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'OpenRA'))
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$EngineSource = (Resolve-Path -LiteralPath $EngineSource).Path
function Run-Git([string]$root, [string[]]$gitArguments) {
 & git -C $root @gitArguments
 if ($LASTEXITCODE -ne 0) { throw "Git failed in $root" }
}
Run-Git $projectRoot @('fetch','origin','main')
Run-Git $projectRoot @('merge','--ff-only','origin/main')
Run-Git $EngineSource @('fetch','fork','main')
Run-Git $EngineSource @('merge','--ff-only','fork/main')
foreach ($root in @($projectRoot,$EngineSource)) {
 if (& git -C $root status --porcelain) { throw "Commit source changes before building: $root" }
}
$modCommit = (& git -C $projectRoot rev-parse HEAD).Trim()
$engineCommit = (& git -C $EngineSource rev-parse HEAD).Trim()
& python (Join-Path $PSScriptRoot 'shared-content.py') check
if ($LASTEXITCODE -ne 0) { throw 'Shared content is stale; compile and commit it before building.' }
Push-Location $EngineSource
try { & dotnet build OpenRA.slnx -c Release --nologo -v quiet; if ($LASTEXITCODE -ne 0) { throw 'Engine build failed.' } }
finally { Pop-Location }
Push-Location $projectRoot
try {
 foreach ($project in @('OpenRA.Mods.RA2','OpenRA.Mods.RTSAI')) {
  & dotnet build "$project/$project.csproj" -c Release "-p:EngineRootPath=$EngineSource" --nologo -v quiet
  if ($LASTEXITCODE -ne 0) { throw "$project build failed." }
 }
}
finally { Pop-Location }
$runtimeRoot = Join-Path $projectRoot ".recovery/native-$($modCommit.Substring(0,7))-$($engineCommit.Substring(0,7))"
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
foreach ($relative in @('bin','glsl','mods/common','mods/common-content','global mix database.dat','AUTHORS','COPYING','VERSION')) {
 $sourcePath = Join-Path $EngineSource $relative
 if (!(Test-Path -LiteralPath $sourcePath)) { continue }
 $destinationPath = Join-Path $runtimeRoot $relative
 New-Item -ItemType Directory -Path (Split-Path $destinationPath -Parent) -Force | Out-Null
 if (Test-Path -LiteralPath $sourcePath -PathType Container) {
  New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null
  Get-ChildItem -LiteralPath $sourcePath -Force | Copy-Item -Destination $destinationPath -Recurse -Force
 } else { Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force }
}
$supportRoot = Join-Path $projectRoot '.recovery/support'
# Snapshot game data as well as assemblies so later source edits cannot change this build.
foreach ($pack in Get-ChildItem -LiteralPath (Join-Path $projectRoot 'mods') -Directory) {
 $destinationPack = Join-Path $runtimeRoot "mods/$($pack.Name)"
 New-Item -ItemType Directory -Path $destinationPack -Force | Out-Null
 Get-ChildItem -LiteralPath $pack.FullName -Force | Copy-Item -Destination $destinationPack -Recurse -Force
}
# The existing World Studio protocol calls the native utility as `ra`. Give that
# tool a hidden alias of the recovered Classic pack, using the same engine.
$generatorPack = Join-Path $runtimeRoot 'mods/ra'
New-Item -ItemType Directory -Path $generatorPack -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $projectRoot 'mods/rtsai-classic-core') -Force | Copy-Item -Destination $generatorPack -Recurse -Force
$aliasManifest = Join-Path $generatorPack 'mod.yaml'
$aliasYaml = Get-Content -LiteralPath $aliasManifest -Raw -Encoding utf8
$aliasYaml = $aliasYaml.Replace("Metadata:`n", "Metadata:`n`tHidden: true`n")
$aliasYaml | Set-Content -LiteralPath $aliasManifest -Encoding utf8
& python (Join-Path $PSScriptRoot 'migrate-desktop-support.py') --destination $supportRoot
if ($LASTEXITCODE -ne 0) { throw 'Player data migration failed.' }
$config = @{engineDirectory=$runtimeRoot;supportDirectory=$supportRoot;modCommit=$modCommit;engineCommit=$engineCommit;localOnly=$true}
$json = $config | ConvertTo-Json
$json | Set-Content -LiteralPath (Join-Path $runtimeRoot 'recovery-build.json') -Encoding utf8
$json | Set-Content -LiteralPath (Join-Path $projectRoot 'recovery.local.json') -Encoding utf8
Write-Host "Native desktop ready. Launch $projectRoot/launch-game.cmd"
