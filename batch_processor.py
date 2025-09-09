"""
Batch processor for multiple movie trailers
"""

import asyncio
import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import argparse

from pipeline import MovieShortsDatasetPipeline


class BatchProcessor:
    """Process multiple movie trailers in batch"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.pipeline = MovieShortsDatasetPipeline(config_path)
        self.logger = logging.getLogger(__name__)
        
    async def process_batch(
        self, 
        trailer_urls: List[str], 
        output_dir: str = "batch_output",
        download_videos: bool = False
    ) -> Dict[str, Any]:
        """
        Process multiple trailers in batch
        
        Args:
            trailer_urls: List of YouTube trailer URLs
            output_dir: Directory to save all outputs
            download_videos: Whether to download video files
            
        Returns:
            Batch processing results
        """
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        results = []
        successful = 0
        failed = 0
        
        self.logger.info(f"Starting batch processing of {len(trailer_urls)} trailers")
        
        for i, trailer_url in enumerate(trailer_urls):
            self.logger.info(f"Processing trailer {i+1}/{len(trailer_urls)}: {trailer_url}")
            
            try:
                # Generate output filename based on index
                output_file = output_path / f"movie_{i+1:03d}_dataset"
                
                # Run pipeline for this trailer
                result = await self.pipeline.run_pipeline(
                    trailer_url=trailer_url,
                    output_path=str(output_file),
                    download_videos=download_videos
                )
                
                # Add trailer URL to result
                result['trailer_url'] = trailer_url
                result['output_index'] = i + 1
                
                results.append(result)
                
                if result['status'] == 'completed':
                    successful += 1
                    self.logger.info(f"✅ Success: {result.get('movie_info', {}).get('title', 'Unknown')}")
                else:
                    failed += 1
                    self.logger.error(f"❌ Failed: {trailer_url}")
                
                # Small delay between requests to be respectful to APIs
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.error(f"❌ Error processing {trailer_url}: {e}")
                results.append({
                    'status': 'failed',
                    'trailer_url': trailer_url,
                    'output_index': i + 1,
                    'error': str(e)
                })
                failed += 1
        
        # Save batch summary
        batch_summary = {
            'batch_info': {
                'total_trailers': len(trailer_urls),
                'successful': successful,
                'failed': failed,
                'processed_at': datetime.now().isoformat(),
                'output_directory': str(output_path)
            },
            'results': results
        }
        
        summary_file = output_path / "batch_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(batch_summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Batch processing completed: {successful} successful, {failed} failed")
        self.logger.info(f"Summary saved to: {summary_file}")
        
        return batch_summary
    
    async def process_from_file(
        self, 
        input_file: str, 
        output_dir: str = "batch_output",
        download_videos: bool = False
    ) -> Dict[str, Any]:
        """
        Process trailers from a file
        
        Args:
            input_file: File containing trailer URLs (one per line or CSV)
            output_dir: Directory to save outputs
            download_videos: Whether to download videos
            
        Returns:
            Batch processing results
        """
        
        trailer_urls = self._load_trailer_urls(input_file)
        
        if not trailer_urls:
            raise ValueError(f"No valid trailer URLs found in {input_file}")
        
        return await self.process_batch(trailer_urls, output_dir, download_videos)
    
    def _load_trailer_urls(self, input_file: str) -> List[str]:
        """Load trailer URLs from file"""
        file_path = Path(input_file)
        trailer_urls = []
        
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        try:
            if file_path.suffix.lower() == '.csv':
                # Load from CSV file
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Look for URL in common column names
                        url = (row.get('url') or row.get('trailer_url') or 
                               row.get('youtube_url') or row.get('link'))
                        if url and url.startswith('http'):
                            trailer_urls.append(url)
            else:
                # Load from text file (one URL per line)
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        url = line.strip()
                        if url and url.startswith('http'):
                            trailer_urls.append(url)
                            
        except Exception as e:
            raise RuntimeError(f"Failed to load URLs from {input_file}: {e}")
        
        return trailer_urls
    
    def generate_combined_report(self, batch_summary: Dict[str, Any]) -> str:
        """Generate a combined analysis report for all processed movies"""
        
        output_dir = Path(batch_summary['batch_info']['output_directory'])
        
        # Collect statistics from all successful results
        all_shorts = []
        movie_stats = []
        
        for result in batch_summary['results']:
            if result['status'] == 'completed':
                # Try to load the dataset file
                output_index = result.get('output_index', 0)
                dataset_file = output_dir / f"movie_{output_index:03d}_dataset.json"
                
                if dataset_file.exists():
                    try:
                        with open(dataset_file, 'r', encoding='utf-8') as f:
                            dataset = json.load(f)
                        
                        movie_info = dataset.get('movie_info', {})
                        shorts = dataset.get('shorts', [])
                        
                        movie_stats.append({
                            'title': movie_info.get('title', 'Unknown'),
                            'year': movie_info.get('year', 'Unknown'),
                            'shorts_count': len(shorts),
                            'avg_relevance': sum(s.get('relevanceScore', 0) for s in shorts) / len(shorts) if shorts else 0,
                            'total_views': sum(s.get('viewCount', 0) for s in shorts)
                        })
                        
                        all_shorts.extend(shorts)
                        
                    except Exception as e:
                        self.logger.warning(f"Could not load dataset {dataset_file}: {e}")
        
        # Generate report
        report_lines = [
            "# Batch Processing Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- Total trailers processed: {batch_summary['batch_info']['total_trailers']}",
            f"- Successful: {batch_summary['batch_info']['successful']}",
            f"- Failed: {batch_summary['batch_info']['failed']}",
            f"- Total shorts found: {len(all_shorts)}",
            "",
            "## Movies Processed"
        ]
        
        for i, stats in enumerate(movie_stats, 1):
            report_lines.extend([
                f"### {i}. {stats['title']} ({stats['year']})",
                f"- Shorts found: {stats['shorts_count']}",
                f"- Average relevance: {stats['avg_relevance']:.3f}",
                f"- Total views: {stats['total_views']:,}",
                ""
            ])
        
        if all_shorts:
            # Overall statistics
            total_views = sum(s.get('viewCount', 0) for s in all_shorts)
            avg_relevance = sum(s.get('relevanceScore', 0) for s in all_shorts) / len(all_shorts)
            
            report_lines.extend([
                "## Overall Statistics",
                f"- Total shorts across all movies: {len(all_shorts)}",
                f"- Combined views: {total_views:,}",
                f"- Average relevance score: {avg_relevance:.3f}",
                ""
            ])
        
        # Save report
        report_content = "\n".join(report_lines)
        report_file = output_dir / "combined_report.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(report_file)


async def main():
    """Command line interface for batch processing"""
    
    parser = argparse.ArgumentParser(description="Batch process multiple movie trailers")
    parser.add_argument('--input', required=True, help='Input file with trailer URLs')
    parser.add_argument('--output', default='batch_output', help='Output directory')
    parser.add_argument('--download_videos', action='store_true', help='Download video files')
    parser.add_argument('--config', default='config.yaml', help='Configuration file')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize batch processor
        processor = BatchProcessor(args.config)
        
        # Process trailers
        print(f"🚀 Starting batch processing from: {args.input}")
        batch_result = await processor.process_from_file(
            args.input,
            args.output,
            args.download_videos
        )
        
        # Generate combined report
        report_file = processor.generate_combined_report(batch_result)
        print(f"📊 Combined report saved to: {report_file}")
        
        print("✅ Batch processing completed!")
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
