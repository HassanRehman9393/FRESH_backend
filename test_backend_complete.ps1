# Complete Backend Test Script
# Tests: Login -> Upload Image -> Detection (with classification & disease) -> Get Results

Write-Host "=== FRESH Backend Complete Test ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$backendUrl = "http://localhost:8000"
$email = "hassangill9393@gmail.com"
$password = "Hassan@123"

# --- Step 1: Login ---
Write-Host "Step 1: Logging in..." -ForegroundColor Yellow
$loginPayload = @{
    email = $email
    password = $password
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$backendUrl/api/auth/login" `
        -Method POST `
        -Body $loginPayload `
        -ContentType "application/json"
    
    $token = $loginResponse.access_token
    Write-Host "✓ Login successful!" -ForegroundColor Green
    Write-Host "  User ID: $($loginResponse.user.id)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Login failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# --- Step 2: Test Detection with Existing Image ---
Write-Host "`nStep 2: Testing detection with existing image..." -ForegroundColor Yellow
$imageId = "09b32ea9-7105-4b1e-849b-3fb7686f17f6"  # Use your existing image ID

$detectionPayload = @{
    image_ids = @($imageId)
} | ConvertTo-Json

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

try {
    $detectionResponse = Invoke-RestMethod -Uri "$backendUrl/api/detection/batch-fruit" `
        -Method POST `
        -Body $detectionPayload `
        -Headers $headers `
        -TimeoutSec 300
    
    Write-Host "✓ Detection successful!" -ForegroundColor Green
    Write-Host "  Total processed: $($detectionResponse.total_count)" -ForegroundColor Gray
    Write-Host "  Success count: $($detectionResponse.success_count)" -ForegroundColor Gray
    Write-Host "  Failed count: $($detectionResponse.failed_count)" -ForegroundColor Gray
    
    if ($detectionResponse.results.Count -gt 0) {
        Write-Host "`n  Detection Results:" -ForegroundColor Cyan
        foreach ($result in $detectionResponse.results) {
            Write-Host "    - Fruit: $($result.fruit_type)" -ForegroundColor White
            Write-Host "      Detection Confidence: $($result.confidence)" -ForegroundColor Gray
            
            if ($result.classification) {
                Write-Host "      Classification:" -ForegroundColor Yellow
                Write-Host "        Ripeness: $($result.classification.ripeness_level) ($($result.classification.ripeness_confidence))" -ForegroundColor Gray
                Write-Host "        Color: $($result.classification.color)" -ForegroundColor Gray
                Write-Host "        Size: $($result.classification.size)" -ForegroundColor Gray
                if ($result.classification.defects -and $result.classification.defects.Count -gt 0) {
                    Write-Host "        Defects: $($result.classification.defects -join ', ')" -ForegroundColor Red
                }
            }
            Write-Host ""
        }
    }
} catch {
    Write-Host "✗ Detection failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $errorResponse = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($errorResponse)
        $responseBody = $reader.ReadToEnd()
        Write-Host "  Error details: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# --- Step 3: Get All Detection Results ---
Write-Host "`nStep 3: Getting all detection results..." -ForegroundColor Yellow

try {
    $resultsResponse = Invoke-RestMethod -Uri "$backendUrl/api/detection/fruit/results?limit=10&offset=0" `
        -Method GET `
        -Headers $headers
    
    Write-Host "✓ Retrieved $($resultsResponse.results.Count) results" -ForegroundColor Green
    
    if ($resultsResponse.results.Count -gt 0) {
        Write-Host "`n  Recent Detections:" -ForegroundColor Cyan
        foreach ($result in $resultsResponse.results | Select-Object -First 3) {
            Write-Host "    - $($result.fruit_type) detected on $($result.created_at)" -ForegroundColor White
            if ($result.classification) {
                Write-Host "      Ripeness: $($result.classification.ripeness_level)" -ForegroundColor Gray
            }
        }
    }
} catch {
    Write-Host "✗ Get results failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Green

