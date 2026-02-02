#!/usr/bin/env python3
"""
Setup Playwright for PDF generation.
This script installs Playwright and downloads the required browser.
"""

import subprocess
import sys
import os

def install_playwright():
    """Install Playwright package."""
    print("📦 Installing Playwright...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright==1.40.0"])
        print("✅ Playwright installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Playwright: {e}")
        return False

def install_browsers():
    """Install Playwright browsers."""
    print("🌐 Installing Playwright browsers...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("✅ Playwright browsers installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Playwright browsers: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Playwright PDF generation...")
    
    # Install Playwright
    if not install_playwright():
        print("❌ Installation failed at Playwright step")
        return False
    
    # Install browsers
    if not install_browsers():
        print("❌ Installation failed at browser installation step")
        return False
    
    print("🎉 Playwright setup completed successfully!")
    print("✅ You can now use PDF generation with Playwright")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
