import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import yt_dlp
from datetime import datetime


class DatasetStorage:
    """
    Dataset storage handler for saving metadata and downloading videos
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_formats = config.get('output_formats', ['json'])
        self.download_videos = config.get('download_videos', False)
        self.video_quality = config.get('video_quality', 'worst[height<=480]')
        self.create_directories = config.get('create_directories', True)
        
        self.logger = logging.getLogger(__name__)
    
    async def save_dataset(
        self, 
        dataset: Dict[str, Any], 
        output_path: str
    ) -> Dict[str, Any]:
        """
        Save dataset to specified formats
        
        Args:
            dataset: Dataset dictionary containing movie info and shorts
            output_path: Base output path (extension will be added based on format)
            
        Returns:
            Save operation results
        """
        try:
            results = {}
            base_path = Path(output_path).with_suffix('')  # Remove extension if present
            
            # Create output directory if needed
            if self.create_directories:
                base_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save in requested formats
            for format_type in self.output_formats:
                if format_type == 'json':
                    result = await self._save_json(dataset, f"{base_path}.json")
                    results['json'] = result
                
                elif format_type == 'csv':
                    result = await self._save_csv(dataset, f"{base_path}.csv")
                    results['csv'] = result
                
                elif format_type == 'jsonl':
                    result = await self._save_jsonl(dataset, f"{base_path}.jsonl")
                    results['jsonl'] = result
            
            # Save metadata summary
            summary_path = f"{base_path}_summary.json"
            await self._save_summary(dataset, summary_path)
            results['summary'] = summary_path
            
            self.logger.info(f"Dataset saved successfully to {base_path}")
            return {
                'status': 'success',
                'files': results,
                'total_shorts': len(dataset.get('shorts', []))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to save dataset: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def download_videos(
        self, 
        shorts_data: List[Dict[str, Any]], 
        movie_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Download video files for shorts
        
        Args:
            shorts_data: List of short video metadata
            movie_info: Movie information for directory naming
            
        Returns:
            Download operation results
        """
        if not self.download_videos:
            return {'status': 'skipped', 'reason': 'download_videos is disabled'}
        
        try:
            # Create download directory
            movie_name = self._sanitize_filename(movie_info.get('title', 'unknown_movie'))
            download_dir = Path('dataset') / movie_name / 'shorts'
            
            if self.create_directories:
                download_dir.mkdir(parents=True, exist_ok=True)
            
            # Download videos
            download_results = []
            for short in shorts_data:
                result = await self._download_single_video(short, download_dir)
                download_results.append(result)
            
            # Summarize results
            successful = sum(1 for r in download_results if r['status'] == 'success')
            failed = len(download_results) - successful
            
            return {
                'status': 'completed',
                'download_directory': str(download_dir),
                'total_videos': len(download_results),
                'successful': successful,
                'failed': failed,
                'results': download_results
            }
            
        except Exception as e:
            self.logger.error(f"Video download failed: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def _save_json(self, dataset: Dict[str, Any], file_path: str) -> str:
        """Save dataset as JSON file"""
        try:
            # Add metadata
            dataset_with_meta = {
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'format_version': '1.0',
                    'total_shorts': len(dataset.get('shorts', []))
                },
                **dataset
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(dataset_with_meta, f, indent=2, ensure_ascii=False)
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to save JSON: {e}")
            raise
    
    async def _save_csv(self, dataset: Dict[str, Any], file_path: str) -> str:
        """Save dataset as CSV file"""
        try:
            shorts = dataset.get('shorts', [])
            if not shorts:
                # Create empty CSV with headers
                df = pd.DataFrame(columns=[
                    'videoId', 'title', 'description', 'channelTitle', 
                    'publishedAt', 'viewCount', 'likeCount', 'tags', 
                    'url', 'relevanceScore', 'duration'
                ])
            else:
                # Flatten shorts data for CSV
                flattened_shorts = []
                for short in shorts:
                    flat_short = {
                        'videoId': short.get('videoId', ''),
                        'title': short.get('title', ''),
                        'description': short.get('description', '')[:500],  # Truncate long descriptions
                        'channelTitle': short.get('channelTitle', ''),
                        'publishedAt': short.get('publishedAt', ''),
                        'viewCount': short.get('viewCount', 0),
                        'likeCount': short.get('likeCount', 0),
                        'tags': '|'.join(short.get('tags', [])),  # Join tags with pipe
                        'url': short.get('url', ''),
                        'relevanceScore': short.get('relevanceScore', 0.0),
                        'duration': short.get('duration', 0)
                    }
                    flattened_shorts.append(flat_short)
                
                df = pd.DataFrame(flattened_shorts)
            
            df.to_csv(file_path, index=False, encoding='utf-8')
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to save CSV: {e}")
            raise
    
    async def _save_jsonl(self, dataset: Dict[str, Any], file_path: str) -> str:
        """Save dataset as JSONL file (one JSON object per line)"""
        try:
            shorts = dataset.get('shorts', [])
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write movie info as first line
                movie_record = {
                    'type': 'movie_info',
                    **dataset.get('movie_info', {})
                }
                f.write(json.dumps(movie_record, ensure_ascii=False) + '\n')
                
                # Write each short as a separate line
                for short in shorts:
                    short_record = {
                        'type': 'short',
                        **short
                    }
                    f.write(json.dumps(short_record, ensure_ascii=False) + '\n')
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to save JSONL: {e}")
            raise
    
    async def _save_summary(self, dataset: Dict[str, Any], file_path: str) -> str:
        """Save dataset summary"""
        try:
            shorts = dataset.get('shorts', [])
            movie_info = dataset.get('movie_info', {})
            
            # Calculate statistics
            if shorts:
                relevance_scores = [s.get('relevanceScore', 0) for s in shorts]
                view_counts = [s.get('viewCount', 0) for s in shorts]
                
                summary = {
                    'movie': {
                        'title': movie_info.get('title', ''),
                        'year': movie_info.get('year', ''),
                        'source': movie_info.get('source', '')
                    },
                    'shorts_statistics': {
                        'total_count': len(shorts),
                        'avg_relevance_score': sum(relevance_scores) / len(relevance_scores),
                        'max_relevance_score': max(relevance_scores),
                        'min_relevance_score': min(relevance_scores),
                        'avg_view_count': sum(view_counts) / len(view_counts),
                        'max_view_count': max(view_counts),
                        'total_view_count': sum(view_counts)
                    },
                    'top_channels': self._get_top_channels(shorts),
                    'created_at': datetime.now().isoformat()
                }
            else:
                summary = {
                    'movie': movie_info,
                    'shorts_statistics': {'total_count': 0},
                    'created_at': datetime.now().isoformat()
                }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to save summary: {e}")
            raise
    
    def _get_top_channels(self, shorts: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get top channels by number of shorts"""
        try:
            channel_counts = {}
            for short in shorts:
                channel = short.get('channelTitle', 'Unknown')
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
            
            # Sort by count and return top N
            sorted_channels = sorted(
                channel_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            return [
                {'channel': channel, 'count': count} 
                for channel, count in sorted_channels[:top_n]
            ]
            
        except Exception:
            return []
    
    async def _download_single_video(
        self, 
        short: Dict[str, Any], 
        download_dir: Path
    ) -> Dict[str, Any]:
        """Download a single video file"""
        video_id = short.get('videoId', '')
        video_url = short.get('url', '')
        
        if not video_url or not video_id:
            return {
                'video_id': video_id,
                'status': 'failed',
                'error': 'Missing URL or video ID'
            }
        
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'format': self.video_quality,
                'outtmpl': str(download_dir / f'{video_id}.%(ext)s'),
                'writeinfojson': True,
                'quiet': True,
                'no_warnings': True
            }
            
            # Download video in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._download_with_ytdlp(video_url, ydl_opts)
            )
            
            return {
                'video_id': video_id,
                'status': 'success',
                'file_path': str(download_dir / f'{video_id}.mp4')  # Assuming mp4
            }
            
        except Exception as e:
            self.logger.error(f"Failed to download video {video_id}: {e}")
            return {
                'video_id': video_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _download_with_ytdlp(self, url: str, options: Dict[str, Any]):
        """Download video using yt-dlp"""
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove extra whitespace and truncate if too long
        filename = ' '.join(filename.split())
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename
