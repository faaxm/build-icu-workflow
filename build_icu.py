#!/usr/bin/env python3
"""
ICU Build Script for Windows with MSVC
Builds ICU static libraries with optional embedded data.
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library not found. Please install it with: pip install requests")
    sys.exit(1)


@dataclass
class BuildConfig:
    """Configuration for ICU build."""
    arch: str = "x64"
    build_type: str = "Release"
    embed_data: bool = False
    icu_version: str = "77.1"
    icu_tag: str = "release-77-1"
    
    @property
    def lib_prefix(self) -> str:
        """Get library prefix (s for static data, empty for separate data)."""
        return "s" if self.embed_data else ""
    
    @property
    def artifact_suffix(self) -> str:
        """Get artifact name suffix."""
        return "static-data" if self.embed_data else "separate-data"


class ICUBuilder:
    """Builds ICU static libraries for Windows using MSVC."""
    
    def __init__(self, config: BuildConfig):
        self.config = config
        self.workspace = Path.cwd()
        self.source_dir = self.workspace / f"icu-release-{config.icu_tag}" / "icu4c" / "source"
        self.build_dir = Path("D:/icu-build") / f"{config.arch}-{config.build_type}"
        self.cygwin_path = Path("D:/cygwin")
        
    def download_icu_source(self) -> bool:
        """Download and extract ICU source if not already present."""
        print("🔍 Checking for ICU source...")
        
        # Check if source already exists
        if self.source_dir.exists():
            print(f"✅ ICU source already available at: {self.source_dir}")
            return True
            
        # Download ICU source
        source_zip = self.workspace / "icu-source.zip"
        if not source_zip.exists():
            print(f"📥 Downloading ICU {self.config.icu_version} source...")
            url = f"https://github.com/unicode-org/icu/archive/refs/tags/{self.config.icu_tag}.zip"
            
            try:
                response = requests.get(url, stream=True, timeout=300)
                response.raise_for_status()
                
                with open(source_zip, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                print(f"✅ Downloaded: {source_zip}")
            except Exception as e:
                print(f"❌ Failed to download ICU source: {e}")
                return False
        
        # Extract source
        print("📦 Extracting ICU source...")
        try:
            with zipfile.ZipFile(source_zip, 'r') as zip_ref:
                zip_ref.extractall(self.workspace)
            print(f"✅ Extracted to: {self.source_dir}")
            return True
        except Exception as e:
            print(f"❌ Failed to extract ICU source: {e}")
            return False
    
    def prepare_source(self) -> bool:
        """Prepare ICU source for Windows build."""
        print("🔧 Preparing ICU source for Windows build...")
        
        try:
            # Convert line endings and set permissions using Cygwin
            cmd = [
                str(self.cygwin_path / "bin" / "bash.exe"), "--login", "-o", "igncr", "-c",
                f'''
                cd "{self.source_dir}"
                find . -name "*.sh" -o -name "*.ac" -o -name "*.in" | xargs dos2unix 2>/dev/null || true
                chmod +x runConfigureICU configure install-sh 2>/dev/null || true
                echo "Source preparation completed"
                '''
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.workspace)
            if result.returncode != 0:
                print(f"❌ Source preparation failed: {result.stderr}")
                return False
                
            print("✅ ICU source prepared successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to prepare source: {e}")
            return False
    
    def get_msvc_env(self) -> dict:
        """Get MSVC environment variables."""
        env = os.environ.copy()
        
        # Key MSVC environment variables should be set by GitHub Actions
        required_vars = ['VCINSTALLDIR', 'WindowsSdkBinPath', 'PATH']
        for var in required_vars:
            if var not in env:
                print(f"⚠️  Warning: {var} not found in environment")
        
        return env
    
    def configure_build(self) -> bool:
        """Configure ICU build using Cygwin configure script."""
        print(f"⚙️  Configuring ICU build ({self.config.arch} {self.config.build_type})...")
        
        # Build configure command
        configure_args = [
            "Cygwin/MSVC",
            "--enable-static",
            "--disable-shared", 
            "--disable-samples",
            "--disable-tests",
            "--disable-extras",
            f"--prefix={self.build_dir.as_posix()}"
        ]
        
        if self.config.embed_data:
            configure_args.append("--with-data-packaging=static")
            print("📦 Using static data packaging (embedded data)")
        else:
            print("📦 Using separate data packaging (.dat file)")
        
        # Setup environment for MSVC + Cygwin
        env = self.get_msvc_env()
        
        # Configure build script
        configure_script = f'''
        cd "{self.source_dir}"
        
        # Setup MSVC environment
        if [ -n "$VCINSTALLDIR" ]; then
            VCINSTALLDIR_UNIX=$(cygpath -u "$VCINSTALLDIR")
            MSVC_BIN_PATH=$(find "${{VCINSTALLDIR_UNIX}}Tools/MSVC" -maxdepth 1 -type d -name "*" | head -1)/bin/Host{self.config.arch}/{self.config.arch}
            if [ -d "$MSVC_BIN_PATH" ]; then
                export PATH="$MSVC_BIN_PATH:$PATH"
                echo "✅ Added MSVC tools to PATH: $MSVC_BIN_PATH"
            fi
        fi
        
        # Add Windows SDK tools
        if [ -n "$WindowsSdkBinPath" ]; then
            SDK_BIN_PATH=$(cygpath -u "$WindowsSdkBinPath")
            if [ -d "$SDK_BIN_PATH" ]; then
                export PATH="$SDK_BIN_PATH:$PATH"
                echo "✅ Added Windows SDK tools to PATH"
            fi
        fi
        
        # Remove Cygwin's link to avoid conflict with MSVC link.exe
        export PATH=$(echo "$PATH" | sed 's|/usr/bin:||g' | sed 's|:/usr/bin||g')
        export PATH="$PATH:/usr/bin"
        
        # Verify tools
        echo "🔍 Checking build tools..."
        echo "cl.exe: $(which cl 2>/dev/null || echo 'NOT FOUND')"
        echo "link.exe: $(which link 2>/dev/null || echo 'NOT FOUND')"
        
        # Set compiler flags
        export CPPFLAGS="-MD"
        export CFLAGS="-MD"
        export CXXFLAGS="-MD /std:c++17"
        
        # Run configure
        echo "🚀 Running configure..."
        ./runConfigureICU {' '.join(configure_args)}
        '''
        
        try:
            cmd = [str(self.cygwin_path / "bin" / "bash.exe"), "--login", "-o", "igncr", "-c", configure_script]
            result = subprocess.run(cmd, env=env, cwd=self.workspace, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Configure failed: {result.stderr}")
                print(f"stdout: {result.stdout}")
                return False
                
            print("✅ Configure completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Configure failed: {e}")
            return False
    
    def build_icu(self) -> bool:
        """Build ICU libraries."""
        print("🔨 Building ICU libraries...")
        
        # Build script
        build_script = f'''
        cd "{self.source_dir}"
        
        # Setup MSVC environment (same as configure)
        if [ -n "$VCINSTALLDIR" ]; then
            VCINSTALLDIR_UNIX=$(cygpath -u "$VCINSTALLDIR")
            MSVC_BIN_PATH=$(find "${{VCINSTALLDIR_UNIX}}Tools/MSVC" -maxdepth 1 -type d -name "*" | head -1)/bin/Host{self.config.arch}/{self.config.arch}
            if [ -d "$MSVC_BIN_PATH" ]; then
                export PATH="$MSVC_BIN_PATH:$PATH"
            fi
        fi
        
        if [ -n "$WindowsSdkBinPath" ]; then
            SDK_BIN_PATH=$(cygpath -u "$WindowsSdkBinPath")
            if [ -d "$SDK_BIN_PATH" ]; then
                export PATH="$SDK_BIN_PATH:$PATH"
            fi
        fi
        
        export PATH=$(echo "$PATH" | sed 's|/usr/bin:||g' | sed 's|:/usr/bin||g')
        export PATH="$PATH:/usr/bin"
        
        # Build
        echo "🔨 Starting build..."
        make -j$(nproc)
        '''
        
        try:
            env = self.get_msvc_env()
            cmd = [str(self.cygwin_path / "bin" / "bash.exe"), "--login", "-o", "igncr", "-c", build_script]
            result = subprocess.run(cmd, env=env, cwd=self.workspace)
            
            if result.returncode != 0:
                print("❌ Build failed")
                return False
                
            print("✅ Build completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False
    
    def install_icu(self) -> bool:
        """Install ICU to the build directory."""
        print("📦 Installing ICU...")
        
        install_script = f'''
        cd "{self.source_dir}"
        
        # Setup MSVC environment
        if [ -n "$VCINSTALLDIR" ]; then
            VCINSTALLDIR_UNIX=$(cygpath -u "$VCINSTALLDIR")
            MSVC_BIN_PATH=$(find "${{VCINSTALLDIR_UNIX}}Tools/MSVC" -maxdepth 1 -type d -name "*" | head -1)/bin/Host{self.config.arch}/{self.config.arch}
            if [ -d "$MSVC_BIN_PATH" ]; then
                export PATH="$MSVC_BIN_PATH:$PATH"
            fi
        fi
        
        if [ -n "$WindowsSdkBinPath" ]; then
            SDK_BIN_PATH=$(cygpath -u "$WindowsSdkBinPath")
            if [ -d "$SDK_BIN_PATH" ]; then
                export PATH="$SDK_BIN_PATH:$PATH"
            fi
        fi
        
        export PATH=$(echo "$PATH" | sed 's|/usr/bin:||g' | sed 's|:/usr/bin||g')
        export PATH="$PATH:/usr/bin"
        
        # Install
        echo "📦 Installing to: {self.build_dir}"
        make install
        '''
        
        try:
            env = self.get_msvc_env()
            cmd = [str(self.cygwin_path / "bin" / "bash.exe"), "--login", "-o", "igncr", "-c", install_script]
            result = subprocess.run(cmd, env=env, cwd=self.workspace)
            
            if result.returncode != 0:
                print("❌ Install failed")
                return False
                
            print("✅ Install completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Install failed: {e}")
            return False
    
    def package_artifacts(self) -> bool:
        """Package build artifacts."""
        print("📋 Packaging artifacts...")
        
        artifact_name = f"icu-{self.config.arch}-{self.config.build_type}-{self.config.artifact_suffix}"
        artifact_dir = self.workspace / artifact_name
        
        # Clean and create artifact directory
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir)
        
        artifact_dir.mkdir()
        (artifact_dir / "lib").mkdir()
        (artifact_dir / "include").mkdir()
        (artifact_dir / "bin").mkdir()
        
        # Copy libraries
        lib_src = self.build_dir / "lib"
        if lib_src.exists():
            print(f"📚 Copying libraries from: {lib_src}")
            for lib_file in lib_src.glob("*.lib"):
                shutil.copy2(lib_file, artifact_dir / "lib")
        
        # Copy headers
        include_src = self.build_dir / "include"
        if include_src.exists():
            print(f"📄 Copying headers from: {include_src}")
            shutil.copytree(include_src, artifact_dir / "include", dirs_exist_ok=True)
        
        # Copy binaries if they exist
        bin_src = self.build_dir / "bin"
        if bin_src.exists():
            print(f"⚙️  Copying binaries from: {bin_src}")
            for bin_file in bin_src.glob("*.exe"):
                shutil.copy2(bin_file, artifact_dir / "bin")
        
        # Handle data files for separate data builds
        if not self.config.embed_data:
            (artifact_dir / "data").mkdir()
            
            # Look for .dat files in various locations
            data_paths = [
                self.source_dir / "data" / "out",
                self.source_dir / "data" / "out" / "tmp",
                Path("icu-release-77-1") / "icu4c" / "data" / "out",
                Path("icu-release-77-1") / "icu4c" / "data"
            ]
            
            data_found = False
            for data_path in data_paths:
                if data_path.exists():
                    for dat_file in data_path.glob("*.dat"):
                        print(f"📊 Copying data file: {dat_file.name} ({dat_file.stat().st_size / 1024 / 1024:.2f} MB)")
                        shutil.copy2(dat_file, artifact_dir / "data")
                        data_found = True
            
            if not data_found:
                print("⚠️  Warning: No .dat files found")
        
        # Create build info file
        build_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        build_info = f"""ICU Version: {self.config.icu_version}
Architecture: {self.config.arch}
Build Type: {self.config.build_type}
Compiler: MSVC (Visual Studio 2022)
Build Environment: Python + Cygwin/MSVC
Data Packaging: {'Static (embedded)' if self.config.embed_data else 'Separate (.dat files)'}
Library Prefix: {self.config.lib_prefix or 'none'}
Build Date: {build_date}
"""
        
        with open(artifact_dir / "BUILD_INFO.txt", "w", encoding="utf-8") as f:
            f.write(build_info)
        
        # Create zip archive
        zip_path = self.workspace / f"{artifact_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in artifact_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(artifact_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ Artifacts packaged: {zip_path}")
        return True
    
    def verify_build(self) -> bool:
        """Verify the build output."""
        print("🔍 Verifying build output...")
        
        lib_dir = self.build_dir / "lib"
        if not lib_dir.exists():
            print(f"❌ Library directory not found: {lib_dir}")
            return False
        
        # Check for libraries
        lib_files = list(lib_dir.glob("*.lib"))
        if not lib_files:
            print("❌ No library files found")
            return False
        
        print("📚 Static libraries built:")
        total_size = 0
        for lib_file in lib_files:
            size_mb = lib_file.stat().st_size / 1024 / 1024
            total_size += size_mb
            print(f"  {lib_file.name} ({size_mb:.2f} MB)")
        
        # Check headers
        include_dir = self.build_dir / "include" / "unicode"
        if include_dir.exists():
            header_count = len(list(include_dir.glob("*.h")))
            print(f"📄 Header files installed: {header_count} files")
        else:
            print("❌ Headers not found")
            return False
        
        # Data verification
        if self.config.embed_data:
            data_lib = lib_dir / f"{self.config.lib_prefix}icudt.lib"
            if data_lib.exists():
                size_mb = data_lib.stat().st_size / 1024 / 1024
                print(f"📊 Data library: {data_lib.name} ({size_mb:.2f} MB) - embedded data")
            else:
                print("⚠️  Data library not found")
        else:
            print("📊 Data files should be in separate .dat files")
        
        print(f"✅ Build verification completed - Total library size: {total_size:.2f} MB")
        return True
    
    def build(self) -> bool:
        """Execute the complete build process."""
        print(f"🚀 Starting ICU {self.config.icu_version} build...")
        print(f"   Architecture: {self.config.arch}")
        print(f"   Build Type: {self.config.build_type}")
        print(f"   Data Packaging: {'Embedded' if self.config.embed_data else 'Separate'}")
        print()
        
        steps = [
            ("Download ICU source", self.download_icu_source),
            ("Prepare source", self.prepare_source),
            ("Configure build", self.configure_build),
            ("Build ICU", self.build_icu),
            ("Install ICU", self.install_icu),
            ("Package artifacts", self.package_artifacts),
            ("Verify build", self.verify_build),
        ]
        
        for step_name, step_func in steps:
            print(f"{'='*50}")
            print(f"🔸 {step_name}")
            print(f"{'='*50}")
            
            if not step_func():
                print(f"❌ Build failed at step: {step_name}")
                return False
            print()
        
        print("🎉 ICU build completed successfully!")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build ICU static libraries for Windows")
    parser.add_argument("--arch", default="x64", choices=["x64", "x86"], 
                       help="Target architecture")
    parser.add_argument("--build-type", default="Release", choices=["Release", "Debug"],
                       help="Build type")
    parser.add_argument("--embed-data", action="store_true",
                       help="Embed ICU data in static libraries")
    parser.add_argument("--version", default="77.1", help="ICU version")
    parser.add_argument("--tag", default="release-77-1", help="ICU release tag")
    
    args = parser.parse_args()
    
    config = BuildConfig(
        arch=args.arch,
        build_type=args.build_type,
        embed_data=args.embed_data,
        icu_version=args.version,
        icu_tag=args.tag
    )
    
    builder = ICUBuilder(config)
    success = builder.build()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()