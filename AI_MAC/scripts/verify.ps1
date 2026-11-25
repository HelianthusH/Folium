param([Parameter(Mandatory=$true)][string]$Dest)
& "$PSScriptRoot/run.ps1" verify --dest $Dest
