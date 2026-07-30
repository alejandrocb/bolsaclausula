@echo off
REM Ejecuta la conciliacion de bolsas N91c / S9b1a en Windows.
REM Doble clic o: run.bat
setlocal

REM 1) Entorno virtual (lo crea la primera vez)
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error

REM 2) Dependencias e instalacion del paquete en modo editable
echo Instalando dependencias...
py -m pip install -q -r requirements.txt || goto :error
py -m pip install -q -e . || goto :error

REM 3) Comprobacion de datos
if not exist "data\inicial" (
    echo.
    echo ATENCION: falta la carpeta data\inicial con los 3 ficheros del corte.
    goto :error
)
if not exist "data\periodicas" (
    echo.
    echo ATENCION: falta la carpeta data\periodicas con los 5 ficheros periodicos.
    goto :error
)

REM 4) Ejecucion
echo.
py -m bolsa.cli
echo.
echo Listo. Revisa la carpeta "salidas".
goto :fin

:error
echo.
echo Se produjo un error. Revisa el mensaje anterior.
exit /b 1

:fin
endlocal
pause
