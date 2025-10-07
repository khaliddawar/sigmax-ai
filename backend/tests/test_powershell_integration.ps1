# Complete YouTube Extension Integration Test - PowerShell Version
# Tests the full workflow: transcript ingestion -> processing -> RAG chat

Write-Host "Starting Complete YouTube Extension Integration Test" -ForegroundColor Green
Write-Host "================================================================================"

# Configuration
$BASE_URL = "http://localhost:8000"
$TEST_VIDEO_ID = "dQw4w9WgXcQ"
$TEST_USER_ID = "extension_test_user"

# Financial market transcript for testing
$FINANCIAL_TRANSCRIPT = @"
Good morning everyone and welcome to today's market analysis session. 

The Federal Reserve announced yesterday that they are maintaining the current interest rates at 5.25-5.5%, which has had a significant impact on market sentiment. The S&P 500 opened higher this morning, gaining approximately 1.2% in pre-market trading.

Let me discuss the key sectors showing strength today. Technology stocks are leading the rally, with NVIDIA up 3.4% and Microsoft gaining 2.1%. The semiconductor sector is particularly strong due to positive earnings guidance from several major players.

In the energy sector, we're seeing mixed signals. Crude oil prices have declined by 2.3% following the EIA inventory report showing higher than expected builds. This is putting pressure on energy names like ExxonMobil and Chevron, both down approximately 1.5%.

Looking at the options market, we're seeing increased call activity in the QQQ, suggesting bullish sentiment for tech stocks. The put-call ratio has dropped to 0.85, indicating more bullish positioning.

From a technical analysis perspective, the S&P 500 has broken above the 4,200 resistance level, which could signal a move towards 4,300 if volume continues to support this breakout.

Key economic data to watch this week includes the CPI inflation report on Wednesday and the retail sales data on Friday. These will be crucial for understanding the Fed's next policy moves.

In conclusion, while we're seeing short-term bullish momentum, investors should remain cautious about the upcoming economic data releases and their potential impact on monetary policy.
"@

# Step 1: Health Check
Write-Host "Testing Health Endpoint..." -ForegroundColor Cyan

try {
    $healthResponse = Invoke-RestMethod -Uri "$BASE_URL/api/health" -Method Get -TimeoutSec 30
    Write-Host "Health check successful!" -ForegroundColor Green
    Write-Host "Redis Connected: $($healthResponse.redis_connected)" -ForegroundColor Yellow
    Write-Host "Postmark Configured: $($healthResponse.postmark_configured)" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 2: YouTube Ingestion
Write-Host "Testing YouTube Transcript Ingestion..." -ForegroundColor Cyan

$testData = @{
    video_id = $TEST_VIDEO_ID
    title = "Market Analysis: Fed Rates & Tech Rally"
    channel_name = "Financial News Network"
    duration = 480
    transcript = $FINANCIAL_TRANSCRIPT
    source = "chrome_extension"
    user_id = $TEST_USER_ID
    metadata = @{
        source = "chrome_extension"
        extraction_method = "youtube_captions_api"
    }
} | ConvertTo-Json -Depth 3

$headers = @{
    "Content-Type" = "application/json"
    "Idempotency-Key" = "extension_test_$($TEST_VIDEO_ID)_$(Get-Date -UFormat %s)"
}

try {
    Write-Host "Sending transcript for processing..." -ForegroundColor Yellow
    $ingestionResponse = Invoke-RestMethod -Uri "$BASE_URL/api/yt_test_ingest" -Method Post -Body $testData -Headers $headers -TimeoutSec 120
    
    Write-Host "YouTube ingestion successful!" -ForegroundColor Green
    Write-Host "Job ID: $($ingestionResponse.job_id)" -ForegroundColor Yellow
    Write-Host "Video ID: $($ingestionResponse.video_id)" -ForegroundColor Yellow
    Write-Host "Estimated Tokens: $($ingestionResponse.estimated_tokens)" -ForegroundColor Yellow
    Write-Host "Message: $($ingestionResponse.message.Substring(0, [Math]::Min(100, $ingestionResponse.message.Length)))..." -ForegroundColor Yellow
    
    # Extract transcript ID from message
    $transcript_id = $null
    if ($ingestionResponse.message -match "Transcript ID: ([^\s\.]+)") {
        $transcript_id = $matches[1]
        Write-Host "Generated Transcript ID: $transcript_id" -ForegroundColor Green
    }
    
    Write-Host ""
    
} catch {
    Write-Host "YouTube ingestion failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 3: RAG Chat Testing
if ($transcript_id) {
    Write-Host "Testing RAG Chat Interface..." -ForegroundColor Cyan
    Write-Host "Using transcript ID: $transcript_id" -ForegroundColor Yellow
    Write-Host ""
    
    # Test questions
    $testQuestions = @(
        "What did the Federal Reserve announce about interest rates?",
        "Which technology stocks were mentioned and how did they perform?", 
        "What were the key economic data points to watch this week?",
        "What was said about the energy sector and oil prices?",
        "What technical analysis was provided for the S&P 500?"
    )
    
    $successfulChats = 0
    
    for ($i = 0; $i -lt $testQuestions.Count; $i++) {
        $question = $testQuestions[$i]
        Write-Host "Question $($i+1): $question" -ForegroundColor Cyan
        
        $chatData = @{
            question = $question
            transcript_id = $transcript_id
            user_id = $TEST_USER_ID
            context = @{
                source = "chrome_extension"
                video_title = "Market Analysis: Fed Rates & Tech Rally"
            }
        } | ConvertTo-Json -Depth 3
        
        try {
            $chatResponse = Invoke-RestMethod -Uri "$BASE_URL/api/qa" -Method Post -Body $chatData -Headers @{"Content-Type"="application/json"} -TimeoutSec 30
            
            $answer = $chatResponse.answer
            $confidence = $chatResponse.confidence
            $sourcesCount = if ($chatResponse.sources) { $chatResponse.sources.Count } else { 0 }
            
            Write-Host "Answer received (confidence: $($confidence.ToString('F2')))" -ForegroundColor Green
            Write-Host "Answer preview: $($answer.Substring(0, [Math]::Min(150, $answer.Length)))..." -ForegroundColor Yellow
            Write-Host "Sources used: $sourcesCount chunks" -ForegroundColor Yellow
            Write-Host ""
            
            $successfulChats++
            
        } catch {
            Write-Host "Chat failed for question $($i+1): $($_.Exception.Message)" -ForegroundColor Red
            Write-Host ""
        }
        
        Start-Sleep -Seconds 1
    }
    
    # Summary
    Write-Host "Integration Test Complete!" -ForegroundColor Green
    Write-Host "================================================================================"
    Write-Host "Summary:" -ForegroundColor Yellow
    Write-Host "Health Check: PASSED" -ForegroundColor Green
    Write-Host "YouTube Ingestion: PASSED" -ForegroundColor Green
    Write-Host "RAG Chat: $successfulChats/$($testQuestions.Count) questions answered successfully" -ForegroundColor Green
    
    if ($successfulChats -eq $testQuestions.Count) {
        Write-Host ""
        Write-Host "COMPLETE SUCCESS: YouTube Extension fully integrated!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Extension Status: READY FOR DEPLOYMENT" -ForegroundColor Green
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Build Chrome extension: cd extension/simply && npm run build" -ForegroundColor White
        Write-Host "2. Load extension in Chrome developer mode" -ForegroundColor White
        Write-Host "3. Test on real YouTube videos" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "PARTIAL SUCCESS: $successfulChats/$($testQuestions.Count) chat features working" -ForegroundColor Yellow
        Write-Host "Some RAG features may need adjustment" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "No transcript ID generated - cannot test chat" -ForegroundColor Red
} 