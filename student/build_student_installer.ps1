#Requires -Version 5.1
param(
    [string]$ZipPath,
    [string]$SourceDir
)

$ErrorActionPreference = 'Stop'
$StudentDir = $PSScriptRoot
$DistDir = Join-Path $StudentDir 'dist'
$StagingRoot = Join-Path $DistDir '_installer_staging'
$PayloadDir = Join-Path $StagingRoot 'Payload'
$IssFile = Join-Path $StudentDir 'StructuralToolbox.iss'
$BuildStamp = Get-Date -Format 'yyyyMMdd'

function Find-InnoSetupCompiler {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    return $null
}

function Prepare-PayloadFromZip {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "ZIP not found: $Path"
    }
    if (Test-Path -LiteralPath $StagingRoot) {
        Remove-Item -LiteralPath $StagingRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null
    Expand-Archive -LiteralPath $Path -DestinationPath $StagingRoot -Force
    $top = Get-ChildItem -LiteralPath $StagingRoot -Directory | Select-Object -First 1
    if (-not $top) {
        throw "ZIP is empty: $Path"
    }
    if ($top.FullName -ne $PayloadDir) {
        if (Test-Path -LiteralPath $PayloadDir) {
            Remove-Item -LiteralPath $PayloadDir -Recurse -Force
        }
        Move-Item -LiteralPath $top.FullName -Destination $PayloadDir
        # -Exclude は -Path に * が無いと無視され、Payload ごと消える
        Get-ChildItem -LiteralPath $StagingRoot -Force |
            Where-Object { $_.Name -ne 'Payload' } |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Test-PayloadLayout {
    param([string]$Dir)
    $required = @(
        (Join-Path $Dir 'Install_once.bat'),
        (Join-Path $Dir 'setup_runtime.py'),
        (Join-Path $Dir 'python-embed\python.exe'),
        (Join-Path $Dir 'grasshopper\StbGrasshopper.gha')
    )
    foreach ($item in $required) {
        if (-not (Test-Path -LiteralPath $item)) {
            throw "Invalid payload (missing): $item"
        }
    }
    $wheels = Get-ChildItem -LiteralPath (Join-Path $Dir 'wheels') -Filter '*.whl' -ErrorAction SilentlyContinue
    if (-not $wheels) {
        throw "Invalid payload (no bundled libraries): $(Join-Path $Dir 'wheels')"
    }
    # The Start-menu guide shortcut needs this file, whose name is not ASCII.
    $guides = Get-ChildItem -LiteralPath $Dir -File -Filter '*.md' |
        Where-Object { $_.Name -notin @('README.md', 'report.md') }
    if (-not $guides) {
        throw "Invalid payload (student guides are missing): $Dir"
    }
}

if ($SourceDir) {
    $PayloadDir = (Resolve-Path -LiteralPath $SourceDir).Path
}
elseif ($ZipPath) {
    $ZipPath = (Resolve-Path -LiteralPath $ZipPath).Path
    Prepare-PayloadFromZip -Path $ZipPath
}
else {
    $zips = Get-ChildItem -LiteralPath $DistDir -Filter 'StructuralToolbox_Windows_*.zip' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    if (-not $zips) {
        throw "No ZIP found. Run student\build_student_zip.ps1 first, or pass -ZipPath."
    }
    $ZipPath = $zips[0].FullName
    Write-Host "Using ZIP: $ZipPath"
    Prepare-PayloadFromZip -Path $ZipPath
}

Test-PayloadLayout -Dir $PayloadDir

$Iscc = Find-InnoSetupCompiler
if (-not $Iscc) {
    throw "Inno Setup 6 not found. Install from https://jrsoftware.org/isdl.php"
}

New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

Write-Host ""
Write-Host "Building installer with Inno Setup..."
Write-Host "  Source: $PayloadDir"
Write-Host ""

& $Iscc "/DStbSourceDir=$PayloadDir" "/DStudentDist=$DistDir" "/DBuildStamp=$BuildStamp" $IssFile
if ($LASTEXITCODE -ne 0) {
    throw "ISCC failed with exit code $LASTEXITCODE"
}

$outFile = Join-Path $DistDir "StructuralToolbox_Setup_$BuildStamp.exe"
Write-Host ""
Write-Host "Done: $outFile"
if (Test-Path -LiteralPath $outFile) {
    $sizeMb = [math]::Round((Get-Item -LiteralPath $outFile).Length / 1MB, 1)
    Write-Host "Size: about ${sizeMb} MB"
}
