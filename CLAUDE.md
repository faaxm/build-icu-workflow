# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a GitHub Actions workflow for building ICU (International Components for Unicode) static library for Windows. The workflow is designed to create statically-linked ICU libraries using MSVC compiler in a Cygwin environment.

## Architecture

The project centers around a single GitHub Actions workflow (`.github/workflows/build-icu-windows.yml`) that:

1. **Downloads ICU 77.1 source** from the official Unicode GitHub repository
2. **Sets up a Windows build environment** with MSVC and Cygwin
3. **Configures ICU** for static-only builds with minimal components (no samples, tests, or extras)
4. **Builds and packages** the resulting static libraries and headers
5. **Uploads artifacts** for distribution

Key technical details:
- Uses Cygwin bash environment with MSVC toolchain for compilation
- Carefully manages PATH to prioritize MSVC linker over Cygwin's link utility
- Builds only static libraries (`.lib` files) to avoid DLL dependencies
- Supports x64 architecture with Release builds
- Caches ICU source downloads for faster subsequent builds

## Development Commands

### GitHub Actions Management
```bash
# Watch workflow runs
gh run watch

# View specific run details  
gh run view <run-id>

# List recent workflow runs
gh run list
```

### Manual Testing
The workflow can be triggered via:
- `workflow_dispatch` (manual trigger)
- Push to `master` or `main` branches affecting workflow files or scripts
- Pull requests to `master` or `main` branches

### Build Output
The workflow produces:
- Static libraries in `D:\icu-build\<arch>-<build_type>\lib\`
- Header files in `D:\icu-build\<arch>-<build_type>\include\`  
- Packaged artifacts as `icu-<arch>-<build_type>.zip`

## Configuration

The `.claude/settings.local.json` file contains permissions for:
- Fetching from unicode-org.github.io domain
- GitHub CLI operations for workflow monitoring
- Basic file system operations

## Build Matrix

Current build matrix targets:
- Architecture: x64
- Build Type: Release
- Compiler: MSVC (Visual Studio 2022)
- Environment: Cygwin on Windows

## ICU Configuration

The ICU build is configured with:
- `--enable-static` / `--disable-shared`: Static libraries only
- `--disable-samples --disable-tests --disable-extras`: Minimal build footprint
- MSVC runtime linking (`-MD` for Release)

## Git Commit Guidelines

**IMPORTANT**: When creating git commits, NEVER include Claude Code attribution or signatures. Commit messages should appear as if written by the repository owner. Do not include:
- "Generated with Claude Code"
- "Co-Authored-By: Claude"
- Any AI tool attribution
- References to automated generation

Use standard, professional commit messages that describe the actual changes made.

## Critical Build Environment Insights

**⚠️ IMPORTANT**: The ICU+Cygwin+MSVC build environment is extremely fragile. The current working configuration should be preserved exactly as-is. The following lessons were learned through extensive debugging:

### The GNU link vs Microsoft link.exe Conflict

The most critical issue in ICU+Cygwin+MSVC builds is the conflict between:
- **GNU link** (`/usr/bin/link`) - Cygwin's symbolic link utility
- **Microsoft link.exe** - MSVC linker required for ICU compilation

**Solution**: PATH must be carefully manipulated in each build step to ensure MSVC's `link.exe` is found before Cygwin's `link`. This is done via:
```bash
# Remove Cygwin's link from PATH to avoid conflict with MSVC link.exe
export PATH=$(echo "$PATH" | sed 's|/usr/bin:||g' | sed 's|:/usr/bin||g')
# Add /usr/bin back at the end (after MSVC tools)
export PATH="$PATH:/usr/bin"
```

### Why the Working Configuration Works

The current working configuration (`8cc99c0` and later) succeeds because:

1. **Cygwin Installation Location**: `D:\cygwin` (not `C:\cygwin`) - affects PATH resolution
2. **Matrix Strategy**: Even single-value matrices provide proper variable scoping
3. **Inline PATH Setup**: Environment setup in each step (not centralized script)
4. **Specific Shell Invocation**: `D:\cygwin\bin\bash.exe --login -o igncr {0}`
5. **Environment Variable Passing**: Explicit passing of `VCINSTALLDIR`, `WindowsSdkBinPath`, `PATH`

### Common Failure Patterns

1. **"link.exe is not a valid linker"**: GNU link vs Microsoft link.exe conflict
2. **"command not found"**: Line ending issues, use `-o igncr` flag
3. **PATH not found errors**: MSVC tools not properly prioritized in PATH
4. **Configuration script failures**: Environment variables not properly expanded

### Debugging Guidelines

When the build fails:
1. **First check**: Is `link.exe` being found correctly? Run `which link` and verify it's Microsoft's linker
2. **Second check**: Are MSVC tools in PATH? Verify `cl.exe` location
3. **Third check**: Are environment variables properly passed to Cygwin bash?
4. **Last resort**: Compare against the working commit `8cc99c0` line-by-line

### Build Performance

- **Typical build time**: 5-6 minutes for full ICU static library build
- **Cache effectiveness**: ICU source cache saves ~30 seconds on subsequent runs
- **Artifact size**: ~15-20MB for complete ICU x64 Release package

## Resources
**IMPORTANT**: Consult the following resources for examples and documentation. Do additional web searches whenever you are unsure and make sure you have as many sources as possible to back up your ideas/solutions/implementations.

- ICU Project workflow: https://raw.githubusercontent.com/unicode-org/icu/refs/heads/main/.github/workflows/icu4c.yml
- Build documentation: https://unicode-org.github.io/icu/userguide/icu4c/build.html
- Qt Docs: https://wiki.qt.io/Compiling-ICU-with-MSVC
- Qt Docs: https://wiki.qt.io/Compiling-ICU-with-MinGW