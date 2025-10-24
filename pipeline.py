import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import yaml
import re
import httpx  # Async HTTP client
import logging

from youtube_api import YouTubeAPI
from filtering import RelevanceFilter
from storage import DatasetStorage

# -------------------------------
# Hardcoded API keys
YOUTUBE_API_KEY = "AIzaSyCx5CsNFMNgunLROPVAdBElVy-5MUNPmhE"
TMDB_API_KEY = "22d95288429b11d8ba8b809f83eb3752"
OMDB_API_KEY = "dd17f76f"
# -------------------------------

@dataclass
class PipelineConfig:
    youtube_config: Dict[str, Any]
    movie_config: Dict[str, Any]
    filtering_config: Dict[str, Any]
    storage_config: Dict[str, Any]
    search_config: Dict[str, Any]

class MovieAPI:
    """Async Movie API wrapper for TMDb and OMDb with retries and timeout."""

    def __init__(self, tmdb_key: str, omdb_key: str):
        self.tmdb_key = tmdb_key
        self.omdb_key = omdb_key
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.omdb_base_url = "http://www.omdbapi.com"
        self.logger = logging.getLogger(__name__)

    async def identify_movie(self, title: str, description: str = "") -> Optional[Dict[str, Any]]:
        try:
            title_clean = title.strip()
            self.logger.info(f"Querying TMDb for movie title: {title_clean}")
            tmdb_data = await self._tmdb_search(title_clean)
            if not tmdb_data:
                self.logger.warning("TMDb returned no results")
                return None

            movie = tmdb_data[0]
            imdb_id = movie.get("imdb_id")
            omdb_data = await self._omdb_lookup(imdb_id) if imdb_id else {}

            combined = {
                "title": movie.get("title"),
                "year": movie.get("release_date", "").split("-")[0] if movie.get("release_date") else None,
                "genres": [g["name"] for g in movie.get("genres", [])],
                "overview": movie.get("overview"),
                "imdb_data": omdb_data,
            }
            return combined
        except Exception as e:
            self.logger.error(f"MovieAPI error: {e}", exc_info=True)
            return None

    async def _tmdb_search(self, title: str) -> Optional[list]:
        url = f"{self.tmdb_base_url}/search/movie"
        params = {"api_key": self.tmdb_key, "query": title}
        return await self._request_with_retries(url, params, key="results")

    async def _omdb_lookup(self, imdb_id: str) -> Optional[dict]:
        url = self.omdb_base_url
        params = {"apikey": self.omdb_key, "i": imdb_id}
        return await self._request_with_retries(url, params)

    async def _request_with_retries(self, url: str, params: dict, key: Optional[str] = None, retries: int = 3) -> Optional[Any]:
        attempt = 0
        while attempt < retries:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    if key:
                        return data.get(key, [])
                    return data
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                attempt += 1
                self.logger.warning(f"Request attempt {attempt} failed for {url}: {e}")
                await asyncio.sleep(2)
        self.logger.error(f"All {retries} attempts failed for {url}")
        return None
   
class MovieShortsDatasetPipeline:
    """Main pipeline orchestrator for creating YouTube Shorts datasets"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()

        # Initialize components
        self.youtube_api = YouTubeAPI(self.config.youtube_config)
        self.movie_api = MovieAPI(tmdb_key=TMDB_API_KEY, omdb_key=OMDB_API_KEY)  # <-- pass keys here
        self.relevance_filter = RelevanceFilter(self.config.filtering_config)
        self.storage = DatasetStorage(self.config.storage_config)
        self.logger = logging.getLogger(__name__)

    def _load_config(self, config_path: str) -> PipelineConfig:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            return PipelineConfig(
                youtube_config=config_data["youtube"],
                movie_config={**config_data["tmdb"], **config_data["omdb"]},
                filtering_config=config_data["filtering"],
                storage_config=config_data["storage"],
                search_config=config_data["search"],
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")

    def _setup_logging(self):
        log_config = {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "pipeline.log",
        }
        log_level = getattr(logging, log_config["level"].upper())
        logging.basicConfig(
            level=log_level,
            format=log_config["format"],
            handlers=[logging.FileHandler(log_config["file"]), logging.StreamHandler()],
        )

    async def run_pipeline(
        self, trailer_url: str, output_path: str, download_videos: bool = False
    ) -> Dict[str, Any]:
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
            self.logger.info(f"Retrieved {len(shorts_data)} potential shorts")

            # Stage 3: Filter for Relevance
            self.logger.info("Stage 3: Filtering for relevance")
            filtered_shorts = await self._filter_for_relevance(shorts_data, movie_info)
            self.logger.info(f"Filtered to {len(filtered_shorts)} relevant shorts")

            # Stage 4: Dataset Storage
            self.logger.info("Stage 4: Saving dataset")
            storage_result = await self._save_dataset(
                filtered_shorts, movie_info, output_path, download_videos
            )

            result = {
                "status": "completed",
                "movie_info": movie_info,
                "total_shorts_found": len(shorts_data),
                "relevant_shorts_count": len(filtered_shorts),
                "output_path": output_path,
                "storage_result": storage_result,
            }
            self.logger.info("Pipeline completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Pipeline failed: {repr(e)}")
            raise

    async def _identify_movie(self, trailer_url: str) -> Optional[Dict[str, Any]]:
        self.logger.info("Fetching video metadata from YouTube API...")
        video_data = await self.youtube_api.get_video_details(trailer_url)
        if not video_data:
            self.logger.warning("YouTube API returned no video data")
            return None

        original_title = video_data.get("title", "")
        cleaned_title = re.split(r"[|:-]", original_title)[0].strip()
        self.logger.info(f"Cleaned movie title: '{cleaned_title}'")

        movie_info = await self.movie_api.identify_movie(
            cleaned_title, video_data.get("description", "")
        )
        if not movie_info:
            self.logger.warning("Movie API returned no data")
            return None

        movie_info["trailer_data"] = video_data
        return movie_info

    async def _retrieve_shorts(self, movie_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        movie_title = movie_info.get("title", "")
        search_keywords = self.config.search_config["search_keywords"]
        queries = self._generate_search_queries(movie_title, search_keywords)

        all_shorts = []
        for query in queries:
            shorts = await self.youtube_api.search_shorts(
                query, max_results=self.config.youtube_config.get("max_results_per_query", 50)
            )
            all_shorts.extend(shorts)

        unique_shorts = self._remove_duplicates(all_shorts)
        filtered_shorts = await self._filter_by_duration(unique_shorts)
        return filtered_shorts

    async def _filter_for_relevance(
        self, shorts_data: List[Dict[str, Any]], movie_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        scored_shorts = await self.relevance_filter.calculate_relevance_scores(shorts_data, movie_info)
        min_score = self.config.filtering_config.get("min_relevance_score", 0.3)
        relevant_shorts = [s for s in scored_shorts if s.get("relevanceScore", 0) >= min_score]
        relevant_shorts.sort(key=lambda x: x.get("relevanceScore", 0), reverse=True)
        return relevant_shorts

    async def _save_dataset(
        self, shorts_data: List[Dict[str, Any]], movie_info: Dict[str, Any], output_path: str, download_videos: bool
    ) -> Dict[str, Any]:
        dataset = self._prepare_dataset(shorts_data, movie_info)
        save_result = await self.storage.save_dataset(dataset, output_path)
        if download_videos:
            download_result = await self.storage.download_videos(shorts_data, movie_info)
            save_result["download_result"] = download_result
        return save_result

    def _generate_search_queries(self, movie_title: str, keywords: List[str]) -> List[str]:
        queries = [f'"{movie_title}"'] + [f'"{movie_title}" {k}' for k in keywords]
        queries += [f"{q} duration:short" for q in queries]
        return queries

    def _remove_duplicates(self, shorts_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for s in shorts_list:
            vid = s.get("videoId")
            if vid and vid not in seen:
                seen.add(vid)
                unique.append(s)
        return unique

    async def _filter_by_duration(self, shorts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        threshold = self.config.search_config.get("short_duration_threshold", 60)
        return [s for s in shorts_data if s.get("duration") is None or s.get("duration") <= threshold]

    def _prepare_dataset(self, shorts_data: List[Dict[str, Any]], movie_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "movie_info": movie_info,
            "shorts": shorts_data,
            "metadata": {
                "total_shorts": len(shorts_data),
                "pipeline_version": "1.0.0",
                "created_at": asyncio.get_event_loop().time(),
            },
        }
