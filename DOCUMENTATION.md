# YouTube Shorts Dataset Pipeline - Documentation

## Overview

This pipeline extracts YouTube Shorts related to movie trailers and creates structured datasets. It combines multiple APIs and filtering techniques to identify relevant content.

## Features

- ✅ **Movie Identification**: Extract movie info from trailer using YouTube Data API + TMDb/OMDb
- ✅ **Smart Search**: Generate targeted queries for finding related shorts
- ✅ **Relevance Filtering**: Keyword + semantic similarity scoring
- ✅ **Multiple Formats**: Export to JSON, CSV, or JSONL
- ✅ **Video Downloads**: Optional video file downloads using yt-dlp
- ✅ **Async Processing**: Non-blocking API calls for better performance
- ✅ **Error Handling**: Graceful quota management and retry logic

## Project Structure

```
Youtube_Short/
├── pipeline.py         # Main orchestrator
├── youtube_api.py      # YouTube Data API wrapper  
├── movie_api.py        # TMDb/OMDb API wrappers
├── filtering.py        # Relevance scoring algorithms
├── storage.py          # Dataset saving and video downloads
├── config.yaml         # Configuration settings
├── main.py            # Command-line interface
├── test_pipeline.py   # Test script
├── setup.py           # Setup automation
├── requirements.txt   # Dependencies
└── README.md          # This file
```

## Quick Start

### 1. Setup

```bash
# Clone or download the project
cd Youtube_Short

# Install dependencies
python setup.py

# Or manually:
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file with your API keys:

```bash
YOUTUBE_API_KEY=your_youtube_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here
OMDB_API_KEY=your_omdb_api_key_here
```

**Getting API Keys:**
- **YouTube Data API**: [Google Cloud Console](https://console.developers.google.com/)
- **TMDb API**: [The Movie Database](https://www.themoviedb.org/settings/api) 
- **OMDb API**: [OMDb API](http://www.omdbapi.com/apikey.aspx)

### 3. Run the Pipeline

```bash
# Basic usage
python main.py --trailer "https://youtube.com/watch?v=VIDEO_ID" --output dataset.json

# With video downloads
python main.py --trailer "https://youtube.com/watch?v=VIDEO_ID" --output dataset.json --download_videos True

# Verbose logging
python main.py --trailer "https://youtube.com/watch?v=VIDEO_ID" --output dataset.json --verbose
```

### 4. Test Without API Keys

```bash
python test_pipeline.py
```

## Configuration

Edit `config.yaml` to customize pipeline behavior:

### API Settings
```yaml
youtube:
  max_results_per_query: 50      # Max results per search query
  max_total_results: 500         # Total max results across all queries
  quota_retry_delay: 60          # Seconds to wait on quota exceed
  max_retries: 3                 # Max retry attempts
```

### Filtering Settings
```yaml
filtering:
  min_relevance_score: 0.3       # Minimum score to include shorts
  use_semantic_similarity: true   # Enable ML-based scoring
  keyword_weight: 0.4            # Weight for keyword matching
  semantic_weight: 0.6           # Weight for semantic similarity
```

### Storage Settings  
```yaml
storage:
  output_formats: ["json", "csv"] # Output formats
  download_videos: false          # Download video files
  video_quality: "worst[height<=480]" # Video quality for downloads
```

## Output Format

### JSON Structure
```json
{
  "metadata": {
    "created_at": "2024-01-15T10:30:00",
    "total_shorts": 25
  },
  "movie_info": {
    "title": "Dune: Part Two",
    "year": "2024",
    "genres": ["Science Fiction", "Adventure"],
    "cast": ["Timothée Chalamet", "Zendaya"],
    "directors": ["Denis Villeneuve"]
  },
  "shorts": [
    {
      "videoId": "abc123",
      "title": "Dune Part 2 Epic Scene",
      "description": "Best moments from the movie...",
      "channelTitle": "Movie Clips",
      "publishedAt": "2024-01-01T00:00:00Z",
      "viewCount": 100000,
      "likeCount": 5000,
      "tags": ["dune", "scene"],
      "url": "https://youtube.com/watch?v=abc123",
      "relevanceScore": 0.85,
      "duration": 45
    }
  ]
}
```

### CSV Columns
- `videoId`: Unique YouTube video identifier
- `title`: Video title
- `description`: Video description (truncated)
- `channelTitle`: Channel name
- `publishedAt`: Publication timestamp
- `viewCount`: Number of views
- `likeCount`: Number of likes
- `tags`: Video tags (pipe-separated)
- `url`: YouTube URL
- `relevanceScore`: Computed relevance score (0-1)
- `duration`: Video duration in seconds

## Pipeline Stages

### Stage 1: Movie Identification
1. Extract video metadata from YouTube trailer URL
2. Parse movie title from video title/description
3. Search movie databases (TMDb/OMDb) using fuzzy matching
4. Return canonical movie information

### Stage 2: Retrieve Shorts
1. Generate search queries combining movie name + keywords
2. Search YouTube for short videos (duration < 60s)
3. Batch fetch detailed metadata for found videos
4. Remove duplicates and filter by duration

### Stage 3: Filter for Relevance
1. **Keyword Matching**: Check for movie title, cast, director mentions
2. **Semantic Similarity**: Use sentence-transformers for semantic scoring
3. **Combined Score**: Weighted average of keyword + semantic scores
4. **Threshold Filtering**: Keep only shorts above minimum score

### Stage 4: Dataset Storage
1. Save metadata in requested formats (JSON/CSV/JSONL)
2. Generate summary statistics
3. Optionally download video files using yt-dlp
4. Organize downloads in structured directories

## Advanced Usage

### Custom Configuration

Create a custom config file:

```bash
python main.py --config my_config.yaml --trailer "..." --output dataset.json
```

### Programmatic Usage

```python
import asyncio
from pipeline import MovieShortsDatasetPipeline

async def run_pipeline():
    pipeline = MovieShortsDatasetPipeline('config.yaml')
    
    result = await pipeline.run_pipeline(
        trailer_url='https://youtube.com/watch?v=VIDEO_ID',
        output_path='my_dataset.json',
        download_videos=False
    )
    
    print(f"Found {result['relevant_shorts_count']} relevant shorts")

asyncio.run(run_pipeline())
```

### Custom Filtering

Extend the `RelevanceFilter` class:

```python
from filtering import RelevanceFilter

class CustomFilter(RelevanceFilter):
    async def _calculate_single_relevance_score(self, short, movie_context):
        # Your custom scoring logic
        base_score = await super()._calculate_single_relevance_score(short, movie_context)
        
        # Add custom factors
        if 'official' in short.get('title', '').lower():
            base_score += 0.2
            
        return min(1.0, base_score)
```

## Troubleshooting

### Common Issues

**API Quota Exceeded**
- The pipeline automatically retries with delays
- Consider reducing `max_results_per_query` in config
- Spread requests across multiple days

**No Shorts Found**
- Check if movie title is correctly identified
- Lower `min_relevance_score` threshold
- Verify search keywords in config

**Download Failures**
- Some videos may be geo-blocked or removed
- Check video URLs are accessible
- Verify yt-dlp is installed correctly

### Error Messages

```
RuntimeError: YouTube API quota exceeded
→ Wait or reduce query limits

ValueError: YouTube API key not found
→ Check .env file exists and contains valid key

ImportError: No module named 'sentence_transformers'
→ Run: pip install sentence-transformers
```

## Performance Optimization

### Reduce API Calls
- Lower `max_results_per_query` and `max_total_results`
- Disable semantic similarity for faster processing
- Use more specific search keywords

### Memory Usage
- Process results in batches for large datasets
- Avoid downloading videos for very large result sets
- Clear intermediate data structures

### Speed Improvements
- Use faster semantic models (e.g., `all-MiniLM-L6-v2`)
- Disable video downloads for metadata-only collection
- Run on multiple trailers in parallel

## Examples

### Movie Franchise Dataset
```bash
# Create datasets for multiple movies in a franchise
python main.py --trailer "https://youtube.com/watch?v=dune1" --output dune1.json
python main.py --trailer "https://youtube.com/watch?v=dune2" --output dune2.json
```

### High-Quality Shorts Only
```yaml
# config_quality.yaml
filtering:
  min_relevance_score: 0.7  # Higher threshold
  use_semantic_similarity: true

search:
  search_keywords: ["official", "clip", "scene"]  # More specific
```

### Download Videos for Analysis
```bash
python main.py \
  --trailer "https://youtube.com/watch?v=VIDEO_ID" \
  --output dataset.json \
  --download_videos True
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

### Adding New APIs

To add support for additional movie databases:

```python
# In movie_api.py
async def _search_new_api(self, movie_title: str):
    # Implementation for new API
    pass
```

### Custom Output Formats

To add new export formats:

```python
# In storage.py  
async def _save_xml(self, dataset: Dict[str, Any], file_path: str):
    # XML export implementation
    pass
```

## License

This project is provided as-is for educational and research purposes. Please respect YouTube's Terms of Service and API quotas when using this tool.

## Support

For issues and questions:
1. Check this documentation
2. Review error logs in `pipeline.log`
3. Test with `test_pipeline.py`
4. Verify API keys and quotas
