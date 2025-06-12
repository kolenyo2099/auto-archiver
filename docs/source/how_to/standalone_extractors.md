# Using Extractors Standalone

## Overview

Several extractors within `auto-archiver` are designed to be reusable and can be employed independently in other Python projects or scripts. These extractors encapsulate the logic for fetching metadata and media from specific platforms or generic URLs. They output data in a standardized dictionary format, making them easy to integrate.

This guide explains the general pattern for using these extractors and provides details for specific ones like `GenericExtractor`, `InstagramExtractor`, and `TwitterApiExtractor`.

## General Usage Pattern

The following example demonstrates a common workflow for using a refactored extractor:

```python
import os
import logging
from tempfile import TemporaryDirectory

# Replace with the specific extractor you want to use
from auto_archiver.modules.generic_extractor.generic_extractor import GenericExtractor

# Configure basic logging for the example
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 1. Configuration for the chosen extractor
# This example uses GenericExtractor. Refer to specific extractor sections for required parameters.
extractor_config = {
    "ytdlp_update_interval": -1,        # Disable yt-dlp auto-updates for this example
    "bguils_po_token_method": "disabled", # Disable Proof of Origin token generation
    "authentication_settings": {},      # No authentication needed for public content
    # "proxy": "http://yourproxy:port", # Optional: if you need a proxy
    "extractor_args": {"quiet": True} # Pass 'quiet' to yt-dlp to reduce console noise
}

# 2. Instantiate the extractor
try:
    # Note: 'tmp_dir_path_for_orchestrator' is primarily for when the extractor is used
    # within the auto-archiver's main 'download()' flow. For direct 'extract_data()' usage,
    # the 'tmp_dir_path' argument to 'extract_data()' is the important one.
    extractor = GenericExtractor(**extractor_config)
    # For some extractors, an explicit setup call might be relevant if not done in __init__
    # extractor.setup()
except Exception as e:
    logging.error(f"Failed to instantiate extractor: {e}", exc_info=True)
    exit(1)

# 3. Prepare Temporary Directory for downloads
# The 'extract_data' method requires a 'tmp_dir_path' where all downloaded files will be stored.
with TemporaryDirectory() as tmpdir:
    logging.info(f"Using temporary directory for downloads: {tmpdir}")

    # Example URL (Me at the zoo - first YouTube video)
    # Ensure URL is accessible and public for testing without authentication
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

    # 4. Extract Data
    try:
        logging.info(f"Attempting to extract data from: {test_url}")
        # The 'tmp_dir_path' provided here is where media files will be downloaded.
        data = extractor.extract_data(url=test_url, tmp_dir_path=tmpdir)

        if data:
            logging.info("Extraction successful!")
            # Data can be a single dictionary or a list of dictionaries (e.g., for playlists)
            display_data_list = data if isinstance(data, list) else [data]

            for i, item_data in enumerate(display_data_list):
                logging.info(f"--- Item {i+1} ---")
                logging.info(f"  Metadata: {item_data.get('metadata', {}).get('title', 'N/A')}")
                # For brevity, you might print limited metadata fields or use json.dumps for full view
                # import json
                # logging.info(f"  Full Metadata: {json.dumps(item_data.get('metadata'), indent=2)}")

                media_items = item_data.get('media', [])
                logging.info(f"  Media items found: {len(media_items)}")
                for media_item in media_items:
                    logging.info(f"    - File: {media_item.get('filepath')}")
                    logging.info(f"      Type: {media_item.get('type')}, Original URL: {media_item.get('original_url', 'N/A')}")
                    # Verify file existence (optional, for confirmation)
                    if os.path.exists(media_item.get('filepath', '')):
                        logging.info(f"      File exists at path. Size: {os.path.getsize(media_item['filepath'])} bytes.")
                    else:
                        logging.warning(f"      File NOT found at path: {media_item.get('filepath')}")

                logging.info(f"  Extractor Info: {item_data.get('extractor_info')}")
        else:
            logging.warning(f"Failed to extract data for URL: {test_url}. No data returned.")

    except Exception as e:
        logging.error(f"An error occurred during extraction for {test_url}: {e}", exc_info=True)

# Note: The TemporaryDirectory context manager automatically cleans up 'tmpdir' and its contents.
# If not using a context manager, ensure manual cleanup of the temporary directory.
```

## Output Structure

The `extract_data()` method of a refactored extractor returns a dictionary (or a list of dictionaries in cases like playlists) with the following structure:

```json
{
  "metadata": {
    // Common metadata fields:
    "title": "Title of the content",
    "description": "Description of the content (can be plain text or HTML)",
    "timestamp": "ISO 8601 datetime string (UTC) of content creation/upload",
    "original_url": "The URL provided to extract_data or a canonical version",
    "uploader": "Name of the uploader/author",
    "author": "Alias for uploader", // Often same as uploader
    "uploader_id": "Platform-specific ID of the uploader",
    "channel": "Name of the channel, if applicable",
    "channel_id": "Platform-specific ID of the channel",
    "duration": "Duration in seconds (for A/V media)",
    "tags": ["list", "of", "tags"],
    "categories": ["list", "of", "categories"],
    "view_count": 12345,
    "like_count": 123,
    "comment_count": 12,
    "age_limit": 0, // Or specific age if restricted
    "live_status": "not_live", // Or "is_live", "was_live", "is_upcoming"
    // Extractor-specific raw data (optional, content varies):
    "raw_yt_dlp_info": { /* ... if from GenericExtractor ... */ },
    "raw_instaloader_info": { /* ... if from InstagramExtractor ... */ },
    "tweet_data": { /* ... if from TwitterApiExtractor (this is the main tweet object) ... */ },
    "author_data": { /* ... user object for the tweet author from TwitterApiExtractor ... */ }
    // ... other platform-specific metadata fields ...
  },
  "media": [
    {
      "filepath": "/absolute/path/to/downloaded/media_file.mp4", // Absolute path
      "type": "video", // General type: "video", "image", "audio", "subtitle", "thumbnail", etc.
      "mimetype": "video/mp4", // Specific MIME type if available
      "original_url": "URL from where this specific media file was downloaded",
      "id": "cover", // Optional: identifier like 'cover' for a thumbnail
      "language": "en", // Optional: for subtitles
      "text_content": "...", // Optional: for subtitles, the text content
      // ... other media-specific fields like width, height, duration_ms, alt_text ...
    }
    // ... more media items ...
  ],
  "extractor_info": "name_of_extractor_or_library_used (e.g., yt-dlp_youtube, instagram_instaloader, twitter_api)"
}
```

**Key points about the output:**
- **`metadata`**: A dictionary containing various pieces of information about the content. Field availability varies by extractor and source.
- **`media`**: A list of dictionaries, where each dictionary represents a downloaded file (video, image, audio, subtitle, thumbnail, etc.).
    - **`filepath`**: Always an absolute path to the downloaded file within the `tmp_dir_path` you provided to `extract_data()`.
    - **`type`**: A general category for the media.
- **`extractor_info`**: A string indicating which underlying tool or library (and often which specific part of it) was used for the extraction.

## Specific Extractors

### 1. GenericExtractor

- **Module**: `auto_archiver.modules.generic_extractor.generic_extractor.GenericExtractor`
- **Description**: Uses `yt-dlp` (a fork of `youtube-dl`) to download videos and metadata from a vast number of websites.
- **Key `__init__` Parameters**:
    - `ytdlp_update_interval` (int): Days between `yt-dlp` auto-updates. Set to `-1` to disable.
    - `bguils_po_token_method` (str): Method for Proof of Origin tokens for `bgutil-ytdlp-pot-provider` (e.g., "auto", "script", "disabled").
    - `proxy` (str, optional): Proxy URL (e.g., "http://user:pass@host:port").
    - `max_downloads` (str): Max downloads for playlists (e.g., "10", "inf" for no limit).
    - `allow_playlist` (bool): Whether to download entire playlists if URL is a playlist URL.
    - `subtitles` (bool): If true, attempts to download subtitles.
    - `comments` (bool): If true, attempts to fetch comments (via `yt-dlp`, site-dependent).
    - `livestreams` (bool): Whether to attempt downloading ongoing livestreams.
    - `ytdlp_args` (str, optional): Additional command-line arguments for `yt-dlp`.
    - `extractor_args` (dict, optional): Extractor-specific arguments for `yt-dlp` (e.g., `{"youtube": {"skip": ["dash", "hls"]}}`).
    - `authentication_settings` (dict, optional): For providing credentials to `yt-dlp` (e.g., for private videos). Structure depends on `yt-dlp` needs. Example: `{"youtube": {"username": "...", "password": "..."}}`.
    - `dropin_paths` (list[str], optional): List of directory paths for custom `yt-dlp` dropin modules.
- **Main External Library**: `yt-dlp`
- **Notes**:
    - Extremely versatile due to `yt-dlp`'s broad compatibility.
    - Output for playlists will be a list of dictionaries, each following the standard output structure.

### 2. InstagramExtractor

- **Module**: `auto_archiver.modules.instagram_extractor.instagram_extractor.InstagramExtractor`
- **Description**: Uses `instaloader` to download content from Instagram (posts, profiles).
- **Key `__init__` Parameters**:
    - `username` (str, optional): Instagram username for login.
    - `password` (str, optional): Instagram password for login.
    - `session_file` (str, optional): Path to an Instaloader session file for login.
    - `download_folder_name` (str): Name of the sub-folder created within the `tmp_dir_path` to store downloads (default: "instagram_media").
    - `download_geotags` (bool): Whether to download geotags with posts.
    - `download_comments` (bool): Whether to download comments with posts.
- **Main External Library**: `instaloader`
- **Notes**:
    - **Maintenance Status**: This extractor is not actively maintained and may have issues due to Instagram's frequent changes. Consider alternative Instagram extractors if available.
    - Login (via username/password or session file) is usually required for reliable operation.
    - `extract_data` will create a subfolder (specified by `download_folder_name`) inside the provided `tmp_dir_path`. `instaloader` then downloads into target-specific subfolders (e.g., profile name) within that. These are cleaned up automatically by `extract_data`.

### 3. TwitterApiExtractor

- **Module**: `auto_archiver.modules.twitter_api_extractor.twitter_api_extractor.TwitterApiExtractor`
- **Description**: Uses the Twitter API (via `pytwitter` library) to fetch tweet details and media.
- **Key `__init__` Parameters**:
    - `bearer_tokens` (list[str], optional): List of Twitter API v2 Bearer Tokens.
    - `bearer_token` (str, optional): Single Bearer Token (for backward compatibility, appended to `bearer_tokens`).
    - `consumer_key` (str, optional): Twitter API v1.1 Consumer Key.
    - `consumer_secret` (str, optional): Twitter API v1.1 Consumer Secret.
    - `access_token` (str, optional): Twitter API v1.1 Access Token.
    - `access_secret` (str, optional): Twitter API v1.1 Access Secret.
- **Main External Library**: `pytwitter`
- **Notes**:
    - Requires valid Twitter API credentials. You can provide multiple Bearer Tokens, and the extractor will cycle through them if one fails.
    - Fetches tweet details including text, author information, creation date, and associated media (images, videos, GIFs).
    - Media is downloaded to the provided `tmp_dir_path`.

## Error Handling

- If `extract_data()` fails to retrieve or process content for any reason (e.g., network error, invalid URL, authentication failure, content not found, library error), it will typically log an error and return `None`.
- More specific exceptions might be raised by the underlying libraries (`yt-dlp`, `instaloader`, `pytwitter`) in some cases, so using a `try...except` block as shown in the general usage pattern is recommended.

## Dependencies Installation

To use these extractors standalone, you'll need to install `auto-archiver` itself and the main external libraries used by the specific extractor(s) you intend to use.

1.  **Install `auto-archiver` (core)**:
    ```bash
    pip install auto-archiver
    ```
    This will install the core framework but might not include all optional extractor dependencies.

2.  **Install Extractor-Specific Dependencies**:
    - **For `GenericExtractor`**:
      ```bash
      pip install yt-dlp
      # Optional, for PO Token script method with bgutil-ytdlp-pot-provider
      # Ensure Node.js, yarn, npx are installed, then:
      # pip install bgutil-ytdlp-pot-provider
      ```
    - **For `InstagramExtractor`**:
      ```bash
      pip install instaloader
      ```
    - **For `TwitterApiExtractor`**:
      ```bash
      pip install pytwitter slugify
      ```
      (`slugify` is used for creating safe filenames from URLs/IDs).

You can also install `auto-archiver` with optional extras, which might cover some of these:
```bash
pip install auto-archiver[core] # For example, if such an extra is defined
# Check auto-archiver's setup.py or documentation for available extras.
```
If you have cloned the `auto-archiver` repository, you can often install all dependencies (including those for development and testing) using:
```bash
pip install -e .[dev]
# or similar, depending on the project's setup.cfg or pyproject.toml
```

Always refer to the primary documentation of `yt-dlp`, `instaloader`, and `pytwitter` for their specific installation instructions and dependencies if you encounter issues.
