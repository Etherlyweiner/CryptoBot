Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
Set oShellLink = WshShell.CreateShortcut(strDesktop & "\CryptoBot.lnk")
oShellLink.TargetPath = "c:\Users\Jonat\CryptoBot\start_cryptobot.bat"
oShellLink.WorkingDirectory = "c:\Users\Jonat\CryptoBot"
oShellLink.IconLocation = "C:\Windows\System32\SHELL32.dll,35"
oShellLink.Save
