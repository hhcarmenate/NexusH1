@echo off
echo ============================================
echo   Nexus H1 - Instalando servicio
echo ============================================
echo.

set "NSSM=C:\Tools\nssm.exe"
set "PYTHON=C:\Users\Yosva\AppData\Local\Programs\Python\Python312\python.exe"
set "WORKDIR=C:\Users\Yosva\Desktop\nexus H1\nexus-h1"
set "SCRIPT=start.py"
set "SERVICE=NexusH1"
set "LOGDIR=%WORKDIR%\logs"

echo [1/5] Eliminando servicio anterior si existe...
net stop %SERVICE% >nul 2>&1
%NSSM% remove %SERVICE% confirm >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/5] Creando servicio NexusH1...
%NSSM% install %SERVICE% "%PYTHON%" "%SCRIPT%"
%NSSM% set %SERVICE% DisplayName "Nexus H1 Assistant"
%NSSM% set %SERVICE% Description "Personal assistant for organization and communication"
%NSSM% set %SERVICE% AppDirectory "%WORKDIR%"
%NSSM% set %SERVICE% AppExit Default Restart
%NSSM% set %SERVICE% AppRestartDelay 10000
%NSSM% set %SERVICE% Start SERVICE_AUTO_START

echo [3/5] Configurando logs...
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
%NSSM% set %SERVICE% AppStdout "%LOGDIR%\service.log"
%NSSM% set %SERVICE% AppStderr "%LOGDIR%\service-error.log"
%NSSM% set %SERVICE% AppStdoutCreationDisposition 4
%NSSM% set %SERVICE% AppStderrCreationDisposition 4
%NSSM% set %SERVICE% AppRotateFiles 1
%NSSM% set %SERVICE% AppRotateBytes 1048576

echo [4/5] Iniciando servicio...
net start %SERVICE%
timeout /t 3 /nobreak >nul

echo [5/5] Verificando estado...
sc query %SERVICE% | findstr "STATE"

echo.
echo ============================================
echo   Instalacion completa
echo ============================================
echo Logs: %LOGDIR%
echo.
pause
