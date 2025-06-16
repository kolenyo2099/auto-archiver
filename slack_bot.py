import os
import subprocess
import logging
import tempfile
import yaml
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    logging.error("SLACK_BOT_TOKEN or SLACK_APP_TOKEN not found! Please set them in your .env file.")
    exit(1)

app = App(token=SLACK_BOT_TOKEN)

# Path to your auto-archiver installation
AUTO_ARCHIVER_PATH = "/Users/guillen/Documents/auto-archiver2/.venv/bin/auto-archiver"
CONFIG_PATH = "/Users/guillen/Documents/auto-archiver2/secrets/orchestration.yaml"

def create_custom_config(folder_name):
    """Create a temporary config file with custom storage folder"""
    try:
        # Read the base config
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        # Modify the local_storage path
        config['local_storage']['save_to'] = f"./local_archive/{folder_name}"
        
        # Create temporary config file
        temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(config, temp_config, default_flow_style=False)
        temp_config.close()
        
        logging.info(f"Created temporary config for folder '{folder_name}': {temp_config.name}")
        return temp_config.name
        
    except Exception as e:
        logging.error(f"Failed to create custom config: {e}")
        return CONFIG_PATH  # Fall back to default config

@app.command("/archive")
def handle_archive_command(ack, respond, command):
    ack()
    text = command.get('text', '').strip()
    user_id = command.get('user_id')

    if not text:
        respond("Please provide a URL. Usage: `/archive <url>` or `/archive <folder_name> <url>`")
        return

    # Parse arguments: can be either "url" or "folder_name url"
    parts = text.split()
    
    if len(parts) == 1:
        # Format: /archive <url>
        folder_name = None
        url_to_archive = parts[0]
    elif len(parts) == 2:
        # Format: /archive <folder_name> <url>
        folder_name = parts[0]
        url_to_archive = parts[1]
    else:
        respond("Invalid format. Usage: `/archive <url>` or `/archive <folder_name> <url>`")
        return

    # Validate URL (basic check)
    if not (url_to_archive.startswith('http://') or url_to_archive.startswith('https://')):
        respond(f"Invalid URL: `{url_to_archive}`. Please provide a valid HTTP/HTTPS URL.")
        return

    # Validate folder name if provided
    if folder_name:
        # Remove potentially dangerous characters
        folder_name = "".join(c for c in folder_name if c.isalnum() or c in ('-', '_', '.'))
        if not folder_name:
            respond("Invalid folder name. Use only letters, numbers, hyphens, underscores, and dots.")
            return

    folder_display = f" in folder `{folder_name}`" if folder_name else ""
    logging.info(f"Received /archive from {user_id} for URL: {url_to_archive}{folder_display}")
    respond(f"Request received! Archiving `{url_to_archive}`{folder_display}. This may take a minute...")

    try:
        # Create custom config if folder specified
        config_to_use = CONFIG_PATH
        if folder_name:
            config_to_use = create_custom_config(folder_name)
        
        # Using the direct auto-archiver command instead of Docker
        command_to_run = [
            AUTO_ARCHIVER_PATH,
            "feed", 
            "--config", config_to_use,
            "--url", url_to_archive,
            "--feeder-name", "cli_feeder"
        ]
        
        process = subprocess.run(
            command_to_run,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
            cwd="/Users/guillen/Documents/auto-archiver2"
        )
        
        # Clean up temporary config if created
        if folder_name and config_to_use != CONFIG_PATH:
            try:
                os.remove(config_to_use)
            except:
                pass  # Don't fail if cleanup fails
        
        logging.info("Archiver process finished successfully.")
        archive_location = f"`local_archive/{folder_name}`" if folder_name else "`local_archive`"
        respond(f"✅ Successfully archived `{url_to_archive}`!\n\nCheck the {archive_location} folder for results.")

    except subprocess.CalledProcessError as e:
        logging.error(f"Archiver process failed for URL: {url_to_archive}")
        error_message = (
            f"❌ Failed to archive `{url_to_archive}`.\n\n"
            f"*Exit Code:* `{e.returncode}`\n\n"
            f"*Error Output:*\n```\n{e.stderr}\n```"
        )
        respond(error_message)
    except subprocess.TimeoutExpired:
        logging.error(f"Archiver process timed out for URL: {url_to_archive}")
        respond(f"❌ Archiving `{url_to_archive}` timed out after 10 minutes.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        respond(f"❌ An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    logging.info("Starting Slack Bot in Socket Mode...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start() 