import logging
import os
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import yaml
import re
import httpx  # Async HTTP client
import torch
import re
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

from youtube_api import YouTubeAPI
from filtering import RelevanceFilter
from storage import DatasetStorage
from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

# Access the variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
# -------------------------------
# Hardcoded API keys
#YOUTUBE_API_KEY = "AIzaSyB2LTOyquEjMklc2RWs9iEr7xfC0ITCCMs"
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
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
        self.movie_api = MovieAPI(tmdb_key=TMDB_API_KEY, omdb_key=OMDB_API_KEY)
        self.relevance_filter = RelevanceFilter(self.config.filtering_config)
        self.storage = DatasetStorage(self.config.storage_config)
        self.logger = logging.getLogger(__name__)
        os.environ["HF_HUB_OFFLINE"] = "1"
        

        # -------------------------------
        # Load Qwen model once (for efficiency)
        # -------------------------------
       
        self.logger.info("Loading local Qwen1.5-0.5B-Chat model for movie name deduction...")


        model_path = "./Qwen1.5-0.5B-Chat"  # Local folder path (same directory as pipeline.py)

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype="auto",       # Let PyTorch pick best available type
                device_map="cpu",         # Ensure it runs fully on CPU
                trust_remote_code=True
            )
            self.logger.info("✅ Qwen1.5-0.5B-Chat model loaded successfully (CPU mode).")
        except Exception as e:
            self.logger.error(f"❌ Failed to load Qwen model from {model_path}: {e}")
            raise
        

        # -------------------------------

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

    # -------------------------------
    # New LLM-based movie title deduction
    # -------------------------------
 

    async def _deduce_movie_name_with_llm(self, title: str, description: str = "") -> str:
        """
        Uses local Qwen model to intelligently infer the correct movie name
        from YouTube title and description, with post-processing, fallback,
        and final hardcoded cleanup.
        """
        # -------------------------------
        # Step 1: LLM prompt
        # -------------------------------
        prompt = f"""
        Extract the movie title ONLY from the following YouTube trailer information.

        Title: {title}
        Description: {description}

        Respond with ONLY the movie title. No extra text.
        """

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        # Configure generation to avoid prompt echo
        gen_config = GenerationConfig(
            max_new_tokens=20,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
            eos_token_id=self.tokenizer.eos_token_id
        )

        # -------------------------------
        # Step 2: Generate title with LLM
        # -------------------------------
        try:
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    generation_config=gen_config,
                    return_dict_in_generate=True,
                    output_scores=False
                )

            # Only the generated portion (exclude prompt)
            raw_title = self.tokenizer.decode(
                outputs.sequences[0][inputs['input_ids'].shape[-1]:],
                skip_special_tokens=True
            ).strip()

        except Exception as e:
            self.logger.warning(f"LLM failed with error: {e}")
            raw_title = ""

        # -------------------------------
        # Step 3: Post-process LLM output
        # -------------------------------
        if raw_title:
            # Remove trailing punctuation, extra whitespace
            clean_title = re.sub(r'[\|\-\_\(\)\[\]\{\}\:]*$', '', raw_title).strip()
            # Remove common extra words mistakenly included
            clean_title = re.sub(r'(trailer|official|clip|hd|movie|full).*$', '', clean_title, flags=re.IGNORECASE).strip()
        else:
            clean_title = ""

        # -------------------------------
        # Step 4: Fallback regex extraction from video title
        # -------------------------------
        if not clean_title:
            clean_title = title
            # Remove year in parentheses
            clean_title = re.sub(r'\(\d{4}\)', '', clean_title)
            # Remove words like "trailer", "official", etc.
            clean_title = re.sub(r'(trailer|official|clip|hd|movie|full).*$', '', clean_title, flags=re.IGNORECASE)
            clean_title = clean_title.strip()

        # -------------------------------
        # Step 5: Final hardcoded cleanup
        # -------------------------------
        clean_title = re.sub(r'[\|\;\\\/]+', '', clean_title)  # remove | ; \ /
        clean_title = re.sub(r'\s{2,}', ' ', clean_title)      # collapse multiple spaces
        clean_title = clean_title.strip()

        self.logger.info(f"LLM-deduced and cleaned movie title: '{clean_title}'")
        return clean_title

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

        # 🧠 LLM-based movie title inference
        self.logger.info("Inferring movie title using Qwen-3-8B model...")
        cleaned_title = await self._deduce_movie_name_with_llm(
            original_title, video_data.get("description", "")
        )
        self.logger.info(f"LLM-deduced movie title: '{cleaned_title}'")

        movie_info = await self.movie_api.identify_movie(
            cleaned_title, video_data.get("description", "")
        )
        if not movie_info:
            self.logger.warning("Movie API returned no data")
            return None

        movie_info["trailer_data"] = video_data
        return movie_info

    # (Rest of the code for retrieve_shorts, filtering, storage, etc. remains unchanged)
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


