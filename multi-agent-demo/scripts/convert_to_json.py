#!/usr/bin/env python3
import json
import sys

if len(sys.argv) != 2:
    print("Usage: python convert_to_json.py <file_path>")
    sys.exit(1)

with open(sys.argv[1], 'r') as f:
    content = f.read()

print(json.dumps({"alarm": content}))
