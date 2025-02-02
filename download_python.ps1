$url = "https://www.python.org/ftp/python/3.10.9/python-3.10.9-amd64.exe"
$output = "python-3.10.9-amd64.exe"

Write-Output "Downloading Python 3.10.9..."
Invoke-WebRequest -Uri $url -OutFile $output
Write-Output "Download completed!"

Write-Output "Installing Python 3.10.9..."
Start-Process -FilePath $output -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
Write-Output "Installation completed!"

Remove-Item $output
Write-Output "Cleaned up installer."
