Option Explicit

Dim fileSystem, shell, projectDir, shortcut, shortcutPath

Set fileSystem = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
projectDir = fileSystem.GetParentFolderName(WScript.ScriptFullName)
shortcutPath = shell.SpecialFolders("Desktop") & "\VendeBem.lnk"
Set shortcut = shell.CreateShortcut(shortcutPath)

shortcut.TargetPath = projectDir & "\executar_windows.bat"
shortcut.WorkingDirectory = projectDir
shortcut.IconLocation = projectDir & "\assets\vendebem.ico,0"
shortcut.Description = "Abrir o VendeBem - Gerenciador de Vendas"
shortcut.Save

MsgBox "Atalho do VendeBem criado na Área de Trabalho.", vbInformation, "VendeBem"
