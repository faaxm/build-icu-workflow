#!/bin/bash
# Build environment setup for ICU Windows build with MSVC and Cygwin
# This script eliminates the repetitive PATH and environment setup

set -e

echo "=== Setting up ICU build environment ==="

# Configuration
ARCH="${1:-x64}"
BUILD_TYPE="${2:-Release}"

echo "Architecture: $ARCH"
echo "Build Type: $BUILD_TYPE" 

# Ensure MSVC tools are prioritized in PATH (they should already be there from msvc-dev-cmd action)
# Critical: Remove Cygwin's link from PATH to avoid conflict with MSVC link.exe
export PATH=$(echo "$PATH" | sed 's|/usr/bin:||g' | sed 's|:/usr/bin||g')
export PATH="$PATH:/usr/bin"

echo "Using PATH from MSVC environment setup"

# Set compiler flags based on build type
if [ "$BUILD_TYPE" = "Debug" ]; then
    export CPPFLAGS="-MDd"
    export CFLAGS="-MDd"
    export CXXFLAGS="-MDd /std:c++17"
else
    export CPPFLAGS="-MD"
    export CFLAGS="-MD" 
    export CXXFLAGS="-MD /std:c++17"
fi

# Verify critical tools are available
echo "=== Tool verification ==="
if which cl >/dev/null 2>&1; then
    echo "cl.exe found: $(which cl)"
else
    echo "cl.exe NOT FOUND"
    exit 1
fi

if which link >/dev/null 2>&1; then
    echo "link.exe found: $(which link)"
    # Verify it's Microsoft linker, not Cygwin's
    if link /? 2>&1 | grep -q "Microsoft"; then
        echo "Confirmed Microsoft linker"
    else
        echo "Wrong linker detected - should be Microsoft link.exe"
        exit 1
    fi
else
    echo "link.exe NOT FOUND"
    exit 1
fi

echo "=== Build environment ready ==="