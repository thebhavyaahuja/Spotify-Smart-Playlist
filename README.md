# Spotify-Smart-Playlist - Automatic Spotify Playlist Sorting

I find adding to playlist feature very tedious personally for new songs I listen to. Most of them can fit into predictable playlists. Sometimes I'm not even sure if that song I'm liking is already is in the wanted(probable) playlist or not.

This tool automatically sorts your newly liked Spotify songs into your existing playlists based on artist genres.

![image](https://github.com/user-attachments/assets/0b51d9df-fa99-4083-8b30-37f5cd03edcc)

## Setup and Usage

1.  **Get Spotify API credentials:**
    *   Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create a new application.
    *   Once your app is created, note down your **Client ID** and **Client Secret**.
    *   In your application settings on the Spotify Developer Dashboard, add a **Redirect URI**. A common one for local development is `http://127.0.0.1:8888/callback` (ensure the port matches what `get_token.py` uses, which is 8888 by default).

2.  **Run the application:**
    Open your terminal, navigate to the `Spotify-Smart-Playlist` directory, and run:
    ```bash
    python3 app.py
    ```
    The application will guide you through the following steps:
    *   It will first attempt to load an existing `SPOTIFY_ACCESS_TOKEN` if you've run it before.
    *   Then, it will run `get_token.py`:
        *   You'll be prompted to **Enter your Spotify Client ID**.
        *   Next, **Enter your Spotify Client Secret**.
        *   The script will display a URL. **Copy this URL and paste it into your web browser.**
        *   Authorize the application in your browser. After authorization, Spotify will redirect you to the callback URI you set up (e.g., `http://127.0.0.1:8888/callback?code=...`).
        *   **Copy the part after "...code=" redirected URL from your browser's address bar.**
        *   Back in the terminal, you'll be prompted to **Enter the authorization code** (this refers to the `code` parameter in the redirected URL, but pasting the full redirected URL usually works as the script is designed to extract the code).
        *   If the token is obtained successfully, `app.py` will automatically use this token for the subsequent scripts.

3.  **Automatic Processing:**
    After successfully obtaining the token, `app.py` will automatically run the following scripts in sequence:
    *   `fetch_playlists.py`: Fetches your playlists from Spotify.
    *   `analyze_playlists.py`: Analyzes your playlists to generate sorting rules.
    *   `autolist_increment.py`: Sorts your newly liked songs based on the generated rules. The first run might use an `--init` flag (handled by `app.py`) to establish a baseline.

    You will see the output of each script in the terminal as it runs.

## How It Works 

The `app.py` script orchestrates the following underlying processes:

*   **`get_token.py`**: Handles the OAuth 2.0 flow to get an access token from Spotify.
*   **`fetch_playlists.py`**: Retrieves all your playlists and saves their details.
*   **`analyze_playlists.py`**:
    *   Scans your existing playlists to learn which genres are typically found in each.
    *   Creates automatic mappings (e.g., "garage rock" → "rock" playlist) based on this analysis.
*   **`autolist_increment.py`**:
    *   Fetches your recently liked songs.
    *   Compares them against a history of already processed songs.
    *   For new songs, it looks up the artist's genres.
    *   Uses the rules from `generated_config.json` (and partial genre matching) to decide which playlist a song belongs to and adds it.

## Files Created

*   `playlists.json`: A list of your Spotify playlists.
*   `playlist_mapping.json`: A simple mapping of playlist names to their IDs.
*   `generated_config.json`: Genre-to-playlist rules generated by `analyze_playlists.py`.
*   `processing_history.json`: Tracks processed songs to avoid duplicates and manage incremental updates.
*   `playlist_analysis.json`: Detailed analysis results from `analyze_playlists.py`.
*   `artist_genres.json`: A cache for artist genre lookups to speed up processing and reduce API calls.

## Options for `autolist_increment.py` (if run manually)

While `app.py` handles the typical workflow, `autolist_increment.py` can be run manually with options:

```bash
# Initialize with specific date (process songs liked since this date)
python3 autolist_increment.py --init date --date YYYY-MM-DD

# Initialize with index (skip the first N liked songs)
python3 autolist_increment.py --init index --index <number>
```
The `app.py` script typically runs `autolist_increment.py --init date` on its first successful setup or if `processing_history.json` is missing/empty, using the current date.

## Automation (Optional - Manual Setup)

If you want to run the sorting process regularly without manual intervention (after the initial setup with `app.py`), you can set up a cron job. Ensure `SPOTIFY_ACCESS_TOKEN` is available in the cron environment or modify `app.py` or `autolist_increment.py` to refresh the token if needed.

A cron job might look like this:
```bash
# Every 30 minutes, run app.py
*/30 * * * * cd /path/to/Spotify-Smart-Playlist && /usr/bin/python3 app.py >> /path/to/spotify_sorter.log 2>&1
```
*(Note: Managing token refresh within a fully automated cron job requires `get_token.py` to be non-interactive or for `app.py` to handle token expiry and re-authentication, which is an advanced setup.)*

**Result**: New songs you like are automatically sorted into the right playlists without any manual work. yay!

[TODO]
*   Sorting based on song's actual audio characteristics. Using vectors and distance to find the best playlist match.
*   More robust handling of token expiration and refresh, especially for automation.