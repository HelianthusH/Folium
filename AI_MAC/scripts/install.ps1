param([string]$Python="python",[string]$ModelArchive)
$ErrorActionPreference="Stop"
$root=(Resolve-Path "$PSScriptRoot/..").Path
& $Python -m venv "$root/.venv"
if($LASTEXITCODE){throw "Python 3.10 x64 required"}
$py="$root/.venv/Scripts/python.exe"
& $py -m pip install -r "$root/desktop/requirements.txt"
if($LASTEXITCODE){throw "Dependency installation failed"}
if($ModelArchive){ & $py "$root/scripts/model.py" $ModelArchive } else { & $py "$root/scripts/model.py" }
exit $LASTEXITCODE

