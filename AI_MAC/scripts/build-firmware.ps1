param([string]$Python="python", [string]$GccRoot="", [switch]$Bootstrap,
      [string]$BuildRoot=(Join-Path $env:TEMP "VoiceCard-Zephyr42"))
$ErrorActionPreference="Stop"
$root=(Resolve-Path "$PSScriptRoot/..").Path
$BuildRoot=[IO.Path]::GetFullPath($BuildRoot)
if ($BuildRoot -match '[^\x20-\x7e]') { throw "Use -BuildRoot with a dedicated ASCII path." }
$ws=Join-Path $BuildRoot "ws"
$venv=Join-Path $BuildRoot "env"
$app=Join-Path $BuildRoot "app"
$out=Join-Path $BuildRoot "out"
New-Item -ItemType Directory -Force $app | Out-Null
Copy-Item "$root/firmware/*" $app -Recurse -Force
$env:PYTHONUTF8="1"
function Run([string]$exe,[string[]]$argv) {
  & $exe @argv
  if ($LASTEXITCODE -ne 0) { throw "$exe failed ($LASTEXITCODE)" }
}
if ($Bootstrap) {
  Run $Python @("-m","venv",$venv)
  $py="$venv/Scripts/python.exe"
  Run $py @("-m","pip","install","west==1.4.0","cmake==3.31.6","ninja==1.11.1.4")
}
$env:PATH="$venv/Scripts;$env:PATH"
$west="$venv/Scripts/west.exe"
if ($Bootstrap) {
  if (!(Test-Path "$ws/.west")) { Run $west @("init","--mr","v4.2.0","--mf","west.yml",$ws) }
}
Push-Location $ws
try {
  if ($Bootstrap) {
    Run $west @("update","--narrow","--fetch-opt=--depth=1","hal_nordic","cmsis","cmsis_6","fatfs","mbedtls","segger")
    Run "$venv/Scripts/python.exe" @("-m","pip","install","-r","zephyr/scripts/requirements-base.txt")
  }
  if (!$GccRoot) { $GccRoot=(Get-Item (Get-Command arm-none-eabi-gcc).Source).Directory.Parent.FullName }
  $env:ZEPHYR_TOOLCHAIN_VARIANT="gnuarmemb"
  $env:GNUARMEMB_TOOLCHAIN_PATH=$GccRoot
  $env:ZEPHYR_BASE="$ws/zephyr"
  $cmake="$venv/Lib/site-packages/cmake/data/bin/cmake.exe"
  $py="$venv/Scripts/python.exe"
  Run $cmake @("-S",$app,"-B",$out,"-GNinja","-DBOARD=xiao_ble/nrf52840/sense","-DPython3_EXECUTABLE=$py","-DWEST_PYTHON=$py")
  Run $cmake @("--build",$out,"--parallel","8")
  New-Item -ItemType Directory -Force "$root/release" | Out-Null
  Copy-Item "$out/zephyr/zephyr.uf2" "$root/release/voicecard.uf2"
} finally { Pop-Location }

