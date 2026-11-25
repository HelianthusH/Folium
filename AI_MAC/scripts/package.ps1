param([string]$Python="python")
$ErrorActionPreference="Stop"
$root=(Resolve-Path "$PSScriptRoot/..").Path
Push-Location $root
try {
 & $Python -m PyInstaller --noconfirm --onedir --name VoiceCard --distpath release --workpath .build/bundle --specpath .build --collect-all uiautomation --collect-all winpty --collect-all sherpa_onnx --collect-all sherpa_onnx_core --collect-submodules winrt --collect-submodules bleak.backends.winrt voicecard.py
 if($LASTEXITCODE){throw "Package failed"}
 Copy-Item config,models release/VoiceCard/ -Recurse -Force
} finally {Pop-Location}

