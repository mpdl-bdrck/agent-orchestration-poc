#!/bin/bash
# Setup script for Python 3.13 environment
# This creates a new venv with Python 3.13 and installs all dependencies

set -e  # Exit on error

echo "🐍 Setting up Python 3.13 environment..."
echo ""

# Check if Python 3.13 is available
if ! command -v python3.13 &> /dev/null; then
    echo "❌ Error: python3.13 not found"
    echo "Install with: brew install python@3.13"
    exit 1
fi

echo "✅ Found Python 3.13: $(python3.13 --version)"
echo ""

# Backup current venv if it exists
if [ -d "venv" ]; then
    echo "📦 Backing up current venv to venv_python314..."
    mv venv venv_python314
    echo "✅ Current venv backed up"
    echo ""
fi

# Create new venv with Python 3.13
echo "🔨 Creating new virtual environment with Python 3.13..."
python3.13 -m venv venv
echo "✅ Virtual environment created"
echo ""

# Activate venv
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip
echo "✅ Pip upgraded"
echo ""

# Install dependencies
echo "📥 Installing dependencies from requirements.txt..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Verify Chainlit installation
echo "🔍 Verifying Chainlit installation..."
if python -c "import chainlit; print(f'Chainlit version: {chainlit.__version__}')" 2>/dev/null; then
    echo "✅ Chainlit installed successfully"
else
    echo "❌ Chainlit installation failed"
    exit 1
fi
echo ""

# Test that app.py can be imported
echo "🧪 Testing app.py import..."
if python -c "import sys; sys.path.insert(0, '.'); import app; print('✅ app.py imports successfully')" 2>/dev/null; then
    echo "✅ app.py imports successfully"
else
    echo "⚠️  Warning: app.py import test failed (this might be okay)"
fi
echo ""

echo "🎉 Setup complete!"
echo ""
echo "To activate the new environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run Chainlit:"
echo "  chainlit run app.py -w"
echo ""
echo "Your old Python 3.14 venv is backed up as: venv_python314"

