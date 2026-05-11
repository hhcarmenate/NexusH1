@echo off
echo Stopping Nexus H1...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Nexus H1*" 2>nul
taskkill /F /IM python.exe /FI "COMMANDLINE eq *start.py*" 2>nul
echo Done.
pause
