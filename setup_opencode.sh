#!/bin/bash
# OpenCode Setup Script for cribl-hc
# Configures environment to use Harbor/Ollama for AI assistance

echo "🤖 Setting up OpenCode for cribl-hc development..."
echo ""

# Set environment variables
export OPENCODE_CONFIG="$(pwd)/opencode.json"
export OPENCODE_PROVIDER="harbor-ollama"

echo "✅ Environment configured:"
echo "  OPENCODE_CONFIG=$OPENCODE_CONFIG"
echo "  OPENCODE_PROVIDER=$OPENCODE_PROVIDER"
echo ""

# Test the connection
echo "🧪 Testing Harbor/Ollama connection..."
python3 -c "
import asyncio
import httpx

async def test():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get('http://overlord:33821/api/tags')
            if response.status_code == 200:
                data = response.json()
                models = len(data.get('models', []))
                print(f'✅ Connection successful! {models} models available')
                return True
            else:
                print(f'❌ HTTP {response.status_code}')
                return False
    except Exception as e:
        print(f'❌ Connection failed: {e}')
        return False

result = asyncio.run(test())
if result:
    print('')
    print('🎉 OpenCode is ready for AI-assisted development!')
    print('You can now use AI delegation in your development workflow.')
else:
    print('')
    print('⚠️  Connection test failed. Check that Harbor is running on overlord.')
"

echo ""
echo "💡 To make this permanent, add these lines to your ~/.bashrc or ~/.zshrc:"
echo "  export OPENCODE_CONFIG=\"$(pwd)/opencode.json\""
echo "  export OPENCODE_PROVIDER=\"harbor-ollama\""