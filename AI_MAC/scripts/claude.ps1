$root=(Resolve-Path "$PSScriptRoot/..").Path
if(Test-Path "$root/release/VoiceCard/VoiceCard.exe"){ & conhost.exe "$root/release/VoiceCard/VoiceCard.exe" claude }
else { & conhost.exe "$root/.venv/Scripts/python.exe" "$root/voicecard.py" claude }

