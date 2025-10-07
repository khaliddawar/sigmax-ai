$transcriptText = Get-Content -Raw "scripts/short_transcript.txt"

$body = @{
    transcript_id = "short_test"
    transcript_text = $transcriptText
    metadata = @{
        title = "Short S&P Market Analysis"
        source = "test"
    }
} | ConvertTo-Json -Depth 5

$body | Out-File -FilePath "scripts/short_payload.json"

Write-Host "Sending short transcript to API..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/transcripts" -Method POST -Body $body -ContentType "application/json"
    Write-Host "Success! Transcript ID: $($response.transcript_id)"
    $response.transcript_id | Out-File -FilePath "scripts/current_id.txt"
} catch {
    Write-Host "Error: $_"
} 