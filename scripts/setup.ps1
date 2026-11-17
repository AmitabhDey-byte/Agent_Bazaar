$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
function Invoke-Checked($Command, $Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
}
Invoke-Checked git @('submodule', 'update', '--init', '--recursive')
Invoke-Checked npm.cmd @('ci')
Invoke-Checked npm.cmd @('--prefix', 'web', 'ci')
Invoke-Checked uv @('sync', '--project', 'api', '--frozen')
Invoke-Checked npx.cmd @('playwright', 'install', 'chromium')
Invoke-Checked "$projectRoot/api/.venv/Scripts/python.exe" @('scripts/sync_public_env.py')
Write-Host 'Dependencies ready. Frontend: npm --prefix web run dev'
