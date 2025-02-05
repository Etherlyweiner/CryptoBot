# Run with administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {    
    $arguments = "& '" + $myinvocation.mycommand.definition + "'"
    Start-Process powershell -Verb runAs -ArgumentList $arguments
    Break
}

$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\CryptoBot Dashboard.lnk")
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/c `"cd /d `"$PWD`" && start_all.bat`""
$Shortcut.WorkingDirectory = "$PWD"
$Shortcut.IconLocation = "C:\Windows\System32\SHELL32.dll,70"  # Money icon
$Shortcut.Description = "Start CryptoBot Trading Dashboard"

# Set shortcut to run as administrator
$bytes = [System.IO.File]::ReadAllBytes("$DesktopPath\CryptoBot Dashboard.lnk")
$bytes[0x15] = $bytes[0x15] -bor 0x20 # Set run as administrator flag
[System.IO.File]::WriteAllBytes("$DesktopPath\CryptoBot Dashboard.lnk", $bytes)

$Shortcut.Save()

Write-Host "Desktop shortcut created successfully at: $DesktopPath\CryptoBot Dashboard.lnk"
Write-Host "The shortcut has been configured to run with administrator privileges."
