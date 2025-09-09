import argparse
import asyncio
import logging
import sys
from pathlib import Path

from pipeline import MovieShortsDatasetPipeline


async def main():
    """Main entry point for the YouTube Shorts dataset pipeline"""
    
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description="Create a dataset of YouTube Shorts related to a movie trailer"
    )
    parser.add_argument(
        '--trailer',
        required=True,
        help='YouTube movie trailer URL'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output file path (extension will be added based on format)'
    )
    parser.add_argument(
        '--download_videos',
        type=str,
        default='False',
        choices=['True', 'False'],
        help='Whether to download video files (True/False)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Configuration file path'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Validate inputs
        if not args.trailer.startswith(('http://', 'https://')):
            logger.error("Trailer URL must start with http:// or https://")
            return 1
        
        if not Path(args.config).exists():
            logger.error(f"Configuration file not found: {args.config}")
            return 1
        
        # Convert string to boolean
        download_videos = args.download_videos.lower() == 'true'
        
        # Initialize pipeline
        logger.info("Initializing YouTube Shorts dataset pipeline...")
        pipeline = MovieShortsDatasetPipeline(config_path=args.config)
        
        # Run pipeline
        logger.info(f"Starting pipeline for trailer: {args.trailer}")
        logger.info(f"Output will be saved to: {args.output}")
        logger.info(f"Video download: {'enabled' if download_videos else 'disabled'}")
        
        result = await pipeline.run_pipeline(
            trailer_url=args.trailer,
            output_path=args.output,
            download_videos=download_videos
        )
        
        # Display results
        if result['status'] == 'completed':
            logger.info("Pipeline completed successfully!")
            logger.info(f"Movie identified: {result['movie_info'].get('title', 'Unknown')}")
            logger.info(f"Total shorts found: {result['total_shorts_found']}")
            logger.info(f"Relevant shorts: {result['relevant_shorts_count']}")
            logger.info(f"Output saved to: {result['output_path']}")
            
            if 'storage_result' in result and 'download_result' in result['storage_result']:
                download_result = result['storage_result']['download_result']
                if download_result['status'] == 'completed':
                    logger.info(f"Videos downloaded: {download_result['successful']}/{download_result['total_videos']}")
        
        else:
            logger.error("Pipeline failed!")
            return 1
    
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 1
    
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


def run_example():
    """Run example with sample data"""
    import asyncio
    
    async def example():
        # Example usage
        trailer_url = "https://www.youtube.com/watch?v=8g18jFHCLXk"  # Dune trailer
        output_path = "dune_shorts_dataset"
        
        try:
            pipeline = MovieShortsDatasetPipeline()
            result = await pipeline.run_pipeline(
                trailer_url=trailer_url,
                output_path=output_path,
                download_videos=False
            )
            
            print("Example pipeline result:")
            print(f"Status: {result['status']}")
            print(f"Movie: {result.get('movie_info', {}).get('title', 'Unknown')}")
            print(f"Shorts found: {result.get('relevant_shorts_count', 0)}")
            
        except Exception as e:
            print(f"Example failed: {e}")
    
    asyncio.run(example())


if __name__ == "__main__":
    # Check if running as example
    if len(sys.argv) == 1:
        print("Running example...")
        run_example()
    else:
        # Run with command line arguments
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
