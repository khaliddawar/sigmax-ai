$transcript_text = Get-Content -Raw "scripts/market_analysis.txt"
$json = @"
{
  "transcript_id": "market_analysis",
  "transcript_text": "$transcript_text",
  "metadata": {
    "title": "Market Analysis Discussion"
  }
}
"@

$json | Out-File -Path "scripts/market_payload.json" -Encoding utf8

Write-Host "Created payload file. Now sending to API..."
Invoke-RestMethod -Uri "http://localhost:8001/api/transcripts" -Method POST -InFile "scripts/market_payload.json" -ContentType "application/json" 