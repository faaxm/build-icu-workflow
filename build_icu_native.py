#!/usr/bin/env python3
"""
ICU Build Script for Windows with Native MSVC (MSBuild)
Builds ICU static libraries using Visual Studio solution files.
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
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
    icu_version: str = "77.1"
    icu_tag: str = "release-77-1"
    
    @property
    def artifact_name(self) -> str:
        """Get artifact name."""
        return f"icu-{self.arch}-{self.build_type}"


class ICUNativeBuilder:
    """Builds ICU static libraries for Windows using native MSVC/MSBuild."""
    
    def __init__(self, config: BuildConfig):
        self.config = config
        self.workspace = Path.cwd()
        self.source_dir = self.workspace / f"icu-release-{config.icu_tag}" / "icu4c" / "source"
        self.solution_path = self.source_dir / "allinone" / "allinone.sln"
        
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
    
    def verify_visual_studio_solution(self) -> bool:
        """Verify that Visual Studio solution exists."""
        print("🔍 Verifying Visual Studio solution...")
        
        if not self.solution_path.exists():
            print(f"❌ Visual Studio solution not found at: {self.solution_path}")
            
            # Check if allinone directory exists
            allinone_dir = self.source_dir / "allinone"
            if allinone_dir.exists():
                print("📁 Available files in allinone directory:")
                for file in allinone_dir.iterdir():
                    print(f"  {file.name}")
            else:
                print("❌ allinone directory does not exist")
            return False
            
        print(f"✅ Found Visual Studio solution: {self.solution_path}")
        return True
    
    def update_visual_studio_toolset(self) -> bool:
        """Update Visual Studio toolset for VS 2022."""
        print("🔧 Updating project configuration for Visual Studio 2022...")
        
        props_file = self.source_dir / "allinone" / "Build.Windows.ProjectConfiguration.props"
        if not props_file.exists():
            print(f"⚠️  Warning: Could not find project configuration file: {props_file}")
            return True  # Not critical, continue
            
        try:
            # Read the file
            content = props_file.read_text(encoding='utf-8')
            
            # Update toolset to v143 (VS 2022)
            updated = False
            if '<PlatformToolset>v141</PlatformToolset>' in content:
                content = content.replace('<PlatformToolset>v141</PlatformToolset>', '<PlatformToolset>v143</PlatformToolset>')
                updated = True
            if '<PlatformToolset>v140</PlatformToolset>' in content:
                content = content.replace('<PlatformToolset>v140</PlatformToolset>', '<PlatformToolset>v143</PlatformToolset>')
                updated = True
                
            if updated:
                props_file.write_text(content, encoding='utf-8')
                print("✅ Updated toolset to v143 (Visual Studio 2022)")
            else:
                print("ℹ️  Toolset already up to date or not found")
                
            return True
        except Exception as e:
            print(f"⚠️  Warning: Failed to update toolset: {e}")
            return True  # Not critical, continue
    
    def build_icu_with_msbuild(self) -> bool:
        """Build ICU using MSBuild."""
        print(f"🔨 Building ICU with MSBuild ({self.config.arch} {self.config.build_type})...")
        
        # Build command arguments
        msbuild_args = [
            "msbuild",
            str(self.solution_path),
            f"/p:Configuration={self.config.build_type}",
            f"/p:Platform={self.config.arch}",
            "/p:SkipUWP=true",
            f"/p:UseDebugLibraries={'true' if self.config.build_type == 'Debug' else 'false'}",
            "/m",
            "/verbosity:normal"
        ]
        
        print(f"🚀 Running: {' '.join(msbuild_args)}")
        
        try:
            # Build the complete solution first
            result = subprocess.run(msbuild_args, cwd=self.workspace, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Initial ICU build failed with exit code {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
            print("✅ Initial ICU build completed successfully")
            
            # Build the full ICU data library (not just stubdata)
            print("📊 Building full ICU data library...")
            makedata_args = msbuild_args + ["/target:MakeData"]
            
            result = subprocess.run(makedata_args, cwd=self.workspace, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ ICU data build failed with exit code {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
            print("✅ Full ICU data build completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False
    
    def locate_build_artifacts(self) -> dict:
        """Locate build artifacts in various possible locations."""
        print("🔍 Locating build artifacts...")
        
        # Possible locations for build output
        possible_paths = [
            self.workspace / f"icu-release-{self.config.icu_tag}" / "icu4c" / "bin64",
            self.workspace / f"icu-release-{self.config.icu_tag}" / "icu4c" / "lib64",
            self.workspace / f"icu-release-{self.config.icu_tag}" / "icu4c" / "bin",
            self.workspace / f"icu-release-{self.config.icu_tag}" / "icu4c" / "lib",
            self.source_dir / ".." / ".." / "lib64",
            self.source_dir / ".." / ".." / "bin64",
        ]
        
        artifacts = {
            'lib_files': [],
            'exe_files': [],
            'dat_files': []
        }
        
        for path in possible_paths:
            if path.exists():
                print(f"📁 Checking directory: {path}")
                
                # Look for .lib files
                lib_files = list(path.glob("*.lib"))
                if lib_files:
                    print(f"  Found {len(lib_files)} .lib files")
                    artifacts['lib_files'].extend(lib_files)
                
                # Look for .exe files
                exe_files = list(path.glob("*.exe"))
                if exe_files:
                    print(f"  Found {len(exe_files)} .exe files")
                    artifacts['exe_files'].extend(exe_files)
        
        # Look for data files in specific locations
        data_paths = [
            self.source_dir / "data" / "out",
            self.source_dir / "data" / "out" / "tmp",
            self.workspace / f"icu-release-{self.config.icu_tag}" / "icu4c" / "data" / "out",
            self.workspace / f"icu-release-{self.config.icu_tag}" / "icu4c" / "data",
        ]
        
        for data_path in data_paths:
            if data_path.exists():
                dat_files = list(data_path.glob("*.dat"))
                if dat_files:
                    print(f"📊 Found {len(dat_files)} .dat files in: {data_path}")
                    artifacts['dat_files'].extend(dat_files)
        
        return artifacts
    
    def package_artifacts(self) -> bool:
        """Package build artifacts."""
        print("📦 Packaging artifacts...")
        
        artifacts = self.locate_build_artifacts()
        
        if not artifacts['lib_files']:
            print("❌ No .lib files found in any expected location")
            return False
        
        artifact_dir = self.workspace / self.config.artifact_name
        
        # Clean and create artifact directory
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir)
        
        artifact_dir.mkdir()
        (artifact_dir / "lib").mkdir()
        (artifact_dir / "include").mkdir()
        (artifact_dir / "bin").mkdir()
        (artifact_dir / "data").mkdir()
        
        # Copy libraries
        print(f"📚 Copying {len(artifacts['lib_files'])} library files...")
        for lib_file in artifacts['lib_files']:
            shutil.copy2(lib_file, artifact_dir / "lib")
            size_mb = lib_file.stat().st_size / 1024 / 1024
            print(f"  {lib_file.name} ({size_mb:.2f} MB)")
        
        # Copy headers
        header_paths = [
            self.source_dir / "common" / "unicode",
            self.source_dir / "i18n" / "unicode", 
            self.source_dir / "io" / "unicode"
        ]
        
        unicode_include_dir = artifact_dir / "include" / "unicode"
        unicode_include_dir.mkdir()
        
        for header_path in header_paths:
            if header_path.exists():
                print(f"📄 Copying headers from: {header_path}")
                for header_file in header_path.glob("*.h"):
                    shutil.copy2(header_file, unicode_include_dir)
        
        # Copy binaries
        if artifacts['exe_files']:
            print(f"⚙️  Copying {len(artifacts['exe_files'])} executable files...")
            for exe_file in artifacts['exe_files']:
                shutil.copy2(exe_file, artifact_dir / "bin")
        
        # Copy data files
        if artifacts['dat_files']:
            print(f"📊 Copying {len(artifacts['dat_files'])} data files...")
            for dat_file in artifacts['dat_files']:
                size_mb = dat_file.stat().st_size / 1024 / 1024
                print(f"  {dat_file.name} ({size_mb:.2f} MB)")
                shutil.copy2(dat_file, artifact_dir / "data")
        else:
            print("⚠️  Warning: No .dat files found - ICU data may be incomplete")
        
        # Create build info file
        build_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        build_info = f"""ICU Version: {self.config.icu_version}
Architecture: {self.config.arch}
Build Type: {self.config.build_type}
Compiler: MSVC (Visual Studio 2022)
Build Environment: Native Windows (MSBuild)
Build Date: {build_date}
Static Libraries: Yes
Shared Libraries: No
Data Library: Complete (built with MakeData target)
Data Packaging: Built-in DLL + .dat files
"""
        
        with open(artifact_dir / "BUILD_INFO.txt", "w", encoding="utf-8") as f:
            f.write(build_info)
        
        # Create zip archive
        zip_path = self.workspace / f"{self.config.artifact_name}.zip"
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
        
        artifact_dir = self.workspace / self.config.artifact_name
        
        # Check libraries
        lib_dir = artifact_dir / "lib"
        if not lib_dir.exists():
            print(f"❌ Library directory not found: {lib_dir}")
            return False
        
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
        include_dir = artifact_dir / "include" / "unicode"
        if include_dir.exists():
            header_count = len(list(include_dir.glob("*.h")))
            print(f"📄 Header files installed: {header_count} files")
        else:
            print("❌ Headers not found")
            return False
        
        # Check data files
        data_dir = artifact_dir / "data"
        if data_dir.exists():
            dat_files = list(data_dir.glob("*.dat"))
            if dat_files:
                print("📊 ICU data files:")
                for dat_file in dat_files:
                    size_mb = dat_file.stat().st_size / 1024 / 1024
                    print(f"  {dat_file.name} ({size_mb:.2f} MB)")
            else:
                print("⚠️  Warning: No data files found")
        
        print(f"✅ Build verification completed - Total library size: {total_size:.2f} MB")
        return True
    
    def build(self) -> bool:
        """Execute the complete build process."""
        print(f"🚀 Starting ICU {self.config.icu_version} native MSVC build...")
        print(f"   Architecture: {self.config.arch}")
        print(f"   Build Type: {self.config.build_type}")
        print()
        
        steps = [
            ("Download ICU source", self.download_icu_source),
            ("Verify Visual Studio solution", self.verify_visual_studio_solution),
            ("Update Visual Studio toolset", self.update_visual_studio_toolset),
            ("Build ICU with MSBuild", self.build_icu_with_msbuild),
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
        
        print("🎉 ICU native MSVC build completed successfully!")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build ICU static libraries for Windows using native MSVC")
    parser.add_argument("--arch", default="x64", choices=["x64", "x86"], 
                       help="Target architecture")
    parser.add_argument("--build-type", default="Release", choices=["Release", "Debug"],
                       help="Build type")
    parser.add_argument("--version", default="77.1", help="ICU version")
    parser.add_argument("--tag", default="release-77-1", help="ICU release tag")
    
    args = parser.parse_args()
    
    config = BuildConfig(
        arch=args.arch,
        build_type=args.build_type,
        icu_version=args.version,
        icu_tag=args.tag
    )
    
    builder = ICUNativeBuilder(config)
    success = builder.build()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()