Write-Host "Uploading sample Q&A data to Azure Search..." -ForegroundColor Green
python upload_sample_qa.py
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")