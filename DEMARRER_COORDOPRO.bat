@echo off
title CoordoPro JEPS - Suite du Coordonnateur d'Organisme de Formation
chcp 65001 >nul
cls

echo =====================================================================
echo                COORDOPRO JEPS - Lancement Rapide
echo      Suite Métier pour la Coordination des Formations RNCP & DRAJES
echo =====================================================================
echo.
echo [1/2] Verification de l'environnement Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    echo Veuillez installer Python (version 3.10 ou superieure).
    pause
    exit /b
)

echo [2/2] Demarrage du serveur local CoordoPro JEPS...
echo Le serveur fonctionne a 100%% en local (aucun abonnement API ni LLM requis).
echo.
echo URL d'acces : http://localhost:8088
echo.

:: Ouvre automatiquement le navigateur par defaut
start http://localhost:8088

:: Lance le serveur Python
python server.py

pause
