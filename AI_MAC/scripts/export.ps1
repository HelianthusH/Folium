param([Parameter(Mandatory=$true)][string]$Dest,[string]$SessionId,[string]$Card,[long]$Since,[long]$Until)
$items=@("sessions.export","--dest",$Dest)
if($Card){$items+=@("--card",$Card)}
if($SessionId){$items+=@("--session-id",$SessionId)}
if($Since){$items+=@("--since",$Since)}
if($Until){$items+=@("--until",$Until)}
& "$PSScriptRoot/run.ps1" @items

