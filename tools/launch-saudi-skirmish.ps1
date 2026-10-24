param([ValidateSet('normal', 'medium', 'rush')][string]$Difficulty = 'normal')
$ErrorActionPreference = 'Stop'
# The canonical launcher verifies the accepted shared build and preserves the Library return path.
& (Join-Path $PSScriptRoot 'launch-desktop.ps1') -Mod rtsai -GameArguments @(
 'Launch.Map=twin-fords', 'Launch.Faction=saudi', "Launch.Bots=Multi1:${Difficulty}:iran"
)
exit $LASTEXITCODE
