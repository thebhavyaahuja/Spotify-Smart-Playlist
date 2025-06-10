import requests
import json
import os
from typing import List, Dict

class SpotifyPlaylistFetcher:
    def __init__(self, access_token: str):
        """
        Initialize the playlist fetcher with Spotify access token.
        
        Args:
            access_token: Spotify Web API access token
        """
        self.access_token = access_token
        self.base_url = "https://api.spotify.com/v1"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def fetch_all_playlists(self) -> List[Dict[str, str]]:
        """
        Fetch all user playlists from Spotify API.
        
        Returns:
            List of dictionaries containing playlist names and IDs
        """
        playlists = []
        url = f"{self.base_url}/me/playlists"
        
        while url:
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract playlist names and IDs
                for playlist in data.get('items', []):
                    playlists.append({
                        'name': playlist['name'],
                        'id': playlist['id'],
                        'owner': playlist['owner']['display_name'],
                        'tracks_total': playlist['tracks']['total']
                    })
                
                # Check for next page
                url = data.get('next')
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching playlists: {e}")
                break
        
        return playlists
    
    def save_playlists_to_file(self, playlists: List[Dict], filename: str = "playlists.json"):
        """
        Save playlists data to a JSON file.
        
        Args:
            playlists: List of playlist dictionaries
            filename: Output filename
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(playlists, f, indent=2, ensure_ascii=False)
            print(f"Playlists saved to {filename}")
        except Exception as e:
            print(f"Error saving playlists: {e}")
    
    def print_playlists(self, playlists: List[Dict]):
        """
        Print playlists in a formatted way.
        
        Args:
            playlists: List of playlist dictionaries
        """
        print(f"\nFound {len(playlists)} playlists:")
        print("-" * 80)
        for i, playlist in enumerate(playlists, 1):
            print(f"{i:2d}. {playlist['name']}")
            print(f"    ID: {playlist['id']}")
            print(f"    Owner: {playlist['owner']}")
            print(f"    Tracks: {playlist['tracks_total']}")
            print()

def main():
    """
    Main function to fetch and store Spotify playlists.
    """
    # Get access token from environment variable or user input
    access_token = os.getenv('SPOTIFY_ACCESS_TOKEN')
    
    if not access_token:
        print("Spotify access token not found in environment variables.")
        access_token = input("Please enter your Spotify access token: ").strip()
    
    if not access_token:
        print("Access token is required. Exiting.")
        return
    
    # Initialize fetcher and get playlists
    fetcher = SpotifyPlaylistFetcher(access_token)
    
    print("Fetching playlists from Spotify...")
    playlists = fetcher.fetch_all_playlists()
    
    if playlists:
        # Print playlists
        fetcher.print_playlists(playlists)
        
        # Save to file
        fetcher.save_playlists_to_file(playlists)
        
        # Also save a simple name-ID mapping
        simple_mapping = {playlist['name']: playlist['id'] for playlist in playlists}
        with open('playlist_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(simple_mapping, f, indent=2, ensure_ascii=False)
        print("Simple name-ID mapping saved to playlist_mapping.json")
        
    else:
        print("No playlists found or error occurred.")

if __name__ == "__main__":
    main()