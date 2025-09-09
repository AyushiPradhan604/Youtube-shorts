"""
Analysis and visualization utilities for YouTube Shorts datasets
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional
import argparse


class DatasetAnalyzer:
    """Analyze YouTube Shorts datasets"""
    
    def __init__(self):
        self.datasets = []
        self.combined_data = None
        
    def load_dataset(self, dataset_path: str) -> Dict[str, Any]:
        """Load a single dataset file"""
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            
            self.datasets.append({
                'path': dataset_path,
                'data': dataset
            })
            
            return dataset
            
        except Exception as e:
            print(f"Error loading dataset {dataset_path}: {e}")
            return {}
    
    def load_batch_results(self, batch_dir: str):
        """Load all datasets from a batch processing directory"""
        batch_path = Path(batch_dir)
        
        if not batch_path.exists():
            raise FileNotFoundError(f"Batch directory not found: {batch_dir}")
        
        # Find all dataset JSON files
        dataset_files = list(batch_path.glob("movie_*_dataset.json"))
        
        for dataset_file in sorted(dataset_files):
            self.load_dataset(str(dataset_file))
        
        print(f"Loaded {len(dataset_files)} datasets from {batch_dir}")
    
    def generate_basic_stats(self) -> Dict[str, Any]:
        """Generate basic statistics across all loaded datasets"""
        
        if not self.datasets:
            return {}
        
        stats = {
            'total_movies': len(self.datasets),
            'total_shorts': 0,
            'total_views': 0,
            'avg_relevance_scores': [],
            'genres_distribution': Counter(),
            'year_distribution': Counter(),
            'channel_distribution': Counter(),
            'duration_distribution': []
        }
        
        for dataset_info in self.datasets:
            dataset = dataset_info['data']
            movie_info = dataset.get('movie_info', {})
            shorts = dataset.get('shorts', [])
            
            stats['total_shorts'] += len(shorts)
            
            # Movie-level stats
            if movie_info.get('genres'):
                for genre in movie_info['genres']:
                    stats['genres_distribution'][genre] += 1
            
            if movie_info.get('year'):
                stats['year_distribution'][movie_info['year']] += 1
            
            # Shorts-level stats
            for short in shorts:
                stats['total_views'] += short.get('viewCount', 0)
                stats['avg_relevance_scores'].append(short.get('relevanceScore', 0))
                stats['duration_distribution'].append(short.get('duration', 0))
                
                if short.get('channelTitle'):
                    stats['channel_distribution'][short['channelTitle']] += 1
        
        # Calculate averages
        if stats['avg_relevance_scores']:
            stats['avg_relevance_score'] = sum(stats['avg_relevance_scores']) / len(stats['avg_relevance_scores'])
            stats['max_relevance_score'] = max(stats['avg_relevance_scores'])
            stats['min_relevance_score'] = min(stats['avg_relevance_scores'])
        
        if stats['duration_distribution']:
            stats['avg_duration'] = sum(stats['duration_distribution']) / len(stats['duration_distribution'])
        
        return stats
    
    def create_visualizations(self, output_dir: str = "analysis_output"):
        """Create visualization charts"""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        stats = self.generate_basic_stats()
        
        if not stats:
            print("No data to visualize")
            return
        
        # Set up the plotting style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # 1. Relevance Score Distribution
        if stats['avg_relevance_scores']:
            plt.figure(figsize=(10, 6))
            plt.hist(stats['avg_relevance_scores'], bins=20, alpha=0.7, edgecolor='black')
            plt.xlabel('Relevance Score')
            plt.ylabel('Number of Shorts')
            plt.title('Distribution of Relevance Scores')
            plt.grid(True, alpha=0.3)
            plt.savefig(output_path / 'relevance_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # 2. Top Genres
        if stats['genres_distribution']:
            top_genres = dict(stats['genres_distribution'].most_common(10))
            
            plt.figure(figsize=(12, 6))
            plt.bar(top_genres.keys(), top_genres.values())
            plt.xlabel('Genre')
            plt.ylabel('Number of Movies')
            plt.title('Top Movie Genres')
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_path / 'genres_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # 3. Top Channels
        if stats['channel_distribution']:
            top_channels = dict(stats['channel_distribution'].most_common(15))
            
            plt.figure(figsize=(14, 8))
            plt.barh(list(top_channels.keys()), list(top_channels.values()))
            plt.xlabel('Number of Shorts')
            plt.ylabel('Channel')
            plt.title('Top Channels by Number of Shorts')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_path / 'top_channels.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # 4. Duration Distribution
        if stats['duration_distribution']:
            durations = [d for d in stats['duration_distribution'] if d > 0]
            
            plt.figure(figsize=(10, 6))
            plt.hist(durations, bins=30, alpha=0.7, edgecolor='black')
            plt.xlabel('Duration (seconds)')
            plt.ylabel('Number of Shorts')
            plt.title('Distribution of Short Durations')
            plt.grid(True, alpha=0.3)
            plt.savefig(output_path / 'duration_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # 5. Year Distribution
        if stats['year_distribution']:
            years = sorted(stats['year_distribution'].keys())
            counts = [stats['year_distribution'][year] for year in years]
            
            plt.figure(figsize=(10, 6))
            plt.plot(years, counts, marker='o', linewidth=2, markersize=8)
            plt.xlabel('Year')
            plt.ylabel('Number of Movies')
            plt.title('Movies by Release Year')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(output_path / 'year_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        print(f"📊 Visualizations saved to: {output_path}")
        
        # Print some key insights
        print("\n📈 Key Insights:")
        print(f"   • Total movies analyzed: {stats['total_movies']}")
        print(f"   • Total shorts found: {stats['total_shorts']}")
        print(f"   • Combined views: {stats['total_views']:,}")
        
        if stats.get('avg_relevance_score'):
            print(f"   • Average relevance score: {stats['avg_relevance_score']:.3f}")
        
        if stats['channel_distribution']:
            top_channel = stats['channel_distribution'].most_common(1)[0]
            print(f"   • Most active channel: {top_channel[0]} ({top_channel[1]} shorts)")
        
        if stats.get('avg_duration'):
            print(f"   • Average short duration: {stats['avg_duration']:.1f} seconds")
    
    def export_summary_csv(self, output_path: str = "dataset_summary.csv"):
        """Export summary data to CSV for further analysis"""
        
        if not self.datasets:
            print("No datasets to export")
            return
        
        rows = []
        
        for dataset_info in self.datasets:
            dataset = dataset_info['data']
            movie_info = dataset.get('movie_info', {})
            shorts = dataset.get('shorts', [])
            
            if shorts:
                total_views = sum(s.get('viewCount', 0) for s in shorts)
                avg_relevance = sum(s.get('relevanceScore', 0) for s in shorts) / len(shorts)
                avg_duration = sum(s.get('duration', 0) for s in shorts) / len(shorts)
            else:
                total_views = avg_relevance = avg_duration = 0
            
            rows.append({
                'movie_title': movie_info.get('title', 'Unknown'),
                'year': movie_info.get('year', ''),
                'genres': '|'.join(movie_info.get('genres', [])),
                'cast': '|'.join(movie_info.get('cast', [])[:3]),  # Top 3 cast
                'directors': '|'.join(movie_info.get('directors', [])),
                'shorts_count': len(shorts),
                'total_views': total_views,
                'avg_relevance_score': avg_relevance,
                'avg_duration': avg_duration,
                'dataset_path': dataset_info['path']
            })
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        
        print(f"📄 Summary exported to: {output_path}")
        return df


def main():
    """Command line interface"""
    
    parser = argparse.ArgumentParser(description="Analyze YouTube Shorts datasets")
    parser.add_argument('--input', required=True, help='Dataset file or batch directory')
    parser.add_argument('--output', default='analysis_output', help='Output directory for analysis')
    parser.add_argument('--visualize', action='store_true', help='Create visualization charts')
    parser.add_argument('--export_csv', action='store_true', help='Export summary to CSV')
    
    args = parser.parse_args()
    
    try:
        analyzer = DatasetAnalyzer()
        
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Single dataset file
            analyzer.load_dataset(args.input)
            print(f"✅ Loaded single dataset: {args.input}")
        elif input_path.is_dir():
            # Batch directory
            analyzer.load_batch_results(args.input)
            print(f"✅ Loaded batch results from: {args.input}")
        else:
            print(f"❌ Input not found: {args.input}")
            return 1
        
        # Generate basic statistics
        stats = analyzer.generate_basic_stats()
        
        if stats:
            print("\n📊 Basic Statistics:")
            print(f"   Movies: {stats['total_movies']}")
            print(f"   Shorts: {stats['total_shorts']}")
            print(f"   Total Views: {stats['total_views']:,}")
            
            if stats.get('avg_relevance_score'):
                print(f"   Avg Relevance: {stats['avg_relevance_score']:.3f}")
        
        # Create visualizations if requested
        if args.visualize:
            try:
                analyzer.create_visualizations(args.output)
            except ImportError:
                print("⚠️  Visualization requires matplotlib and seaborn")
                print("   Install with: pip install matplotlib seaborn")
        
        # Export CSV summary if requested
        if args.export_csv:
            csv_path = Path(args.output) / "summary.csv"
            analyzer.export_summary_csv(str(csv_path))
        
        print("✅ Analysis completed!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
