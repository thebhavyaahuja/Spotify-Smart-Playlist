import os
import base64
import requests
import urllib.parse
from typing import Optional

class SpotifyAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:8888/callback"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-library-read"
    
    def get_auth_url(self) -> str:
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'show_dialog': 'true'
        }
        return f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    
    def get_access_token(self, auth_code: str) -> Optional[str]:
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
            return response.json().get('access_token')
        except requests.exceptions.RequestException as e:
            print(f"Error getting access token: {e}")
            return None

def set_env_variable(access_token: str):
    """
    Writes the access token export line to the user's shell profile.
    """
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        profile = os.path.expanduser("~/.zshrc")
    elif "bash" in shell:
        profile = os.path.expanduser("~/.bashrc")
    else:
        profile = os.path.expanduser("~/.profile")
    
    export_line = f"export SPOTIFY_ACCESS_TOKEN='{access_token}'\n"
    try:
        with open(profile, "a") as f:
            f.write(export_line)
        print(f"\n✅ Environment variable added to {profile}")
        print("Restart your terminal or run `source` on the file to activate it.")
    except Exception as e:
        print(f"⚠️ Failed to write environment variable to profile: {e}")

def main():
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
            set_env_variable(access_token)
        else:
            print("Failed to get access token.")
    else:
        print("Authorization code is required.")

if __name__ == "__main__":
    main()
