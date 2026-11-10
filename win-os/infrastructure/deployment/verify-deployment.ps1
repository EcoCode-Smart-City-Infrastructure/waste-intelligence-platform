# WIN OS deployment verification - Windows/PowerShell edition.
# Same six checks as verify-deployment.sh.
# Usage: $env:WIN_API_URL="https://win.example.org"; $env:WIN_API_KEY_OPERATOR="..."; $env:WIN_API_KEY_VIEWER="..."; .erify-deployment.ps1
$Base = if ($env:WIN_API_URL) { $env:WIN_API_URL } else { "http://127.0.0.1:8080" }
$script:Pass = 0; $script:Fail = 0
function Check($name, $expected, $actual) {
    if ($expected -eq $actual) { Write-Host "PASS $name"; $script:Pass++ }
    else { Write-Host "FAIL $name (expected $expected, got $actual)"; $script:Fail++ }
}
function Code($url, $headers, $method = "GET", $body = $null) {
    try {
        $params = @{ Uri = $url; Method = $method; Headers = $headers; UseBasicParsing = $true }
        if ($body) { $params.Body = $body; $params.ContentType = "application/json" }
        return (Invoke-WebRequest @params).StatusCode
    } catch { return [int]$_.Exception.Response.StatusCode }
}
Check "health live" 200 (Code "$Base/health/live" @{})
Check "health ready" 200 (Code "$Base/health/ready" @{})
Check "unauthenticated is 401" 401 (Code "$Base/api/v1/assets" @{})
Check "viewer can read assets" 200 (Code "$Base/api/v1/assets" @{ "X-API-Key" = $env:WIN_API_KEY_VIEWER })
Check "viewer cannot write" 403 (Code "$Base/api/v1/assets" @{ "X-API-Key" = $env:WIN_API_KEY_VIEWER } "POST" '{"name":"verify"}')
try {
    $resp = Invoke-WebRequest -Uri "$Base/api/v1/assets" -Method POST -Headers @{ "X-API-Key" = $env:WIN_API_KEY_OPERATOR } -ContentType "application/json" -Body '{"name":"verify-deployment bin","data_status":"reported"}' -UseBasicParsing
    Check "operator creates asset" "ok" $(if ($resp.Content -match '"id"') { "ok" } else { "fail" })
} catch { Check "operator creates asset" "ok" "fail" }
Write-Host "verify-deployment: $script:Pass passed, $script:Fail failed"
if ($script:Fail -ne 0) { exit 1 }
