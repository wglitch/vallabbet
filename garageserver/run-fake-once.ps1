$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
  if (!(Test-Path -LiteralPath ".\config.json")) {
    Copy-Item -LiteralPath ".\config.example.json" -Destination ".\config.json"
  }
  python .\fetch_valmyndigheten.py --once --config .\config.json
}
finally {
  Pop-Location
}
