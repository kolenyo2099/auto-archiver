# Extractor UI Guide

## Introduction

The Extractor UI provides a user-friendly interface for running individual `auto-archiver` extractors directly through your web browser. This allows you to fetch metadata and media from various sources without directly editing YAML configuration files or running command-line scripts.

**Accessing the Extractor UI:**
You can access the Extractor UI from the main settings page (the YAML configuration page). Look for a button or link, typically labeled "Go to Extractor UI" or similar, usually positioned towards the top of the page. Clicking this will switch you to the Extractor UI interface. You can return to the YAML configurator using a "Back to YAML Configurator" button.

## UI Overview

The Extractor UI is organized into several sections to streamline the extraction process:

1.  **Extractor Selection:** A dropdown menu to choose the extractor you want to use (e.g., Generic Extractor for YouTube, Instagram Extractor, Twitter API Extractor).
2.  **Configuration Parameters:** Once an extractor is selected, this section dynamically displays its specific configuration options. Each option will have a label, an input field, and often a help text to explain its purpose.
3.  **Extraction Target:** Input fields for the content URL (the link to the media or page you want to archive) and the Output Directory Path (an absolute path on the server where downloaded media files will be saved).
4.  **Action Button:** A button to start the extraction process.
5.  **Results Display:** After extraction, this section shows the fetched metadata and a list of downloaded media files with their server paths.
6.  **Log Display:** Shows detailed logs from the extraction process, useful for monitoring progress and troubleshooting errors.

## Step-by-Step Guide

Follow these steps to use the Extractor UI:

1.  **Navigate to the UI:**
    Access the Extractor UI as described in the "Introduction" section.

2.  **Select an Extractor:**
    - Use the "Choose Extractor" dropdown to select the extractor best suited for the content you want to archive.
    - For example, choose "Generic Extractor (yt-dlp)" for YouTube videos or content from many other websites. Choose "Instagram Extractor" for Instagram posts/profiles, or "Twitter API Extractor" for tweets.

3.  **Configure Parameters:**
    - Once an extractor is selected, its specific configuration parameters will appear below the selector.
    - Fill in or adjust these parameters as needed. For example:
        - For `GenericExtractor`, you might want to enable "Allow Playlists" if your URL points to a playlist.
        - For `InstagramExtractor`, you'll likely need to provide your Instagram "Username" and "Password" or a "Session File Path".
        - For `TwitterApiExtractor`, you'll need to provide a "Bearer Token".
    - Each parameter usually has a descriptive label and a help icon or text explaining what it does. Default values are often pre-filled.

4.  **Input URL and Output Directory Path:**
    - **Content URL:** In the "Extraction Target" section, enter the full URL of the content you wish to extract (e.g., `https://www.youtube.com/watch?v=jNQXAC9IVRw`).
    - **Output Path:** Specify an **absolute local path on the server** where `auto-archiver` is running. This is where all downloaded media files (videos, images, etc.) will be saved. For example: `/mnt/archive/my_extractions/cool_video/`.
        - *Important*: Ensure this path is writable by the `auto-archiver` process.

5.  **Start Extraction:**
    - Click the "Start Extraction" button.
    - The UI will indicate that the process is running (e.g., the button might be disabled, and a loader may appear).

6.  **Understand Results:**
    - Once the extraction is complete, the **Results Display** section will populate.
    - **Metadata:** You'll see structured information about the extracted content (e.g., title, description, author, timestamps). This is often shown in a collapsible JSON view.
    - **Media:** A list of all media files downloaded by the extractor will be shown. Each entry typically includes:
        - `filepath`: The absolute path on the server where the file was saved (within your specified Output Directory Path).
        - `type`: The general type of media (e.g., "video", "image", "subtitle").
        - `original_url` (optional): The direct URL from which this specific media file was downloaded.
    - **Extractor Info:** Indicates the specific extractor module used.

7.  **Check Logs:**
    - The **Log Display** section shows messages generated during the extraction. This includes progress information, warnings, and any errors that occurred.
    - If an extraction fails or doesn't produce the expected output, the logs are the first place to look for clues.

## Available Extractors and Key Configurations

Here's a brief overview of the initially available extractors and some key configurations. For exhaustive details on each extractor's parameters and standalone usage, please refer to the [Standalone Extractors Guide](./standalone_extractors.md).

### 1. Generic Extractor (yt-dlp)
   - **Description:** Highly versatile, downloads from YouTube, Vimeo, and thousands of other sites supported by `yt-dlp`.
   - **Key Configurations:**
     - `Allow Playlists`: Set to true if your URL is a playlist and you want all items.
     - `Max Downloads`: Limits items from a playlist.
     - `Download Subtitles`: To fetch available subtitles.
     - `Proxy URL`: If you need to use a proxy for downloads.
   - **Note:** Does not usually require authentication for public content.

### 2. Instagram Extractor
   - **Description:** Downloads content from Instagram posts and profiles using `instaloader`.
   - **Key Configurations:**
     - `Instagram Username` / `Password` / `Session File Path`: Essential for logging into Instagram, which is often required for successful extraction.
   - **Note:** This extractor is marked as "not actively maintained" and might be unreliable due to Instagram's frequent platform changes.

### 3. Twitter API Extractor
   - **Description:** Fetches tweet details and media using the official Twitter API (v2) via `pytwitter`.
   - **Key Configurations:**
     - `Bearer Token`: Your Twitter API v2 Bearer Token is required.
   - **Note:** You need to have valid Twitter Developer API credentials.

## Basic Troubleshooting

- **Extraction Fails / No Data:**
    - Check the **Log Display** carefully for error messages. This is the most important diagnostic tool.
    - **Verify URL:** Ensure the URL is correct and accessible.
    - **Output Path:** Confirm the Output Directory Path is an absolute path on the server and is writable by the `auto-archiver` application.
    - **Extractor Configuration:** Double-check the parameters for the selected extractor. For example, Instagram and Twitter extractors will fail without proper authentication credentials.
    - **Network Issues:** Ensure the server running `auto-archiver` has internet access and can reach the target website (and any API endpoints the extractor uses). Proxies, if needed, must be configured correctly.
- **"Failed to fetch extractor schemas" or "Extractor not found":**
    - This indicates an issue with the backend API itself or the connection to it. Check the main `auto-archiver` server logs.
- **Media Files Not Appearing:**
    - Check logs for any download errors for specific media items.
    - Verify the `filepath` shown in the Results Display and ensure it matches the Output Directory Path you provided.

For more complex issues, you may need to consult the main `auto-archiver` application logs on the server.
