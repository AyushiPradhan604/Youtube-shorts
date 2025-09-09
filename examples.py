"""
Example usage scenarios for the YouTube Shorts Dataset Pipeline
"""

import asyncio
import os
from pathlib import Path
from pipeline import MovieShortsDatasetPipeline


async def example_basic_usage():
    """Basic pipeline usage example"""
    print("🎬 Basic Pipeline Usage Example")
    print("-" * 40)
    
    # Example trailer URLs (you can replace with actual URLs)
    example_trailers = [
        "https://www.youtube.com/watch?v=8g18jFHCLXk",  # Dune trailer example
        "https://www.youtube.com/watch?v=TcMBFSGVi1c",  # Another movie trailer
    ]
    
    try:
        pipeline = MovieShortsDatasetPipeline()
        
        for i, trailer_url in enumerate(example_trailers[:1]):  # Test with first one only
            print(f"\n📹 Processing trailer {i+1}: {trailer_url}")
            
            result = await pipeline.run_pipeline(
                trailer_url=trailer_url,
                output_path=f"example_dataset_{i+1}",
                download_videos=False  # Set to True if you want to download videos
            )
            
            print(f"✅ Status: {result['status']}")
            if result['status'] == 'completed':
                print(f"🎭 Movie: {result.get('movie_info', {}).get('title', 'Unknown')}")
                print(f"📊 Total shorts found: {result.get('total_shorts_found', 0)}")
                print(f"🎯 Relevant shorts: {result.get('relevant_shorts_count', 0)}")
                print(f"💾 Output saved to: {result.get('output_path', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Example failed: {e}")
        print("💡 Make sure you have API keys configured in your .env file")


async def example_with_custom_config():
    """Example with custom configuration"""
    print("\n🔧 Custom Configuration Example")
    print("-" * 40)
    
    # Create a custom config for high-quality results
    custom_config_content = """
youtube:
  api_key_env: "YOUTUBE_API_KEY"
  max_results_per_query: 25
  max_total_results: 100
  quota_retry_delay: 60
  max_retries: 3

tmdb:
  api_key_env: "TMDB_API_KEY"
  base_url: "https://api.themoviedb.org/3"

omdb:
  api_key_env: "OMDB_API_KEY"
  base_url: "http://www.omdbapi.com"

filtering:
  min_relevance_score: 0.6  # Higher threshold for quality
  use_semantic_similarity: true
  semantic_model: "sentence-transformers/all-MiniLM-L6-v2"
  keyword_weight: 0.5
  semantic_weight: 0.5

storage:
  output_formats: ["json", "csv"]  # Multiple formats
  download_videos: false
  video_quality: "best[height<=720]"
  create_directories: true

search:
  short_duration_threshold: 60
  search_keywords: ["official", "clip", "scene", "highlight"]
  exclude_keywords: ["full movie", "complete"]

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "pipeline.log"
"""
    
    # Save custom config
    with open("custom_config.yaml", "w") as f:
        f.write(custom_config_content)
    
    print("✅ Created custom configuration: custom_config.yaml")
    print("🔧 Configuration highlights:")
    print("   - Higher relevance threshold (0.6)")
    print("   - Multiple output formats (JSON + CSV)")
    print("   - Focused search keywords")
    print("   - Limited results for faster processing")


def show_dataset_analysis_example():
    """Show how to analyze the generated dataset"""
    print("\n📈 Dataset Analysis Example")
    print("-" * 40)
    
    analysis_code = '''
import pandas as pd
import json
from collections import Counter

# Load the dataset
with open("example_dataset_1.json", "r") as f:
    dataset = json.load(f)

# Basic statistics
shorts = dataset.get("shorts", [])
print(f"Total shorts: {len(shorts)}")

if shorts:
    # Relevance score distribution
    scores = [s.get("relevanceScore", 0) for s in shorts]
    print(f"Average relevance score: {sum(scores)/len(scores):.3f}")
    print(f"Best relevance score: {max(scores):.3f}")
    
    # Top channels
    channels = [s.get("channelTitle", "Unknown") for s in shorts]
    top_channels = Counter(channels).most_common(5)
    print("\\nTop channels:")
    for channel, count in top_channels:
        print(f"  {channel}: {count} shorts")
    
    # View count analysis
    views = [s.get("viewCount", 0) for s in shorts]
    print(f"\\nTotal views: {sum(views):,}")
    print(f"Average views per short: {sum(views)/len(views):,.0f}")
'''
    
    print("💡 Example analysis code:")
    print(analysis_code)


async def main():
    """Run all examples"""
    print("🚀 YouTube Shorts Dataset Pipeline Examples")
    print("=" * 50)
    
    # Check if API keys are configured
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  No .env file found!")
        print("📝 Please create a .env file with your API keys:")
        print("   YOUTUBE_API_KEY=your_key_here")
        print("   TMDB_API_KEY=your_key_here")
        print("   OMDB_API_KEY=your_key_here")
        print("\n🔗 Get API keys from:")
        print("   - YouTube: https://console.developers.google.com/")
        print("   - TMDb: https://www.themoviedb.org/settings/api")
        print("   - OMDb: http://www.omdbapi.com/apikey.aspx")
        return
    
    # Run examples
    await example_basic_usage()
    await example_with_custom_config()
    show_dataset_analysis_example()
    
    print("\n🎉 Examples completed!")
    print("\n📋 Next steps:")
    print("1. Configure your API keys in .env file")
    print("2. Run: python main.py --trailer 'YOUR_TRAILER_URL' --output dataset.json")
    print("3. Analyze the results using the generated files")


if __name__ == "__main__":
    asyncio.run(main())
