# YouTube Movie Shorts Dataset Pipeline

This pipeline extracts YouTube Shorts related to movie trailers and creates a structured dataset.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```
YOUTUBE_API_KEY=your_youtube_api_key
TMDB_API_KEY=your_tmdb_api_key
OMDB_API_KEY=your_omdb_api_key
```

3. Configure the pipeline in `config.yaml`

## Usage

```bash
python main.py --trailer "https://youtube.com/watch?v=abcdef" --output dataset.json --download_videos False
```

## Project Structure

- `pipeline.py`: Main orchestrator
- `youtube_api.py`: YouTube Data API wrapper
- `movie_api.py`: TMDb/OMDb API wrappers
- `filtering.py`: Relevance filtering methods
- `storage.py`: Dataset saving and video downloading
- `config.yaml`: Configuration file
- `main.py`: Example usage script
