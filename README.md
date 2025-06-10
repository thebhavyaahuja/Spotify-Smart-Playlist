# Spotify-Smart-Playlist - Automatic Spotify Playlist Sorting

I find adding to playlist feature very tedious personally for new songs I listen to. Most of them can fit into predictable playlists. Sometimes I'm not even sure if that song I'm liking is already is in a good playlist or not.

This tool automatically sorts your newly liked Spotify songs into your existing playlists based on artist genres.

![image](https://github.com/user-attachments/assets/0b51d9df-fa99-4083-8b30-37f5cd03edcc)


## Quick Setup

1. **Get Spotify API credentials:**
   - Create app at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Add redirect URI: `http://127.0.0.1:<PORT>/callback`
   - Note your Client ID and Client Secret

2. **Get access token:**
   ```bash
   python3 get_token.py
   # Follow authorization flow, paste the token
   export SPOTIFY_ACCESS_TOKEN='your_token_here'
   ```

3. **Analyze your playlists** (generates smart rules):
   ```bash
   python3 analyze_playlists.py
   # Creates 'generated_config.json' with genre-to-playlist mappings
   ```

4. **Run automatic sorting:**
   ```bash
   # First run - sets up baseline (marks existing songs as processed)
   python3 autolist_increment.py
   
   # Future runs - only processes new liked songs
   python3 autolist_increment.py
   ```

## How It Works

Scans your existing playlists to learn which genres go where

Creates automatic mappings (e.g., "garage rock" → "rock" playlist)

Only processes newly liked songs, skips old ones

Uses partial genre matching for better coverage

## Files Created

- `generated_config.json` - Genre-to-playlist rules
- `processing_history.json` - Tracks processed songs
- `playlist_analysis.json` - Detailed analysis results

## Options

```bash
# Initialize with specific date
python3 autolist_increment.py --init date --date 2025-06-10

# Initialize with index (skip first N songs)
python3 autolist_increment.py --init index --index 1781
```

## Automation

Set up cron job for automatic processing:
```bash
# Every 5 minutes
*/5 * * * * cd /path/to/project && python3 autolist_increment.py
```

**Result**: New songs you like are automatically sorted into the right playlists without any manual work. yay!

[TODO]
Sorting based on song's actual audio characteristics. Using vectors and distance to find the best playlist match.
