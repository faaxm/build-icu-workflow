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

# Set up MSVC environment in PATH
if [ -n "$VCINSTALLDIR" ]; then
    VCINSTALLDIR_UNIX=$(cygpath -u "$VCINSTALLDIR")
    MSVC_BIN_PATH=$(find "${VCINSTALLDIR_UNIX}Tools/MSVC" -maxdepth 2 -path "*/bin/Host${ARCH}" -type d | head -1)/${ARCH}
    
    if [ -d "$MSVC_BIN_PATH" ]; then
        export PATH="$MSVC_BIN_PATH:$PATH"
        echo "Added MSVC tools to PATH: $MSVC_BIN_PATH"
    else
        echo "Warning: MSVC bin path not found: $MSVC_BIN_PATH"
    fi
else
    echo "Warning: VCINSTALLDIR not set"
fi

# Add Windows SDK tools to PATH
if [ -n "$WindowsSdkBinPath" ]; then
    SDK_BIN_PATH=$(cygpath -u "$WindowsSdkBinPath")
    if [ -d "$SDK_BIN_PATH" ]; then
        export PATH="$SDK_BIN_PATH:$PATH"
        echo "Added Windows SDK tools to PATH: $SDK_BIN_PATH"
    fi
fi

# Critical: Remove Cygwin's link from PATH to avoid conflict with MSVC link.exe
# Keep all other Cygwin tools but ensure MSVC linker takes precedence
export PATH=$(echo "$PATH" | sed 's|/usr/bin:||g' | sed 's|:/usr/bin||g')
export PATH="$PATH:/usr/bin"

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