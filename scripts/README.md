# Scripts Directory

This directory contains utility scripts for the AIOps Investigation Demo project.

## Available Scripts

### 🧹 `clean-up-test-data.sh`

Comprehensive cleanup script that removes all generated test sample data from the project.

**Usage:**
```bash
# Run from project root
./scripts/clean-up-test-data.sh
```

**What it cleans:**
- ✅ **Test sample files** - All `sample_run_*` files from test directories
- ✅ **Export summary files** - All `export_summary_*` files
- ✅ **Temporary files** - `.tmp`, `.temp`, `.DS_Store` files
- ⚠️ **Log files** - Optional cleanup with user confirmation

**Features:**
- 🎨 **Colored output** - Easy to read progress and results
- 📊 **File counting** - Shows how many files will be cleaned
- 🔍 **Smart discovery** - Automatically finds all test directories
- ⚠️ **Safe operation** - Confirms before cleaning logs
- 📋 **Detailed summary** - Shows what was cleaned

**Example output:**
```
🧹 AIOps Test Data Cleanup Script
===================================
Project root: /path/to/project

🔍 Scanning for test data files...

📁 Found 3 files in Alarm Analyzer samples:
   - sample_run_20250628_180001_000.txt
   - sample_run_20250628_175744_000.txt
   - sample_run_20250628_175620_000.txt
   ✅ Cleaned up 3 files

🎉 Cleanup completed!
```

**When to use:**
- Before committing code to avoid including test artifacts
- When test directories become cluttered
- To reset test environment for fresh runs
- During development cleanup

**Regenerating test data:**
After cleanup, regenerate test data with:
```bash
EXPORT_TEST_DATA=true python src/test/[node_name]/test.py
```

## Script Development Guidelines

When adding new scripts to this directory:

1. **Make scripts executable**: `chmod +x script-name.sh`
2. **Use descriptive names**: Clear purpose from filename
3. **Add help/usage info**: Include `--help` option
4. **Use colors for output**: Improve readability
5. **Handle errors gracefully**: Use `set -e` and proper error handling
6. **Document in this README**: Keep documentation updated

## Common Patterns

### Script Template
```bash
#!/bin/bash
set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}🔧 Script Name${NC}"
echo -e "${BLUE}==============${NC}"

# Script logic here...

echo -e "${GREEN}✅ Completed!${NC}"
```

### Error Handling
```bash
# Safe file operations
if [ -f "$file" ]; then
    rm "$file" 2>/dev/null || true
fi

# Safe directory operations  
if [ -d "$dir" ]; then
    find "$dir" -name "pattern" -delete 2>/dev/null || true
fi
```
