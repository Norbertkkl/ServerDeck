#!/usr/bin/env bash
# ==============================================================================
# ServerDeck - PyPI Release & Build Tool
# ==============================================================================
set -e

echo "Cleaning previous build artifacts..."
rm -rf build dist *.egg-info

echo "Building sdist and bdist_wheel..."
python3 setup.py sdist bdist_wheel

echo "Running twine package verification..."
if command -v twine &>/dev/null; then
    twine check dist/*
elif [ -f "/home/pann/homelab/.venv/bin/twine" ]; then
    /home/pann/homelab/.venv/bin/twine check dist/*
fi

echo "=============================================================================="
echo "Packages built successfully in dist/:"
ls -lh dist/
echo "=============================================================================="
echo "To publish to TestPyPI:"
echo "  twine upload --repository testpypi dist/*"
echo ""
echo "To publish to Official Production PyPI:"
echo "  twine upload dist/*"
echo "=============================================================================="

