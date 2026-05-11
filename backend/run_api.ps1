$root = "C:\Users\user\Documents\Codex\2026-04-23-can-you-design-ui-ux"
$python = Join-Path $root ".venv\Scripts\python.exe"
$log = Join-Path $root "backend\run_api.log"

Set-Location $root
"[$(Get-Date -Format s)] Starting ClinicAI Sentinel API" | Out-File -FilePath $log -Encoding utf8 -Append
& $python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 2>&1 | Tee-Object -FilePath $log -Append
