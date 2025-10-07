# Fix CSP Script for Simply Chrome Extension
# This script removes unsafe-inline and unsafe-eval from the CSP to make Chrome accept the extension

Write-Host "🔧 Fixing Content Security Policy in manifest.json..." -ForegroundColor Yellow

$manifestPath = "build/chrome-mv3-prod/manifest.json"

if (Test-Path $manifestPath) {
    try {
        # Read and parse the manifest
        $manifest = Get-Content $manifestPath | ConvertFrom-Json
        
        # Check if CSP exists and has unsafe directives
        if ($manifest.content_security_policy -and $manifest.content_security_policy.extension_pages) {
            $currentCSP = $manifest.content_security_policy.extension_pages
            Write-Host "Current CSP: $currentCSP" -ForegroundColor Gray
            
            # Remove unsafe directives
            $secureCSP = "script-src 'self'; object-src 'self'; frame-src 'self' data: blob:;"
            $manifest.content_security_policy.extension_pages = $secureCSP
            
            # Write back to file
            $manifest | ConvertTo-Json -Depth 10 -Compress | Set-Content $manifestPath
            
            Write-Host "✅ CSP updated successfully!" -ForegroundColor Green
            Write-Host "New CSP: $secureCSP" -ForegroundColor Green
        } else {
            Write-Host "⚠️  No CSP found in manifest" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Error updating manifest: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ Manifest file not found at: $manifestPath" -ForegroundColor Red
    Write-Host "Make sure to run 'npm run build' first" -ForegroundColor Yellow
    exit 1
}

Write-Host "🎉 Ready to load extension from: build/chrome-mv3-prod" -ForegroundColor Cyan 