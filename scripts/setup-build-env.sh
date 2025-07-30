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

# Use the original working PATH setup approach
# The working version (8cc99c0) had MSVC tools properly prioritized

# Ensure MSVC tools are in PATH before Cygwin tools  
if [ -n "$VCINSTALLDIR" ]; then
    # Convert Windows path to Cygwin path and expand wildcard
    VCINSTALLDIR_UNIX=$(cygpath -u "$VCINSTALLDIR")
    MSVC_BIN_PATH=$(find "${VCINSTALLDIR_UNIX}Tools/MSVC" -maxdepth 1 -type d -name "*" | head -1)/bin/Host${ARCH}/${ARCH}
    
    if [ -d "$MSVC_BIN_PATH" ]; then
        export PATH="$MSVC_BIN_PATH:$PATH"
        echo "Added MSVC tools to PATH: $MSVC_BIN_PATH"
    else
        echo "Warning: MSVC bin path not found: $MSVC_BIN_PATH"
    fi
fi

# Add Windows SDK tools to PATH
if [ -n "$WindowsSdkBinPath" ]; then
    SDK_BIN_PATH=$(cygpath -u "$WindowsSdkBinPath")
    if [ -d "$SDK_BIN_PATH" ]; then
        export PATH="$SDK_BIN_PATH:$PATH"
        echo "Added Windows SDK tools to PATH: $SDK_BIN_PATH"
    fi
fi

# Remove Cygwin's link from PATH to avoid conflict with MSVC link.exe
export PATH=$(echo "$PATH" | sed 's|/usr/bin:||g' | sed 's|:/usr/bin||g')
# Add /usr/bin back at the end (after MSVC tools)
export PATH="$PATH:/usr/bin"

echo "PATH configured using working approach from 8cc99c0"

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