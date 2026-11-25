param([ValidateSet("ima","pcm16")]$Codec="ima")
& "$PSScriptRoot/run.ps1" record.start --codec $Codec

