import logging
import asyncio
from typing import List, Dict, Any, Optional
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class RelevanceFilter:
    """
    Relevance filtering for YouTube Shorts based on movie information
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_relevance_score = config.get('min_relevance_score', 0.3)
        self.use_semantic_similarity = config.get('use_semantic_similarity', True)
        self.keyword_weight = config.get('keyword_weight', 0.4)
        self.semantic_weight = config.get('semantic_weight', 0.6)
        self.model_name = config.get('semantic_model', 'sentence-transformers/all-MiniLM-L6-v2')
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize semantic model if enabled
        self.semantic_model = None
        if self.use_semantic_similarity:
            try:
                self.semantic_model = SentenceTransformer(self.model_name)
                self.logger.info(f"Loaded semantic model: {self.model_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load semantic model: {e}")
                self.use_semantic_similarity = False
    
    async def calculate_relevance_scores(
        self, 
        shorts_data: List[Dict[str, Any]], 
        movie_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calculate relevance scores for shorts based on movie information
        
        Args:
            shorts_data: List of short video metadata
            movie_info: Movie information for comparison
            
        Returns:
            List of shorts with relevance scores added
        """
        try:
            # Prepare movie context for comparison
            movie_context = self._prepare_movie_context(movie_info)
            
            # Calculate scores for each short
            scored_shorts = []
            for short in shorts_data:
                relevance_score = await self._calculate_single_relevance_score(
                    short, movie_context
                )
                
                short_copy = short.copy()
                short_copy['relevanceScore'] = relevance_score
                scored_shorts.append(short_copy)
            
            self.logger.info(f"Calculated relevance scores for {len(scored_shorts)} shorts")
            return scored_shorts
            
        except Exception as e:
            self.logger.error(f"Relevance scoring failed: {e}")
            # Return original data with default scores
            return [
                {**short, 'relevanceScore': 0.0} for short in shorts_data
            ]
    
    def _prepare_movie_context(self, movie_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare movie context for relevance comparison
        
        Args:
            movie_info: Movie information dictionary
            
        Returns:
            Processed movie context
        """
        context = {
            'title': movie_info.get('title', '').lower(),
            'original_title': movie_info.get('original_title', '').lower(),
            'year': movie_info.get('year', ''),
            'overview': movie_info.get('overview', '').lower(),
            'genres': [genre.lower() for genre in movie_info.get('genres', [])],
            'cast': [actor.lower() for actor in movie_info.get('cast', [])],
            'directors': [director.lower() for director in movie_info.get('directors', [])],
            'keywords': [keyword.lower() for keyword in movie_info.get('keywords', [])]
        }
        
        # Create combined text for semantic similarity
        text_parts = [
            context['title'],
            context['original_title'],
            context['overview']
        ]
        text_parts.extend(context['genres'])
        text_parts.extend(context['cast'][:3])  # Top 3 cast members
        text_parts.extend(context['directors'])
        text_parts.extend(context['keywords'][:5])  # Top 5 keywords
        
        context['combined_text'] = ' '.join(filter(None, text_parts))
        
        return context
    
    async def _calculate_single_relevance_score(
        self, 
        short: Dict[str, Any], 
        movie_context: Dict[str, Any]
    ) -> float:
        """
        Calculate relevance score for a single short video
        
        Args:
            short: Short video metadata
            movie_context: Movie context for comparison
            
        Returns:
            Relevance score between 0 and 1
        """
        try:
            # Prepare short context
            short_context = self._prepare_short_context(short)
            
            # Calculate keyword-based score
            keyword_score = self._calculate_keyword_score(short_context, movie_context)
            
            # Calculate semantic similarity score if enabled
            semantic_score = 0.0
            if self.use_semantic_similarity and self.semantic_model:
                semantic_score = await self._calculate_semantic_score(
                    short_context, movie_context
                )
            
            # Combine scores with weights
            if self.use_semantic_similarity:
                final_score = (
                    self.keyword_weight * keyword_score + 
                    self.semantic_weight * semantic_score
                )
            else:
                final_score = keyword_score
            
            return min(1.0, max(0.0, final_score))  # Clamp to [0, 1]
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {e}")
            return 0.0
    
    def _prepare_short_context(self, short: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare short video context for comparison
        
        Args:
            short: Short video metadata
            
        Returns:
            Processed short context
        """
        title = short.get('title', '').lower()
        description = short.get('description', '').lower()
        tags = [tag.lower() for tag in short.get('tags', [])]
        channel_title = short.get('channelTitle', '').lower()
        
        # Combined text for semantic similarity
        combined_text = ' '.join(filter(None, [title, description, ' '.join(tags), channel_title]))
        
        return {
            'title': title,
            'description': description,
            'tags': tags,
            'channel_title': channel_title,
            'combined_text': combined_text
        }
    
    def _calculate_keyword_score(
        self, 
        short_context: Dict[str, Any], 
        movie_context: Dict[str, Any]
    ) -> float:
        """
        Calculate keyword-based relevance score
        
        Args:
            short_context: Short video context
            movie_context: Movie context
            
        Returns:
            Keyword relevance score between 0 and 1
        """
        score = 0.0
        max_score = 0.0
        
        # Check movie title matches
        movie_titles = [movie_context['title'], movie_context['original_title']]
        for title in movie_titles:
            if title and self._contains_phrase(short_context['combined_text'], title):
                score += 0.4
            elif title and self._fuzzy_contains(short_context['combined_text'], title):
                score += 0.2
        max_score += 0.4
        
        # Check cast matches
        for actor in movie_context['cast'][:5]:  # Top 5 cast
            if actor and self._contains_phrase(short_context['combined_text'], actor):
                score += 0.1
        max_score += 0.2
        
        # Check director matches
        for director in movie_context['directors']:
            if director and self._contains_phrase(short_context['combined_text'], director):
                score += 0.1
        max_score += 0.1
        
        # Check genre matches
        for genre in movie_context['genres']:
            if genre and self._contains_phrase(short_context['combined_text'], genre):
                score += 0.05
        max_score += 0.1
        
        # Check keyword matches
        for keyword in movie_context['keywords'][:10]:  # Top 10 keywords
            if keyword and self._contains_phrase(short_context['combined_text'], keyword):
                score += 0.03
        max_score += 0.1
        
        # Check year matches
        if movie_context['year']:
            if movie_context['year'] in short_context['combined_text']:
                score += 0.1
        max_score += 0.1
        
        # Normalize score
        if max_score > 0:
            return min(1.0, score / max_score)
        
        return 0.0
    
    async def _calculate_semantic_score(
        self, 
        short_context: Dict[str, Any], 
        movie_context: Dict[str, Any]
    ) -> float:
        """
        Calculate semantic similarity score using sentence transformers
        
        Args:
            short_context: Short video context
            movie_context: Movie context
            
        Returns:
            Semantic similarity score between 0 and 1
        """
        try:
            if not self.semantic_model:
                return 0.0
            
            # Prepare texts for encoding
            short_text = short_context.get('combined_text', '')
            movie_text = movie_context.get('combined_text', '')
            
            if not short_text or not movie_text:
                return 0.0
            
            # Encode texts in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, 
                lambda: self.semantic_model.encode([short_text, movie_text])
            )
            
            # Calculate cosine similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            # Convert to 0-1 range (cosine similarity can be negative)
            return max(0.0, float(similarity))
            
        except Exception as e:
            self.logger.error(f"Semantic similarity calculation failed: {e}")
            return 0.0
    
    def _contains_phrase(self, text: str, phrase: str) -> bool:
        """
        Check if text contains a phrase (word boundary aware)
        
        Args:
            text: Text to search in
            phrase: Phrase to search for
            
        Returns:
            True if phrase is found with word boundaries
        """
        if not phrase or not text:
            return False
        
        # Create word boundary pattern
        pattern = r'\b' + re.escape(phrase) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _fuzzy_contains(self, text: str, phrase: str, threshold: float = 0.8) -> bool:
        """
        Check if text contains phrase with fuzzy matching
        
        Args:
            text: Text to search in
            phrase: Phrase to search for
            threshold: Similarity threshold
            
        Returns:
            True if fuzzy match found above threshold
        """
        if not phrase or not text:
            return False
        
        try:
            from fuzzywuzzy import fuzz
            
            # Split text into words and check for partial matches
            words = text.split()
            phrase_words = phrase.split()
            
            # Check all possible n-grams of the same length as phrase
            for i in range(len(words) - len(phrase_words) + 1):
                text_segment = ' '.join(words[i:i + len(phrase_words)])
                similarity = fuzz.ratio(phrase.lower(), text_segment.lower())
                
                if similarity >= (threshold * 100):
                    return True
            
            return False
            
        except ImportError:
            # Fallback to simple substring search
            return phrase.lower() in text.lower()
