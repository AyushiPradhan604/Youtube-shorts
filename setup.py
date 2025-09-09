#!/usr/bin/env python3
"""
Setup script for YouTube Shorts Dataset Pipeline
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        print(f"✅ {description} completed")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up YouTube Shorts Dataset Pipeline")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return 1
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("💡 You may need to create a virtual environment first:")
        print("   python -m venv venv")
        print("   venv\\Scripts\\activate  (Windows)")
        print("   source venv/bin/activate  (Linux/Mac)")
        return 1
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creating .env file template...")
        with open(".env", "w") as f:
            f.write("YOUTUBE_API_KEY=your_youtube_api_key_here\n")
            f.write("TMDB_API_KEY=your_tmdb_api_key_here\n")
            f.write("OMDB_API_KEY=your_omdb_api_key_here\n")
        print("✅ .env file created - please add your API keys")
    
    # Create directories
    directories = ["dataset", "logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print(f"✅ Created directories: {', '.join(directories)}")
    
    # Test basic imports
    print("🧪 Testing imports...")
    try:
        import yaml
        import pandas
        import sentence_transformers
        import yt_dlp
        print("✅ All required packages imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return 1
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Add your API keys to the .env file")
    print("2. Run a test: python test_pipeline.py")
    print("3. Run the pipeline: python main.py --trailer 'TRAILER_URL' --output dataset.json")
    print("\n📚 API Key setup:")
    print("- YouTube Data API: https://console.developers.google.com/")
    print("- TMDb API: https://www.themoviedb.org/settings/api")
    print("- OMDb API: http://www.omdbapi.com/apikey.aspx")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
