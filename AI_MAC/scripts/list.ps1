param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Options)
& "$PSScriptRoot/run.ps1" sessions.list @Options
