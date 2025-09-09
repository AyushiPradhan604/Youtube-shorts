import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import yaml
from dotenv import load_dotenv

from youtube_api import YouTubeAPI
from movie_api import MovieAPI
from filtering import RelevanceFilter
from storage import DatasetStorage


@dataclass
class PipelineConfig:
    """Pipeline configuration data class"""
    youtube_config: Dict[str, Any]
    movie_config: Dict[str, Any]
    filtering_config: Dict[str, Any]
    storage_config: Dict[str, Any]
    search_config: Dict[str, Any]


class MovieShortsDatasetPipeline:
    """
    Main pipeline orchestrator for creating YouTube Shorts datasets from movie trailers
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.youtube_api = YouTubeAPI(self.config.youtube_config)
        self.movie_api = MovieAPI(self.config.movie_config)
        self.relevance_filter = RelevanceFilter(self.config.filtering_config)
        self.storage = DatasetStorage(self.config.storage_config)
        
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> PipelineConfig:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            return PipelineConfig(
                youtube_config=config_data['youtube'],
                movie_config={**config_data['tmdb'], **config_data['omdb']},
                filtering_config=config_data['filtering'],
                storage_config=config_data['storage'],
                search_config=config_data['search']
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'pipeline.log'
        }
        
        # Configure logging
        log_level = getattr(logging, log_config['level'].upper())
        logging.basicConfig(
            level=log_level,
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_config['file']),
                logging.StreamHandler()
            ]
        )
    
    async def run_pipeline(
        self, 
        trailer_url: str, 
        output_path: str, 
        download_videos: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline
        
        Args:
            trailer_url: YouTube trailer URL
            output_path: Path to save the dataset
            download_videos: Whether to download video files
            
        Returns:
            Pipeline results summary
        """
        self.logger.info(f"Starting pipeline for trailer: {trailer_url}")
        
        try:
            # Stage 1: Movie Identification
            self.logger.info("Stage 1: Identifying movie from trailer")
            movie_info = await self._identify_movie(trailer_url)
            
            if not movie_info:
                raise RuntimeError("Failed to identify movie from trailer")
            
            self.logger.info(f"Identified movie: {movie_info.get('title', 'Unknown')}")
            
            # Stage 2: Retrieve Shorts
            self.logger.info("Stage 2: Retrieving related YouTube Shorts")
            shorts_data = await self._retrieve_shorts(movie_info)
            
            if not shorts_data:
                self.logger.warning("No shorts found for the movie")
                return {"status": "completed", "shorts_count": 0}
            
            self.logger.info(f"Retrieved {len(shorts_data)} potential shorts")
            
            # Stage 3: Filter for Relevance
            self.logger.info("Stage 3: Filtering for relevance")
            filtered_shorts = await self._filter_for_relevance(shorts_data, movie_info)
            
            self.logger.info(f"Filtered to {len(filtered_shorts)} relevant shorts")
            
            # Stage 4: Dataset Storage
            self.logger.info("Stage 4: Saving dataset")
            storage_result = await self._save_dataset(
                filtered_shorts, 
                movie_info, 
                output_path, 
                download_videos
            )
            
            result = {
                "status": "completed",
                "movie_info": movie_info,
                "total_shorts_found": len(shorts_data),
                "relevant_shorts_count": len(filtered_shorts),
                "output_path": output_path,
                "storage_result": storage_result
            }
            
            self.logger.info("Pipeline completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise
    
    async def _identify_movie(self, trailer_url: str) -> Optional[Dict[str, Any]]:
        """Stage 1: Extract movie information from trailer"""
        try:
            # Get video metadata from YouTube
            video_data = await self.youtube_api.get_video_details(trailer_url)
            
            if not video_data:
                return None
            
            # Extract movie name using movie APIs
            movie_info = await self.movie_api.identify_movie(
                video_data.get('title', ''),
                video_data.get('description', '')
            )
            
            # Combine YouTube and movie API data
            if movie_info:
                movie_info['trailer_data'] = video_data
                
            return movie_info
            
        except Exception as e:
            self.logger.error(f"Movie identification failed: {e}")
            return None
    
    async def _retrieve_shorts(self, movie_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Stage 2: Retrieve YouTube Shorts related to the movie"""
        try:
            movie_title = movie_info.get('title', '')
            search_keywords = self.config.search_config['search_keywords']
            
            # Generate search queries
            queries = self._generate_search_queries(movie_title, search_keywords)
            
            # Search for shorts
            all_shorts = []
            for query in queries:
                shorts = await self.youtube_api.search_shorts(
                    query, 
                    max_results=self.config.youtube_config.get('max_results_per_query', 50)
                )
                all_shorts.extend(shorts)
            
            # Remove duplicates based on video ID
            unique_shorts = self._remove_duplicates(all_shorts)
            
            # Filter by duration if possible
            filtered_shorts = await self._filter_by_duration(unique_shorts)
            
            return filtered_shorts
            
        except Exception as e:
            self.logger.error(f"Shorts retrieval failed: {e}")
            return []
    
    async def _filter_for_relevance(
        self, 
        shorts_data: List[Dict[str, Any]], 
        movie_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Stage 3: Filter shorts for relevance to the movie"""
        try:
            # Calculate relevance scores
            scored_shorts = await self.relevance_filter.calculate_relevance_scores(
                shorts_data, movie_info
            )
            
            # Filter by minimum relevance score
            min_score = self.config.filtering_config.get('min_relevance_score', 0.3)
            relevant_shorts = [
                short for short in scored_shorts 
                if short.get('relevanceScore', 0) >= min_score
            ]
            
            # Sort by relevance score (descending)
            relevant_shorts.sort(key=lambda x: x.get('relevanceScore', 0), reverse=True)
            
            return relevant_shorts
            
        except Exception as e:
            self.logger.error(f"Relevance filtering failed: {e}")
            return shorts_data  # Return unfiltered data on error
    
    async def _save_dataset(
        self, 
        shorts_data: List[Dict[str, Any]], 
        movie_info: Dict[str, Any], 
        output_path: str, 
        download_videos: bool
    ) -> Dict[str, Any]:
        """Stage 4: Save dataset and optionally download videos"""
        try:
            # Prepare dataset
            dataset = self._prepare_dataset(shorts_data, movie_info)
            
            # Save dataset
            save_result = await self.storage.save_dataset(dataset, output_path)
            
            # Download videos if requested
            download_result = None
            if download_videos:
                download_result = await self.storage.download_videos(shorts_data, movie_info)
                save_result['download_result'] = download_result
            
            return save_result
            
        except Exception as e:
            self.logger.error(f"Dataset saving failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _generate_search_queries(self, movie_title: str, keywords: List[str]) -> List[str]:
        """Generate search queries for YouTube API"""
        queries = []
        
        # Base query with movie title
        queries.append(f'"{movie_title}"')
        
        # Movie title + keywords
        for keyword in keywords:
            queries.append(f'"{movie_title}" {keyword}')
        
        # Add duration filter to queries
        duration_queries = [f"{query} duration:short" for query in queries]
        queries.extend(duration_queries)
        
        return queries
    
    def _remove_duplicates(self, shorts_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate shorts based on video ID"""
        seen_ids = set()
        unique_shorts = []
        
        for short in shorts_list:
            video_id = short.get('videoId')
            if video_id and video_id not in seen_ids:
                seen_ids.add(video_id)
                unique_shorts.append(short)
        
        return unique_shorts
    
    async def _filter_by_duration(self, shorts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter shorts by duration threshold"""
        threshold = self.config.search_config.get('short_duration_threshold', 60)
        filtered_shorts = []
        
        for short in shorts_data:
            duration = short.get('duration')
            if duration is None or duration <= threshold:
                filtered_shorts.append(short)
        
        return filtered_shorts
    
    def _prepare_dataset(
        self, 
        shorts_data: List[Dict[str, Any]], 
        movie_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare final dataset structure"""
        return {
            "movie_info": movie_info,
            "shorts": shorts_data,
            "metadata": {
                "total_shorts": len(shorts_data),
                "pipeline_version": "1.0.0",
                "created_at": asyncio.get_event_loop().time()
            }
        }
