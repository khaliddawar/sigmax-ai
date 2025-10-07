# PowerShell script to process the real meeting transcript

# Read the transcript file
$transcriptText = Get-Content -Raw "real_meeting.txt"

# Create request body
$body = @{
    transcript_id = "real_meeting_test"
    transcript_text = $transcriptText
    metadata = @{
        title = "Macro Roadmap Trading Discussion"
        meeting_id = "macro-20250519"
        source = "manual"
    }
} | ConvertTo-Json -Depth 5

# Save the request body to a temporary file
$body | Out-File -FilePath "transcript_payload.json"

Write-Host "Created transcript payload file. Sending request..."

# Send the request
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/transcripts" -Method POST -Body $body -ContentType "application/json"
    Write-Host "Successfully processed transcript:"
    $response | ConvertTo-Json
    $transcriptId = $response.transcript_id
    Write-Host "Transcript ID: $transcriptId"
    
    # Save the transcript ID to use in subsequent requests
    $transcriptId | Out-File -FilePath "current_transcript_id.txt"
    Write-Host "Saved transcript ID to current_transcript_id.txt"
} catch {
    Write-Host "Error processing transcript: $_"
    Write-Host $_.Exception.Message
} 