@echo off
REM ============================================================
REM Season Awards - Scraper Automatico
REM ============================================================
REM Questo script esegue:
REM 1. Scraping dei dati per l'anno corrente
REM 2. Aggiornamento del Control Panel
REM 3. Generazione delle statistiche aggregate
REM ============================================================

cd /d "%~dp0"

echo ============================================
echo   SEASON AWARDS - SCRAPER AUTOMATICO
echo ============================================
echo.

REM Calcola l'anno corrente (se siamo prima di settembre, usa l'anno corrente, altrimenti usa l'anno successivo)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set datetime=%%I
set year=%datetime:~0,4%
set month=%datetime:~4,2%

REM Se siamo dopo agosto (mese > 08), aggiungi 1 all'anno per la nuova stagione
if %month% GEQ 09 (
    set /a year=%year%+1
)

echo Anno stagione corrente: %year%/%year%
echo.

REM Controlla che Python sia installato
where py >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERRORE: Python non trovato! Installa Python e riprova.
    pause
    exit /b 1
)

echo [1/3] Esecuzione scraping per anno %year%...
echo ============================================
py scraper/scrape_and_upload.py --years %year%
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ATTENZIONE: Lo scraping ha riscontrato alcuni errori.
    echo Controlla il log sopra per dettagli.
)

echo.
echo [2/3] Control Panel aggiornato automaticamente.
echo ============================================
echo I file data_*.json sono stati generati.
echo Il Control Panel (control.html) usa i dati da Firebase.

echo.
echo [3/3] Statistiche aggiornate.
echo ============================================
echo Le statistiche vengono calcolate dinamicamente
echo dalla pagina web leggendo i dati da Firebase.
echo.

echo ============================================
echo   COMPLETATO!
echo ============================================
echo.
echo Apri index.html nel browser per vedere i dati aggiornati.
echo Apri control.html per vedere il Control Panel.
echo Clicca su "Statistics" nel menu per le statistiche.
echo.
pause
