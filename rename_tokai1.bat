@echo off
powershell -ExecutionPolicy Bypass -Command "& { $f='C:\Users\USER\Desktop\TOKAI　RIT\TOKAIRIT1日目'; Get-ChildItem $f '*.mp4' | Where-Object {$_.Name -match '^\d{2}_'} | ForEach-Object { Rename-Item $_.FullName ($_.Name -replace '^\d{2}_','') }; $i=1; Get-ChildItem $f '*.mp4' | Sort-Object CreationTime | ForEach-Object { $n='{0:D2}' -f $i; Rename-Item $_.FullName ($n+'_'+$_.Name); $i++ }; Write-Host '完了'; }"
pause
