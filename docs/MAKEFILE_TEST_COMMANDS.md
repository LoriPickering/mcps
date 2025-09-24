# Makefile Test Commands Documentation

## ✅ Test Commands Reorganized

The Makefile now has properly organized test commands that separate code tests from MCP server tests.

## 📋 Available Test Commands

### `make test`
**Purpose**: Run code-based unit tests only
- Tests indicator calculations
- Tests integration logic
- Does NOT test MCP server endpoints
- **Files tested**:
  - `tests/test_indicators.py`
  - `tests/test_integration.py`

### `make test-mcp`
**Purpose**: Run MCP server tests only
- Tests MCP server endpoints
- Tests DARPA integration
- Tests server initialization
- **Files tested**:
  - `tests/test_mcp_server.py`
  - `tests/integration/test_mcp_darpa_integration.py`

### `make test-all`
**Purpose**: Run ALL tests (comprehensive)
- Runs the complete test suite
- Includes unit tests, MCP tests, and integration tests
- Checks files and directories
- Uses `scripts/test_all_mcp.sh` if available
- **Coverage**: Everything

### `make test-quick`
**Purpose**: Quick health check (4 critical tests)
- Market status check
- Watchlist verification
- DARPA events check
- Capabilities test
- **Time**: ~2 seconds
- **Perfect for**: Quick validation before commits

### `make test-summary`
**Purpose**: Display test suite information
- Shows all available test commands
- Lists test file locations
- Provides guidance on which test to run

## 🎯 Usage Examples

### Quick validation before commit:
```bash
make test-quick
# Result: 4/4 tests passed
```

### Test only MCP server functionality:
```bash
make test-mcp
# Runs 18 MCP-specific tests
```

### Test only code logic (no server tests):
```bash
make test
# Runs 15 unit tests
```

### Full comprehensive testing:
```bash
make test-all
# Runs everything - unit, MCP, integration, health checks
```

## 🏗️ Test Organization

```
tests/
├── Unit Tests (make test)
│   ├── test_indicators.py      # Indicator calculations
│   └── test_integration.py     # Integration logic
│
├── MCP Tests (make test-mcp)
│   ├── test_mcp_server.py      # MCP server endpoints
│   └── integration/
│       └── test_mcp_darpa_integration.py
│
├── Comprehensive (make test-all)
│   ├── All unit tests
│   ├── All MCP tests
│   ├── All integration tests
│   └── Health checks
│
└── Quick Check (make test-quick)
    └── 4 critical health checks

scripts/
├── test_mcp_health.py    # Health check tool
└── test_all_mcp.sh      # Master test runner
```

## ⚡ Performance

| Command | Tests Run | Time | Use Case |
|---------|-----------|------|----------|
| `make test-quick` | 4 | ~2s | Pre-commit check |
| `make test` | 15 | ~5s | Code logic validation |
| `make test-mcp` | 18 | ~10s | MCP server validation |
| `make test-all` | 50+ | ~30s | Full validation |

## 🔧 Behind the Scenes

The Makefile commands now:
1. Set `PYTHONPATH` correctly for imports
2. Use `--tb=short` for concise error output
3. Suppress unnecessary warnings with `2>/dev/null` where appropriate
4. Provide clear section headers for output

## ✅ Summary

You now have:
- **`make test`** - Code tests only (no MCP)
- **`make test-mcp`** - MCP server tests only
- **`make test-all`** - Everything
- **`make test-quick`** - 4 critical tests in 2 seconds

This separation allows you to:
- Test code changes without server overhead
- Test MCP changes without running unit tests
- Do quick health checks before commits
- Run comprehensive tests when needed