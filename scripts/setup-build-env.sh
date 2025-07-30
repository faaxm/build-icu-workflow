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

# Fix the classic link.exe vs GNU link conflict for ICU configure script
# The MSVC dev environment should have already set up the PATH correctly,
# but we need to ensure Cygwin's link doesn't interfere with Microsoft's link.exe

# Save the original PATH that includes MSVC tools at the front
ORIGINAL_PATH="$PATH"

# Remove ALL instances of /usr/bin from PATH (including middle and end positions)  
export PATH=$(echo "$PATH" | sed 's|/usr/bin:||g' | sed 's|:/usr/bin||g' | sed 's|/usr/bin$||g')

# Add back essential Cygwin tools at the end, but exclude /usr/bin to avoid link conflict
# We need make, bash, and other build tools, but not the GNU link command
export PATH="$PATH:/usr/local/bin"

# Add essential tools back but create a workaround for the link conflict
# ICU's configure script needs various Unix tools from /usr/bin
export PATH="$PATH:/usr/bin"

# Create a temporary override for link to ensure Microsoft's linker is used
# We'll create a temporary directory with a link symlink to the Microsoft linker
TEMP_BIN_DIR="/tmp/msvc-override"
mkdir -p "$TEMP_BIN_DIR"
ln -sf "/cygdrive/c/Program Files/Microsoft Visual Studio/2022/Enterprise/VC/Tools/MSVC/14.44.35207/bin/HostX64/x64/link.exe" "$TEMP_BIN_DIR/link"
export PATH="$TEMP_BIN_DIR:$PATH"

echo "Created temporary link override at $TEMP_BIN_DIR/link"

echo "PATH configured for ICU build (avoiding GNU link conflict)"
echo "MSVC tools prioritized, Cygwin link excluded"

# Verify the correct link.exe is first in PATH
if which link >/dev/null 2>&1; then
    LINK_PATH=$(which link)
    echo "Using linker: $LINK_PATH"
else
    echo "ERROR: No link.exe found in PATH"
    exit 1
fi

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