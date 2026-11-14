<#
.SYNOPSIS
  Batch DWG to DXF on QD, from a miner manifest. Works on COPIES. Never writes to Q:, S:, G:, H:, T: or the NAS.

.DESCRIPTION
  Reads manifest.csv (columns path, client, master_id; made by manifest_from_master_list.py), copies each DWG to a work
  folder, converts the copy to DXF, and logs the result. Re-run safely: files already converted are skipped.
  Tool autocad : AutoCAD Mechanical's console (accoreconsole /product ACM), the route ADR-0010 chose while the licence lasts.
  Tool libredwg: the LibreDWG dwg2dxf command line (GPL, run only as a separate program), the documented fallback.
  NOT YET TRIED ON QD. Run with -TestOne first and open the DXF before a bigger run.

.EXAMPLE
  .\dwg_to_dxf_batch.ps1 -Manifest C:\dr-staging\manifest.csv -TestOne
  .\dwg_to_dxf_batch.ps1 -Manifest C:\dr-staging\manifest.csv -Client AFJ -Limit 50
#>
param(
  [Parameter(Mandatory = $true)][string]$Manifest,
  [string]$OutDir = 'C:\dr-staging\dxf',
  [string]$Work = 'C:\dr-staging\dwg-copy',
  [ValidateSet('autocad', 'libredwg')][string]$Tool = 'autocad',
  [string]$Console = '',
  [string]$DwgToDxf = 'dwg2dxf.exe',
  [string]$Client = '',
  [int]$Limit = 0,
  [int]$TimeoutSec = 180,
  [switch]$TestOne,
  [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$protected = @('Q:\', 'S:\', 'G:\', 'H:\', 'T:\', '\\WHY4RSNAS', '\\WHY4RSNAS.local')
foreach ($p in @($OutDir, $Work)) {
  foreach ($r in $protected) {
    if ($p.StartsWith($r, [StringComparison]::OrdinalIgnoreCase)) { throw "Refusing: $p is under protected root $r. Output goes to C:\dr-staging only." }
  }
}
New-Item -ItemType Directory -Force -Path $OutDir, $Work | Out-Null
$log = Join-Path $OutDir 'convert-log.csv'
if (-not (Test-Path $log)) { 'master_id,source,out,status,seconds,bytes,error' | Out-File -Encoding utf8 $log }

if ($Tool -eq 'autocad' -and -not $Console) {
  $found = Get-ChildItem 'C:\Program Files\Autodesk' -Filter accoreconsole.exe -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match 'Mechanical' } | Sort-Object FullName -Descending | Select-Object -First 1
  if (-not $found) { throw 'accoreconsole.exe (AutoCAD Mechanical) not found. Pass -Console "<path>" or use -Tool libredwg.' }
  $Console = $found.FullName
}

$rows = Import-Csv -LiteralPath $Manifest | Where-Object { $_.path -match '\.dwg$' }
if ($Client) { $rows = $rows | Where-Object { $_.client -eq $Client } }
if ($TestOne) { $Limit = 1 }
if ($Limit -gt 0) { $rows = $rows | Select-Object -First $Limit }
Write-Host ("{0} drawing(s) to convert with {1}" -f @($rows).Count, $Tool)

function Add-Log($id, $src, $out, $status, $sec, $bytes, $err) {
  $line = '"{0}","{1}","{2}","{3}",{4},{5},"{6}"' -f $id, ($src -replace '"', "'"), ($out -replace '"', "'"), $status, $sec, $bytes, ($err -replace '"', "'")
  Add-Content -LiteralPath $log -Value $line -Encoding utf8
}

foreach ($r in $rows) {
  $id = if ($r.master_id) { $r.master_id } else { 'NA' }
  $safe = ([IO.Path]::GetFileNameWithoutExtension($r.path) -replace '[^A-Za-z0-9._ -]', '_')
  $out = Join-Path $OutDir ("{0}_{1}.dxf" -f $id, $safe)
  if ((Test-Path -LiteralPath $out) -and ((Get-Item -LiteralPath $out).Length -gt 0)) { continue }
  if (-not (Test-Path -LiteralPath $r.path)) { Add-Log $id $r.path $out 'missing' 0 0 'source not found'; continue }
  if ($WhatIf) { Write-Host "would convert $($r.path) -> $out"; continue }
  $copy = Join-Path $Work ("{0}_{1}.dwg" -f $id, $safe)
  $t0 = Get-Date
  try {
    Copy-Item -LiteralPath $r.path -Destination $copy -Force          # the original is only ever read
    if ($Tool -eq 'autocad') {
      $scr = Join-Path $Work ("{0}.scr" -f $id)
      # FILEDIA/CMDDIA 0 so commands take typed answers. DXFOUT: file name, V for version, 2018, Enter to accept the default accuracy.
      $lines = @('FILEDIA', '0', 'CMDDIA', '0', '_.DXFOUT', ('"' + $out + '"'), 'V', '2018', '', '_.QUIT', 'Y')
      Set-Content -LiteralPath $scr -Value $lines -Encoding ascii
      $argList = @('/product', 'ACM', '/i', ('"' + $copy + '"'), '/s', ('"' + $scr + '"'), '/l', 'en-US')
      $p = Start-Process -FilePath $Console -ArgumentList $argList -PassThru -WindowStyle Hidden
      if (-not $p.WaitForExit($TimeoutSec * 1000)) { $p.Kill(); throw "timed out after $TimeoutSec s" }
    } else {
      & $DwgToDxf -y -o $out $copy 2>&1 | Out-Null
    }
    $sec = [int]((Get-Date) - $t0).TotalSeconds
    if ((Test-Path -LiteralPath $out) -and ((Get-Item -LiteralPath $out).Length -gt 0)) {
      Add-Log $id $r.path $out 'ok' $sec (Get-Item -LiteralPath $out).Length ''
    } else { Add-Log $id $r.path $out 'no-output' $sec 0 'tool ran but wrote no DXF' }
  } catch {
    Add-Log $id $r.path $out 'error' ([int]((Get-Date) - $t0).TotalSeconds) 0 $_.Exception.Message
  } finally {
    Remove-Item -LiteralPath $copy -Force -ErrorAction SilentlyContinue
    if ($scr) { Remove-Item -LiteralPath $scr -Force -ErrorAction SilentlyContinue }
  }
}
Write-Host "Done. Log: $log"
