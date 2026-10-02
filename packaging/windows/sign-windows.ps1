<#
.SYNOPSIS
Authenticode-sign RTS AI Windows executables when signing is configured; otherwise report "unsigned".

.DESCRIPTION
Two configurations are supported. Credentials are only ever read from the environment or the
Windows certificate store; nothing is written to disk except Azure's non-secret metadata file.

1. Azure Trusted Signing (recommended)
     AZURE_TRUSTED_SIGNING_ENDPOINT   e.g. https://eus.codesigning.azure.net/
     AZURE_TRUSTED_SIGNING_ACCOUNT    the Trusted Signing account name
     AZURE_TRUSTED_SIGNING_PROFILE    the certificate profile name
     AZURE_TRUSTED_SIGNING_DLIB       path to Azure.CodeSigning.Dlib.dll (NuGet: Microsoft.Trusted.Signing.Client, bin\x64)
   Authentication uses DefaultAzureCredential inside the dlib: either AZURE_TENANT_ID,
   AZURE_CLIENT_ID and AZURE_CLIENT_SECRET for a service principal with the
   "Trusted Signing Certificate Profile Signer" role, or an interactive `az login`.

2. A code-signing certificate with signtool
     WINDOWS_SIGNING_CERTIFICATE_THUMBPRINT   SHA-1 thumbprint of a certificate in Cert:\<store>\My
     WINDOWS_SIGNING_CERTIFICATE_STORE        CurrentUser (default) or LocalMachine
   or
     WINDOWS_SIGNING_PFX                      path to a .pfx file
     WINDOWS_SIGNING_PFX_PASSWORD             its password (environment only)

Optional for both:
     WINDOWS_SIGNTOOL_PATH           signtool.exe (default: PATH, then the newest Windows 10/11 SDK)
     WINDOWS_SIGNING_TIMESTAMP_URL   RFC 3161 timestamp server (default: Microsoft for Azure, DigiCert otherwise)
     RTSAI_REQUIRE_SIGNING=1         fail instead of producing unsigned artifacts

.OUTPUTS
"signed:<method>" or "unsigned".
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Paths,
    [switch]$RequireSignatures,
    [string]$Description = "RTS AI"
)

$ErrorActionPreference = "Stop"
$required = $RequireSignatures -or $env:RTSAI_REQUIRE_SIGNING -eq "1"

$files = @($Paths | Where-Object { $_ } | ForEach-Object {
    if (-not (Test-Path -LiteralPath $_ -PathType Leaf)) { throw "Signing input is missing: $_" }
    (Resolve-Path -LiteralPath $_).Path
})
if ($files.Count -eq 0) { return "unsigned" }

$azure = $env:AZURE_TRUSTED_SIGNING_ENDPOINT -and $env:AZURE_TRUSTED_SIGNING_ACCOUNT -and
    $env:AZURE_TRUSTED_SIGNING_PROFILE -and $env:AZURE_TRUSTED_SIGNING_DLIB
$thumbprint = ([string]$env:WINDOWS_SIGNING_CERTIFICATE_THUMBPRINT -replace '\s', '').ToUpperInvariant()
$pfx = $env:WINDOWS_SIGNING_PFX

if (-not $azure -and -not $thumbprint -and -not $pfx) {
    if ($required) {
        throw "Signing is required but not configured. Set the Azure Trusted Signing or certificate variables (see packaging/windows/sign-windows.ps1)."
    }
    Write-Warning "Code signing is not configured; $($files.Count) file(s) stay unsigned."
    return "unsigned"
}

function Resolve-SignTool {
    if ($env:WINDOWS_SIGNTOOL_PATH) {
        if (-not (Test-Path -LiteralPath $env:WINDOWS_SIGNTOOL_PATH -PathType Leaf)) { throw "WINDOWS_SIGNTOOL_PATH does not point to signtool.exe." }
        return (Resolve-Path -LiteralPath $env:WINDOWS_SIGNTOOL_PATH).Path
    }
    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $kits = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    $candidate = Get-ChildItem -Path (Join-Path $kits "*\x64\signtool.exe") -File -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($candidate) { return $candidate.FullName }
    throw "signtool.exe is required for signing. Install the Windows SDK (winget install Microsoft.WindowsSDK.10.0.26100) or set WINDOWS_SIGNTOOL_PATH."
}

$signTool = Resolve-SignTool
$arguments = @("sign", "/fd", "SHA256", "/td", "SHA256", "/d", $Description)
$metadata = $null
if ($azure) {
    if (-not (Test-Path -LiteralPath $env:AZURE_TRUSTED_SIGNING_DLIB -PathType Leaf)) { throw "AZURE_TRUSTED_SIGNING_DLIB does not point to Azure.CodeSigning.Dlib.dll." }
    $metadata = Join-Path ([IO.Path]::GetTempPath()) ("rtsai-trusted-signing-" + [guid]::NewGuid().ToString("N") + ".json")
    [ordered]@{
        Endpoint = $env:AZURE_TRUSTED_SIGNING_ENDPOINT
        CodeSigningAccountName = $env:AZURE_TRUSTED_SIGNING_ACCOUNT
        CertificateProfileName = $env:AZURE_TRUSTED_SIGNING_PROFILE
    } | ConvertTo-Json | Set-Content -LiteralPath $metadata -Encoding UTF8
    $timestamp = if ($env:WINDOWS_SIGNING_TIMESTAMP_URL) { $env:WINDOWS_SIGNING_TIMESTAMP_URL } else { "http://timestamp.acs.microsoft.com" }
    $arguments += @("/tr", $timestamp, "/dlib", $env:AZURE_TRUSTED_SIGNING_DLIB, "/dmdf", $metadata)
    $method = "azure-trusted-signing"
} elseif ($thumbprint) {
    if ($thumbprint -notmatch '^[A-F0-9]{40}$') { throw "WINDOWS_SIGNING_CERTIFICATE_THUMBPRINT must be a 40-character SHA-1 thumbprint." }
    $store = if ($env:WINDOWS_SIGNING_CERTIFICATE_STORE) { $env:WINDOWS_SIGNING_CERTIFICATE_STORE } else { "CurrentUser" }
    if ($store -notin @("CurrentUser", "LocalMachine")) { throw "WINDOWS_SIGNING_CERTIFICATE_STORE must be CurrentUser or LocalMachine." }
    $certificate = Get-Item -LiteralPath "Cert:\$store\My\$thumbprint" -ErrorAction SilentlyContinue
    if (-not $certificate -or -not $certificate.HasPrivateKey) { throw "The signing certificate is not in Cert:\$store\My or has no private key." }
    $timestamp = if ($env:WINDOWS_SIGNING_TIMESTAMP_URL) { $env:WINDOWS_SIGNING_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }
    $arguments += @("/tr", $timestamp, "/sha1", $thumbprint)
    if ($store -eq "LocalMachine") { $arguments += "/sm" }
    $method = "certificate-store"
} else {
    if (-not (Test-Path -LiteralPath $pfx -PathType Leaf)) { throw "WINDOWS_SIGNING_PFX does not point to a .pfx file." }
    $timestamp = if ($env:WINDOWS_SIGNING_TIMESTAMP_URL) { $env:WINDOWS_SIGNING_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }
    $arguments += @("/tr", $timestamp, "/f", $pfx)
    if ($env:WINDOWS_SIGNING_PFX_PASSWORD) { $arguments += @("/p", $env:WINDOWS_SIGNING_PFX_PASSWORD) }
    $method = "pfx"
}

try {
    # Batches keep the command line short; signtool signs every file it is given.
    for ($index = 0; $index -lt $files.Count; $index += 20) {
        $batch = $files[$index..([Math]::Min($index + 19, $files.Count - 1))]
        $previous = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $signTool @arguments @batch 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -notmatch '/p ' } | Out-Host
        $code = $LASTEXITCODE
        $ErrorActionPreference = $previous
        if ($code -ne 0) { throw "signtool failed (exit $code)." }
    }
    foreach ($file in $files) {
        $signature = Get-AuthenticodeSignature -LiteralPath $file
        if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid -or -not $signature.TimeStamperCertificate) {
            throw "Signature verification failed for ${file}: $($signature.Status) $($signature.StatusMessage)"
        }
    }
} finally {
    if ($metadata) { Remove-Item -LiteralPath $metadata -Force -ErrorAction SilentlyContinue }
}

return "signed:$method"
