import json
import re
import mimetypes
import requests

from loguru import logger
from pytwitter import Api
from slugify import slugify

from auto_archiver.core import Extractor
from auto_archiver.core import Metadata, Media
from auto_archiver.utils import get_datetime_from_str


class TwitterApiExtractor(Extractor):
    valid_url: re.Pattern = re.compile(r"(?:twitter|x).com\/(?:\#!\/)?(\w+)\/status(?:es)?\/(\d+)")

    def __init__(self,
                 bearer_tokens: list[str] = None,
                 bearer_token: str = None, # backward compatibility
                 consumer_key: str = None,
                 consumer_secret: str = None,
                 access_token: str = None,
                 access_secret: str = None,
                 tmp_dir_path_for_orchestrator: str = None
                 ):
        super().__init__()
        self._bearer_tokens = bearer_tokens if bearer_tokens is not None else []
        if bearer_token: # append if old single bearer_token is provided
            self._bearer_tokens.append(bearer_token)
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._access_token = access_token
        self._access_secret = access_secret
        self._tmp_dir_path_for_orchestrator = tmp_dir_path_for_orchestrator

        self.apis: list[Api] = []
        self._setup_done = False

        # Hybrid configuration: if self.config (from BaseModule) is available, use its values
        if hasattr(self, "config"):
            # Prioritize lists from config if available, otherwise use __init__ passed ones
            self._bearer_tokens = self.config.get("TWITTER_BEARER_TOKENS", self._bearer_tokens)
            # For single bearer_token, consumer_key etc., config overrides __init__ if key exists
            _single_bearer = self.config.get("TWITTER_BEARER_TOKEN", None)
            if _single_bearer and _single_bearer not in self._bearer_tokens:
                self._bearer_tokens.append(_single_bearer)

            self._consumer_key = self.config.get("TWITTER_CONSUMER_KEY", self._consumer_key)
            self._consumer_secret = self.config.get("TWITTER_CONSUMER_SECRET", self._consumer_secret)
            self._access_token = self.config.get("TWITTER_ACCESS_TOKEN", self._access_token)
            self._access_secret = self.config.get("TWITTER_ACCESS_SECRET", self._access_secret)

            if hasattr(self, "tmp_dir") and hasattr(self.tmp_dir, "name"):
                 self._tmp_dir_path_for_orchestrator = self.tmp_dir.name


    def setup(self) -> None:
        if self._setup_done:
            return

        self.apis = []
        if self._bearer_tokens: # Checks if list is not empty
            for bt in self._bearer_tokens:
                if bt: # Ensure token string is not empty
                    self.apis.append(Api(bearer_token=bt))

        if self._consumer_key and self._consumer_secret and self._access_token and self._access_secret:
            self.apis.append(
                Api(
                    consumer_key=self._consumer_key,
                    consumer_secret=self._consumer_secret,
                    access_token=self._access_token,
                    access_secret=self._access_secret,
                )
            )

        if not self.apis:
            logger.error("Missing Twitter API configurations. Please provide Bearer Token(s) or Consumer/Access Key pairs.")
            # Not raising an assert here to allow attempting extraction if credentials might be picked up differently later
            # or if a subclass handles it. However, extract_data will likely fail.

        self._setup_done = True

    def sanitize_url(self, url: str) -> str:
        # expand URL if t.co and clean tracker GET params
        # This method is inherited but shown here for context if it were overridden.
        return super().sanitize_url(url)

    def download(self, item: Metadata) -> Metadata | bool:
        # Ensure tmp_dir_path_for_orchestrator is set, especially if not via __init__ (e.g. direct use of Extractor)
        if not self._tmp_dir_path_for_orchestrator and hasattr(self, "tmp_dir") and hasattr(self.tmp_dir, "name"):
            self._tmp_dir_path_for_orchestrator = self.tmp_dir.name

        if not self._tmp_dir_path_for_orchestrator:
            logger.error(f"{self.__class__.__name__}.download called without a temporary directory path.")
            item.status = "error_misconfigured_tmp_dir"
            return False

        sanitized_url = self.sanitize_url(item.get_url())
        extracted_data = self.extract_data(sanitized_url, tmp_dir_path=self._tmp_dir_path_for_orchestrator)

        if not extracted_data:
            item.status = "error_no_data_extracted"
            return False

        # Convert generic dict to Metadata object
        metadata_dict = extracted_data.get("metadata", {})
        item.set_title(metadata_dict.get("text", ""))
        item.set_content(json.dumps(metadata_dict, ensure_ascii=False, indent=2)) # Store all metadata

        timestamp_str = metadata_dict.get("created_at")
        if timestamp_str:
            item.set_timestamp(get_datetime_from_str(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ"))

        for media_info in extracted_data.get("media", []):
            if media_info.get("filepath") and media_info["filepath"] not in item.get_media_filenames():
                media_obj = Media(media_info["filepath"])
                media_obj.set("type", media_info.get("type"))
                media_obj.set("original_url", media_info.get("original_url"))
                item.add_media(media_obj)

        return item.success(extracted_data.get("extractor_info", "twitter_api"))


    def extract_data(self, url: str, tmp_dir_path: str) -> dict | None:
        self.setup() # Ensure API clients are configured
        if not self.apis:
            logger.error("No Twitter API clients configured, cannot extract data.")
            return None

        username, tweet_id = self.get_username_tweet_id(url)
        if not tweet_id: # Only tweet_id is strictly necessary for get_tweet
            logger.error(f"Could not parse Tweet ID from URL: {url}")
            return None

        api_index = 0
        while api_index < len(self.apis):
            api_client = self.apis[api_index]
            logger.debug(f"Attempting to fetch tweet {tweet_id} using API client #{api_index + 1}")
            try:
                # Pass original_url for slugify, tmp_dir_path for downloads
                data = self._fetch_tweet_and_media_data(api_client, tweet_id, original_url=url, tmp_dir_path=tmp_dir_path)
                if data:
                    return data
                # If data is None, it means a non-exception failure within _fetch_tweet_and_media_data, try next client
                logger.warning(f"Fetching tweet {tweet_id} with API client #{api_index + 1} returned no data, trying next.")
            except Exception as e: # Catch exceptions from API calls or processing
                logger.error(f"Error fetching tweet {tweet_id} with API client #{api_index + 1}: {e}", exc_info=True)
                # Exception occurred, try next client

            api_index += 1

        logger.error(f"All Twitter API clients failed for tweet {tweet_id}.")
        return None

    def _fetch_tweet_and_media_data(self, api_client: Api, tweet_id: str, original_url: str, tmp_dir_path: str) -> dict | None:
        try:
            tweet = api_client.get_tweet(
                tweet_id,
                expansions=["attachments.media_keys", "author_id"],
                media_fields=["type", "duration_ms", "url", "preview_image_url", "variants", "width", "height", "alt_text"],
                tweet_fields=["attachments", "author_id", "created_at", "entities", "id", "text", "possibly_sensitive", "lang", "source", "geo"],
                user_fields=["username", "name", "profile_image_url"]
            )
            logger.debug(f"Tweet data received: {tweet}")
        except Exception as e:
            # Let extract_data handle retries with other clients by re-raising or returning None to signal failure with this client
            logger.error(f"pytwitter.Api().get_tweet({tweet_id=}) failed: {e}")
            raise # Re-raise to be caught by extract_data's loop for retries
            # return None # Alternative: return None to signal failure with this client

        if not tweet.data:
            logger.warning(f"No tweet data found for {tweet_id}")
            return None

        # Prepare metadata dictionary
        tweet_data_dict = tweet.data.as_dict()
        # Include user data if available from expansions
        if tweet.includes and tweet.includes.users:
            tweet_data_dict["author_data"] = tweet.includes.users[0].as_dict()

        # Remove id_str from dicts as 'id' (int) is already there
        if "id_str" in tweet_data_dict: del tweet_data_dict["id_str"]
        if "author_data" in tweet_data_dict and "id_str" in tweet_data_dict["author_data"]: del tweet_data_dict["author_data"]["id_str"]


        processed_media_items = []
        if tweet.includes and tweet.includes.media:
            for i, media_item in enumerate(tweet.includes.media):
                media_url = None
                mimetype = None

                if media_item.type == "photo":
                    media_url = media_item.url
                    mimetype = "image/jpeg" # Or guess from URL extension
                elif media_item.type == "video" or media_item.type == "animated_gif":
                    if media_item.variants:
                        chosen_variant = self.choose_variant(media_item.variants)
                        if chosen_variant:
                            media_url = chosen_variant.url
                            mimetype = chosen_variant.content_type
                # Add other types like 'gif' if distinct from 'animated_gif' based on API response

                if not media_url:
                    logger.warning(f"Could not determine media URL for media item: {media_item.type} key: {media_item.media_key}")
                    continue

                ext = mimetypes.guess_extension(mimetype) or ""
                # Use media_key or index for unique filename part. slugify(original_url) provides context.
                filename_slug = slugify(original_url.split("/")[-1]) # slug from tweet id part of URL
                target_filename = f"{filename_slug}_media_{i}_{media_item.media_key}{ext}"

                try:
                    downloaded_filepath = self.download_from_url(media_url, target_filename, tmp_dir_path=tmp_dir_path)
                    if downloaded_filepath and isinstance(downloaded_filepath, str) and os.path.exists(downloaded_filepath):
                        processed_media_items.append({
                            "filepath": downloaded_filepath,
                            "type": media_item.type, # "photo", "video", "animated_gif"
                            "original_url": media_url,
                            "width": media_item.width,
                            "height": media_item.height,
                            "alt_text": media_item.alt_text,
                            "duration_ms": media_item.duration_ms if media_item.type != "photo" else None
                        })
                    else:
                        logger.error(f"Failed to download media {media_url} or path invalid: {downloaded_filepath}")
                except Exception as e_dl:
                    logger.error(f"Error downloading media {media_url}: {e_dl}")

        return {
            "metadata": tweet_data_dict,
            "media": processed_media_items,
            "extractor_info": "twitter_api"
        }

    def get_username_tweet_id(self, url: str) -> tuple[str | bool, str | bool]:
        matches = self.valid_url.findall(url)
        if not matches:
            return False, False
        username, tweet_id = matches[0]
        logger.debug(f"Parsed from URL: {username=}, {tweet_id=}")
        return username, tweet_id

    def choose_variant(self, variants: list) -> dict | None:
        """
        Chooses the highest quality video variant possible out of a list of variants.
        Variants is a list of dict-like objects from pytwitter.
        """
        variant, bit_rate = None, -1
        for var in variants:
            if var.content_type == "video/mp4":
                if var.bit_rate > bit_rate:
                    bit_rate = var.bit_rate
                    variant = var
            else:
                variant = var if not variant else variant
        return variant
