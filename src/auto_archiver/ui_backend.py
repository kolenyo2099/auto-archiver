import os
import tempfile
import shutil
import json
import logging
import traceback

from flask import Flask, request, jsonify # Removed send_from_directory as it's not used yet

# Import the refactored extractors
from auto_archiver.modules.generic_extractor.generic_extractor import GenericExtractor
from auto_archiver.modules.instagram_extractor.instagram_extractor import InstagramExtractor
from auto_archiver.modules.twitter_api_extractor.twitter_api_extractor import TwitterApiExtractor

# Initialize Flask app
app = Flask(__name__)

# Setup basic logging if not run via __main__ where it's also configured
if __name__ != '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


EXTRACTOR_SCHEMAS = [
    {
        "id": "generic_extractor",
        "name": "Generic Extractor (yt-dlp)",
        "description": "Uses yt-dlp to download from many websites like YouTube, Vimeo, etc.",
        "params": [
            {"name": "allow_playlist", "label": "Allow Playlists", "type": "boolean", "default": False, "help_text": "Download entire playlists if URL is a playlist URL."},
            {"name": "max_downloads", "label": "Max Downloads (for playlists)", "type": "text", "default": "inf", "help_text": "Maximum number of items to download from a playlist ('inf' for no limit)."},
            {"name": "subtitles", "label": "Download Subtitles", "type": "boolean", "default": False, "help_text": "Attempt to download subtitles."},
            {"name": "comments", "label": "Download Comments", "type": "boolean", "default": False, "help_text": "Attempt to fetch comments (site-dependent)."},
            {"name": "livestreams", "label": "Download Livestreams", "type": "boolean", "default": False, "help_text": "Attempt to download ongoing livestreams."},
            {"name": "proxy", "label": "Proxy URL", "type": "text", "default": "", "help_text": "Optional proxy (e.g., http://user:pass@host:port)."},
            {"name": "ytdlp_args", "label": "Extra yt-dlp Arguments", "type": "text", "default": "", "help_text": "Additional command-line arguments for yt-dlp."},
            # Note: authentication_settings and extractor_args are complex dicts, might need special UI handling.
            # For simplicity in this schema, they are omitted or could be represented as JSON strings.
        ]
    },
    {
        "id": "instagram_extractor",
        "name": "Instagram Extractor",
        "description": "Uses Instaloader to download from Instagram. Login is recommended. (Not actively maintained)",
        "params": [
            {"name": "username", "label": "Instagram Username", "type": "text", "default": "", "help_text": "Required for login."},
            {"name": "password", "label": "Instagram Password", "type": "password", "default": "", "help_text": "Required for login."},
            {"name": "session_file", "label": "Session File Path", "type": "text", "default": "", "help_text": "Path to Instaloader session file (alternative to user/pass)."},
            {"name": "download_geotags", "label": "Download Geotags", "type": "boolean", "default": True},
            {"name": "download_comments", "label": "Download Comments", "type": "boolean", "default": True},
        ]
    },
    {
        "id": "twitter_api_extractor",
        "name": "Twitter API Extractor",
        "description": "Uses the Twitter API (via pytwitter) to fetch tweet details and media.",
        "params": [
            # For simplicity, bearer_tokens is a JSON string array if multiple are needed.
            {"name": "bearer_token", "label": "Bearer Token", "type": "password", "default": "", "help_text": "Twitter API v2 Bearer Token."},
            # Could add fields for consumer_key, consumer_secret, access_token, access_secret if needed by UI
        ]
    }
]

EXTRACTOR_MAP = {
    "generic_extractor": GenericExtractor,
    "instagram_extractor": InstagramExtractor,
    "twitter_api_extractor": TwitterApiExtractor,
}

@app.route('/api/ui/extractors', methods=['GET'])
def get_extractors_schema():
    return jsonify(EXTRACTOR_SCHEMAS)

@app.route('/api/ui/extract', methods=['POST'])
def extract_content():
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"status": "error", "message": "Invalid JSON payload."}), 400
    except Exception as e:
        logging.error(f"Failed to parse JSON payload: {e}")
        return jsonify({"status": "error", "message": f"Failed to parse JSON payload: {str(e)}"}), 400

    extractor_id = payload.get('extractor_id')
    url = payload.get('url')
    output_path = payload.get('output_path')
    config_values = payload.get('config_values', {}) # Default to empty dict

    # --- Input Validation ---
    if not extractor_id:
        return jsonify({"status": "error", "message": "Missing 'extractor_id'."}), 400
    if not url:
        return jsonify({"status": "error", "message": "Missing 'url'."}), 400
    if not output_path:
        return jsonify({"status": "error", "message": "Missing 'output_path'."}), 400
    if not os.path.isabs(output_path):
        # For security and clarity, demand absolute paths from the client if it's creating them.
        # Alternatively, the backend could make it relative to a predefined base output directory.
        # For this iteration, require absolute.
        return jsonify({"status": "error", "message": "'output_path' must be an absolute path."}), 400

    ExtractorClass = EXTRACTOR_MAP.get(extractor_id)
    if not ExtractorClass:
        return jsonify({"status": "error", "message": f"Unknown extractor ID: {extractor_id}"}), 400

    # --- Instantiate Extractor ---
    try:
        # Process config_values for type conversion (e.g., string "true" to boolean True)
        # This is a basic approach; more robust type coercion should ideally be in extractor __init__ methods.
        processed_config_values = {}
        schema_params = next((s['params'] for s in EXTRACTOR_SCHEMAS if s['id'] == extractor_id), [])

        for param_info in schema_params:
            param_name = param_info['name']
            if param_name in config_values: # Only process if provided
                value = config_values[param_name]
                param_type = param_info['type']

                if param_type == 'boolean':
                    if isinstance(value, str):
                        processed_config_values[param_name] = value.lower() == 'true'
                    else: # Assume already boolean or None
                        processed_config_values[param_name] = bool(value)
                elif param_type == 'number': # Example if we had a number type
                    try:
                        processed_config_values[param_name] = int(value) # Or float(value)
                    except ValueError:
                        logging.warning(f"Could not convert param '{param_name}' value '{value}' to number, using as is.")
                        processed_config_values[param_name] = value
                else: # text, password, etc.
                    processed_config_values[param_name] = value
            elif 'default' in param_info: # Use schema default if not provided
                 processed_config_values[param_name] = param_info['default']


        # Special handling for Twitter bearer_tokens list if only single bearer_token is in schema
        if extractor_id == "twitter_api_extractor" and "bearer_token" in processed_config_values:
            bt = processed_config_values.pop("bearer_token") # Remove single
            processed_config_values["bearer_tokens"] = [bt] if bt else [] # Pass as list

        logging.info(f"Instantiating {ExtractorClass.__name__} with config: {processed_config_values}")
        extractor_instance = ExtractorClass(**processed_config_values)
    except Exception as e:
        logging.error(f"Failed to instantiate extractor {extractor_id}: {e}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": f"Failed to instantiate extractor: {str(e)}"}), 500

    # --- Extraction Process ---
    # Using a temporary directory that the extractor will use for its downloads.
    # Files will then be moved to the user-specified output_path.
    with tempfile.TemporaryDirectory(prefix="autoarchiver_backend_") as backend_tmp_dir:
        logging.info(f"Using temporary directory for extraction: {backend_tmp_dir} for URL: {url}")
        try:
            extracted_data_list_or_dict = extractor_instance.extract_data(url=url, tmp_dir_path=backend_tmp_dir)

            if not extracted_data_list_or_dict:
                logging.warning(f"Extractor {extractor_id} returned no data for URL {url}.")
                return jsonify({"status": "error", "message": "Extractor returned no data."}), 500 # Or 200 with empty data?

            # Ensure output_path exists
            try:
                os.makedirs(output_path, exist_ok=True)
            except OSError as e:
                logging.error(f"Failed to create output directory {output_path}: {e}")
                return jsonify({"status": "error", "message": f"Failed to create output directory: {str(e)}"}), 500

            processed_results_list = []
            # Standardize to list for easier processing, even if extractor returns a single dict
            input_data_list = extracted_data_list_or_dict if isinstance(extracted_data_list_or_dict, list) else [extracted_data_list_or_dict]

            for single_extraction_result in input_data_list:
                current_media_items_for_this_result = []
                if "media" in single_extraction_result and single_extraction_result["media"]:
                    for media_item in single_extraction_result["media"]:
                        original_temp_filepath = media_item.get('filepath')
                        if not original_temp_filepath or not os.path.exists(original_temp_filepath):
                            logging.warning(f"Media item file path missing or file does not exist: {original_temp_filepath} for URL {url}. Skipping this media item.")
                            continue

                        destination_filename = os.path.basename(original_temp_filepath)

                        # Ensure unique filenames in destination to prevent overwrites
                        counter = 0
                        base, ext = os.path.splitext(destination_filename)
                        final_destination_path = os.path.join(output_path, destination_filename)

                        while os.path.exists(final_destination_path):
                            counter += 1
                            final_destination_path = os.path.join(output_path, f"{base}_{counter}{ext}")

                        try:
                            shutil.move(original_temp_filepath, final_destination_path)
                            logging.info(f"Moved media file from {original_temp_filepath} to {final_destination_path}")
                            new_media_item = media_item.copy()
                            new_media_item['filepath'] = final_destination_path # Store absolute final path
                            current_media_items_for_this_result.append(new_media_item)
                        except Exception as e_move:
                            logging.error(f"Failed to move media file {original_temp_filepath} to {final_destination_path}: {e_move}")
                            # Decide if we should include this media item with its original temp path or skip
                            # For now, skipping if move fails.

                result_copy = single_extraction_result.copy()
                result_copy["media"] = current_media_items_for_this_result
                processed_results_list.append(result_copy)

            # Return single dict if input was single, list if input was list (from extractor)
            final_data_to_return = processed_results_list[0] if not isinstance(extracted_data_list_or_dict, list) and processed_results_list else processed_results_list

            logging.info(f"Successfully extracted and processed data for URL {url} to {output_path}.")
            return jsonify({"status": "success", "data": final_data_to_return, "logs": ["Extraction successful."]})

        except Exception as e:
            logging.error(f"Extraction failed for URL {url} with extractor {extractor_id}: {e}\n{traceback.format_exc()}")
            return jsonify({"status": "error", "message": f"Extraction error: {str(e)}", "logs": [traceback.format_exc()]}), 500

if __name__ == '__main__':
    # Configure logging for when running this script directly
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set Flask's logger to the same level
    # app.logger.setLevel(logging.INFO) # Not needed as Flask uses root logger by default if not configured itself.

    # Get host and port from environment variables or use defaults
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    logging.info(f"Starting Flask app on {host}:{port} (Debug: {debug_mode})")
    app.run(debug=debug_mode, host=host, port=port)
