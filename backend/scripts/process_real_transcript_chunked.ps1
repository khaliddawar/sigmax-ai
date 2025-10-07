# PowerShell script to process the real meeting transcript using a file-based approach
# This avoids issues with large string handling in PowerShell

# Step 1: Create a temp directory if it doesn't exist
$tempDir = "scripts/temp"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}

# Step 2: Read the transcript file as plain text
$transcriptContent = Get-Content -Raw -Path "real_meeting.txt"

# Step 3: Create the JSON payload directly as a string and escape it properly
# The here-string @"..."@ helps avoid many escaping issues
$jsonPayload = @"
{
    "transcript_id": "real_meeting_test",
    "transcript_text": $($transcriptContent | ConvertTo-Json),
    "metadata": {
        "title": "Macro Roadmap Trading Discussion",
        "meeting_id": "macro-20250519",
        "source": "manual"
    }
}
"@

# Step 4: Write the JSON to a temporary file
$jsonFilePath = "$tempDir/real_meeting_payload.json"
$jsonPayload | Out-File -FilePath $jsonFilePath -Encoding utf8

Write-Host "Created JSON payload at: $jsonFilePath"
Write-Host "File size: $((Get-Item $jsonFilePath).Length) bytes"
Write-Host "Sending request to API..."

# Step 5: Send the request using the file
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/transcripts" -Method POST -InFile $jsonFilePath -ContentType "application/json"
    
    Write-Host "Successfully processed transcript!" -ForegroundColor Green
    Write-Host "Transcript ID: $($response.transcript_id)" -ForegroundColor Green
    
    # Save the ID for later use
    $response.transcript_id | Out-File -FilePath "$tempDir/current_transcript_id.txt"
    Write-Host "Saved transcript ID to: $tempDir/current_transcript_id.txt"
} catch {
    Write-Host "Error processing transcript:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    # Try to get more details from the response if available
    if ($_.Exception.Response) {
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $reader.BaseStream.Position = 0
            $reader.DiscardBufferedData()
            $responseBody = $reader.ReadToEnd()
            Write-Host "Response body:" -ForegroundColor Red
            Write-Host $responseBody -ForegroundColor Red
        } catch {
            Write-Host "Could not read response body: $_" -ForegroundColor Red
        }
    }
}

Write-Host "Script execution completed." 