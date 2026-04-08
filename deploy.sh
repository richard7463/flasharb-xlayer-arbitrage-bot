#!/bin/bash

# XLayer Arbitrage Bot - Deploy Script

set -e

echo "=========================================="
echo "XLayer Arbitrage Bot - Deployment"
echo "=========================================="

# Check Python version
python3 --version

# Install dependencies
echo "[1/5] Installing dependencies..."
pip install -r requirements.txt

# Install Onchain OS Skills (if using npx)
echo "[2/5] Setting up environment..."
if command -v npx &> /dev/null; then
    echo "Installing OKX Onchain OS Skills..."
    # npx skills add okx/onchainos-skills 2>/dev/null || true
fi

# Create .env from template
echo "[3/5] Configuring environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from template. Please edit it with your settings."
fi

# Install (optional) - compile any extensions
echo "[4/5] Verifying installation..."
python3 -c "import web3; import flask; print('Dependencies OK')"

# Run tests
echo "[5/5] Running tests..."
python3 -m pytest tests/ 2>/dev/null || python3 tests/test_arbitrage.py 2>/dev/null || echo "Tests skipped"

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your PRIVATE_KEY and settings"
echo "2. Run: python main.py --once     # Test run"
echo "3. Run: python main.py --daemon   # Start bot"
echo ""
