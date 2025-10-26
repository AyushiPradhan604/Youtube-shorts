import os
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

YOUTUBE_API_KEY="AIzaSyB2LTOyquEjMklc2RWs9iEr7xfC0ITCCMs"

class YouTubeAPI:
    """
    YouTube Data API wrapper for retrieving video metadata and searching for Shorts.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Use environment variable first, fallback to hardcoded key
        self.api_key = YOUTUBE_API_KEY

        self.max_results_per_query = config.get('max_results_per_query', 1)
        self.max_total_results = config.get('max_total_results', 5)
        self.quota_retry_delay = config.get('quota_retry_delay', 60)
        self.max_retries = config.get('max_retries', 3)

        if not self.api_key:
            raise ValueError("YouTube API key not found")

        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.logger = logging.getLogger(__name__)

    async def get_video_details(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract video details from YouTube URL.
        """
        try:
            video_id = self._extract_video_id(video_url)
            if not video_id:
                self.logger.error(f"Could not extract video ID from URL: {video_url}")
                return None

            request = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            )
            response = await self._execute_with_retry(request)

            if not response.get('items'):
                self.logger.error(f"No video found with ID: {video_id}")
                return None

            video_data = response['items'][0]

            return {
                'videoId': video_id,
                'title': video_data['snippet'].get('title', ''),
                'description': video_data['snippet'].get('description', ''),
                'channelTitle': video_data['snippet'].get('channelTitle', ''),
                'publishedAt': video_data['snippet'].get('publishedAt', ''),
                'tags': video_data['snippet'].get('tags', []),
                'duration': self._parse_duration(video_data['contentDetails'].get('duration', '')),
                'viewCount': int(video_data['statistics'].get('viewCount', 0)),
                'likeCount': int(video_data['statistics'].get('likeCount', 0)),
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }

        except Exception as e:
            self.logger.error(f"Failed to get video details: {e}")
            return None

    async def search_shorts(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for YouTube Shorts based on query.
        """
        if max_results is None:
            max_results = self.max_results_per_query

        try:
            all_videos = []
            next_page_token = None

            while len(all_videos) < max_results:
                remaining = min(50, max_results - len(all_videos))  # YouTube max per request

                search_request = self.youtube.search().list(
                    part='snippet',
                    q=query,
                    type='video',
                    maxResults=remaining,
                    pageToken=next_page_token,
                    videoDuration='short',
                    order='relevance'
                )

                search_response = await self._execute_with_retry(search_request)

                if not search_response.get('items'):
                    break

                video_ids = [item['id']['videoId'] for item in search_response['items']]
                videos_detail = await self._get_videos_details_batch(video_ids)
                shorts = [v for v in videos_detail if self._is_short_video(v)]
                all_videos.extend(shorts)

                next_page_token = search_response.get('nextPageToken')
                if not next_page_token:
                    break

            self.logger.info(f"Found {len(all_videos)} shorts for query: {query}")
            return all_videos[:max_results]

        except Exception as e:
            self.logger.error(f"Failed to search for shorts: {e}")
            return []

    async def _get_videos_details_batch(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information for a batch of video IDs."""
        try:
            batch_size = 50
            all_videos = []

            for i in range(0, len(video_ids), batch_size):
                batch_ids = video_ids[i:i + batch_size]
                request = self.youtube.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=','.join(batch_ids)
                )
                response = await self._execute_with_retry(request)

                for video_data in response.get('items', []):
                    video_info = {
                        'videoId': video_data['id'],
                        'title': video_data['snippet'].get('title', ''),
                        'description': video_data['snippet'].get('description', ''),
                        'channelTitle': video_data['snippet'].get('channelTitle', ''),
                        'publishedAt': video_data['snippet'].get('publishedAt', ''),
                        'tags': video_data['snippet'].get('tags', []),
                        'duration': self._parse_duration(video_data['contentDetails'].get('duration', '')),
                        'viewCount': int(video_data['statistics'].get('viewCount', 0)),
                        'likeCount': int(video_data['statistics'].get('likeCount', 0)),
                        'url': f"https://www.youtube.com/watch?v={video_data['id']}"
                    }
                    all_videos.append(video_info)

            return all_videos

        except Exception as e:
            self.logger.error(f"Failed to get video details batch: {e}")
            return []

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL (supports youtu.be, /watch?v=, /embed/)."""
        patterns = [
            r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed/)([0-9A-Za-z_-]{11})',
            r'(?:v/)([0-9A-Za-z_-]{11})',
            r'youtu\.be/([0-9A-Za-z_-]{11})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """Convert ISO 8601 duration (PT1M30S) to seconds."""
        if not duration_str:
            return None
        try:
            duration_str = duration_str.replace('PT', '')
            total_seconds = 0
            h = re.search(r'(\d+)H', duration_str)
            m = re.search(r'(\d+)M', duration_str)
            s = re.search(r'(\d+)S', duration_str)
            if h: total_seconds += int(h.group(1)) * 3600
            if m: total_seconds += int(m.group(1)) * 60
            if s: total_seconds += int(s.group(1))
            return total_seconds
        except Exception:
            return None

    def _is_short_video(self, video: Dict[str, Any]) -> bool:
        """Check if video duration <= 60 seconds."""
        duration = video.get('duration')
        return duration is not None and duration <= 60

    async def _execute_with_retry(self, request) -> Dict[str, Any]:
        """Execute YouTube API request with retry logic for quota/rate limits."""
        for attempt in range(self.max_retries):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, request.execute)
                return response

            except HttpError as e:
                if e.resp.status in [403, 429]:  # Quota exceeded or rate limit
                    if attempt < self.max_retries - 1:
                        self.logger.warning(f"YouTube API quota/rate limit. Retry in {self.quota_retry_delay}s...")
                        await asyncio.sleep(self.quota_retry_delay)
                        continue
                    else:
                        raise RuntimeError("YouTube API quota/rate limit exceeded.")
                else:
                    raise
            except Exception as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"YouTube API request failed (attempt {attempt+1}): {e}")
                    await asyncio.sleep(5)
                    continue
                else:
                    raise
        raise RuntimeError("All YouTube API retry attempts failed")
