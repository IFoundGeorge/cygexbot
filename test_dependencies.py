#!/usr/bin/env python3

import sys
import importlib

def test_import(module_name, package_name=None):
    """Test if a module can be imported"""
    try:
        if package_name:
            importlib.import_module(module_name)
            print(f"✅ {package_name} imported successfully")
        else:
            importlib.import_module(module_name)
            print(f"✅ {module_name} imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return False

def main():
    print("🔍 Testing Python dependencies...")
    print(f"Python version: {sys.version}")
    
    # Test core dependencies
    dependencies = [
        ("discord", "discord.py"),
        ("requests", "requests"),
        ("better_profanity", "better-profanity"),
        ("json", "json (built-in)"),
        ("os", "os (built-in)"),
        ("re", "re (built-in)"),
        ("asyncio", "asyncio (built-in)"),
        ("datetime", "datetime (built-in)")
    ]
    
    all_passed = True
    for module, name in dependencies:
        if not test_import(module, name):
            all_passed = False
    
    if all_passed:
        print("\n✅ All dependencies are working correctly!")
        print("🚀 Ready to run the bot!")
    else:
        print("\n❌ Some dependencies failed to import.")
        print("Please install missing packages with: pip3 install -r requirements.txt")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 