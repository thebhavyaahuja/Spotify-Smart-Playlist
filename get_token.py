import base64
import requests
import urllib.parse
from typing import Optional

class SpotifyAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:8888/callback"):
        """
        Initialize Spotify authentication.
        
        Args:
            client_id: Your Spotify app client ID
            client_secret: Your Spotify app client secret
            redirect_uri: Redirect URI (must match your app settings)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        # UPDATED: Added user-library-read scope for accessing liked songs
        self.scope = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-library-read"
    
    def get_auth_url(self) -> str:
        """
        Get the authorization URL for user consent.
        
        Returns:
            Authorization URL
        """
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'show_dialog': 'true'
        }
        
        auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
        return auth_url
    
    def get_access_token(self, auth_code: str) -> Optional[str]:
        """
        Exchange authorization code for access token.
        
        Args:
            auth_code: Authorization code from callback
            
        Returns:
            Access token or None if failed
        """
        # Encode client credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri
        }
        
        try:
            response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data.get('access_token')
            
        except requests.exceptions.RequestException as e:
            print(f"Error getting access token: {e}")
            return None

def main():
    """
    Interactive token retrieval process.
    """
    print("Spotify Access Token Helper")
    print("=" * 30)
    
    client_id = input("Enter your Spotify Client ID: ").strip()
    client_secret = input("Enter your Spotify Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("Client ID and Client Secret are required.")
        return
    
    auth = SpotifyAuth(client_id, client_secret)
    
    print("\n1. Visit this URL to authorize the application:")
    print(auth.get_auth_url())
    
    print("\n2. After authorization, copy the 'code' parameter from the callback URL")
    auth_code = input("Enter the authorization code: ").strip()
    
    if auth_code:
        access_token = auth.get_access_token(auth_code)
        if access_token:
            print(f"\nAccess Token: {access_token}")
            print("\nYou can now use this token with the playlist fetcher.")
            print("Consider setting it as an environment variable:")
            print(f"export SPOTIFY_ACCESS_TOKEN='{access_token}'")
        else:
            print("Failed to get access token.")
    else:
        print("Authorization code is required.")

if __name__ == "__main__":
    main()

# ACCESS?: BQAKmxNpfQivzu2vXNXfSqkyDq1cLdcgSXdWstwf2TBBgw0TLOs0cgyLnUPkZcIylYEMbPu9v3IN5QqKIkbDf_cSyAYGKMaoqyPMLrrpOfPcVEHUOMu1UJbxMBDfPDvaxg95MiaYCK7Iv2AiqqM_j8IBMP3J0aE6d3_Zp2wXIRmstu2suK6yFQ5GlkA7IoqduuamYgKlopmwWAx5w9K1bgvfWMEhdCaeJqnlLyo1-ddE5UCLkeeHs4oQtjRTLw