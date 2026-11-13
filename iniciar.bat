@echo off
rem Conserje: prepara todo la primera vez, levanta el servidor y abre la pagina.
rem Doble clic para usarlo. Para cortar el servidor: cerrar esta ventana o Ctrl+C.
chcp 65001 >nul
cd /d "%~dp0"
title Conserje - servidor

set "PY=.venv\Scripts\python.exe"

rem --- 1. Entorno virtual (solo la primera vez) ---------------------------------
if not exist "%PY%" (
    echo Preparando el entorno de Python por primera vez...
    where py >nul 2>nul && (py -3 -m venv .venv) || (python -m venv .venv)
    if not exist "%PY%" (
        echo.
        echo No se encontro Python. Instalalo desde https://www.python.org/downloads/
        echo tildando "Add python.exe to PATH" y volve a abrir este archivo.
        pause
        exit /b 1
    )
)

rem --- 2. Librerias (Flask y compania) -----------------------------------------
echo Revisando las librerias...
"%PY%" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo No se pudieron instalar las librerias. Revisa la conexion a internet.
    pause
    exit /b 1
)

rem --- 3. Archivo .env con la clave secreta ------------------------------------
if not exist ".env" if exist ".env.example" copy ".env.example" ".env" >nul

rem --- 4. Datos de ejemplo (Hotel Mirador) -------------------------------------
rem Las reservas de la demo se arman alrededor de la fecha de hoy: conviene
rem recargarlas el dia que se presenta.
if not exist "instance\hotel.db" (
    echo Cargando el hotel de ejemplo...
    "%PY%" -m flask --app app demo --si
) else (
    choice /c SN /t 8 /d N /m "Recargar los datos de ejemplo con la fecha de hoy (borra los cambios)"
    if not errorlevel 2 "%PY%" -m flask --app app demo --si
)

rem --- 5. Abrir el navegador cuando el servidor ya este andando -----------------
echo.
echo  Sitio del hotel:   http://127.0.0.1:5000/
echo  Administracion:    http://127.0.0.1:5000/administracion
echo  Usuarios de prueba: admin@mirador.demo / admin123  -  recepcion@mirador.demo / recepcion123
echo.
start "" /min powershell -NoProfile -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:5000/'"

"%PY%" run.py
pause
