<#
.SYNOPSIS
Build the RTS AI Windows release on a Windows host: portable zip, per-user NSIS installer and checksums.

.DESCRIPTION
A Windows-native port of the Mod SDK's packaging/windows/buildpackage.sh (which needs Linux,
wine64 and ImageMagick). It publishes the pinned engine and the mod self-contained for win-x64,
builds the RTSAI.exe launcher with the RTS AI icon, stamps version resources with rcedit, adds
the frozen AI companion when -CompanionDirectory is given (companion\, from OpenRA-AI
scripts/package-rtsai-companion.ps1), signs every .exe when signing is configured (sign-windows.ps1)
and writes:

    RTSAI-<version>-win-x64-setup.exe        per-user installer (no admin)
    RTSAI-<version>-win-x64-portable.zip     unzip and run RTSAI.exe
    RTSAI-VoicePack-<version>.zip            optional offline voice pack (copied from -VoicePack)
    *.sha256 and SHA256SUMS.txt

The installer only offers the AI options this build can deliver:
    no -CompanionDirectory           no AI page; the co-commander starts off (rtsai-install.json "none")
    -CompanionDirectory              "Full local AI" and "No AI"
    -CompanionDirectory -HostedAI    also "Hosted AI + local voice" (only once the hosted service is live)

PACKAGING_STANDALONE="True" in mod.config (the rtsai/standalone game) ships only mods/<MOD_ID> and leaves
out the engine's MIX filename database and every Red Alert 2 reference in the installer and version info.

Requirements: .NET 10 SDK, NSIS 3 (winget install NSIS.NSIS), rcedit-x64.exe
(https://github.com/electron/rcedit/releases) and tar.exe (built into Windows 10/11).
Run `make.cmd all` once first so ./engine exists.

.EXAMPLE
packaging\windows\build-release.ps1 -Version 0.3.0-alpha.1 -OutputDirectory D:\rtsai-release\out `
    -WorkDirectory D:\rtsai-release\work -RcEdit C:\tools\rcedit-x64.exe
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [string]$CompanionDirectory,
    [switch]$HostedAI,
    [string]$VoicePack,
    [string]$WorkDirectory,
    [string]$RcEdit = $env:RCEDIT_PATH,
    [string]$MakeNsis,
    [switch]$SkipInstaller,
    [switch]$RequireSignatures
)

$ErrorActionPreference = "Stop"
$packagingDirectory = $PSScriptRoot
$root = (Resolve-Path (Join-Path $packagingDirectory "..\..")).Path

function Invoke-Native {
    param([Parameter(Mandatory = $true)][string]$FilePath, [string[]]$Arguments = @(), [string]$Failure, [string]$WorkingDirectory)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    if ($WorkingDirectory) { Push-Location $WorkingDirectory }
    try {
        & $FilePath @Arguments 2>&1 | ForEach-Object { "$_" } | Out-Host
        $code = $LASTEXITCODE
    } finally {
        if ($WorkingDirectory) { Pop-Location }
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) { throw "$Failure (exit $code)" }
}

# mod.config is a shell file of KEY="value" lines.
$config = @{}
foreach ($line in Get-Content -LiteralPath (Join-Path $root "mod.config")) {
    if ($line -match '^\s*([A-Z_]+)="(.*)"\s*$') { $config[$Matches[1]] = $Matches[2] }
}
$userConfig = Join-Path $root "user.config"
if (Test-Path -LiteralPath $userConfig) {
    foreach ($line in Get-Content -LiteralPath $userConfig) {
        if ($line -match '^\s*([A-Z_]+)="(.*)"\s*$') { $config[$Matches[1]] = $Matches[2] }
    }
}
$modId = $config["MOD_ID"]
$launcherName = $config["PACKAGING_WINDOWS_LAUNCHER_NAME"]
$engine = [IO.Path]::GetFullPath((Join-Path $root $config["ENGINE_DIRECTORY"]))
$installerName = $config["PACKAGING_INSTALLER_NAME"]
$standalone = $config["PACKAGING_STANDALONE"] -eq "True"
if (-not (Test-Path -LiteralPath (Join-Path $engine "OpenRA.Game\OpenRA.Game.csproj"))) {
    throw "The pinned engine is missing in $engine. Run make.cmd all (or fetch-local-engine.sh) first."
}

if ($Version -notmatch '^(\d+)\.(\d+)\.(\d+)(?:-[a-z]+\.?(\d+))?$') { throw "Version must look like 0.2.0-alpha.1" }
$fileVersion = "$($Matches[1]).$($Matches[2]).$($Matches[3]).$(if ($Matches[4]) { $Matches[4] } else { 0 })"

if ($CompanionDirectory) {
    $CompanionDirectory = (Resolve-Path -LiteralPath $CompanionDirectory).Path
    if (-not (Test-Path -LiteralPath (Join-Path $CompanionDirectory "rtsai-companion.exe"))) {
        throw "No rtsai-companion.exe in $CompanionDirectory (build it with OpenRA-AI scripts/package-rtsai-companion.ps1)."
    }
} elseif ($HostedAI -or $VoicePack) {
    throw "-HostedAI and -VoicePack need the AI companion (-CompanionDirectory)."
}
if (-not $RcEdit -or -not (Test-Path -LiteralPath $RcEdit)) {
    throw "rcedit-x64.exe is required: download it from https://github.com/electron/rcedit/releases and pass -RcEdit (or set RCEDIT_PATH)."
}
if (-not $SkipInstaller) {
    if (-not $MakeNsis) {
        $MakeNsis = @(
            (Get-Command makensis.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
            (Join-Path $env:LOCALAPPDATA "Programs\NSIS\makensis.exe"),
            "${env:ProgramFiles(x86)}\NSIS\makensis.exe",
            "$env:ProgramFiles\NSIS\makensis.exe"
        ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    }
    if (-not $MakeNsis) { throw "NSIS 3 is required: winget install --id NSIS.NSIS --exact" }
}

if (-not $WorkDirectory) { $WorkDirectory = Join-Path $packagingDirectory "build" }
$WorkDirectory = [IO.Path]::GetFullPath($WorkDirectory)
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $WorkDirectory, $OutputDirectory | Out-Null
$releaseName = "$installerName-$Version-win-x64"
# A short staging folder keeps deep companion paths (PyInstaller's _internal tree) under MAX_PATH for makensis.
$stage = Join-Path $WorkDirectory "stage"
if (Test-Path -LiteralPath $stage) {
    if (-not $stage.StartsWith($WorkDirectory + [IO.Path]::DirectorySeparatorChar)) { throw "Refusing to replace $stage" }
    Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Path $stage | Out-Null
$icon = Join-Path $packagingDirectory "..\artwork\rtsai.ico"
$icon = (Resolve-Path -LiteralPath $icon).Path

Write-Host "== Engine assemblies (self-contained win-x64)"
Invoke-Native dotnet @("publish", "-c", "Release", "-p:TargetPlatform=win-x64", "-p:CopyGenericLauncher=False",
    "-p:CopyCncDll=$($config['PACKAGING_COPY_CNC_DLL'])", "-p:CopyD2kDll=$($config['PACKAGING_COPY_D2K_DLL'])",
    "-r", "win-x64", "-p:PublishDir=$stage\", "--self-contained", "true", "--nologo", "-v", "q", "-m:1") "Engine publish failed" $engine

Write-Host "== Engine data"
$engineFiles = @("VERSION", "AUTHORS", "COPYING", "IP2LOCATION-LITE-DB1.IPV6.BIN.ZIP")
# The MIX filename database only serves Westwood archives, which the standalone game never mounts.
if (-not $standalone) { $engineFiles += "global mix database.dat" }
foreach ($file in $engineFiles) {
    Copy-Item -LiteralPath (Join-Path $engine $file) -Destination $stage
}
Copy-Item -LiteralPath (Join-Path $engine "glsl") -Destination $stage -Recurse
New-Item -ItemType Directory -Path (Join-Path $stage "mods") | Out-Null
Copy-Item -LiteralPath (Join-Path $engine "mods\common") -Destination (Join-Path $stage "mods") -Recurse
# mods/common-content is the content installer's chrome; the standalone game has no content installer.
$engineExtras = if ($standalone) { @() } else { @($config["PACKAGING_COPY_ENGINE_FILES"] -split '\s+' | Where-Object { $_ }) }
foreach ($extra in $engineExtras) {
    $relative = $extra -replace '^\./', '' -replace '/', '\'
    $target = Join-Path $stage $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath (Join-Path $engine $relative) -Destination $target -Recurse
}

Write-Host "== Mod assemblies and content"
Invoke-Native dotnet @("publish", (Join-Path $root "RTSAI.sln"), "-c", "Release", "-p:TargetPlatform=win-x64", "-r", "win-x64",
    "-p:PublishDir=$stage\", "--self-contained", "true", "--nologo", "-v", "q") "Mod publish failed" $root
$mods = @(Get-ChildItem -LiteralPath (Join-Path $root "mods") -Directory)
# Standalone: the game only. The classic add-on and its content installer need the player's own RA2 files.
if ($standalone) { $mods = @($mods | Where-Object { $_.Name -eq $modId }) }
if ($mods.Count -eq 0) { throw "No mods\$modId to package." }
foreach ($mod in $mods) {
    Copy-Item -LiteralPath $mod.FullName -Destination (Join-Path $stage "mods") -Recurse
    $manifest = Join-Path $stage "mods\$($mod.Name)\mod.yaml"
    if (Test-Path -LiteralPath $manifest) {
        # The SDK's set_mod_version: the release tag replaces the development placeholder.
        $text = [IO.File]::ReadAllText($manifest).Replace("{DEV_VERSION}", $Version)
        [IO.File]::WriteAllText($manifest, $text)
    }
}
Set-Content -LiteralPath (Join-Path $stage "VERSION") -Value $config["ENGINE_VERSION"] -Encoding ASCII

Write-Host "== $launcherName.exe launcher"
$launcherObj = Join-Path $engine "OpenRA.WindowsLauncher\obj"
if (Test-Path -LiteralPath $launcherObj) { Remove-Item -LiteralPath $launcherObj -Recurse -Force }
Invoke-Native dotnet @("publish", (Join-Path $engine "OpenRA.WindowsLauncher\OpenRA.WindowsLauncher.csproj"), "-c", "Release", "-r", "win-x64",
    "-p:LauncherName=$launcherName", "-p:TargetPlatform=win-x64", "-p:ModID=$modId", "-p:PublishDir=$stage\",
    "-p:FaqUrl=$($config['PACKAGING_FAQ_URL'])", "-p:InformationalVersion=$Version", "-p:DisplayName=$($config['PACKAGING_DISPLAY_NAME'])",
    "-p:LauncherIcon=$icon", "--self-contained", "true", "--nologo", "-v", "q") "Launcher publish failed" $root
Copy-Item -LiteralPath $icon -Destination (Join-Path $stage "rtsai.ico")
$launcher = Join-Path $stage "$launcherName.exe"
foreach ($edit in @(
    @("--set-icon", $icon),
    @("--set-file-version", $fileVersion),
    @("--set-product-version", $Version),
    @("--set-version-string", "ProductName", $config["PACKAGING_DISPLAY_NAME"]),
    @("--set-version-string", "CompanyName", $config["PACKAGING_AUTHORS"]),
    @("--set-version-string", "FileDescription", $config["PACKAGING_DISPLAY_NAME"]),
    @("--set-version-string", "LegalCopyright", $(if ($standalone) { "GPLv3. Built on OpenRA." } else { "GPLv3. Built on OpenRA. Red Alert 2 content is not included." }))
)) {
    Invoke-Native $RcEdit (@($launcher) + $edit) "rcedit failed on $launcherName.exe"
}

if ($CompanionDirectory) {
    Write-Host "== AI companion"
    Copy-Item -LiteralPath $CompanionDirectory -Destination (Join-Path $stage "companion") -Recurse
    foreach ($junk in @("ai\models", "ai\pack.json")) {
        $path = Join-Path $stage "companion\$junk"
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
    }
} else {
    # Without the companion the co-commander starts switched off (CompanionHost applies this once) instead of
    # reporting missing files. The installer rewrites this file with the same choice.
    Write-Host "== No AI companion: the co-commander starts off"
    Set-Content -LiteralPath (Join-Path $stage "rtsai-install.json") -Encoding ASCII `
        -Value "{`"ai_mode`": `"none`", `"version`": `"$Version`", `"stamp`": `"portable-$Version`"}"
}

Write-Host "== Signing"
$executables = @(Get-ChildItem -LiteralPath $stage -Recurse -File -Filter *.exe | Select-Object -ExpandProperty FullName)
$signing = & (Join-Path $packagingDirectory "sign-windows.ps1") -Paths $executables -RequireSignatures:$RequireSignatures
Write-Host "Executables: $($executables.Count), signing: $signing"

Write-Host "== Portable zip"
$portable = Join-Path $OutputDirectory "$releaseName-portable.zip"
if (Test-Path -LiteralPath $portable) { Remove-Item -LiteralPath $portable }
# Entries are written one by one so names use "/" (Windows PowerShell's ZipFile writes "\") and the
# top folder carries the release name rather than the short staging name.
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::Open($portable, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in Get-ChildItem -LiteralPath $stage -Recurse -File) {
        $entry = "$releaseName/" + $file.FullName.Substring($stage.Length + 1).Replace("\", "/")
        [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $entry, [IO.Compression.CompressionLevel]::Optimal)
    }
} finally {
    $archive.Dispose()
}

$artifacts = @($portable)
if (-not $SkipInstaller) {
    Write-Host "== Installer"
    $uninstallList = Join-Path $WorkDirectory "uninstall-files.nsh"
    $lines = foreach ($item in Get-ChildItem -LiteralPath $stage) {
        if ($item.PSIsContainer) { "  RMDir /r `"`$INSTDIR\$($item.Name)`"" } else { "  Delete `"`$INSTDIR\$($item.Name)`"" }
    }
    Set-Content -LiteralPath $uninstallList -Value $lines -Encoding UTF8
    $setup = Join-Path $OutputDirectory "$releaseName-setup.exe"
    $voicePackName = "RTSAI-VoicePack-$Version.zip"
    $nsisArguments = @("/V2", "/DVERSION=$Version", "/DVIVERSION=$fileVersion", "/DPAYLOAD=$stage", "/DOUTFILE=$setup",
        "/DICON=$icon", "/DLICENSE=$(Join-Path $root 'COPYING')", "/DVOICEPACK=$voicePackName", "/DUNINSTALLLIST=$uninstallList")
    if ($standalone) { $nsisArguments += "/DSTANDALONE" }
    if ($CompanionDirectory) { $nsisArguments += "/DCOMPANION" }
    if ($HostedAI) { $nsisArguments += "/DHOSTEDAI" }
    if ($signing -ne "unsigned") {
        $signer = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $packagingDirectory 'sign-windows.ps1')`" -RequireSignatures -Paths"
        $nsisArguments += "/DUNINSTALLSIGNER=$signer"
    }
    $nsisArguments += (Join-Path $packagingDirectory "rtsai-installer.nsi")
    Invoke-Native $MakeNsis $nsisArguments "makensis failed"
    $installerSigning = & (Join-Path $packagingDirectory "sign-windows.ps1") -Paths @($setup) -RequireSignatures:$RequireSignatures -Description "RTS AI setup"
    Write-Host "Installer signing: $installerSigning"
    $artifacts += $setup
}

if ($VoicePack) {
    $voiceTarget = Join-Path $OutputDirectory "RTSAI-VoicePack-$Version.zip"
    if ((Resolve-Path -LiteralPath $VoicePack).Path -ne $voiceTarget) { Copy-Item -LiteralPath $VoicePack -Destination $voiceTarget -Force }
    $artifacts += $voiceTarget
}

$sums = foreach ($artifact in $artifacts) {
    $line = "$((Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant())  $([IO.Path]::GetFileName($artifact))"
    Set-Content -LiteralPath "$artifact.sha256" -Value $line -Encoding ASCII
    $line
}
Set-Content -LiteralPath (Join-Path $OutputDirectory "SHA256SUMS.txt") -Value $sums -Encoding ASCII

[pscustomobject]@{
    Version = $Version
    Stage = $stage
    Signing = $signing
    AI = $(if (-not $CompanionDirectory) { "none" } elseif ($HostedAI) { "local, hosted" } else { "local" })
    Artifacts = $artifacts | ForEach-Object { "{0} ({1:N0} bytes)" -f [IO.Path]::GetFileName($_), (Get-Item -LiteralPath $_).Length }
}
