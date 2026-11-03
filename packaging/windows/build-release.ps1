<#
.SYNOPSIS
Build the RTS AI Windows release on a Windows host: portable zip, per-user NSIS installer and checksums.

.DESCRIPTION
A Windows-native port of the Mod SDK's packaging/windows/buildpackage.sh (which needs Linux,
wine64 and ImageMagick). It publishes the pinned engine and the mod self-contained for win-x64,
builds the RTSAI.exe launcher with the RTS AI icon, stamps version resources with rcedit, adds
the frozen AI companion when -CompanionDirectory is given (companion\, from this repository's companion/
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

PACKAGING_STANDALONE="True" in mod.config (the rtsai/standalone game) ships only the mods named in
PACKAGING_STANDALONE_MODS (the desktop Library, its three games and Classic's content installer; never the owned-RA2
add-ons) and leaves out every Red Alert 2 reference in the installer and version info. The engine's content installer
chrome and MIX filename database ship only when a shipped mod uses them (Classic downloads the freeware Red Alert
content on first start). RTSAI.exe opens PACKAGING_LAUNCHER_MOD_ID (the Library).

The engine is the canonical sibling checkout ..\OpenRA (or -EngineSource), like tools/build-desktop-recovery.ps1:
both repositories are fast-forwarded to their owner main and must be clean, so the release is built from committed
main only. BUILD-INPUTS.json in the output records the mod and engine commits, and the companion's from its SOURCE.json.

Requirements: .NET 10 SDK, NSIS 3 (winget install NSIS.NSIS), rcedit-x64.exe
(https://github.com/electron/rcedit/releases) and tar.exe (built into Windows 10/11).

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
    [string]$EngineSource,
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
$launcherMod = if ($config["PACKAGING_LAUNCHER_MOD_ID"]) { $config["PACKAGING_LAUNCHER_MOD_ID"] } else { $modId }
$engine = if ($EngineSource) { $EngineSource } else { Join-Path (Split-Path $root -Parent) "OpenRA" }
$engine = [IO.Path]::GetFullPath($engine)
$installerName = $config["PACKAGING_INSTALLER_NAME"]
$standalone = $config["PACKAGING_STANDALONE"] -eq "True"
if (-not (Test-Path -LiteralPath (Join-Path $engine "OpenRA.Game\OpenRA.Game.csproj"))) {
    throw "No engine checkout in $engine (the canonical OpenRA checkout, or pass -EngineSource)."
}

# Committed main only, as tools/build-desktop-recovery.ps1 builds the local desktop.
Invoke-Native git @("-C", $root, "fetch", "origin", "main") "git fetch failed in $root"
Invoke-Native git @("-C", $root, "merge", "--ff-only", "origin/main") "$root cannot fast-forward to origin/main"
Invoke-Native git @("-C", $engine, "fetch", "fork", "main") "git fetch failed in $engine"
Invoke-Native git @("-C", $engine, "merge", "--ff-only", "fork/main") "$engine cannot fast-forward to fork/main"
foreach ($repository in @($root, $engine)) {
    if (& git -C $repository status --porcelain) { throw "Commit source changes before building: $repository" }
}
$engineCommit = (& git -C $engine rev-parse HEAD).Trim()

# Both games should ship the same units: RTSAI-WebGame tools/gameplay-check.mjs compares a web bundle with the desktop
# game this mod commit builds and leaves a receipt. Warn-only for now (owner, 23 Oct 2026); it becomes a refusal later.
$modCommit = (& git -C $root rev-parse HEAD).Trim()
$receipts = "D:/Builds/RTSAI/play-release/gameplay-check/receipts"
$compared = @(if (Test-Path -LiteralPath $receipts) {
    Get-ChildItem -LiteralPath $receipts -Filter *.json | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json } |
        Where-Object { $_.mod -eq $modCommit }
})
if (-not $compared) {
    Write-Warning "Mod $($modCommit.Substring(0,7)) has not been compared with the web game. Run node tools/gameplay-check.mjs --pack <live public web-bundle.pack> in RTSAI-WebGame."
} elseif (-not ($compared | Where-Object { $_.passed })) {
    Write-Warning "The web game and the desktop game this commit builds disagree (gameplay check failed); see $receipts."
}

if ($Version -notmatch '^(\d+)\.(\d+)\.(\d+)(?:-[a-z]+\.?(\d+))?$') { throw "Version must look like 0.2.0-alpha.1" }
$fileVersion = "$($Matches[1]).$($Matches[2]).$($Matches[3]).$(if ($Matches[4]) { $Matches[4] } else { 0 })"

if ($CompanionDirectory) {
    $CompanionDirectory = (Resolve-Path -LiteralPath $CompanionDirectory).Path
    if (-not (Test-Path -LiteralPath (Join-Path $CompanionDirectory "rtsai-companion.exe"))) {
        throw "No rtsai-companion.exe in $CompanionDirectory (build it with companion/scripts/package-rtsai-companion.ps1)."
    }
    # GPL: the release names the public source of everything it ships, the companion included.
    $companionSourceFile = Join-Path $CompanionDirectory "SOURCE.json"
    if (-not (Test-Path -LiteralPath $companionSourceFile)) {
        throw "The companion has no SOURCE.json: package it again with companion/scripts/package-rtsai-companion.ps1, which records its commit."
    }
    $companionSource = Get-Content -LiteralPath $companionSourceFile -Raw | ConvertFrom-Json
    $companionCommit = "$($companionSource.commit)"
    if ($companionCommit -notmatch '^[0-9a-f]{40}$') { throw "$companionSourceFile names no commit." }
    if ($companionSource.dirty) { throw "The companion was packaged from uncommitted changes: commit them and package it again." }
    Invoke-Native git @("-C", $root, "merge-base", "--is-ancestor", $companionCommit, "origin/main") `
        "The companion's commit $($companionCommit.Substring(0, 7)) is not on origin/main, so its source is not public: push it and package it again"
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
$engineAssemblies = @{}
foreach ($assembly in @("OpenRA.Game.dll", "OpenRA.Mods.Common.dll", "OpenRA.Mods.Cnc.dll")) {
    $engineAssemblies[$assembly] = (Get-FileHash -LiteralPath (Join-Path $stage $assembly)).Hash
}

$mods = @(Get-ChildItem -LiteralPath (Join-Path $root "mods") -Directory)
if ($standalone) {
    # The desktop Library and its games, sharing authored content; never the owned-RA2 add-ons.
    $wanted = @($config["PACKAGING_STANDALONE_MODS"] -split '\s+' | Where-Object { $_ })
    if ($wanted.Count -eq 0) { $wanted = @($modId) }
    $missing = @($wanted | Where-Object { $_ -notin $mods.Name })
    if ($missing) { throw "PACKAGING_STANDALONE_MODS names mods that do not exist: $($missing -join ', ')" }
    $mods = @($mods | Where-Object { $_.Name -in $wanted })
}
if (-not ($mods.Name -contains $launcherMod)) { throw "No mods\$launcherMod to package." }
$manifests = @($mods | ForEach-Object { Get-Content -LiteralPath (Join-Path $_.FullName "mod.yaml") -Raw })
# Classic mounts the freeware Red Alert archives its content installer downloads on first start.
$contentInstaller = -not $standalone -or [bool]($manifests -match '(?m)^\s*ContentInstallerMod:')
$mixArchives = -not $standalone -or [bool]($manifests -match '(?m)^PackageFormats:.*\bMix\b')

Write-Host "== Engine data"
$engineFiles = @("AUTHORS", "COPYING", "IP2LOCATION-LITE-DB1.IPV6.BIN.ZIP")
# The MIX filename database only serves Westwood archives.
if ($mixArchives) { $engineFiles += "global mix database.dat" }
foreach ($file in $engineFiles) {
    Copy-Item -LiteralPath (Join-Path $engine $file) -Destination $stage
}
Copy-Item -LiteralPath (Join-Path $engine "glsl") -Destination $stage -Recurse
New-Item -ItemType Directory -Path (Join-Path $stage "mods") | Out-Null
Copy-Item -LiteralPath (Join-Path $engine "mods\common") -Destination (Join-Path $stage "mods") -Recurse
# mods/common-content is the content installer's chrome.
$engineExtras = if ($contentInstaller) { @($config["PACKAGING_COPY_ENGINE_FILES"] -split '\s+' | Where-Object { $_ }) } else { @() }
foreach ($extra in $engineExtras) {
    $relative = $extra -replace '^\./', '' -replace '/', '\'
    $target = Join-Path $stage $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath (Join-Path $engine $relative) -Destination $target -Recurse
}

Write-Host "== Mod assemblies and content"
# The mod projects alone: RTSAI.sln names the old ./engine projects, and publishing it overwrote the engine's
# assemblies with that copy's. The engine references are Private=False, so only the mod assemblies are added.
foreach ($project in @("OpenRA.Mods.RA2", "OpenRA.Mods.RTSAI")) {
    Invoke-Native dotnet @("publish", (Join-Path $root "$project\$project.csproj"), "-c", "Release", "-p:TargetPlatform=win-x64", "-r", "win-x64",
        "-p:EngineRootPath=$engine", "-p:PublishDir=$stage\", "--self-contained", "true", "--nologo", "-v", "q") "$project publish failed" $root
}
foreach ($assembly in $engineAssemblies.Keys) {
    if ((Get-FileHash -LiteralPath (Join-Path $stage $assembly)).Hash -ne $engineAssemblies[$assembly]) {
        throw "The mod publish replaced the engine's $assembly."
    }
}
foreach ($mod in $mods) {
    Copy-Item -LiteralPath $mod.FullName -Destination (Join-Path $stage "mods") -Recurse
    $manifest = Join-Path $stage "mods\$($mod.Name)\mod.yaml"
    if (Test-Path -LiteralPath $manifest) {
        # The SDK's set_mod_version: the release tag replaces the development placeholder.
        $text = [IO.File]::ReadAllText($manifest).Replace("{DEV_VERSION}", $Version)
        [IO.File]::WriteAllText($manifest, $text)
    }
}
Set-Content -LiteralPath (Join-Path $stage "VERSION") -Value $engineCommit -Encoding ASCII

Write-Host "== $launcherName.exe launcher"
$launcherObj = Join-Path $engine "OpenRA.WindowsLauncher\obj"
if (Test-Path -LiteralPath $launcherObj) { Remove-Item -LiteralPath $launcherObj -Recurse -Force }
Invoke-Native dotnet @("publish", (Join-Path $engine "OpenRA.WindowsLauncher\OpenRA.WindowsLauncher.csproj"), "-c", "Release", "-r", "win-x64",
    "-p:LauncherName=$launcherName", "-p:TargetPlatform=win-x64", "-p:ModID=$launcherMod", "-p:PublishDir=$stage\",
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
[ordered]@{
    version = $Version; modCommit = $modCommit; engineCommit = $engineCommit; launcherMod = $launcherMod
    mods = @($mods.Name); companion = [bool]$CompanionDirectory; companionCommit = $companionCommit; hostedAI = [bool]$HostedAI; signing = $signing
    artifacts = @($sums)
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutputDirectory "BUILD-INPUTS.json") -Encoding ASCII

[pscustomobject]@{
    Version = $Version
    Stage = $stage
    Signing = $signing
    AI = $(if (-not $CompanionDirectory) { "none" } elseif ($HostedAI) { "local, hosted" } else { "local" })
    Artifacts = $artifacts | ForEach-Object { "{0} ({1:N0} bytes)" -f [IO.Path]::GetFileName($_), (Get-Item -LiteralPath $_).Length }
}
