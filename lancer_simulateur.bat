@echo off
title Simulateur de Certification Excel
cd /d "%~dp0\excel_cert_app"

echo ====================================================
echo   Lancement du Simulateur de Certification Excel
echo ====================================================
echo.

:: Vérifier si Python est installé
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.11+ depuis https://www.python.org/
    goto end
)

:: Créer le venv s'il n'existe pas
if not exist .venv (
    echo [INFO] Creation de l'environnement virtuel (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERREUR] Impossible de creer l'environnement virtuel.
        goto end
    )
)

:: Activer le venv
echo [INFO] Activation de l'environnement virtuel...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERREUR] Impossible d'activer l'environnement virtuel.
    goto end
)

:: Installer ou mettre à jour les dépendances
echo [INFO] Verification et installation des dependances...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERREUR] Echec de l'installation des dependances.
    goto end
)

:: Lancer l'application
echo [INFO] Lancement de l'application...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [INFO] L'application s'est terminee ou a rencontre un probleme.
)

:end
echo.
echo Appuyez sur une touche pour quitter...
pause >nul
