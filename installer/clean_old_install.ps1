#Requires -Version 5.1
<#
Removes an earlier Structural Toolbox install before Setup copies the new one.

Run by StructuralToolbox.iss (PrepareToInstall). Everything in an old install is
deleted, the bundled Python and .venv included, except model and result files
the user added (.dat, .out, .gh, .ghx and .project.json sidecars that are not
part of a shipped payload). Those stay in -Dir; files found in an old install
elsewhere (-OldDir, or the folder recorded in -LocationFile) are moved into -Dir.
A folder is touched only when it looks like a Structural Toolbox install and is
not a git checkout. installer/mac/clean_old_install.sh applies the same rules.

Exit codes: 0 done (or nothing to do), 1 files could not be removed.
#>
param(
    [Parameter(Mandatory = $true)][string]$Dir,
    [string]$OldDir,
    [string]$LocationFile,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [string]$Log = (Join-Path $env:TEMP 'StructuralToolbox_clean.log')
)

$ErrorActionPreference = 'Stop'

$KeepExtensions = @('.dat', '.out', '.gh', '.ghx')
$KeepSuffixes = @('.project.json')
# Runtime folders are rebuilt by every install; libraries inside them ship
# their own .dat test files, so they are removed without looking inside.
$RuntimeFolders = @('.venv', 'python-embed', 'wheels')

function Write-Log([string]$Text) {
    $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $Text
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
}

function Normalize([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
    try {
        return [IO.Path]::GetFullPath($Path.Trim()).TrimEnd('\')
    } catch {
        return $null
    }
}

function Test-StbInstall([string]$Root) {
    if (-not $Root -or -not (Test-Path -LiteralPath $Root -PathType Container)) { return $false }
    if (Test-Path -LiteralPath (Join-Path $Root '.git')) { return $false }
    return (Test-Path -LiteralPath (Join-Path $Root 'Install_once.bat')) -and
           (Test-Path -LiteralPath (Join-Path $Root 'setup_runtime.py'))
}

function Read-Manifest([string]$Path, $Set) {
    if ($Path -and (Test-Path -LiteralPath $Path -PathType Leaf)) {
        foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
            $rel = $line.Trim()
            if ($rel) { [void]$Set.Add($rel.Replace('\', '/')) }
        }
    }
}

function Test-UserFile([string]$Rel, $Shipped) {
    $name = [IO.Path]::GetFileName($Rel).ToLowerInvariant()
    $isModel = ($KeepExtensions -contains [IO.Path]::GetExtension($name)) -or
               ($KeepSuffixes | Where-Object { $name.EndsWith($_) })
    if (-not $isModel) { return $false }
    if ($Rel -match '(^|/)__pycache__/') { return $false }
    # Inno Setup's own uninstall log (unins000.dat) sits in the install root.
    if ($Rel -match '^unins\d+\.dat$') { return $false }
    return -not $Shipped.Contains($Rel)
}

function Get-FreeTarget([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $Path }
    $dir = [IO.Path]::GetDirectoryName($Path)
    $stem = [IO.Path]::GetFileNameWithoutExtension($Path)
    $ext = [IO.Path]::GetExtension($Path)
    for ($i = 1; ; $i++) {
        $candidate = Join-Path $dir ("{0} (old {1}){2}" -f $stem, $i, $ext)
        if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
}

function Test-InUse([string]$Root) {
    $prefix = $Root + '\'
    foreach ($proc in Get-Process -ErrorAction SilentlyContinue) {
        try {
            if ($proc.Path -and $proc.Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                Write-Log ("in use by {0} (pid {1}): {2}" -f $proc.ProcessName, $proc.Id, $proc.Path)
                return $true
            }
        } catch { }
    }
    return $false
}

# Returns the number of files that could not be removed.
function Clear-Install([string]$Root, [string]$Target, $Shipped) {
    $failed = 0
    $kept = 0
    $moved = 0

    foreach ($folder in $RuntimeFolders) {
        $path = Join-Path $Root $folder
        if (Test-Path -LiteralPath $path) {
            try {
                Remove-Item -LiteralPath $path -Recurse -Force
            } catch {
                Write-Log ("could not remove {0}: {1}" -f $path, $_.Exception.Message)
                $failed++
            }
        }
    }

    $local = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    Read-Manifest (Join-Path $Root 'install_manifest.txt') $local
    $local.UnionWith($Shipped)

    foreach ($file in Get-ChildItem -LiteralPath $Root -Recurse -File -Force -ErrorAction SilentlyContinue) {
        $rel = $file.FullName.Substring($Root.Length + 1).Replace('\', '/')
        try {
            if (Test-UserFile $rel $local) {
                if ($Root -ieq $Target) {
                    $kept++
                    continue
                }
                $dest = Get-FreeTarget (Join-Path $Target ($rel.Replace('/', '\')))
                New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($dest)) | Out-Null
                Move-Item -LiteralPath $file.FullName -Destination $dest
                Write-Log ("moved {0} -> {1}" -f $file.FullName, $dest)
                $moved++
                continue
            }
            Remove-Item -LiteralPath $file.FullName -Force
        } catch {
            Write-Log ("could not remove {0}: {1}" -f $file.FullName, $_.Exception.Message)
            $failed++
        }
    }

    # Deepest folders first, then the install folder itself when nothing is left.
    $folders = @(Get-ChildItem -LiteralPath $Root -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Sort-Object { $_.FullName.Length } -Descending)
    foreach ($folder in $folders) {
        if (-not (Get-ChildItem -LiteralPath $folder.FullName -Force -ErrorAction SilentlyContinue)) {
            Remove-Item -LiteralPath $folder.FullName -Force -ErrorAction SilentlyContinue
        }
    }
    if ($Root -ine $Target -and -not (Get-ChildItem -LiteralPath $Root -Force -ErrorAction SilentlyContinue)) {
        Remove-Item -LiteralPath $Root -Force -ErrorAction SilentlyContinue
    }

    Write-Log ("cleaned {0}: kept {1}, moved {2}, failed {3}" -f $Root, $kept, $moved, $failed)
    return $failed
}

$target = Normalize $Dir
$shipped = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
Read-Manifest $Manifest $shipped

$roots = New-Object System.Collections.Generic.List[string]
$roots.Add($target)
$candidates = @($OldDir)
if ($LocationFile -and (Test-Path -LiteralPath $LocationFile -PathType Leaf)) {
    $candidates += (Get-Content -LiteralPath $LocationFile -Encoding UTF8 -TotalCount 1)
}
foreach ($candidate in $candidates) {
    $path = Normalize $candidate
    if ($path -and -not ($roots | Where-Object { $_ -ieq $path })) { $roots.Add($path) }
}

Write-Log ("new install: {0}" -f $target)
$installs = @($roots | Where-Object { Test-StbInstall $_ })
foreach ($root in $installs) {
    if (Test-InUse $root) {
        Write-Log "aborted: Structural Toolbox is running"
        exit 1
    }
}

$failed = 0
foreach ($root in $installs) {
    Write-Log ("old install found: {0}" -f $root)
    $failed += Clear-Install $root $target $shipped
}
if ($installs.Count -eq 0) {
    Write-Log 'no earlier install found'
}
if ($failed -gt 0) { exit 1 }
exit 0
