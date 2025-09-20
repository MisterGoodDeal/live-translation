@echo off
echo 🚀 Live Translation - Démarrage automatique
echo ==========================================

cd /d "%~dp0"

echo 📦 Activation de l'environnement virtuel...
call .venv\Scripts\activate.bat

echo 🐍 Lancement de l'application...
python run_all.py

pause
