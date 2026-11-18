[CmdletBinding()]
param([int]$BackendPort=8000,[int]$FrontendPort=3000,[switch]$Stop)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$runtimeRoot=Join-Path $projectRoot 'storage\launcher'
$recordPath=Join-Path $runtimeRoot 'processes.private.json'
function Descendants([int]$parentId) {
  $found=@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$parentId")
  foreach($child in $found){Descendants $child.ProcessId;$child}
}
if($Stop){
  if(-not (Test-Path -LiteralPath $recordPath)){Write-Output 'No launcher-owned process record.';return}
  $record=Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
  if($record.root -ne $projectRoot){throw 'Foreign launcher record; nothing stopped.'}
  foreach($entry in $record.parents){
    $p=Get-CimInstance Win32_Process -Filter "ProcessId=$($entry.pid)"
    if($p -and $p.CreationDate.ToString('o') -eq $entry.created -and $p.CommandLine -eq $entry.command){
      $children=@(Descendants $p.ProcessId)
      # Capture actual creation identities before terminating any owned tree.
      $held=@($p)+@($children)
      foreach($owned in $held){
        $now=Get-CimInstance Win32_Process -Filter "ProcessId=$($owned.ProcessId)"
        if($now -and $now.CreationDate -eq $owned.CreationDate){Stop-Process -Id $now.ProcessId -ErrorAction SilentlyContinue}
      }
    }
  }
  Write-Output 'Stopped only processes matching this checkout launcher record.';return
}
foreach($port in @($BackendPort,$FrontendPort)){
  if(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue){throw "Port $port is occupied. No process was stopped. Use the owning terminal or this script's -Stop option first."}
}
$python=Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
if(-not (Test-Path -LiteralPath $python)){throw 'Run scripts\Setup-Windows.ps1 first.'}
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
$parents=@()
$backend=Start-Process -FilePath $python -ArgumentList @('-B','-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$BackendPort") -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeRoot 'backend.stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'backend.stderr.log') -PassThru
$p=Get-CimInstance Win32_Process -Filter "ProcessId=$($backend.Id)"
$parents+=@{pid=$p.ProcessId;created=$p.CreationDate.ToString('o');command=$p.CommandLine}
@{root=$projectRoot;parents=$parents;backend_port=$BackendPort;frontend_port=$FrontendPort} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $recordPath
$ready=$false
for($i=0;$i -lt 45;$i++){
  try{$health=Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec 2;if($health.status -eq 'ok'){$ready=$true;break}}catch{}
  if($backend.HasExited){break};Start-Sleep -Seconds 1
}
if(-not $ready){throw "Backend not ready; inspect $runtimeRoot\backend.stderr.log. Use -Stop for owned cleanup."}
$env:SMART_WARDROBE_BACKEND_URL="http://127.0.0.1:$BackendPort"
$next=Join-Path $projectRoot 'frontend\node_modules\next\dist\bin\next'
$frontend=Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @(('"'+$next+'"'),'dev','--webpack','--hostname','127.0.0.1','--port',"$FrontendPort") -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeRoot 'frontend.stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'frontend.stderr.log') -PassThru
$p=Get-CimInstance Win32_Process -Filter "ProcessId=$($frontend.Id)"
$parents+=@{pid=$p.ProcessId;created=$p.CreationDate.ToString('o');command=$p.CommandLine}
@{root=$projectRoot;parents=$parents;backend_port=$BackendPort;frontend_port=$FrontendPort} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $recordPath
$frontReady=$false
for($i=0;$i -lt 12;$i++){
  if($frontend.HasExited){break}
  try{$page=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort/auth" -TimeoutSec 15;if($page.StatusCode -eq 200){$frontReady=$true;break}}catch{}
  Start-Sleep -Seconds 1
}
if(-not $frontReady){throw "Frontend not ready; inspect $runtimeRoot\frontend.stderr.log. Use -Stop for owned cleanup."}
Write-Output "Both services ready. Open http://localhost:$FrontendPort (backend 127.0.0.1:$BackendPort). Logs: $runtimeRoot. Stop with .\scripts\Start-Windows.ps1 -Stop."
