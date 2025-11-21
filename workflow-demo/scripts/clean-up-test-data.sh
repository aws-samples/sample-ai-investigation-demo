#!/bin/bash

# Clean up test data script
# This script removes all generated test sample data from the project

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}🧹 AIOps Test Data Cleanup Script${NC}"
echo -e "${BLUE}===================================${NC}"
echo -e "Project root: ${PROJECT_ROOT}"
echo ""

# Function to safely remove files with confirmation
cleanup_directory() {
    local dir_path="$1"
    local description="$2"
    
    if [ -d "$dir_path" ]; then
        local file_count=$(find "$dir_path" -name "sample_run_*" -type f 2>/dev/null | wc -l)
        local summary_count=$(find "$dir_path" -name "export_summary_*" -type f 2>/dev/null | wc -l)
        local total_count=$((file_count + summary_count))
        
        if [ $total_count -gt 0 ]; then
            echo -e "${YELLOW}📁 Found $total_count files in $description:${NC}"
            find "$dir_path" -name "sample_run_*" -o -name "export_summary_*" | head -10 | while read file; do
                echo "   - $(basename "$file")"
            done
            if [ $total_count -gt 10 ]; then
                echo "   ... and $((total_count - 10)) more files"
            fi
            
            # Remove the files
            find "$dir_path" -name "sample_run_*" -type f -delete 2>/dev/null || true
            find "$dir_path" -name "export_summary_*" -type f -delete 2>/dev/null || true
            
            echo -e "${GREEN}   ✅ Cleaned up $total_count files${NC}"
        else
            echo -e "${GREEN}📁 $description: No test files to clean${NC}"
        fi
    else
        echo -e "${YELLOW}📁 $description: Directory not found${NC}"
    fi
    echo ""
}

# Function to clean up log files
cleanup_logs() {
    local logs_dir="$PROJECT_ROOT/logs"
    
    if [ -d "$logs_dir" ]; then
        local log_count=$(find "$logs_dir" -name "*.log" -type f 2>/dev/null | wc -l)
        
        if [ $log_count -gt 0 ]; then
            echo -e "${YELLOW}📋 Found $log_count log files:${NC}"
            find "$logs_dir" -name "*.log" | head -5 | while read file; do
                echo "   - $(basename "$file")"
            done
            if [ $log_count -gt 5 ]; then
                echo "   ... and $((log_count - 5)) more log files"
            fi
            
            read -p "$(echo -e ${YELLOW}Do you want to clean up log files too? [y/N]: ${NC})" -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                find "$logs_dir" -name "*.log" -type f -delete 2>/dev/null || true
                echo -e "${GREEN}   ✅ Cleaned up $log_count log files${NC}"
            else
                echo -e "${BLUE}   ℹ️  Log files kept${NC}"
            fi
        else
            echo -e "${GREEN}📋 Logs: No log files to clean${NC}"
        fi
    else
        echo -e "${YELLOW}📋 Logs: Directory not found${NC}"
    fi
    echo ""
}

# Main cleanup process
echo -e "${BLUE}🔍 Scanning for test data files...${NC}"
echo ""

# Clean up test sample directories
cleanup_directory "$PROJECT_ROOT/src/test/alarm_analyzer/samples" "Alarm Analyzer samples"
cleanup_directory "$PROJECT_ROOT/src/test/logs_collector/samples" "Logs Collector samples"
cleanup_directory "$PROJECT_ROOT/src/test/cloudtrail_collector/samples" "CloudTrail Collector samples"
cleanup_directory "$PROJECT_ROOT/src/test/trace_graph_analyzer/samples" "Trace Graph Analyzer samples"
cleanup_directory "$PROJECT_ROOT/src/test/trace_details_analyzer/samples" "Trace Details Analyzer samples"
cleanup_directory "$PROJECT_ROOT/src/test/trace_resource_collector/samples" "Trace Resource Collector samples"
cleanup_directory "$PROJECT_ROOT/src/test/root_cause_analysis/samples" "Root Cause Analysis samples"

# Look for any other test directories
echo -e "${BLUE}🔍 Scanning for other test directories...${NC}"
other_test_dirs=$(find "$PROJECT_ROOT/src/test" -name "samples" -type d 2>/dev/null | grep -v -E "(alarm_analyzer|logs_collector|cloudtrail_collector|trace_graph_analyzer|trace_details_analyzer|trace_resource_collector|root_cause_analysis)" || true)

if [ -n "$other_test_dirs" ]; then
    echo -e "${YELLOW}📁 Found additional test directories:${NC}"
    echo "$other_test_dirs" | while read dir; do
        parent_dir=$(basename "$(dirname "$dir")")
        cleanup_directory "$dir" "$parent_dir samples"
    done
else
    echo -e "${GREEN}📁 No additional test directories found${NC}"
    echo ""
fi

# Clean up export summary files in root test directory
cleanup_directory "$PROJECT_ROOT/src/test" "Test root export summaries"

# Offer to clean up logs
cleanup_logs

# Clean up any temporary files
echo -e "${BLUE}🔍 Scanning for temporary files...${NC}"
temp_files=$(find "$PROJECT_ROOT" -name "*.tmp" -o -name "*.temp" -o -name ".DS_Store" 2>/dev/null | wc -l)
if [ $temp_files -gt 0 ]; then
    echo -e "${YELLOW}🗑️  Found $temp_files temporary files${NC}"
    find "$PROJECT_ROOT" -name "*.tmp" -o -name "*.temp" -o -name ".DS_Store" -delete 2>/dev/null || true
    echo -e "${GREEN}   ✅ Cleaned up temporary files${NC}"
else
    echo -e "${GREEN}🗑️  No temporary files to clean${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}🎉 Cleanup completed!${NC}"
echo -e "${BLUE}===================================${NC}"
echo -e "${GREEN}✅ All test sample data has been cleaned up${NC}"
echo -e "${GREEN}✅ Export summary files removed${NC}"
echo -e "${GREEN}✅ Temporary files cleaned${NC}"
echo ""
echo -e "${BLUE}💡 To generate new test data, run your tests with:${NC}"
echo -e "${BLUE}   EXPORT_TEST_DATA=true python src/test/[node_name]/test.py${NC}"
echo ""
