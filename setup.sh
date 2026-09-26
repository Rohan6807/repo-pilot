#!/usr/bin/env bash
# One-command setup + smoke test for RepoPilot. Tries several install
# strategies in order so environment quirks (existing virtualenv, locked-down
# system Python, no venv module, etc.) don't block you. Run from repo-pilot/:
#   bash setup.sh

echo "=== RepoPilot setup ==="

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "ERROR: no python3 or python found on PATH."
    echo "Install Python from https://python.org and re-run this script."
    exit 1
fi
echo "Using: $($PY --version)"

cd sample-project

# 0. Already satisfied? Skip everything.
if $PY -c "import flask" >/dev/null 2>&1; then
    echo "Flask already available — skipping install."
    INSTALLED=1
else
    INSTALLED=0
fi

# 1. Already inside a virtualenv/conda env? Just install directly into it.
if [ "$INSTALLED" -eq 0 ] && $PY -c "import sys; exit(0 if sys.prefix != sys.base_prefix else 1)" >/dev/null 2>&1; then
    echo "Detected an active virtual environment — installing into it..."
    if $PY -m pip install -r requirements.txt; then
        INSTALLED=1
    fi
fi

# 2. Try creating our own venv.
if [ "$INSTALLED" -eq 0 ]; then
    echo "Trying to create a fresh virtual environment..."
    if $PY -m venv venv >/dev/null 2>&1; then
        if [ -f venv/bin/activate ]; then source venv/bin/activate; fi
        if [ -f venv/Scripts/activate ]; then source venv/Scripts/activate; fi
        if pip install -r requirements.txt; then
            INSTALLED=1
            echo "Installed into venv/."
        fi
    else
        echo "venv creation failed (module may be missing — on Ubuntu/Debian try: sudo apt install python3-venv)"
    fi
fi

# 3. Fall back to --user install.
if [ "$INSTALLED" -eq 0 ]; then
    echo "Trying a --user install..."
    if $PY -m pip install --user -r requirements.txt 2>/dev/null; then
        INSTALLED=1
    fi
fi

# 4. Fall back to --break-system-packages (needed on newer Debian/Ubuntu system Python).
if [ "$INSTALLED" -eq 0 ]; then
    echo "Trying --break-system-packages (needed on some newer Linux distros)..."
    if $PY -m pip install --break-system-packages -r requirements.txt 2>/dev/null; then
        INSTALLED=1
    fi
fi

# 5. Plain install as a last resort.
if [ "$INSTALLED" -eq 0 ]; then
    echo "Trying a plain install..."
    if $PY -m pip install -r requirements.txt 2>/dev/null; then
        INSTALLED=1
    fi
fi

if [ "$INSTALLED" -eq 0 ]; then
    echo ""
    echo "ERROR: could not install Flask automatically. Try one of these by hand:"
    echo "  $PY -m pip install --user flask"
    echo "  sudo apt install python3-flask        (Debian/Ubuntu)"
    echo "  $PY -m pip install --break-system-packages flask"
    exit 1
fi

echo ""
echo "=== Running sample app tests (on current branch) ==="
$PY -m unittest discover tests
echo "(Failures above are expected if you're on feature/bulk-update — that IS the planted breaking change.)"

cd ..

echo ""
echo "=== Running RepoPilot PR mode ==="
$PY -m orchestrator.run --mode=pr --base=master --branch=feature/bulk-update

echo ""
echo "=== Running RepoPilot Onboarding mode ==="
$PY -m orchestrator.run --mode=onboard

echo ""
echo "=== Done ==="
echo "See release-report.md and onboarding-brief.md for the results."
echo "Next: open this folder in Bob IDE, run /init, and create the 5 custom"
echo "modes from bob-agents/*.md. See README.md for the full walkthrough."
