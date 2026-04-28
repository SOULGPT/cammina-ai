#!/bin/bash

# Cammina AI Installation Script
set -e

echo "
 ██████╗ █████╗ ███╗   ███╗███╗   ███╗██╗███╗   ██╗ █████╗ 
██╔════╝██╔══██╗████╗ ████║████╗ ████║██║████╗  ██║██╔══██╗
██║     ███████║██╔████╔██║██╔████╔██║██║██╔██╗ ██║███████║
██║     ██╔══██║██║╚██╔╝██║██║╚██╔╝██║██║██║╚██╗██║██╔══██║
╚██████╗██║  ██║██║ ╚═╝ ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║
 ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝
         AI - Your Autonomous Development Assistant
"

echo "🔍 Checking requirements..."

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ from https://python.org"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION found"

# 2. Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ from https://nodejs.org"
    exit 1
fi
NODE_VERSION=$(node -v | cut -d'v' -f2)
echo "✅ Node.js $NODE_VERSION found"

# 3. Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed."
    exit 1
fi
echo "✅ npm found"

# 4. Check git
if ! command -v git &> /dev/null; then
    echo "❌ git is not installed."
    exit 1
fi
echo "✅ git found"

echo "📦 Creating virtual environments and installing dependencies..."

# Local Agent
echo "🔧 Setting up Local Agent..."
cd services/local_agent
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
cd ../..

# LLM Manager
echo "🔧 Setting up LLM Manager..."
cd services/llm_manager
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
cd ../..

# Memory
echo "🔧 Setting up Memory Service..."
cd services/memory
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
cd ../..

# Orchestrator
echo "🔧 Setting up Orchestrator..."
cd services/orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
cd ../..

# Web UI
echo "🌐 Installing Web UI dependencies (this may take a minute)..."
cd apps/web
npm install
cd ../..

echo "🗄️ Initializing database..."
mkdir -p database
if [ -f "database/init_db.py" ]; then
    python3 database/init_db.py
fi

echo "📁 Creating directory structure..."
mkdir -p logs/projects
mkdir -p logs/errors
mkdir -p logs/agent_actions
mkdir -p logs/system
mkdir -p database/chroma_data

echo "🔐 Setting up environment..."
if [ ! -f .env.local ]; then
  if [ -f .env.example ]; then
    cp .env.example .env.local
    echo "✅ Created .env.local from example."
  else
    echo "⚠️ .env.example not found. Creating blank .env.local"
    touch .env.local
  fi
fi

# Ensure LOCAL_AGENT_SECRET is set
if ! grep -q "LOCAL_AGENT_SECRET=.." .env.local; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  if grep -q "LOCAL_AGENT_SECRET=" .env.local; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s/LOCAL_AGENT_SECRET=.*/LOCAL_AGENT_SECRET=$SECRET/" .env.local
    else
      sed -i "s/LOCAL_AGENT_SECRET=.*/LOCAL_AGENT_SECRET=$SECRET/" .env.local
    fi
  else
    echo "LOCAL_AGENT_SECRET=$SECRET" >> .env.local
  fi
  echo "✅ Generated secure LOCAL_AGENT_SECRET in .env.local"
fi

echo "🚀 Making scripts executable..."
chmod +x cammina
if [ -f "scripts/cammina.sh" ]; then
    chmod +x scripts/cammina.sh
fi

echo ""
echo "✅ Cammina AI installed successfully!"
echo ""
echo "Next steps:"
echo "1. Add your free API keys to .env.local:"
echo "   - OpenRouter: https://openrouter.ai/keys (free)"
echo "   - Nvidia NIM: https://build.nvidia.com (free)"  
echo "   - Groq: https://console.groq.com (free)"
echo ""
echo "2. Start Cammina AI:"
echo "   ./cammina start"
echo ""
echo "3. Open browser:"
echo "   http://localhost:3000"
echo ""
echo "Need help? Visit: https://github.com/SOULGPT/cammina-ai"
