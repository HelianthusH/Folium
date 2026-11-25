param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$root=(Resolve-Path "$PSScriptRoot/..").Path
if(Test-Path "$root/release/VoiceCard/VoiceCard.exe"){ & "$root/release/VoiceCard/VoiceCard.exe" @Arguments }
elseif(Test-Path "$root/.venv/Scripts/python.exe"){ & "$root/.venv/Scripts/python.exe" "$root/voicecard.py" @Arguments }
else { throw "Run install.ps1 first or unpack the Windows package." }
exit $LASTEXITCODE

