#!/bin/bash

# Download nlohmann/json header
# This script downloads the single-header JSON library

set -e

echo "Downloading nlohmann/json..."

mkdir -p third_party

curl -L https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp \
    -o third_party/json.hpp

echo "✓ Downloaded nlohmann/json to third_party/json.hpp"
