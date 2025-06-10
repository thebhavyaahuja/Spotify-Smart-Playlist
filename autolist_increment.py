import requests
import json
import os
import time
from typing import List, Dict, Optional, Set
from datetime import datetime, date
import argparse

class AutoListIncremental:
    def __init__(self, access_token: str, config_file: str = "generated_config.json"):
        """
        Initialize AutoList with processing history tracking.
        
        Args:
            access_token: Spotify Web API access token
            config_file: Path to configuration JSON file
        """
        self.access_token = access_token
        self.base_url = "https://api.spotify.com/v1"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Load configuration
        self.config = self._load_config(config_file)
        self.rules = self.config.get("rules", {})
        self.settings = self.config.get("settings", {})
        
        # Load/initialize processing history
        self.history_file = "processing_history.json"
        self.processing_history = self._load_processing_history()
        
        # Artist genre cache
        self.artist_genre_cache = {}
        
        # Processing statistics
        self.stats = {
            "total_liked": 0,
            "new_tracks": 0,
            "processed": 0,
            "sorted": 0,
            "skipped": 0,
            "duplicates": 0,
            "errors": 0,
            "genre_matches": {}
        }
    
    def _load_processing_history(self) -> Dict:
        """Load processing history from file."""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                print(f"📜 Loaded processing history: {len(history.get('processed_tracks', {}))} tracks")
                return history
        except FileNotFoundError:
            print("📜 No processing history found. Starting fresh.")
            return {
                "processed_tracks": {},  # track_id -> {processed_at, action, playlist_id}
                "last_run": None,
                "total_runs": 0,
                "start_date": None,  # Track when we started monitoring
                "start_index": None  # Track index position if using index-based
            }
        except json.JSONDecodeError as e:
            print(f"❌ Error loading processing history: {e}")
            return {"processed_tracks": {}, "last_run": None, "total_runs": 0}
    
    def _save_processing_history(self):
        """Save processing history to file."""
        try:
            self.processing_history["last_run"] = datetime.now().isoformat()
            self.processing_history["total_runs"] += 1
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.processing_history, f, indent=2, ensure_ascii=False)
            print(f"💾 Processing history saved ({len(self.processing_history['processed_tracks'])} tracks)")
        except Exception as e:
            print(f"❌ Error saving processing history: {e}")
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"✅ Loaded configuration with {len(config.get('rules', {}))} genre rules")
                return config
        except FileNotFoundError:
            print(f"❌ Configuration file '{config_file}' not found.")
            return {"rules": {}, "settings": {"check_limit": 50}}
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing configuration file: {e}")
            return {}
    
    def initialize_baseline(self, mode: str = "date", start_date: str = None, start_index: int = None):
        """
        Initialize the baseline for processing - mark existing songs as processed without actually processing them.
        
        Args:
            mode: "date" or "index" - how to determine starting point
            start_date: ISO date string (YYYY-MM-DD) for date mode
            start_index: Index position for index mode
        """
        if self.processing_history.get("start_date") or self.processing_history.get("start_index"):
            print("📊 Baseline already initialized. Skipping initialization.")
            return
        
        print("🔧 Initializing baseline - marking existing songs as processed...")
        
        # Get all liked songs
        all_tracks = self.get_all_liked_songs()
        
        if mode == "date":
            if not start_date:
                start_date = date.today().isoformat()
            
            print(f"📅 Using date-based filtering: songs liked before {start_date} will be marked as processed")
            self.processing_history["start_date"] = start_date
            
            # Mark songs liked before start_date as processed
            baseline_count = 0
            for track in all_tracks:
                liked_at = track.get("liked_at", "")
                if liked_at and liked_at[:10] < start_date:
                    self._mark_as_baseline_processed(track)
                    baseline_count += 1
            
            print(f"📊 Marked {baseline_count} songs (liked before {start_date}) as baseline processed")
            
        elif mode == "index":
            if start_index is None:
                start_index = len(all_tracks)  # Start from end (newest)
            
            print(f"📍 Using index-based filtering: first {start_index} songs will be marked as processed")
            self.processing_history["start_index"] = start_index
            
            # Mark first N songs as processed (they're ordered newest first)
            baseline_count = min(start_index, len(all_tracks))
            for i in range(baseline_count):
                self._mark_as_baseline_processed(all_tracks[i])
            
            print(f"📊 Marked first {baseline_count} songs as baseline processed")
        
        # Save the baseline
        self._save_processing_history()
        print("✅ Baseline initialization complete!")
    
    def _mark_as_baseline_processed(self, track: Dict):
        """Mark a track as baseline processed (without actually processing it)."""
        track_id = track.get("id")
        if track_id:
            self.processing_history["processed_tracks"][track_id] = {
                "processed_at": datetime.now().isoformat(),
                "action": "baseline",
                "playlist_id": None,
                "reason": "Marked as baseline processed (existing song)",
                "track_name": track.get("name", "Unknown"),
                "artists": [artist["name"] for artist in track.get("artists", [])]
            }
    
    def get_all_liked_songs(self) -> List[Dict]:
        """
        Get ALL liked songs to find new ones since last run.
        
        Returns:
            List of all liked songs with timestamps (newest first)
        """
        all_tracks = []
        offset = 0
        limit = 50
        
        print("🔍 Fetching all liked songs...")
        
        while True:
            url = f"{self.base_url}/me/tracks"
            params = {
                "limit": limit,
                "offset": offset,
                "market": "from_token"
            }
            
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    break
                
                # Add tracks with metadata
                for item in items:
                    track = item.get("track")
                    if track and track.get("id"):
                        track["liked_at"] = item.get("added_at")
                        all_tracks.append(track)
                
                offset += len(items)
                
                # Show progress every 200 songs
                if len(all_tracks) % 200 == 0:
                    print(f"   Fetched {len(all_tracks)} songs so far...")
                
                # Rate limiting
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching liked songs: {e}")
                break
        
        print(f"✅ Fetched {len(all_tracks)} total liked songs")
        return all_tracks
    
    def filter_new_tracks(self, all_tracks: List[Dict]) -> List[Dict]:
        """
        Filter out tracks that have already been processed.
        
        Args:
            all_tracks: All liked songs (newest first)
            
        Returns:
            Only new/unprocessed tracks
        """
        processed_track_ids = set(self.processing_history.get("processed_tracks", {}).keys())
        
        new_tracks = []
        for track in all_tracks:
            track_id = track.get("id")
            if track_id and track_id not in processed_track_ids:
                new_tracks.append(track)
        
        return new_tracks
    
    def get_artist_genres_batch(self, artist_ids: List[str]) -> Dict[str, List[str]]:
        """Get genres for multiple artists efficiently."""
        # Check cache first
        uncached_ids = [aid for aid in artist_ids if aid not in self.artist_genre_cache]
        
        if uncached_ids:
            # Batch request for uncached artists
            batch_size = 50
            for i in range(0, len(uncached_ids), batch_size):
                batch = uncached_ids[i:i + batch_size]
                
                url = f"{self.base_url}/artists"
                params = {"ids": ",".join(batch)}
                
                try:
                    response = requests.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    artists = data.get("artists", [])
                    
                    for artist in artists:
                        if artist:
                            artist_id = artist.get("id")
                            genres = artist.get("genres", [])
                            self.artist_genre_cache[artist_id] = genres
                    
                    time.sleep(0.1)
                    
                except requests.exceptions.RequestException as e:
                    print(f"❌ Error fetching artist genres: {e}")
                    for aid in batch:
                        self.artist_genre_cache[aid] = []
        
        return {aid: self.artist_genre_cache.get(aid, []) for aid in artist_ids}
    
    def get_track_genres(self, track: Dict) -> List[str]:
        """Get all genres for a track's artists."""
        artists = track.get("artists", [])
        if not artists:
            return []
        
        artist_ids = [artist.get("id") for artist in artists if artist.get("id")]
        if not artist_ids:
            return []
        
        artist_genres_map = self.get_artist_genres_batch(artist_ids)
        
        all_genres = []
        for artist_id in artist_ids:
            genres = artist_genres_map.get(artist_id, [])
            all_genres.extend(genres)
        
        # Return unique genres
        return list(dict.fromkeys(all_genres))
    
    def match_genres_to_playlist(self, genres: List[str]) -> Optional[Dict]:
        """Match genres to playlist rules."""
        case_sensitive = self.settings.get("case_sensitive", False)
        partial_match = self.settings.get("partial_match", True)
        
        for genre in genres:
            genre_check = genre if case_sensitive else genre.lower()
            
            for rule_genre, playlist_id in self.rules.items():
                rule_check = rule_genre if case_sensitive else rule_genre.lower()
                
                match_found = False
                match_type = ""
                
                if partial_match:
                    if rule_check in genre_check:
                        match_found = True
                        match_type = "partial_rule_in_genre"
                    elif genre_check in rule_check:
                        match_found = True
                        match_type = "partial_genre_in_rule"
                else:
                    if rule_check == genre_check:
                        match_found = True
                        match_type = "exact"
                
                if match_found:
                    return {
                        "playlist_id": playlist_id,
                        "matched_genre": genre,
                        "rule_genre": rule_genre,
                        "match_type": match_type
                    }
        
        return None
    
    def get_playlist_tracks_set(self, playlist_id: str) -> Set[str]:
        """Get all track IDs from a playlist."""
        if not hasattr(self, '_playlist_cache'):
            self._playlist_cache = {}
        
        cache_key = f"playlist_tracks_{playlist_id}"
        if cache_key in self._playlist_cache:
            return self._playlist_cache[cache_key]
        
        track_ids = set()
        url = f"{self.base_url}/playlists/{playlist_id}/tracks"
        
        while url:
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get("items", []):
                    if item["track"] and item["track"]["id"]:
                        track_ids.add(item["track"]["id"])
                
                url = data.get("next")
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching playlist tracks: {e}")
                break
        
        self._playlist_cache[cache_key] = track_ids
        return track_ids
    
    def add_track_to_playlist(self, playlist_id: str, track_id: str) -> bool:
        """Add track to playlist."""
        url = f"{self.base_url}/playlists/{playlist_id}/tracks"
        data = {"uris": [f"spotify:track:{track_id}"]}
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            # Invalidate cache
            cache_key = f"playlist_tracks_{playlist_id}"
            if hasattr(self, '_playlist_cache') and cache_key in self._playlist_cache:
                del self._playlist_cache[cache_key]
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error adding track to playlist: {e}")
            return False
    
    def process_track(self, track: Dict) -> Dict:
        """Process a single track."""
        result = {
            "track_name": track.get("name", "Unknown"),
            "artist_names": [artist["name"] for artist in track.get("artists", [])],
            "track_id": track.get("id"),
            "liked_at": track.get("liked_at"),
            "action": "skipped",
            "reason": "",
            "playlist_id": None,
            "match_details": None,
            "genres_found": []
        }
        
        track_id = track.get("id")
        if not track_id:
            result["reason"] = "Invalid track ID"
            return result
        
        # Get genres
        genres = self.get_track_genres(track)
        result["genres_found"] = genres
        
        if not genres:
            result["reason"] = "No genres found"
            return result
        
        # Match to playlist
        match = self.match_genres_to_playlist(genres)
        
        if not match:
            result["reason"] = f"No rule match for genres: {', '.join(genres)}"
            return result
        
        playlist_id = match["playlist_id"]
        result["match_details"] = match
        
        # Check duplicates
        existing_tracks = self.get_playlist_tracks_set(playlist_id)
        if track_id in existing_tracks:
            result["action"] = "duplicate"
            result["reason"] = "Track already exists in target playlist"
            result["playlist_id"] = playlist_id
            return result
        
        # Add to playlist
        if self.add_track_to_playlist(playlist_id, track_id):
            result["action"] = "sorted"
            result["reason"] = f"Added to playlist (matched: {match['matched_genre']} → {match['rule_genre']})"
            result["playlist_id"] = playlist_id
            
            # Update stats
            matched_genre = match["rule_genre"]
            self.stats["genre_matches"][matched_genre] = self.stats["genre_matches"].get(matched_genre, 0) + 1
        else:
            result["action"] = "error"
            result["reason"] = "Failed to add track to playlist"
        
        return result
    
    def record_processing_result(self, track_id: str, result: Dict):
        """Record the processing result in history."""
        self.processing_history["processed_tracks"][track_id] = {
            "processed_at": datetime.now().isoformat(),
            "action": result["action"],
            "playlist_id": result.get("playlist_id"),
            "reason": result["reason"],
            "track_name": result["track_name"],
            "artists": result["artist_names"]
        }
    
    def run(self, initialize_mode: str = None, start_date: str = None, start_index: int = None) -> Dict:
        """
        Run incremental processing.
        
        Args:
            initialize_mode: "date" or "index" - how to initialize baseline
            start_date: ISO date string for date mode
            start_index: Index for index mode
        """
        print("🎵 AutoList Incremental - Smart Playlist Sorting")
        print("=" * 60)
        
        if not self.rules:
            print("❌ No sorting rules configured.")
            return self.stats
        
        print(f"📋 Loaded {len(self.rules)} sorting rules")
        
        # Initialize baseline if needed
        if initialize_mode and not (self.processing_history.get("start_date") or self.processing_history.get("start_index")):
            self.initialize_baseline(initialize_mode, start_date, start_index)
        
        # Get all liked songs
        all_tracks = self.get_all_liked_songs()
        self.stats["total_liked"] = len(all_tracks)
        
        if not all_tracks:
            print("📭 No liked songs found")
            return self.stats
        
        # Filter to only new tracks
        new_tracks = self.filter_new_tracks(all_tracks)
        self.stats["new_tracks"] = len(new_tracks)
        
        if not new_tracks:
            print(f"✅ No new tracks to process! All {len(all_tracks)} liked songs have been processed.")
            print(f"📊 Last run: {self.processing_history.get('last_run', 'Never')}")
            
            # Show baseline info
            if self.processing_history.get("start_date"):
                print(f"📅 Monitoring songs liked after: {self.processing_history['start_date']}")
            elif self.processing_history.get("start_index"):
                print(f"📍 Monitoring from index: {self.processing_history['start_index']}")
            
            return self.stats
        
        print(f"🆕 Found {len(new_tracks)} new tracks to process (out of {len(all_tracks)} total)")
        print("-" * 60)
        
        # Process new tracks
        for i, track in enumerate(new_tracks, 1):
            self.stats["processed"] += 1
            
            track_name = track.get("name", "Unknown")
            artists = ", ".join([a["name"] for a in track.get("artists", [])])
            liked_date = track.get("liked_at", "Unknown")[:10] if track.get("liked_at") else "Unknown"
            
            print(f"[{i:2d}/{len(new_tracks)}] {track_name} - {artists} (liked: {liked_date})")
            
            result = self.process_track(track)
            
            # Record result in history
            self.record_processing_result(track["id"], result)
            
            # Update stats and show result
            if result["action"] == "sorted":
                self.stats["sorted"] += 1
                print(f"  ✅ {result['reason']}")
            elif result["action"] == "duplicate":
                self.stats["duplicates"] += 1
                print(f"  🔄 {result['reason']}")
            elif result["action"] == "error":
                self.stats["errors"] += 1
                print(f"  ❌ {result['reason']}")
            else:  # skipped
                self.stats["skipped"] += 1
                print(f"  ⏭️  {result['reason']}")
            
            time.sleep(0.2)
        
        # Save processing history
        self._save_processing_history()
        
        # Print summary
        self._print_summary()
        
        return self.stats
    
    def _print_summary(self):
        """Print processing summary."""
        print("\n" + "=" * 60)
        print("📊 INCREMENTAL PROCESSING SUMMARY")
        print("=" * 60)
        
        print(f"  Total Liked Songs: {self.stats['total_liked']}")
        print(f"  🆕 New Tracks Found: {self.stats['new_tracks']}")
        print(f"  📝 Processed: {self.stats['processed']}")
        print(f"  ✅ Successfully Sorted: {self.stats['sorted']}")
        print(f"  🔄 Duplicates Skipped: {self.stats['duplicates']}")
        print(f"  ⏭️  No Match (Skipped): {self.stats['skipped']}")
        print(f"  ❌ Errors: {self.stats['errors']}")
        
        if self.stats["new_tracks"] > 0:
            success_rate = (self.stats["sorted"] / self.stats["new_tracks"] * 100)
            print(f"  🎯 Success Rate: {success_rate:.1f}%")
        
        if self.stats["genre_matches"]:
            print(f"\n🎵 Genre Matches:")
            sorted_matches = sorted(self.stats["genre_matches"].items(), key=lambda x: x[1], reverse=True)
            for genre, count in sorted_matches:
                print(f"   {genre}: {count} tracks")

def main():
    """Main function with command line arguments."""
    parser = argparse.ArgumentParser(description='AutoList Incremental - Smart Playlist Sorting')
    parser.add_argument('--init', choices=['date', 'index'], help='Initialize baseline processing')
    parser.add_argument('--date', type=str, help='Start date for date mode (YYYY-MM-DD)')
    parser.add_argument('--index', type=int, help='Start index for index mode')
    
    args = parser.parse_args()
    
    access_token = os.getenv('SPOTIFY_ACCESS_TOKEN')
    
    if not access_token:
        print("❌ Spotify access token not found.")
        print("Please set the SPOTIFY_ACCESS_TOKEN environment variable.")
        return
    
    autolist = AutoListIncremental(access_token)
    
    # Determine initialization parameters
    init_mode = args.init
    start_date = args.date
    start_index = args.index
    
    # If no arguments provided, use smart defaults
    if not init_mode and not autolist.processing_history.get("start_date") and not autolist.processing_history.get("start_index"):
        print("🔧 No baseline found. Initializing with today's date...")
        init_mode = "date"
        start_date = date.today().isoformat()
    
    autolist.run(init_mode, start_date, start_index)

if __name__ == "__main__":
    main()