@echo off
title CoordoPro JEPS - Suite Administrative & Pedagogique OF
echo ======================================================================
echo           COORDOPRO JEPS - DEMARRAGE DU SERVEUR LOCAL
echo ======================================================================
echo.
echo Demarrage du serveur local sans LLM ni API payante...
echo Interface Web : http://localhost:8088
echo.
start http://localhost:8088
python server.py
pause
