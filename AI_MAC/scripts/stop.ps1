param([string]$SessionId)
if($SessionId){ & "$PSScriptRoot/run.ps1" record.stop --session-id $SessionId } else { & "$PSScriptRoot/run.ps1" record.stop }

