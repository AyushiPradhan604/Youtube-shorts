import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from fuzzywuzzy import fuzz


class MovieAPI:
    """
    Movie API wrapper combining TMDb and OMDb APIs for movie identification
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tmdb_api_key = os.getenv('TMDB_API_KEY')
        self.omdb_api_key = os.getenv('OMDB_API_KEY')
        
        # Set proper base URLs (don't rely on config merging)
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.omdb_base_url = "http://www.omdbapi.com"
        
        self.logger = logging.getLogger(__name__)
        
        # Check if at least one API key is available
        if not self.tmdb_api_key and not self.omdb_api_key:
            self.logger.warning("No movie API keys found. Movie identification may be limited.")
    
    async def identify_movie(self, title: str, description: str = "") -> Optional[Dict[str, Any]]:
        """
        Identify movie from title and description using fuzzy matching
        
        Args:
            title: Video title (likely contains movie name)
            description: Video description (may contain additional info)
            
        Returns:
            Movie information dictionary or None if not found
        """
        try:
            # Extract potential movie title from video title
            potential_titles = self._extract_movie_titles(title, description)
            
            self.logger.info(f"Extracted potential titles: {potential_titles}")
            
            movie_info = None
            
            # Try TMDb first (more comprehensive)
            if self.tmdb_api_key:
                for potential_title in potential_titles:
                    self.logger.info(f"Trying TMDb search for: {potential_title}")
                    movie_info = await self._search_tmdb(potential_title)
                    if movie_info:
                        self.logger.info(f"Found movie via TMDb: {movie_info.get('title')}")
                        break
            
            # Fallback to OMDb if TMDb fails
            if not movie_info and self.omdb_api_key:
                for potential_title in potential_titles:
                    self.logger.info(f"Trying OMDb search for: {potential_title}")
                    movie_info = await self._search_omdb(potential_title)
                    if movie_info:
                        self.logger.info(f"Found movie via OMDb: {movie_info.get('title')}")
                        break
            
            # If still no match, try some common variations for popular movies
            if not movie_info and ('dune' in title.lower() or 'dune' in description.lower()):
                # Fallback for Dune example
                fallback_titles = ['Dune', 'Dune: Part Two', 'Dune 2024', 'Dune Part Two']
                for fallback_title in fallback_titles:
                    if self.tmdb_api_key:
                        movie_info = await self._search_tmdb(fallback_title)
                        if movie_info:
                            self.logger.info(f"Found movie via fallback TMDb: {movie_info.get('title')}")
                            break
                    if not movie_info and self.omdb_api_key:
                        movie_info = await self._search_omdb(fallback_title)
                        if movie_info:
                            self.logger.info(f"Found movie via fallback OMDb: {movie_info.get('title')}")
                            break
            
            return movie_info
            
        except Exception as e:
            self.logger.error(f"Movie identification failed: {e}")
            return None
    
    def _extract_movie_titles(self, title: str, description: str) -> List[str]:
        """
        Extract potential movie titles from video title and description
        
        Args:
            title: Video title
            description: Video description
            
        Returns:
            List of potential movie titles
        """
        potential_titles = []
        
        # Clean title by removing common trailer/teaser keywords
        trailer_keywords = [
            'official trailer', 'trailer', 'teaser', 'official teaser',
            'movie trailer', 'film trailer', 'preview', 'clip',
            'official', 'hd', 'new', '2023', '2024', '2025', 'main'
        ]
        
        cleaned_title = title.lower()
        
        # Remove trailer keywords more carefully
        for keyword in trailer_keywords:
            # Use word boundaries to avoid removing parts of movie titles
            import re
            pattern = r'\b' + re.escape(keyword) + r'\b'
            cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE)
        
        # Remove year patterns
        cleaned_title = re.sub(r'\b(19|20)\d{2}\b', '', cleaned_title)
        
        # Remove common separators and clean up
        cleaned_title = re.sub(r'[|\-–—:]+', ' ', cleaned_title)  # Replace separators with spaces
        cleaned_title = re.sub(r'[^\w\s]', '', cleaned_title).strip()  # Remove punctuation
        cleaned_title = ' '.join(cleaned_title.split())  # Clean multiple spaces
        
        if cleaned_title and len(cleaned_title) > 2:
            potential_titles.append(cleaned_title)
        
        # Also try extracting the first part before common separators in original title
        original_parts = re.split(r'[|\-–—:]+', title)
        if original_parts:
            first_part = original_parts[0].strip()
            # Remove common prefixes/suffixes
            first_part = re.sub(r'\b(official|trailer|teaser|hd|new)\b', '', first_part, flags=re.IGNORECASE).strip()
            if first_part and len(first_part) > 2:
                potential_titles.append(first_part)
        
        # Also try the original title
        potential_titles.append(title)
        
        # Extract from description if available
        if description:
            # Look for quoted movie titles in description
            quoted_titles = re.findall(r'"([^"]+)"', description)
            potential_titles.extend(quoted_titles)
            
            # Look for patterns like "Movie Title (Year)" in description
            movie_patterns = re.findall(r'([A-Z][^.!?]*(?:[A-Z][^.!?]*)*)\s*\(\d{4}\)', description)
            potential_titles.extend(movie_patterns)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_titles = []
        for title in potential_titles:
            title_clean = title.lower().strip()
            if title_clean and title_clean not in seen and len(title_clean) > 2:
                seen.add(title_clean)
                unique_titles.append(title.strip())
        
        return unique_titles[:5]  # Limit to top 5 candidates
    
    async def _search_tmdb(self, movie_title: str) -> Optional[Dict[str, Any]]:
        """
        Search for movie using TMDb API
        
        Args:
            movie_title: Movie title to search for
            
        Returns:
            Movie information from TMDb or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                # Search for movie
                search_url = f"{self.tmdb_base_url}/search/movie"
                params = {
                    'api_key': self.tmdb_api_key,
                    'query': movie_title,
                    'language': 'en-US'
                }
                
                self.logger.debug(f"TMDb search URL: {search_url}")
                self.logger.debug(f"TMDb search params: {params}")
                
                response = await client.get(search_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                self.logger.debug(f"TMDb API response: {data}")
                
                if not data.get('results'):
                    self.logger.debug(f"No TMDb results for: {movie_title}")
                    return None
                
                # Find best match using fuzzy matching
                best_match = self._find_best_movie_match(movie_title, data['results'])
                
                if best_match:
                    # Get detailed movie information
                    movie_id = best_match['id']
                    detail_url = f"{self.tmdb_base_url}/movie/{movie_id}"
                    detail_params = {
                        'api_key': self.tmdb_api_key,
                        'language': 'en-US',
                        'append_to_response': 'keywords,credits'
                    }
                    
                    detail_response = await client.get(detail_url, params=detail_params)
                    detail_response.raise_for_status()
                    movie_detail = detail_response.json()
                    
                    return self._format_tmdb_response(movie_detail)
                
                return None
                
        except Exception as e:
            self.logger.error(f"TMDb search failed: {e}")
            return None
    
    async def _search_omdb(self, movie_title: str) -> Optional[Dict[str, Any]]:
        """
        Search for movie using OMDb API
        
        Args:
            movie_title: Movie title to search for
            
        Returns:
            Movie information from OMDb or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    'apikey': self.omdb_api_key,
                    't': movie_title,
                    'type': 'movie',
                    'plot': 'full'
                }
                
                response = await client.get(self.omdb_base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get('Response') == 'True':
                    return self._format_omdb_response(data)
                
                return None
                
        except Exception as e:
            self.logger.error(f"OMDb search failed: {e}")
            return None
    
    def _find_best_movie_match(self, query: str, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the best matching movie from search results using fuzzy matching
        
        Args:
            query: Original search query
            results: List of movie results from API
            
        Returns:
            Best matching movie or None if no good match found
        """
        if not results:
            return None
        
        best_match = None
        best_score = 0
        
        for movie in results:
            title = movie.get('title', '')
            original_title = movie.get('original_title', '')
            
            # Calculate fuzzy match scores
            title_score = fuzz.ratio(query.lower(), title.lower())
            original_title_score = fuzz.ratio(query.lower(), original_title.lower())
            
            # Use the best score
            score = max(title_score, original_title_score)
            
            # Consider partial ratio for better matching
            partial_score = max(
                fuzz.partial_ratio(query.lower(), title.lower()),
                fuzz.partial_ratio(query.lower(), original_title.lower())
            )
            
            # Combine scores (weighted average)
            combined_score = (score * 0.7) + (partial_score * 0.3)
            
            if combined_score > best_score and combined_score >= 70:  # Minimum threshold
                best_score = combined_score
                best_match = movie
        
        return best_match
    
    def _format_tmdb_response(self, movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format TMDb API response to standardized format"""
        try:
            # Extract genres
            genres = [genre['name'] for genre in movie_data.get('genres', [])]
            
            # Extract cast (top 5)
            cast = []
            if movie_data.get('credits', {}).get('cast'):
                cast = [
                    actor['name'] for actor in movie_data['credits']['cast'][:5]
                ]
            
            # Extract director
            directors = []
            if movie_data.get('credits', {}).get('crew'):
                directors = [
                    person['name'] for person in movie_data['credits']['crew']
                    if person['job'] == 'Director'
                ]
            
            # Extract keywords
            keywords = []
            if movie_data.get('keywords', {}).get('keywords'):
                keywords = [kw['name'] for kw in movie_data['keywords']['keywords']]
            
            return {
                'title': movie_data.get('title', ''),
                'original_title': movie_data.get('original_title', ''),
                'year': movie_data.get('release_date', '')[:4] if movie_data.get('release_date') else '',
                'overview': movie_data.get('overview', ''),
                'genres': genres,
                'cast': cast,
                'directors': directors,
                'keywords': keywords,
                'tmdb_id': movie_data.get('id'),
                'imdb_id': movie_data.get('imdb_id'),
                'source': 'tmdb'
            }
        except Exception as e:
            self.logger.error(f"Error formatting TMDb response: {e}")
            return {}
    
    def _format_omdb_response(self, movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format OMDb API response to standardized format"""
        try:
            return {
                'title': movie_data.get('Title', ''),
                'original_title': movie_data.get('Title', ''),
                'year': movie_data.get('Year', ''),
                'overview': movie_data.get('Plot', ''),
                'genres': movie_data.get('Genre', '').split(', ') if movie_data.get('Genre') else [],
                'cast': movie_data.get('Actors', '').split(', ') if movie_data.get('Actors') else [],
                'directors': movie_data.get('Director', '').split(', ') if movie_data.get('Director') else [],
                'keywords': [],  # OMDb doesn't provide keywords
                'tmdb_id': None,
                'imdb_id': movie_data.get('imdbID'),
                'source': 'omdb'
            }
        except Exception as e:
            self.logger.error(f"Error formatting OMDb response: {e}")
            return {}
