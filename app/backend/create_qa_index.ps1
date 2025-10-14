Write-Host "Creating Q&A index in Azure Search..." -ForegroundColor Green
python create_qa_index.py
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")