#!/bin/bash
#
# Demonstration of cribl-hc CLI capabilities
#
# This script shows all the ways to use the CLI

set -e

echo "======================================================================"
echo "CRIBL-HC CLI DEMONSTRATION"
echo "======================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Show version
echo -e "${BLUE}1. Version Information${NC}"
echo "----------------------------------------------------------------------"
cribl-hc version
echo ""

# 2. Show help
echo -e "${BLUE}2. Main Help${NC}"
echo "----------------------------------------------------------------------"
cribl-hc --help
echo ""

# 3. Show analyze help
echo -e "${BLUE}3. Analyze Command Help${NC}"
echo "----------------------------------------------------------------------"
cribl-hc analyze run --help
echo ""

# 4. List available analyzers
echo -e "${BLUE}4. Available Analyzers${NC}"
echo "----------------------------------------------------------------------"
python3 -c "
from cribl_hc.analyzers import list_objectives, get_analyzer

objectives = list_objectives()
print(f'Registered analyzers: {len(objectives)}')
print()

for obj in objectives:
    analyzer = get_analyzer(obj)
    perms = ', '.join(analyzer.get_required_permissions())
    print(f'  • {obj}')
    print(f'    Estimated API calls: {analyzer.get_estimated_api_calls()}')
    print(f'    Permissions: {perms}')
    print()
"
echo ""

# 5. Test with environment variables (if set)
if [ -n "$CRIBL_URL" ] && [ -n "$CRIBL_TOKEN" ]; then
    echo -e "${BLUE}5. Running Analysis (using environment variables)${NC}"
    echo "----------------------------------------------------------------------"
    echo "URL: $CRIBL_URL"
    echo "Running health analyzer..."
    echo ""

    cribl-hc analyze run \
        --objective health \
        --verbose

    echo ""
    echo -e "${GREEN}✓ Health analysis completed${NC}"
    echo ""

    # Run config analyzer
    echo "Running config analyzer..."
    cribl-hc analyze run \
        --objective config \
        --verbose

    echo ""
    echo -e "${GREEN}✓ Config analysis completed${NC}"
    echo ""

    # Run resource analyzer
    echo "Running resource analyzer..."
    cribl-hc analyze run \
        --objective resource \
        --verbose

    echo ""
    echo -e "${GREEN}✓ Resource analysis completed${NC}"
    echo ""

    # Run all analyzers
    echo -e "${BLUE}6. Running ALL Analyzers${NC}"
    echo "----------------------------------------------------------------------"
    cribl-hc analyze run --verbose

    echo ""
    echo -e "${GREEN}✓ All analyzers completed${NC}"
    echo ""

    # Test JSON output
    echo -e "${BLUE}7. Generating JSON Report${NC}"
    echo "----------------------------------------------------------------------"
    cribl-hc analyze run \
        --objective health \
        --output /tmp/cribl-hc-report.json

    if [ -f /tmp/cribl-hc-report.json ]; then
        echo -e "${GREEN}✓ JSON report generated: /tmp/cribl-hc-report.json${NC}"
        echo "File size: $(wc -c < /tmp/cribl-hc-report.json) bytes"
        echo ""
        echo "Sample output:"
        head -20 /tmp/cribl-hc-report.json
        echo "..."
    fi
    echo ""

else
    echo -e "${BLUE}5. Skipping Live Tests${NC}"
    echo "----------------------------------------------------------------------"
    echo "Set CRIBL_URL and CRIBL_TOKEN environment variables to run live tests"
    echo ""
    echo "Example:"
    echo "  export CRIBL_URL=https://your-cribl.cloud"
    echo "  export CRIBL_TOKEN=your_bearer_token"
    echo "  ./scripts/demo_cli.sh"
    echo ""
fi

echo "======================================================================"
echo "CLI DEMONSTRATION COMPLETE"
echo "======================================================================"
echo ""
echo "Available commands:"
echo "  • cribl-hc version                    - Show version"
echo "  • cribl-hc analyze run                - Run all analyzers"
echo "  • cribl-hc analyze run -o health      - Run specific analyzer"
echo "  • cribl-hc analyze run --output file  - Save results to file"
echo "  • cribl-hc test-connection            - Test API connection"
echo "  • cribl-hc config set                 - Store credentials"
echo ""
