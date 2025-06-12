"""Uses the Instaloader library to download content from Instagram. This class handles both individual posts
and user profiles, downloading as much information as possible, including images, videos, text, stories,
highlights, and tagged posts. Authentication is required via username/password or a session file.

"""

import datetime
import json
import mimetypes
import re
import os
import shutil
import instaloader
from loguru import logger

from auto_archiver.core import Extractor
from auto_archiver.core import Metadata
from auto_archiver.core import Media

# NB: post regex should be tested before profile
INSTAGRAM_DOMAIN_PATTERN = re.compile(r"(?:(?:http|https):\/\/)?(?:www.)?(?:instagram.com|instagr.am|instagr.com)\/")
# https://regex101.com/r/MGPquX/1
POST_PATTERN = re.compile(r"{INSTAGRAM_DOMAIN_PATTERN}(?:p|reel)\/(\w+)".format(INSTAGRAM_DOMAIN_PATTERN=INSTAGRAM_DOMAIN_PATTERN))
# https://regex101.com/r/6Wbsxa/1
PROFILE_PATTERN = re.compile(r"{INSTAGRAM_DOMAIN_PATTERN}(\w+)".format(INSTAGRAM_DOMAIN_PATTERN=INSTAGRAM_DOMAIN_PATTERN))
# TODO: links to stories

class InstagramExtractor(Extractor):
    """
    Uses Instaloader to download either a post (inc images, videos, text) or as much as possible from a profile (posts, stories, highlights, ...)
    """
    valid_url = INSTAGRAM_DOMAIN_PATTERN # So that Extractor.suitable() works

    def __init__(self,
                 username: str = None,
                 password: str = None,
                 session_file: str = None,
                 download_folder_name: str = "instagram_media", # sub-folder in tmp_dir
                 download_geotags: bool = True,
                 download_comments: bool = True,
                 tmp_dir_path_for_orchestrator: str = None # from self.tmp_dir.name
                 ):
        super().__init__()
        self._username = username
        self._password = password
        self._session_file = session_file
        self._download_folder_name = download_folder_name
        self._download_geotags = download_geotags
        self._download_comments = download_comments
        self._tmp_dir_path_for_orchestrator = tmp_dir_path_for_orchestrator

        self.insta = None # Will be initialized in setup
        self._setup_done = False

        # Hybrid config: if running in AA, override with AA config values
        if hasattr(self, "config"):
            self._username = self.config.get("INSTAGRAM_USERNAME", self._username)
            self._password = self.config.get("INSTAGRAM_PASSWORD", self._password)
            self._session_file = self.config.get("INSTAGRAM_SESSION_FILE", self._session_file)
            self._download_folder_name = self.config.get("INSTAGRAM_DOWNLOAD_FOLDER_NAME", self._download_folder_name)
            self._download_geotags = self.config.get("INSTAGRAM_DOWNLOAD_GEOTAGS", self._download_geotags)
            self._download_comments = self.config.get("INSTAGRAM_DOWNLOAD_COMMENTS", self._download_comments)
            if hasattr(self, "tmp_dir") and hasattr(self.tmp_dir, "name"):
                 self._tmp_dir_path_for_orchestrator = self.tmp_dir.name


    def setup(self) -> None:
        if self._setup_done:
            return

        logger.warning("Instagram Extractor is not actively maintained, and may not work as expected.")
        logger.warning("Please consider using the Instagram Tbot Extractor or Instagram API Extractor instead.")

        self.insta = instaloader.Instaloader(
            download_geotags=self._download_geotags,
            download_comments=self._download_comments,
            compress_json=False,
            # dirname_pattern will be relative to self.insta.context.cwd
            # filename_pattern structures files within the target folder
            filename_pattern="{date_utc}_UTC_{profile}__{typename}", # Using {profile} instead of {target} as target can be post owner for posts.
            dirname_pattern="{target}", # Organizes downloads into {target} named subfolders (e.g. profile name)
        )
        try:
            if self._username and self._session_file:
                self.insta.load_session_from_file(self._username, self._session_file)
                logger.info(f"Instaloader session loaded for {self._username}.")
            elif self._username and self._password:
                 logger.info(f"Attempting Instaloader login for {self._username}.")
                 self.insta.login(self._username, self._password)
                 if self._session_file:
                    self.insta.save_session_to_file(self._session_file)
                    logger.info(f"Instaloader session saved for {self._username} to {self._session_file}.")
            else:
                logger.warning("Instagram username/password or session_file not provided. Limited functionality.")
        except Exception as e:
            logger.error(f"Failed to setup Instagram Extractor with Instaloader: {e}", exc_info=True)
            # self.insta will exist but not be logged in. Instaloader might still work for public profiles.

        self._setup_done = True


    def download(self, item: Metadata) -> Metadata | bool:
        url = item.get_url()
        if not self._tmp_dir_path_for_orchestrator:
            logger.error("InstagramExtractor.download called without a temporary directory path for the orchestrator.")
            if hasattr(self, "tmp_dir") and hasattr(self.tmp_dir, "name"): # Fallback for AA context
                self._tmp_dir_path_for_orchestrator = self.tmp_dir.name
            else:
                item.status = "error_misconfigured_tmp_dir"
                return False

        extracted_data = self.extract_data(url, tmp_dir_path=self._tmp_dir_path_for_orchestrator)

        if not extracted_data:
            item.status = "error_no_data_extracted"
            return False

        item.set_title(extracted_data.get("metadata", {}).get("title", ""))
        item.set_content(json.dumps(extracted_data.get("metadata", {}), ensure_ascii=False, indent=2)) # Store all metadata as content

        timestamp_str = extracted_data.get("metadata", {}).get("timestamp")
        if timestamp_str:
            try:
                item.set_timestamp(datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")))
            except ValueError:
                 logger.warning(f"Could not parse timestamp from extracted data: {timestamp_str}")


        for media_info in extracted_data.get("media", []):
            if media_info.get("filepath") and os.path.exists(media_info["filepath"]):
                media_obj = Media(media_info["filepath"])
                media_obj.set("type", media_info.get("type"))
                if media_info.get("id"): media_obj.set("id", media_info.get("id"))
                item.add_media(media_obj)
            else:
                logger.warning(f"Media file path not found or invalid: {media_info.get('filepath')}")

        extractor_info = extracted_data.get("extractor_info", "instagram_instaloader_unknown")
        return item.success(extractor_info)


    def extract_data(self, url: str, tmp_dir_path: str) -> dict | None:
        self.setup() # Ensure Instaloader is configured and logged in
        if not self.insta:
            logger.error("Instaloader instance not available after setup.")
            return None

        effective_download_path = os.path.join(tmp_dir_path, self._download_folder_name)
        os.makedirs(effective_download_path, exist_ok=True)
        # Set instaloader's working directory for downloads
        self.insta.context.cwd = effective_download_path

        post_match = POST_PATTERN.search(url)
        profile_match = PROFILE_PATTERN.search(url)

        processed_data = None
        try:
            if post_match:
                post_id = post_match.group(1)
                logger.debug(f"Instagram post {post_id=} detected in {url=}")
                post = instaloader.Post.from_shortcode(self.insta.context, post_id)
                # Target for download_post will create a subfolder named after post.owner_username
                if self.insta.download_post(post, target=post.owner_username):
                    # The actual files are now in effective_download_path/post.owner_username/
                    # The _process_generic_downloads needs to know this target folder.
                    target_subfolder = os.path.join(effective_download_path, post.owner_username)
                    processed_data = self._process_generic_downloads(url, post.caption or f"Post by {post.owner_username}", post._asdict(), post.date_utc, target_subfolder)

            elif profile_match:
                username = profile_match.group(1)
                logger.debug(f"Instagram profile {username=} detected in {url=}")
                profile = instaloader.Profile.from_username(self.insta.context, username)

                # Downloads will go into effective_download_path/username/
                # Profile posts
                for post_obj in profile.get_posts():
                    try:
                        self.insta.download_post(post_obj, target=profile.username)
                    except Exception as e:
                        logger.error(f"Failed to download post {post_obj.shortcode} from profile {username}: {e}")
                # TODO: Add story, tagged, IGTV downloads if necessary, similar to old download_profile.
                # Each self.insta.download_* call will use the target argument (profile.username here).
                # All files will be within effective_download_path/profile.username/
                target_subfolder = os.path.join(effective_download_path, profile.username)
                # For profiles, a single representative dict is returned. Title could be username.
                # Content could be profile metadata. Date could be last post or None.
                # This part needs more thought on how to represent a whole profile as one generic dict.
                # For now, using profile's metadata.
                profile_metadata_dict = profile._asdict()
                profile_metadata_dict.pop('context', None) # remove non-serializable context
                processed_data = self._process_generic_downloads(url, f"@{username} profile", profile_metadata_dict, None, target_subfolder)

            else:
                logger.warning(f"URL {url} did not match Instagram post or profile pattern.")
                return None

        except Exception as e:
            logger.error(f"Failed during Instagram extraction for {url}: {e}", exc_info=True)
            return None
        finally:
            if os.path.isdir(effective_download_path):
                shutil.rmtree(effective_download_path)
                logger.debug(f"Cleaned up temporary Instagram download folder: {effective_download_path}")

        return processed_data

    def _process_generic_downloads(self, url:str, title:str, content_dict:dict, date_obj:datetime.datetime|None, downloaded_content_path:str) -> dict | None:
        """
        Processes downloaded files from `downloaded_content_path` and associated metadata.
        Returns data in the generic dictionary format.
        """
        media_items = []
        if os.path.isdir(downloaded_content_path):
            for root, _, files in os.walk(downloaded_content_path):
                for f_name in files:
                    if f_name.endswith(".txt") or f_name.endswith(".json"): # Skip metadata text/json files by instaloader
                        if f_name.endswith("_UTC.json"): # This is instaloader's main post metadata json
                            # Try to enrich content_dict from this json if needed
                            try:
                                with open(os.path.join(root, f_name), 'r') as jf:
                                    post_json_data = json.load(jf)
                                    # Example: if node.caption is missing, try from post_json_data
                                    if not content_dict.get("caption") and post_json_data.get("node", {}).get("edge_media_to_caption", {}).get("edges"):
                                        content_dict["caption"] = post_json_data["node"]["edge_media_to_caption"]["edges"][0]["node"]["text"]
                                    if not content_dict.get("owner") and post_json_data.get("node",{}).get("owner"):
                                        content_dict["owner"] = post_json_data["node"]["owner"]
                                    # Add more fields as necessary
                            except Exception as e:
                                logger.warning(f"Could not read or parse instaloader JSON {f_name}: {e}")
                        continue

                    abs_filepath = os.path.join(root, f_name)
                    file_type = mimetypes.guess_type(abs_filepath)[0] or "application/octet-stream"
                    media_items.append({
                        "filepath": abs_filepath,
                        "type": file_type.split("/")[0], # "image", "video", etc.
                        "mimetype": file_type
                    })
        else:
            logger.warning(f"Downloaded content path does not exist or is not a directory: {downloaded_content_path}")


        # Construct metadata part of the generic dict
        final_metadata = {
            "title": title or content_dict.get("caption"), # Use caption for title if available
            "original_url": url,
            "timestamp": date_obj.isoformat() if date_obj else None,
            "author": content_dict.get("owner", {}).get("username") if content_dict.get("owner") else None,
            "raw_instaloader_info": content_dict # Include the raw dict from instaloader post/profile object
        }
        # Clean None values
        final_metadata = {k:v for k,v in final_metadata.items() if v is not None}

        if not media_items and not final_metadata.get("title"): # No useful data extracted
            logger.warning(f"No media items or significant metadata found for {url} in {downloaded_content_path}")
            return None

        return {
            "metadata": final_metadata,
            "media": media_items,
            "extractor_info": "instagram_instaloader"
        }

    # Old methods to be removed or fully integrated:
    # download_post, download_profile, process_downloads
    # These are now conceptually part of extract_data and _process_generic_downloads
