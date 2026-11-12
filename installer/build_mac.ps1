#Requires -Version 5.1
<#
.SYNOPSIS
  Mac 用インストーラ（tar.gz）を作成する。

.EXAMPLE
  .\installer\build_mac.ps1
#>
$ErrorActionPreference = 'Stop'
$Py = Join-Path $PSScriptRoot 'build_mac.py'
# Child tools (dotnet, pip) print Japanese text; the default cp932 decoding
# in Python's reader threads fails on it.
$env:PYTHONUTF8 = '1'
& py -3 $Py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
