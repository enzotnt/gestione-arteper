@echo off
TITLE Installazione Gestionale arTEper - Windows
echo ==============================================
echo    INSTALLAZIONE GESTIONALE arTEper
echo    Versione per Windows
echo ==============================================
echo.

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python non trovato!
    echo Scarica Python da: https://www.python.org/downloads/
    echo IMPORTANTE: Durante l'installazione, spunta "Add Python to PATH"
    pause
    exit /b 1
)

echo ✅ Python trovato!

REM Rimuovi ambiente virtuale esistente se presente
if exist venv_gestionale (
    echo 🗑️ Rimozione ambiente virtuale esistente...
    rmdir /s /q venv_gestionale
)

REM Crea nuovo ambiente virtuale
echo.
echo 📦 Creazione nuovo ambiente virtuale...
python -m venv venv_gestionale
if errorlevel 1 (
    echo ❌ Errore nella creazione dell'ambiente virtuale
    pause
    exit /b 1
)

REM Attiva ambiente virtuale
echo.
echo 🔌 Attivazione ambiente virtuale...
call venv_gestionale\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Errore nell'attivazione dell'ambiente
    pause
    exit /b 1
)

REM Aggiorna pip
echo.
echo 🔄 Aggiornamento pip...
python -m pip install --upgrade pip

REM Installa dipendenze una per una (più affidabile)
echo.
echo 📥 Installazione dipendenze...

echo   - Installazione Pillow...
pip install Pillow

echo   - Installazione matplotlib...
pip install matplotlib

echo   - Installazione reportlab...
pip install reportlab

echo   - Installazione tkcalendar...
pip install tkcalendar

echo   - Installazione mplcursors...
pip install mplcursors

echo   - Installazione pyperclip...
pip install pyperclip

REM Verifica installazione
echo.
echo 🔍 Verifica installazione...
python -c "from PIL import Image; print('✅ Pillow OK')" || echo ❌ Pillow NON installato
python -c "import matplotlib; print('✅ Matplotlib OK')" || echo ❌ Matplotlib NON installato
python -c "import reportlab; print('✅ Reportlab OK')" || echo ❌ Reportlab NON installato

REM Crea script di avvio
echo.
echo 🚀 Creazione script di avvio...
echo @echo off > avvia_gestionale.bat
echo echo ============================================== >> avvia_gestionale.bat
echo echo    AVVIO GESTIONALE arTEper >> avvia_gestionale.bat
echo echo ============================================== >> avvia_gestionale.bat
echo echo. >> avvia_gestionale.bat
echo call venv_gestionale\Scripts\activate.bat >> avvia_gestionale.bat
echo python main.py >> avvia_gestionale.bat
echo pause >> avvia_gestionale.bat

echo.
echo ==============================================
echo ✅ INSTALLAZIONE COMPLETATA!
echo ==============================================
echo.
echo Per avviare il programma:
echo   doppio click su avvia_gestionale.bat
echo.
pause