[CmdletBinding()]
param(
  [ValidateSet('CPU','GPU')][string]$Mode='CPU',
  [string]$DataDir='', [string]$PythonExe='',
  [int]$BackendPort=8000,
  [switch]$WithTests,[switch]$DownloadModels,[switch]$PasswordFromStdin
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
if(-not $DataDir){$DataDir=Join-Path $projectRoot 'storage\portable-development'}
$DataDir=[IO.Path]::GetFullPath($DataDir)
# Inspect runtimes before creating data or changing configuration.
$node=Get-Command node.exe -ErrorAction Stop
$nodeVersion=(& $node.Source -p 'process.versions.node') | Select-Object -Last 1
if([version]$nodeVersion -lt [version]'20.9.0'){throw 'Install Node.js 24 LTS (tested 24.19.0), or Node >=20.9.0 first.'}
if(-not $PythonExe){$PythonExe=(Get-Command py.exe -ErrorAction Stop).Source;$pythonPrefix=@('-3.12')}else{$pythonPrefix=@()}
& $PythonExe @pythonPrefix -c 'import sys; sys.exit(sys.version_info[:2] != (3,12))'
if($LASTEXITCODE -ne 0){throw 'Python 3.12 is required (tested 3.12.10).'}
$python=Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
if(-not (Test-Path -LiteralPath $python)){
  & $PythonExe @pythonPrefix -m venv (Join-Path $projectRoot 'backend\.venv')
  if($LASTEXITCODE -ne 0){throw 'Python virtual environment creation failed.'}
}
$requirements=if($Mode -eq 'GPU'){'requirements.txt'}elseif($WithTests){'requirements-test-cpu.txt'}else{'requirements-cpu.txt'}
& $python -m pip --disable-pip-version-check install --no-input -r (Join-Path $projectRoot "backend\$requirements")
if($LASTEXITCODE -ne 0){throw 'Dependency installation failed; no database has been installed.'}
& npm.cmd --prefix (Join-Path $projectRoot 'frontend') ci --no-audit --no-fund
if($LASTEXITCODE -ne 0){throw 'npm ci failed; no database has been installed.'}
# Config is generated before proof reconstruction, which uses these grammar selectors.
& $python (Join-Path $projectRoot 'backend\scripts\configure_portable_development.py') --storage $DataDir --mode $Mode --backend-port $BackendPort
if($LASTEXITCODE -ne 0){throw 'Configuration preparation failed.'}
$installerArgs=@((Join-Path $projectRoot 'backend\scripts\install_portable_development.py'),'--storage',$DataDir)
if($PasswordFromStdin){$installerArgs+='--password-stdin'}
Push-Location (Join-Path $projectRoot 'backend')
try {
  & $python @installerArgs
  if($LASTEXITCODE -ne 0){throw 'Portable installation failed. Existing wardrobes were not replaced.'}
  if($DownloadModels){
    if($Mode -ne 'GPU'){throw '-DownloadModels requires explicit -Mode GPU.'}
    & $python scripts/setup_vtoff.py
    if($LASTEXITCODE -ne 0){throw 'VTOFF/SigLIP asset download failed.'}
    & $python scripts/setup_vton.py
    if($LASTEXITCODE -ne 0){throw 'CatVTON asset download failed.'}
  }
} finally {Pop-Location}
Write-Output 'Setup complete. Start with .\scripts\Start-Windows.ps1. Use the account email in README.md and the NEW password you supplied.'
