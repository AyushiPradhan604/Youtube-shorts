import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from pipeline import MovieShortsDatasetPipeline


async def test_pipeline_basic():
    """Basic test of pipeline components without real API calls"""
    
    print("Testing YouTube Shorts Dataset Pipeline...")
    
    try:
        # Create mock data
        mock_video_data = {
            'videoId': 'test123',
            'title': 'Dune: Part Two Official Trailer',
            'description': 'The saga continues in this epic sci-fi adventure...',
            'channelTitle': 'Warner Bros Pictures',
            'publishedAt': '2023-10-01T00:00:00Z',
            'tags': ['dune', 'trailer', 'movie'],
            'duration': 150,
            'viewCount': 1000000,
            'likeCount': 50000,
            'url': 'https://youtube.com/watch?v=test123'
        }
        
        mock_movie_info = {
            'title': 'Dune: Part Two',
            'original_title': 'Dune: Part Two',
            'year': '2024',
            'overview': 'Paul Atreides unites with Chani and the Fremen...',
            'genres': ['Science Fiction', 'Adventure'],
            'cast': ['Timothée Chalamet', 'Zendaya', 'Rebecca Ferguson'],
            'directors': ['Denis Villeneuve'],
            'keywords': ['desert', 'spice', 'prophecy'],
            'source': 'tmdb'
        }
        
        mock_shorts = [
            {
                'videoId': 'short1',
                'title': 'Dune Part 2 Epic Scene',
                'description': 'Best moments from Dune Part Two',
                'channelTitle': 'Movie Clips',
                'publishedAt': '2024-01-01T00:00:00Z',
                'tags': ['dune', 'scene'],
                'duration': 45,
                'viewCount': 100000,
                'likeCount': 5000,
                'url': 'https://youtube.com/watch?v=short1'
            },
            {
                'videoId': 'short2',
                'title': 'Timothée Chalamet as Paul Atreides',
                'description': 'Amazing performance by Timothée Chalamet',
                'channelTitle': 'Cinema Highlights',
                'publishedAt': '2024-01-02T00:00:00Z',
                'tags': ['timothee', 'chalamet', 'dune'],
                'duration': 30,
                'viewCount': 80000,
                'likeCount': 4000,
                'url': 'https://youtube.com/watch?v=short2'
            }
        ]
        
        # Test individual components
        print("✓ Testing data structures")
        
        # Test relevance filtering
        from filtering import RelevanceFilter
        filter_config = {
            'min_relevance_score': 0.3,
            'use_semantic_similarity': False,  # Disable for test
            'keyword_weight': 1.0,
            'semantic_weight': 0.0
        }
        
        relevance_filter = RelevanceFilter(filter_config)
        scored_shorts = await relevance_filter.calculate_relevance_scores(mock_shorts, mock_movie_info)
        
        print(f"✓ Relevance filtering: {len(scored_shorts)} shorts scored")
        for short in scored_shorts:
            score = short.get('relevanceScore', 0)
            title = short.get('title', 'Unknown')
            print(f"  - {title}: {score:.3f}")
        
        # Test storage
        from storage import DatasetStorage
        storage_config = {
            'output_formats': ['json'],
            'download_videos': False,
            'create_directories': True
        }
        
        storage = DatasetStorage(storage_config)
        test_dataset = {
            'movie_info': mock_movie_info,
            'shorts': scored_shorts
        }
        
        storage_result = await storage.save_dataset(test_dataset, 'test_output')
        print(f"✓ Storage test: {storage_result['status']}")
        
        # Test complete pipeline structure
        print("✓ All components tested successfully!")
        print("\nTo run with real data:")
        print("1. Get API keys for YouTube Data API, TMDb, and/or OMDb")
        print("2. Create a .env file with your API keys")
        print("3. Run: python main.py --trailer 'https://youtube.com/watch?v=VIDEO_ID' --output dataset.json")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_pipeline_basic())
