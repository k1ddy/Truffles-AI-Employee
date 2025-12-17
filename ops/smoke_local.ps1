param(
  [string]$BaseUrl = "http://localhost:8000"
)

function Get-Health($url) {
  try {
    $r = Invoke-WebRequest -Method Get -Uri $url -UseBasicParsing
    return @{ ok=$true; status=$r.StatusCode; body=$r.Content }
  } catch {
    return @{ ok=$false; status=$null; body=$null; err=$_.Exception.Message }
  }
}

function Post-Json($url, $obj) {
  $json = $obj | ConvertTo-Json -Depth 30
  # Encode as UTF-8 bytes for proper Cyrillic support
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  try {
    $r = Invoke-WebRequest -Method Post -Uri $url -ContentType "application/json; charset=utf-8" -Body $bytes -UseBasicParsing
    return @{ ok=$true; status=$r.StatusCode; body=$r.Content }
  } catch {
    $status = $null
    try { $status = $_.Exception.Response.StatusCode.value__ } catch {}
    return @{ ok=$false; status=$status; body=$null; err=$_.Exception.Message }
  }
}

Write-Host "== HEALTH =="
$h = Get-Health "$BaseUrl/admin/health"
if (-not $h.ok) { $h = Get-Health "$BaseUrl/health" }
$h | Format-List

Write-Host "`n== WA /webhook =="
$wa = @{
  client_slug = "demo_salon"
  body = @{
    messageType = "text"
    message = "smoke test message"
    metadata = @{
      remoteJid = "77001234567@s.whatsapp.net"
      messageId = "SMOKE-ABC123"
      sender = "77001234567"
      timestamp = [int](Get-Date -UFormat %s)
    }
  }
}
(Post-Json "$BaseUrl/webhook" $wa) | Format-List

Write-Host "`n== TG /telegram-webhook (message) =="
$tgMsg = @{
  update_id = 123456789
  message = @{
    message_id = 100
    date = 1702468800
    chat = @{ id = -1003412216010; type = "supergroup"; title = "Truffles Support" }
    from = @{ id = 1969855532; is_bot = $false; first_name = "Zh" }
    text = "SMOKE TEST 5000"
    message_thread_id = 394
  }
}
(Post-Json "$BaseUrl/telegram-webhook" $tgMsg) | Format-List

Write-Host "`n== TG /telegram-webhook (callback) =="
$tgCb = @{
  update_id = 123456790
  callback_query = @{
    id = "callback123"
    from = @{ id = 1969855532; is_bot = $false; first_name = "Zh" }
    message = @{
      message_id = 388
      date = 1702468800
      chat = @{ id = -1003412216010; type = "supergroup" }
    }
    data = "take_39150bf7-50f8-4d29-857c-dbb177d643a5"
  }
}
(Post-Json "$BaseUrl/telegram-webhook" $tgCb) | Format-List
