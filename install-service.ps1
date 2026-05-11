#Requires -RunAsAdministrator
# Nexus H1 - Instalar como servicio de Windows

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Nexus H1 - Instalando servicio" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Configuracion
$serviceName = "NexusH1"
$displayName = "Nexus H1 Assistant"
$description = "Personal assistant for organization and communication"
$pythonPath = "C:\Users\Yosva\AppData\Local\Programs\Python\Python312\python.exe"
$workingDir = "C:\Users\Yosva\Desktop\nexus H1\nexus-h1"
$scriptName = "start.py"
$nssmDir = "C:\Tools"
$nssmExe = "$nssmDir\nssm.exe"

# 1. Verificar Python
if (-not (Test-Path $pythonPath)) {
    Write-Host "ERROR: No se encontro Python en: $pythonPath" -ForegroundColor Red
    Write-Host "Actualiza la ruta en este script y vuelve a intentar." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Python encontrado: $pythonPath" -ForegroundColor Green

# 2. Descargar NSSM si no existe
if (-not (Test-Path $nssmExe)) {
    Write-Host "Descargando NSSM..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $nssmDir -Force | Out-Null
    $nssmZip = "$env:TEMP\nssm.zip"
    
    try {
        Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $nssmZip -UseBasicParsing
        Expand-Archive -Path $nssmZip -DestinationPath "$env:TEMP\nssm" -Force
        Copy-Item -Path "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" -Destination $nssmExe -Force
        Write-Host "[OK] NSSM instalado en: $nssmExe" -ForegroundColor Green
    } catch {
        Write-Host "ERROR descargando NSSM: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] NSSM ya existe: $nssmExe" -ForegroundColor Green
}

# 3. Detener y eliminar servicio anterior si existe
$existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Servicio existente encontrado. Eliminando..." -ForegroundColor Yellow
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $nssmExe -ArgumentList "remove", $serviceName, "confirm" -Wait -WindowStyle Hidden
    Start-Sleep -Seconds 2
    Write-Host "[OK] Servicio anterior eliminado" -ForegroundColor Green
}

# 4. Crear nuevo servicio
Write-Host "Creando servicio '$serviceName'..." -ForegroundColor Yellow
Start-Process -FilePath $nssmExe -ArgumentList "install", $serviceName, $pythonPath -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "DisplayName", $displayName -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "Description", $description -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "Application", $pythonPath -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppDirectory", $workingDir -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppParameters", $scriptName -Wait -WindowStyle Hidden

# 5. Configurar auto-reinicio
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppExit", "Default", "Restart" -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppRestartDelay", "10000" -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "Start", "SERVICE_AUTO_START" -Wait -WindowStyle Hidden

# 6. Logs del servicio
$logDir = "$workingDir\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppStdout", "$logDir\service.log" -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppStderr", "$logDir\service-error.log" -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppStdoutCreationDisposition", "4" -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppStderrCreationDisposition", "4" -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppRotateFiles", "1" -Wait -WindowStyle Hidden
Start-Process -FilePath $nssmExe -ArgumentList "set", $serviceName, "AppRotateBytes", "1048576" -Wait -WindowStyle Hidden

Write-Host "[OK] Servicio creado con exito" -ForegroundColor Green

# 7. Iniciar servicio
Write-Host "Iniciando servicio..." -ForegroundColor Yellow
Start-Service -Name $serviceName
Start-Sleep -Seconds 3

# 8. Verificar
$service = Get-Service -Name $serviceName
if ($service.Status -eq "Running") {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  Nexus H1 esta corriendo como servicio" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "Servicio: $serviceName" -ForegroundColor Cyan
    Write-Host "Estado: $($service.Status)" -ForegroundColor Cyan
    Write-Host "Logs: $logDir" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Comandos utiles:" -ForegroundColor White
    Write-Host "  services.msc              -> Ver en interfaz grafica" -ForegroundColor Gray
    Write-Host "  Get-Service NexusH1       -> Ver estado en PowerShell" -ForegroundColor Gray
    Write-Host "  Restart-Service NexusH1   -> Reiniciar" -ForegroundColor Gray
    Write-Host "  Stop-Service NexusH1      -> Detener" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "ADVERTENCIA: El servicio no se inicio correctamente." -ForegroundColor Yellow
    Write-Host "Estado: $($service.Status)" -ForegroundColor Yellow
    Write-Host "Revisa los logs en: $logDir" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Presiona Enter para salir"
