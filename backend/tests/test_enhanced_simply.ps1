#!/usr/bin/env powershell
<#
.SYNOPSIS
    Enhanced Simply System Testing Script
.DESCRIPTION
    Comprehensive testing script for the new topic-agnostic Simply system.
    Tests backend, extension, and validates enhanced features.
.EXAMPLE
    .\tests\test_enhanced_simply.ps1 -TestType "all"
.\tests\test_enhanced_simply.ps1 -TestType "backend"
.\tests\test_enhanced_simply.ps1 -TestType "extension"
#>

param(
    [ValidateSet("all", "backend", "extension", "quick")]
    [string]$TestType = "all",
    
    [switch]$SkipBuild,
    [switch]$Verbose
)

# Set error handling
$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Info { param($Message) Write-Host "ℹ️ $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️ $Message" -ForegroundColor Yellow }

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Success "Python: $pythonVersion"
    } catch {
        Write-Error "Python not found. Please install Python 3.8+"
        exit 1
    }
    
    # Check Node.js (for extension)
    if ($TestType -eq "all" -or $TestType -eq "extension") {
        try {
            $nodeVersion = node --version 2>&1
            Write-Success "Node.js: $nodeVersion"
        } catch {
            Write-Error "Node.js not found. Please install Node.js 16+"
            exit 1
        }
    }
    
    # Check if virtual environment exists
    if (Test-Path "venv\Scripts\activate.ps1") {
        Write-Success "Virtual environment found"
    } else {
        Write-Warning "Virtual environment not found, using global Python"
    }
}

function Start-Backend {
    Write-Info "Starting Simply backend server..."
    
    # Check if server is already running
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
        Write-Success "Backend already running"
        return $true
    } catch {
        Write-Info "Starting backend server..."
    }
    
    # Start server in background
    $serverJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        if (Test-Path "venv\Scripts\activate.ps1") {
            & "venv\Scripts\activate.ps1"
        }
        python start_server.py
    }
    
    # Wait for server to start
    $timeout = 30
    $elapsed = 0
    
    while ($elapsed -lt $timeout) {
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2
            Write-Success "Backend started successfully"
            return $serverJob
        } catch {
            Start-Sleep -Seconds 2
            $elapsed += 2
            Write-Host "." -NoNewline
        }
    }
    
    Write-Error "Backend failed to start within $timeout seconds"
    return $false
}

function Test-Backend {
    Write-Info "Testing backend functionality..."
    
    # Test health endpoint
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/health"
        Write-Success "Health check passed: $($health.status)"
    } catch {
        Write-Error "Health check failed: $($_.Exception.Message)"
        return $false
    }
    
    return $true
}

function Build-Extension {
    if ($SkipBuild) {
        Write-Info "Skipping extension build"
        return $true
    }
    
    Write-Info "Building Simply Chrome extension..."
    
    Push-Location "extension\simply"
    
    try {
        # Install dependencies
        Write-Info "Installing extension dependencies..."
        npm install
        
        # Build extension
        Write-Info "Building extension..."
        npm run build
        
        # Check if build was successful
        if (Test-Path "build") {
            Write-Success "Extension built successfully"
            Write-Info "Extension ready at: extension\simply\build"
            return $true
        } else {
            Write-Error "Extension build failed - no build directory found"
            return $false
        }
    } catch {
        Write-Error "Extension build failed: $($_.Exception.Message)"
        return $false
    } finally {
        Pop-Location
    }
}

function Test-Extension {
    Write-Info "Testing extension files..."
    
    $extensionPath = "extension\simply"
    $buildPath = "$extensionPath\build"
    
    # Check if extension is built
    if (-not (Test-Path $buildPath)) {
        Write-Warning "Extension not built. Building now..."
        if (-not (Build-Extension)) {
            return $false
        }
    }
    
    # Check key files
    $requiredFiles = @(
        "$buildPath\manifest.json",
        "$extensionPath\components\Icon.tsx",
        "$extensionPath\components\UsageMeter.tsx",
        "$extensionPath\assets\icons.svg"
    )
    
    $allFilesExist = $true
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Success "Found: $file"
        } else {
            Write-Error "Missing: $file"
            $allFilesExist = $false
        }
    }
    
    return $allFilesExist
}

function Run-ComprehensiveTest {
    Write-Info "Running comprehensive system test..."
    
    try {
        python scripts\test_enhanced_system.py
        Write-Success "Comprehensive test completed"
        return $true
    } catch {
        Write-Error "Comprehensive test failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-EnhancedFeatures {
    Write-Info "Testing enhanced Simply features..."
    
    # Test prompt files
    $promptFiles = @(
        "config\prompts\content_synthesis.yaml",
        "config\prompts\section_discovery.yaml"
    )
    
    foreach ($file in $promptFiles) {
        if (Test-Path $file) {
            Write-Success "Prompt file exists: $file"
        } else {
            Write-Error "Missing prompt file: $file"
        }
    }
    
    # Test service files
    $serviceFiles = @(
        "app\services\summary_service.py",
        "app\services\retrieval_qa_service.py",
        "app\services\email_service.py"
    )
    
    foreach ($file in $serviceFiles) {
        if (Test-Path $file) {
            Write-Success "Service file exists: $file"
        } else {
            Write-Error "Missing service file: $file"
        }
    }
}

function Show-TestResults {
    Write-Info "Test Results Summary"
    Write-Host "=" * 50
    
    # Check for latest test report
    $reportPattern = "reports\simply_test_report_*.json"
    $latestReport = Get-ChildItem $reportPattern | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    
    if ($latestReport) {
        Write-Success "Latest test report: $($latestReport.Name)"
        
        try {
            $report = Get-Content $latestReport.FullName | ConvertFrom-Json
            Write-Info "Test Timestamp: $($report.test_timestamp)"
            Write-Info "Backend Health: $($report.backend_health)"
            Write-Info "Hallucination Rate: $($report.hallucination_rate)%"
            Write-Info "Overall Success: $($report.overall_success)"
            
            if ($report.recommendations) {
                Write-Info "Recommendations:"
                foreach ($rec in $report.recommendations) {
                    Write-Host "  $rec"
                }
            }
        } catch {
            Write-Warning "Could not parse test report"
        }
    } else {
        Write-Warning "No test reports found"
    }
}

# Main execution
Write-Info "🚀 Enhanced Simply System Testing"
Write-Info "Test Type: $TestType"
Write-Host "=" * 50

$allTestsPassed = $true

# Check prerequisites
Test-Prerequisites

# Run tests based on type
switch ($TestType) {
    "quick" {
        Write-Info "Running quick tests..."
        Test-EnhancedFeatures
    }
    
    "backend" {
        $serverJob = Start-Backend
        if ($serverJob) {
            $allTestsPassed = Test-Backend
            if ($allTestsPassed) {
                $allTestsPassed = Run-ComprehensiveTest
            }
        } else {
            $allTestsPassed = $false
        }
    }
    
    "extension" {
        $allTestsPassed = Build-Extension
        if ($allTestsPassed) {
            $allTestsPassed = Test-Extension
        }
    }
    
    "all" {
        # Test enhanced features first
        Test-EnhancedFeatures
        
        # Start backend
        $serverJob = Start-Backend
        if ($serverJob) {
            $backendOk = Test-Backend
            
            # Build and test extension
            $extensionOk = Build-Extension
            if ($extensionOk) {
                $extensionOk = Test-Extension
            }
            
            # Run comprehensive tests
            $comprehensiveOk = $false
            if ($backendOk) {
                $comprehensiveOk = Run-ComprehensiveTest
            }
            
            $allTestsPassed = $backendOk -and $extensionOk -and $comprehensiveOk
        } else {
            $allTestsPassed = $false
        }
    }
}

# Show results
Show-TestResults

# Cleanup
if ($serverJob) {
    Write-Info "Stopping backend server..."
    Stop-Job $serverJob -ErrorAction SilentlyContinue
    Remove-Job $serverJob -ErrorAction SilentlyContinue
}

# Final result
Write-Host "=" * 50
if ($allTestsPassed) {
    Write-Success "🎉 All tests passed! System ready for deployment."
    exit 0
} else {
    Write-Error "❌ Some tests failed. Check output above."
    exit 1
} 