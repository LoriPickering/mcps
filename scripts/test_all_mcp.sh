#!/bin/bash
#
# Master test script for all MCP server functionality
# Run this to verify everything is working correctly
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🧪 MCP SERVER COMPLETE TEST SUITE${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Track overall status
OVERALL_STATUS=0

# Function to run a test and report results
run_test() {
    local test_name=$1
    local test_command=$2

    echo -e "${YELLOW}Running: ${test_name}${NC}"
    echo "----------------------------------------"

    if eval $test_command; then
        echo -e "${GREEN}✅ ${test_name} PASSED${NC}\n"
    else
        echo -e "${RED}❌ ${test_name} FAILED${NC}\n"
        OVERALL_STATUS=1
    fi
}

# Test 1: Quick Health Check
run_test "Quick Health Check" ".venv/bin/python scripts/test_mcp_health.py --quick 2>/dev/null"

# Test 2: Comprehensive Unit Tests
run_test "Unit Tests" ".venv/bin/python -m pytest tests/test_indicators.py -q 2>/dev/null"

# Test 3: MCP Server Tests
run_test "MCP Server Tests" ".venv/bin/python -m pytest tests/test_mcp_server.py -q 2>/dev/null"

# Test 4: DARPA Integration
run_test "DARPA Integration" ".venv/bin/python -m pytest tests/integration/test_mcp_darpa_integration.py::test_mcp_tools -q 2>/dev/null"

# Test 5: News Integration
run_test "News Integration" ".venv/bin/python -m pytest tests/test_news_integration.py -q 2>/dev/null"

# Test 6: Comprehensive MCP Tests
run_test "Comprehensive MCP Tests" ".venv/bin/python -m pytest tests/test_mcp_comprehensive.py -q 2>/dev/null"

# Test 7: Check Critical Files
echo -e "${YELLOW}Checking Critical Files${NC}"
echo "----------------------------------------"
CRITICAL_FILES=(
    "servers/trading/mcp_server_integrated.py"
    "servers/trading/darpa_events_monitor.py"
    "servers/trading/macro_events_tracker.py"
    "servers/trading/news_collector.py"
    "watchlist.txt"
    ".env"
)

FILES_OK=true
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file missing!"
        FILES_OK=false
        OVERALL_STATUS=1
    fi
done

if $FILES_OK; then
    echo -e "${GREEN}✅ All critical files present${NC}\n"
else
    echo -e "${RED}❌ Some critical files missing${NC}\n"
fi

# Test 8: Check Data Directories
echo -e "${YELLOW}Checking Data Directories${NC}"
echo "----------------------------------------"
DATA_DIRS=(
    "data/stocks"
    "data/crypto"
    "data/events"
    "data/news"
    "data/darpa_events"
)

DIRS_OK=true
for dir in "${DATA_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $dir"
    else
        echo -e "  ${RED}✗${NC} $dir missing!"
        DIRS_OK=false
        OVERALL_STATUS=1
    fi
done

if $DIRS_OK; then
    echo -e "${GREEN}✅ All data directories present${NC}\n"
else
    echo -e "${RED}❌ Some data directories missing${NC}\n"
fi

# Final Summary
echo -e "${BLUE}================================================${NC}"
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}MCP Server is fully operational and ready to use${NC}"
else
    echo -e "${RED}⚠️  SOME TESTS FAILED${NC}"
    echo -e "${YELLOW}Please check the errors above and fix any issues${NC}"
fi
echo -e "${BLUE}================================================${NC}"

exit $OVERALL_STATUS