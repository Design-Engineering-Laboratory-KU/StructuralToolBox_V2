#Requires -Version 5.1
<#
.SYNOPSIS
  Mac 学生向けインストーラ（tar.gz）を作成する。

.EXAMPLE
  .\student\build_student_mac.ps1
#>
$ErrorActionPreference = 'Stop'
$Py = Join-Path $PSScriptRoot 'build_student_mac.py'
& py -3 $Py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
