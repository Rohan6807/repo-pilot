@echo off
REM One-command setup + smoke test for RepoPilot on Windows.
REM Run from the repo-pilot\ root: setup.bat

echo === RepoPilot setup ===

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: python not found on PATH.
    echo Install Python from https://python.org and re-run this script.
    echo IMPORTANT: during install, check "Add Python to PATH".
    exit /b 1
)

python --version
cd sample-project

python -m venv venv
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Falling back to a user-level install...
        python -m pip install --user -r requirements.txt
    )
) else (
    echo Falling back to a user-level install (no virtual environment)...
    python -m pip install --user -r requirements.txt
)

echo.
echo === Running sample app tests (on current branch) ===
python -m unittest discover tests
echo (Failures above are expected if you're on feature/bulk-update - that's the planted breaking change.)

cd ..

echo.
echo === Running RepoPilot PR mode ===
python -m orchestrator.run --mode=pr --base=master --branch=feature/bulk-update

echo.
echo === Running RepoPilot Onboarding mode ===
python -m orchestrator.run --mode=onboard

echo.
echo === Done ===
echo See release-report.md and onboarding-brief.md for the results.
echo Next: open this folder in Bob IDE, run /init, and create the 5 custom
echo modes from bob-agents\*.md. See README.md for the full walkthrough.
