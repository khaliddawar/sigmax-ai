# Local Testing Guide for Simply App

This guide helps you test the Simply app locally before pushing to GitHub for deployment.

## Prerequisites

1. **Python Environment**: Python 3.11+ installed
2. **Dependencies**: Install all required packages
3. **Environment Variables**: Configure local environment
4. **Database**: Supabase connection (can use development instance)

## Quick Setup

### 1. Install Dependencies

```powershell
# Install Python dependencies
pip install -r requirements.txt

# Or using Poetry (recommended)
poetry install
```

### 2. Environment Configuration

Copy and configure your environment variables:

```powershell
# Copy example environment file
cp .env.example .env

# Edit .env file with your local settings
notepad .env
```

**Key environment variables for local testing:**

```bash
# Database (use development Supabase instance)
SUPABASE_URL=your_dev_supabase_url
SUPABASE_KEY=your_dev_supabase_key

# AI Services (for testing)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key  # optional

# Local testing flags
USE_MOCK_RESPONSES=true  # Set to true for testing without real API calls
ENVIRONMENT=development

# Optional: Enable new modular architecture for testing
ENABLE_NEW_ARCHITECTURE=true
FALLBACK_TO_ORIGINAL=true
```

## Local Testing Options

### Option 1: FastAPI Backend Only (Recommended for API testing)

```powershell
# Start the FastAPI server
python start.py

# Or directly with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Access points:**
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Option 2: Streamlit Frontend

```powershell
# Set environment variable for frontend
$env:SERVICE_TYPE = "frontend"
python start.py

# Or directly
streamlit run app/web/streamlit_app.py --server.port 8501
```

**Access point:**
- Frontend: http://localhost:8501

### Option 3: Both Services (Recommended for full testing)

**Terminal 1 - Backend:**
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```powershell
streamlit run app/web/streamlit_app.py --server.port 8501
```

## Testing the New Modular Architecture

### Test Modular Components

```powershell
# Test individual modular components
cd scripts
python test_modular_standalone.py
```

Expected output:
```
🎉 All standalone component tests passed!
📊 Summary:
   ✅ All modules have correct structure
   ✅ Vector search module functional
   ✅ Validation module functional
   ✅ Prompts module functional
   ✅ Rerank module functional
```

### Test API with Modular Architecture

```powershell
# Test API endpoints with new architecture
python tests/test_simple_curl.py
```

## Comprehensive Testing Suite

### 1. Basic API Testing

```powershell
# Test core API functionality
python tests/test_simple_curl.py
```

### 2. Full Pipeline Testing

```powershell
# Test complete ingestion pipeline
python tests/test_full_pipeline.py
```

### 3. YouTube Integration Testing

```powershell
# Test YouTube caption extraction
python tests/test_youtube_simple.py

# Test YouTube API integration
python tests/test_youtube_api.py
```

### 4. Extension Integration Testing

```powershell
# Test Chrome extension integration
python tests/test_extension_integration.py
```

### 5. PowerShell Integration Testing

```powershell
# Run PowerShell-specific tests
./tests/test_powershell_integration.ps1
```

## Health Checks and Monitoring

### Check Application Health

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed metrics
curl http://localhost:8000/metrics

# Prometheus metrics
curl http://localhost:8000/metrics/prometheus
```

### Test Modular Architecture Health

```python
# Python script to test modular architecture
import asyncio
import aiohttp

async def test_modular_health():
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        async with session.get('http://localhost:8000/health') as resp:
            health = await resp.json()
            print(f"Health: {health}")
        
        # Test metrics endpoint
        async with session.get('http://localhost:8000/metrics') as resp:
            metrics = await resp.json()
            print(f"Metrics: {metrics}")

# Run the test
asyncio.run(test_modular_health())
```

## Testing Scenarios

### 1. Test Question Answering (Core Feature)

```bash
# Test QA endpoint
curl -X POST http://localhost:8000/api/qa/question \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main topics discussed?",
    "transcript_id": "test-transcript"
  }'
```

### 2. Test Transcript Processing

```bash
# Test transcript upload
curl -X POST http://localhost:8000/test/process-transcript \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_id": "test-123",
    "transcript_text": "This is a test transcript about machine learning and AI.",
    "title": "Test Meeting",
    "date": "2024-01-15T10:00:00Z"
  }'
```

### 3. Test YouTube Integration

```bash
# Test YouTube URL processing
curl -X POST http://localhost:8000/api/youtube/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "extract_captions": true
  }'
```

## Performance Testing

### Test Response Times

```python
import time
import requests

def test_performance():
    url = "http://localhost:8000/health"
    times = []
    
    for i in range(10):
        start = time.time()
        response = requests.get(url)
        end = time.time()
        times.append(end - start)
        print(f"Request {i+1}: {response.status_code} in {times[-1]:.3f}s")
    
    print(f"Average response time: {sum(times)/len(times):.3f}s")

test_performance()
```

### Compare Modular vs Original Architecture

```python
# Test with original architecture
import os
os.environ["ENABLE_NEW_ARCHITECTURE"] = "false"

# Test with modular architecture  
os.environ["ENABLE_NEW_ARCHITECTURE"] = "true"
os.environ["FALLBACK_TO_ORIGINAL"] = "true"
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```powershell
   # Find process using port 8000
   netstat -ano | findstr :8000
   
   # Kill process (replace PID)
   taskkill /PID <PID> /F
   ```

2. **Environment Variables Not Loading**
   ```powershell
   # Verify .env file exists and is readable
   Get-Content .env | Select-String "SUPABASE_URL"
   ```

3. **Database Connection Issues**
   ```python
   # Test Supabase connection
   from app.services.supabase_client import SupabaseService
   service = SupabaseService()
   print(service.check_connection())
   ```

4. **Import Errors**
   ```powershell
   # Ensure you're in the project root
   python -c "import sys; print(sys.path[0])"
   
   # Add current directory to Python path
   $env:PYTHONPATH = "."
   ```

### Debug Mode

Enable detailed logging:

```python
# In your .env file
LOG_LEVEL=DEBUG
STRUCTURED_LOGGING=true
```

## Pre-Deployment Checklist

Before pushing to GitHub:

- [ ] ✅ All modular components pass tests
- [ ] ✅ API health check returns 200
- [ ] ✅ Core QA functionality works
- [ ] ✅ YouTube integration works
- [ ] ✅ No critical errors in logs
- [ ] ✅ Performance is acceptable
- [ ] ✅ Environment variables are properly configured
- [ ] ✅ Database migrations are applied
- [ ] ✅ All tests pass

## Automated Testing Script

Create a comprehensive test script:

```powershell
# test-local.ps1
Write-Host "🚀 Starting Local Testing Suite"

# Test modular components
Write-Host "Testing modular components..."
python scripts/test_modular_standalone.py

# Start server in background
Write-Host "Starting server..."
Start-Process python -ArgumentList "start.py" -NoNewWindow

# Wait for server to start
Start-Sleep 10

# Test API endpoints
Write-Host "Testing API endpoints..."
python tests/test_simple_curl.py

# Test full pipeline
Write-Host "Testing full pipeline..."
python tests/test_full_pipeline.py

Write-Host "✅ Local testing complete!"
```

## Next Steps

After successful local testing:

1. **Commit Changes**: `git add . && git commit -m "feat: implement modular architecture"`
2. **Push to GitHub**: `git push origin main`
3. **Monitor Deployment**: Check Railway/Render deployment logs
4. **Run Production Health Checks**: Verify deployed app works correctly

## Support

If you encounter issues:

1. Check the logs: `tail -f logs/app.log`
2. Review the health endpoint: `curl http://localhost:8000/health`
3. Test individual components: `python scripts/test_modular_standalone.py`
4. Verify environment variables: `python -c "import os; print(os.getenv('SUPABASE_URL'))"` 