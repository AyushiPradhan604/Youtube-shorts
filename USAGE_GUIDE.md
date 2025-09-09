# 🎬 YouTube Shorts Dataset Pipeline - Complete Usage Guide

Welcome to the comprehensive guide for creating YouTube Shorts datasets from movie trailers!

## 🚀 Quick Start

### 1. Installation & Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Or run automated setup
python setup.py
```

### 2. Configure API Keys

Create a `.env` file in the project root:
```env
YOUTUBE_API_KEY=your_youtube_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here
OMDB_API_KEY=your_omdb_api_key_here
```

**📋 Get Your API Keys:**
- **YouTube Data API**: [Google Cloud Console](https://console.developers.google.com/)
  - Enable YouTube Data API v3
  - Create credentials (API Key)
  
- **TMDb API**: [The Movie Database](https://www.themoviedb.org/settings/api)
  - Free registration required
  - Request API key from account settings
  
- **OMDb API**: [OMDb API](http://www.omdbapi.com/apikey.aspx)
  - Free tier available (1000 requests/day)
  - Email verification required

### 3. Test the Installation

```bash
python test_pipeline.py
```

## 📖 Usage Examples

### Basic Usage - Single Movie

```bash
# Process a single trailer
python main.py \
  --trailer "https://www.youtube.com/watch?v=8g18jFHCLXk" \
  --output "dune_dataset.json"

# With video downloads enabled
python main.py \
  --trailer "https://www.youtube.com/watch?v=8g18jFHCLXk" \
  --output "dune_dataset.json" \
  --download_videos True

# Verbose logging for debugging
python main.py \
  --trailer "https://www.youtube.com/watch?v=8g18jFHCLXk" \
  --output "dune_dataset.json" \
  --verbose
```

### Batch Processing - Multiple Movies

```bash
# Process from text file (one URL per line)
python batch_processor.py --input sample_trailers.txt --output batch_results

# Process from CSV file 
python batch_processor.py --input sample_trailers.csv --output batch_results

# With video downloads
python batch_processor.py \
  --input sample_trailers.txt \
  --output batch_results \
  --download_videos
```

### Analysis & Visualization

```bash
# Analyze a single dataset
python analyzer.py --input dataset.json --visualize --export_csv

# Analyze batch results
python analyzer.py --input batch_results --visualize --output analysis_results

# Export summary to CSV only
python analyzer.py --input batch_results --export_csv
```

## 🛠️ Configuration Options

### Pipeline Configuration (`config.yaml`)

```yaml
# YouTube API Settings
youtube:
  max_results_per_query: 50      # Results per search query
  max_total_results: 500         # Total results limit
  quota_retry_delay: 60          # Retry delay (seconds)
  max_retries: 3                 # Max retry attempts

# Filtering Settings
filtering:
  min_relevance_score: 0.3       # Minimum relevance threshold
  use_semantic_similarity: true  # Enable AI-based filtering
  keyword_weight: 0.4            # Keyword matching weight
  semantic_weight: 0.6           # Semantic similarity weight

# Storage Settings
storage:
  output_formats: ["json", "csv"] # Output formats
  download_videos: false          # Download video files
  video_quality: "worst[height<=480]" # Video quality

# Search Settings
search:
  short_duration_threshold: 60   # Max duration for shorts
  search_keywords: ["short", "clip", "scene"] # Search terms
  exclude_keywords: ["full movie"] # Terms to exclude
```

### Custom Configuration

Create your own config file:
```bash
# Copy default config
cp config.yaml my_config.yaml

# Edit settings as needed
# Use custom config
python main.py --config my_config.yaml --trailer "..." --output dataset.json
```

## 📊 Output Formats

### JSON Format
```json
{
  "metadata": {
    "created_at": "2024-01-15T10:30:00",
    "total_shorts": 25
  },
  "movie_info": {
    "title": "Dune: Part Two",
    "year": "2024",
    "overview": "Paul Atreides unites with Chani...",
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

### CSV Format
Contains flattened data with columns:
- `videoId`, `title`, `description`, `channelTitle`
- `publishedAt`, `viewCount`, `likeCount`, `tags`
- `url`, `relevanceScore`, `duration`

### Directory Structure (with video downloads)
```
dataset/
  movie_name/
    shorts/
      video_id_1.mp4
      video_id_1.info.json
      video_id_2.mp4
      video_id_2.info.json
```

## 🔧 Advanced Features

### Programmatic Usage

```python
import asyncio
from pipeline import MovieShortsDatasetPipeline

async def custom_pipeline():
    # Initialize with custom config
    pipeline = MovieShortsDatasetPipeline('my_config.yaml')
    
    # Process trailer
    result = await pipeline.run_pipeline(
        trailer_url='https://youtube.com/watch?v=VIDEO_ID',
        output_path='my_dataset.json',
        download_videos=False
    )
    
    # Access results
    movie_title = result['movie_info']['title']
    shorts_count = result['relevant_shorts_count']
    
    print(f"Found {shorts_count} shorts for {movie_title}")

# Run the custom pipeline
asyncio.run(custom_pipeline())
```

### Custom Filtering

```python
from filtering import RelevanceFilter

class CustomRelevanceFilter(RelevanceFilter):
    async def _calculate_single_relevance_score(self, short, movie_context):
        # Get base score
        base_score = await super()._calculate_single_relevance_score(
            short, movie_context
        )
        
        # Add custom scoring logic
        title = short.get('title', '').lower()
        
        # Boost official content
        if 'official' in title:
            base_score += 0.2
            
        # Reduce score for fan-made content
        if any(word in title for word in ['fan made', 'tribute']):
            base_score -= 0.1
            
        # Boost high-view content
        views = short.get('viewCount', 0)
        if views > 1000000:  # 1M+ views
            base_score += 0.1
            
        return min(1.0, max(0.0, base_score))
```

## 📈 Analytics Features

### Visualization Charts
- Relevance score distribution
- Top genres
- Top channels
- Duration distribution  
- Release year trends

### Export Options
- Summary CSV with movie-level statistics
- Combined batch reports
- Individual dataset analysis

### Example Analysis

```python
from analyzer import DatasetAnalyzer

# Load and analyze datasets
analyzer = DatasetAnalyzer()
analyzer.load_batch_results('batch_output')

# Generate statistics
stats = analyzer.generate_basic_stats()
print(f"Total movies: {stats['total_movies']}")
print(f"Total shorts: {stats['total_shorts']}")

# Create visualizations
analyzer.create_visualizations('analysis_output')

# Export summary
df = analyzer.export_summary_csv('summary.csv')
```

## 🚨 Troubleshooting

### Common Issues

**API Quota Exceeded**
```
RuntimeError: YouTube API quota exceeded
```
**Solutions:**
- Wait for quota reset (daily)
- Reduce `max_results_per_query` in config
- Use multiple API keys (rotate)

**No Shorts Found**
```
Pipeline completed with 0 shorts
```
**Solutions:**
- Check if movie title was correctly identified
- Lower `min_relevance_score` threshold
- Verify trailer URL is accessible
- Check search keywords are appropriate

**Import Errors**
```
ModuleNotFoundError: No module named 'sentence_transformers'
```
**Solutions:**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`
- Install missing packages individually

**Download Failures**
```
Failed to download video: Video unavailable
```
**Solutions:**
- Some videos may be geo-blocked
- Check yt-dlp is updated: `pip install -U yt-dlp`
- Try different video quality settings

### Performance Optimization

**Faster Processing:**
- Disable semantic similarity: `use_semantic_similarity: false`
- Reduce result limits: `max_results_per_query: 25`
- Use lighter semantic model: `all-MiniLM-L6-v2`

**Memory Optimization:**
- Process datasets in smaller batches
- Avoid downloading videos for large datasets
- Clear browser cache and temp files

**API Efficiency:**
- Use specific search keywords
- Enable quota retry with reasonable delays
- Process during off-peak hours

## 📚 Use Cases & Examples

### Academic Research
```bash
# Research on movie marketing trends
python batch_processor.py --input movie_trailers_2023.csv --output research_data
python analyzer.py --input research_data --visualize --export_csv
```

### Content Creation
```bash
# Find popular scenes for video essays
python main.py --trailer "MOVIE_TRAILER_URL" --output content_research.json
# Filter for high-relevance, high-view shorts for analysis
```

### Marketing Analysis
```bash
# Analyze competitor movie shorts
python batch_processor.py --input competitor_trailers.txt --output competitor_analysis
python analyzer.py --input competitor_analysis --visualize
```

### Film Studies
```bash
# Compare shorts across movie genres
python batch_processor.py --input genre_study_trailers.csv --output genre_study
# Analyze patterns in short content vs. movie characteristics
```

## 🤝 Contributing

### Adding Features
1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Add tests: `python test_pipeline.py`
4. Submit pull request

### Extending APIs
- Add new movie databases in `movie_api.py`
- Implement additional filtering methods in `filtering.py`
- Create new export formats in `storage.py`

## 📝 Best Practices

### API Usage
- Respect rate limits and quotas
- Cache results when possible
- Use appropriate retry strategies
- Monitor API costs

### Data Collection
- Verify trailer URLs before processing
- Use appropriate relevance thresholds
- Consider ethical implications of data collection
- Respect YouTube's Terms of Service

### Analysis
- Validate results with manual review
- Consider bias in algorithmic filtering
- Document methodology for reproducibility
- Share insights responsibly

## 🔗 Resources

- [YouTube Data API Documentation](https://developers.google.com/youtube/v3)
- [TMDb API Documentation](https://developers.themoviedb.org/3)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [Sentence Transformers](https://www.sbert.net/)

---

**📧 Support**: For issues and questions, check the error logs in `pipeline.log` and test with `test_pipeline.py` first.

**⚖️ License**: This tool is for educational and research purposes. Please respect all applicable terms of service and copyright laws.
