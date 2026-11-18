See README.md for the Windows handover and CPU/GPU requirements.

First setup: powershell -ExecutionPolicy Bypass -File .\scripts\Setup-Windows.ps1 -Mode CPU
Start: powershell -ExecutionPolicy Bypass -File .\scripts\Start-Windows.ps1
Stop owned services: powershell -ExecutionPolicy Bypass -File .\scripts\Start-Windows.ps1 -Stop
