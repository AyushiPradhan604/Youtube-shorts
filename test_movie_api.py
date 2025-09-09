"""
Simple test for movie API functionality
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from movie_api import MovieAPI

async def test_movie_api():
    """Test movie API functionality"""
    print("🎬 Testing Movie API...")
    
    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Load environment variables
    load_dotenv()
    
    # Check API keys
    tmdb_key = os.getenv('TMDB_API_KEY')
    omdb_key = os.getenv('OMDB_API_KEY')
    
    print(f"TMDb API Key: {'✅ Set' if tmdb_key else '❌ Missing'}")
    print(f"OMDb API Key: {'✅ Set' if omdb_key else '❌ Missing'}")
    
    if not tmdb_key and not omdb_key:
        print("❌ No API keys found!")
        return
    
    # Initialize MovieAPI
    config = {}  # Empty config, using direct environment variables
    movie_api = MovieAPI(config)
    
    # Test with just one case first
    test_cases = [
        ("Dune: Part Two Official Trailer", ""),
    ]
    
    for title, description in test_cases:
        print(f"\n🔍 Testing title: '{title}'")
        try:
            result = await movie_api.identify_movie(title, description)
            if result:
                print(f"✅ Found: {result.get('title', 'Unknown')} ({result.get('year', 'Unknown year')})")
                print(f"   Source: {result.get('source', 'Unknown')}")
            else:
                print("❌ No movie found")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_movie_api())
