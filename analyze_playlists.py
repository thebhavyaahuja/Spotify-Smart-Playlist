import requests
import json
import os
import time
from typing import Dict, List, Set
from collections import defaultdict, Counter

class PlaylistAnalyzer:
    def __init__(self, access_token: str):
        """
        Initialize playlist analyzer with Spotify access token.
        
        Args:
            access_token: Spotify Web API access token
        """
        self.access_token = access_token
        self.base_url = "https://api.spotify.com/v1"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Data storage
        self.playlist_data = {}
        self.genre_analysis = {}
        self.artist_cache = {}  # Cache artist genres to avoid repeated API calls
    
    def load_playlists(self, playlists_file: str = "playlists.json") -> List[Dict]:
        """Load playlists from JSON file."""
        try:
            with open(playlists_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Playlists file '{playlists_file}' not found. Run fetch_playlists.py first.")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing playlists file: {e}")
            return []
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """
        Get all tracks from a specific playlist.
        
        Args:
            playlist_id: Spotify playlist ID
            
        Returns:
            List of track objects
        """
        tracks = []
        url = f"{self.base_url}/playlists/{playlist_id}/tracks"
        
        while url:
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get("items", []):
                    if item["track"] and item["track"]["id"]:
                        tracks.append(item["track"])
                
                url = data.get("next")
                time.sleep(0.1)  # Rate limiting
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching tracks for playlist {playlist_id}: {e}")
                break
        
        return tracks
    
    def get_artist_genres(self, artist_id: str) -> List[str]:
        """
        Get genres for a specific artist (with caching).
        
        Args:
            artist_id: Spotify artist ID
            
        Returns:
            List of genre strings
        """
        if artist_id in self.artist_cache:
            return self.artist_cache[artist_id]
        
        url = f"{self.base_url}/artists/{artist_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            genres = data.get("genres", [])
            self.artist_cache[artist_id] = genres
            
            time.sleep(0.1)  # Rate limiting
            return genres
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching artist genres for {artist_id}: {e}")
            self.artist_cache[artist_id] = []
            return []
    
    def analyze_playlist(self, playlist: Dict) -> Dict:
        """
        Analyze a single playlist's genre distribution.
        
        Args:
            playlist: Playlist dictionary with name, id, etc.
            
        Returns:
            Analysis results for the playlist
        """
        playlist_name = playlist.get("name", "Unknown")
        playlist_id = playlist.get("id")
        
        if not playlist_id:
            return {"error": "No playlist ID"}
        
        print(f"🎵 Analyzing '{playlist_name}' ({playlist.get('tracks_total', 0)} tracks)")
        
        # Get all tracks
        tracks = self.get_playlist_tracks(playlist_id)
        
        if not tracks:
            return {"genres": [], "artists": [], "track_count": 0}
        
        # Collect all genres and artists
        all_genres = []
        all_artists = []
        track_details = []
        
        for track in tracks:
            artists = track.get("artists", [])
            track_genres = []
            
            for artist in artists:
                artist_name = artist.get("name", "Unknown")
                artist_id = artist.get("id")
                
                if artist_id:
                    artist_genres = self.get_artist_genres(artist_id)
                    track_genres.extend(artist_genres)
                    all_genres.extend(artist_genres)
                
                all_artists.append(artist_name)
            
            track_details.append({
                "name": track.get("name", "Unknown"),
                "artists": [a.get("name", "Unknown") for a in artists],
                "genres": list(set(track_genres))  # Remove duplicates
            })
        
        # Count genre frequency
        genre_counts = Counter(all_genres)
        artist_counts = Counter(all_artists)
        
        return {
            "playlist_name": playlist_name,
            "playlist_id": playlist_id,
            "track_count": len(tracks),
            "total_genres": len(set(all_genres)),
            "genre_counts": dict(genre_counts),
            "top_genres": genre_counts.most_common(10),
            "artist_counts": dict(artist_counts),
            "top_artists": artist_counts.most_common(10),
            "tracks": track_details
        }
    
    def analyze_all_playlists(self) -> Dict:
        """
        Analyze all playlists and generate comprehensive genre mapping.
        
        Returns:
            Complete analysis results
        """
        print("🔍 Loading playlists...")
        playlists = self.load_playlists()
        
        if not playlists:
            return {}
        
        print(f"📊 Analyzing {len(playlists)} playlists...")
        print("=" * 60)
        
        analysis_results = {}
        global_genre_counts = Counter()
        playlist_genre_mapping = defaultdict(list)
        
        # Analyze each playlist
        for playlist in playlists:
            if not playlist.get("id"):
                continue
                
            playlist_name = playlist.get("name", "Unknown")
            
            # Skip playlists you don't own (optional - you can remove this filter)
            if playlist.get("owner") != "bhavya":
                print(f"⏭️  Skipping '{playlist_name}' (not owned by you)")
                continue
            
            result = self.analyze_playlist(playlist)
            
            if "error" not in result:
                analysis_results[playlist_name] = result
                
                # Update global counts
                for genre, count in result.get("genre_counts", {}).items():
                    global_genre_counts[genre] += count
                    playlist_genre_mapping[genre].append({
                        "playlist": playlist_name,
                        "count": count,
                        "percentage": round(count / result["track_count"] * 100, 1)
                    })
            
            print()  # Add spacing between playlists
        
        # Generate mapping suggestions
        suggestions = self.generate_mapping_suggestions(playlist_genre_mapping, analysis_results)
        
        return {
            "playlist_analysis": analysis_results,
            "global_genre_counts": dict(global_genre_counts),
            "top_global_genres": global_genre_counts.most_common(20),
            "genre_playlist_mapping": dict(playlist_genre_mapping),
            "mapping_suggestions": suggestions,
            "total_artists_cached": len(self.artist_cache)
        }
    
    def generate_mapping_suggestions(self, genre_mapping: Dict, playlist_analysis: Dict) -> Dict:
        """
        Generate suggested genre-to-playlist mappings based on analysis.
        
        Args:
            genre_mapping: Mapping of genres to playlists
            playlist_analysis: Complete playlist analysis
            
        Returns:
            Suggested mappings
        """
        suggestions = {}
        
        for genre, playlist_data in genre_mapping.items():
            # Find the playlist where this genre is most prominent
            best_match = max(playlist_data, key=lambda x: x["percentage"])
            
            # Only suggest if the genre appears significantly in a playlist
            if best_match["percentage"] >= 20 or best_match["count"] >= 5:
                suggestions[genre] = {
                    "suggested_playlist": best_match["playlist"],
                    "confidence": best_match["percentage"],
                    "track_count": best_match["count"],
                    "reason": f"{best_match['percentage']}% of tracks in '{best_match['playlist']}'"
                }
        
        return suggestions
    
    def save_analysis(self, analysis: Dict, filename: str = "playlist_analysis.json"):
        """Save analysis results to file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            print(f"💾 Analysis saved to {filename}")
        except Exception as e:
            print(f"Error saving analysis: {e}")
    
    def print_summary(self, analysis: Dict):
        """Print a readable summary of the analysis."""
        print("\n" + "=" * 60)
        print("📊 PLAYLIST GENRE ANALYSIS SUMMARY")
        print("=" * 60)
        
        # Global genre overview
        print(f"\n🌍 Top Global Genres:")
        for genre, count in analysis.get("top_global_genres", [])[:15]:
            print(f"  {genre}: {count} tracks")
        
        # Mapping suggestions
        print(f"\n🎯 Suggested Genre-to-Playlist Mappings:")
        suggestions = analysis.get("mapping_suggestions", {})
        
        for genre, suggestion in sorted(suggestions.items(), key=lambda x: x[1]["confidence"], reverse=True)[:20]:
            print(f"  '{genre}' → '{suggestion['suggested_playlist']}' ({suggestion['reason']})")
        
        # Playlist overview
        print(f"\n📝 Playlist Overview:")
        for name, data in analysis.get("playlist_analysis", {}).items():
            top_genre = data.get("top_genres", [])
            if top_genre:
                dominant_genre = top_genre[0][0]
                print(f"  '{name}': {data['track_count']} tracks, dominant genre: '{dominant_genre}'")
    
    def generate_config_file(self, analysis: Dict, output_file: str = "generated_config.json"):
        """
        Generate a config.json file based on the analysis.
        
        Args:
            analysis: Analysis results
            output_file: Output configuration file name
        """
        suggestions = analysis.get("mapping_suggestions", {})
        playlist_analysis = analysis.get("playlist_analysis", {})
        
        # Create playlist ID lookup
        playlist_id_lookup = {}
        for name, data in playlist_analysis.items():
            playlist_id_lookup[name] = data["playlist_id"]
        
        # Generate rules
        rules = {}
        for genre, suggestion in suggestions.items():
            playlist_name = suggestion["suggested_playlist"]
            if playlist_name in playlist_id_lookup and suggestion["confidence"] >= 15:
                rules[genre.lower()] = playlist_id_lookup[playlist_name]
        
        config = {
            "rules": rules,
            "settings": {
                "check_limit": 50,
                "case_sensitive": False,
                "partial_match": True
            },
            "analysis_metadata": {
                "generated_on": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_genres_analyzed": len(suggestions),
                "rules_generated": len(rules),
                "confidence_threshold": 15
            }
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"🎛️  Generated configuration saved to {output_file}")
            print(f"   - {len(rules)} genre rules created")
            print(f"   - Ready to use with autolist.py")
        except Exception as e:
            print(f"Error generating config: {e}")

def main():
    """Main function to run playlist analysis."""
    # Get access token
    access_token = os.getenv('SPOTIFY_ACCESS_TOKEN')
    
    if not access_token:
        print("❌ Spotify access token not found.")
        print("Please set the SPOTIFY_ACCESS_TOKEN environment variable.")
        return
    
    # Initialize analyzer
    analyzer = PlaylistAnalyzer(access_token)
    
    # Run analysis
    print("🎵 Starting comprehensive playlist analysis...")
    analysis = analyzer.analyze_all_playlists()
    
    if analysis:
        # Print summary
        analyzer.print_summary(analysis)
        
        # Save detailed analysis
        analyzer.save_analysis(analysis)
        
        # Generate config file
        analyzer.generate_config_file(analysis)
        
        print(f"\n✅ Analysis complete!")
        print(f"   - Cached {analysis.get('total_artists_cached', 0)} artist genre lookups")
        print(f"   - Check 'playlist_analysis.json' for detailed results")
        print(f"   - Check 'generated_config.json' for AutoList configuration")
    else:
        print("❌ No analysis results generated")

if __name__ == "__main__":
    main()