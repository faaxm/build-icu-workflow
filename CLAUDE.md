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