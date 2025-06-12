import mimetypes
import shutil
import sys
import datetime
import os
import importlib
import subprocess
import zipfile

from typing import Generator, Type
from urllib.request import urlretrieve

import yt_dlp
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import MaxDownloadsReached
import pysubs2

from loguru import logger

from auto_archiver.core.extractor import Extractor
from auto_archiver.core import Metadata, Media
from auto_archiver.utils import get_datetime_from_str
from .dropin import GenericDropin


class SkipYtdlp(Exception):
    pass


class GenericExtractor(Extractor):
    _dropins = {}

    def __init__(self,
                 tmp_dir_path_for_orchestrator: str = None, # from self.tmp_dir.name
                 ytdlp_update_interval: int = 1,
                 bguils_po_token_method: str = "auto", # Literal["auto", "script", "disabled"]
                 proxy: str = None,
                 max_downloads: str = "inf",
                 allow_playlist: bool = False,
                 subtitles: bool = False,
                 live_from_start: bool = False,
                 comments: bool = False,
                 livestreams: bool = False,
                 ytdlp_args: str = "",
                 extractor_args: dict = None, # type: ignore
                 end_means_success: bool = True,
                 authentication_settings: dict = None, # type: ignore
                 dropin_paths: list[str] = None, # type: ignore
                 user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
                 ):
        super().__init__() # calls BaseModule.__init__ which sets up self.config if run through AA
        # Store configuration
        self._tmp_dir_path_for_orchestrator = tmp_dir_path_for_orchestrator
        self._ytdlp_update_interval = ytdlp_update_interval
        self._bguils_po_token_method = bguils_po_token_method
        self._proxy = proxy
        self._max_downloads = max_downloads
        self._allow_playlist = allow_playlist
        self._subtitles = subtitles
        self._live_from_start = live_from_start
        self._comments = comments
        self._livestreams = livestreams
        self._ytdlp_args = ytdlp_args
        self._extractor_args = extractor_args if extractor_args is not None else {}
        self._end_means_success = end_means_success
        self.authentication = authentication_settings if authentication_settings is not None else {} # For auth_for_site
        self._dropin_paths = dropin_paths if dropin_paths is not None else []
        self._user_agent = user_agent # though yt-dlp might handle its own UA

        # If running within Auto Archiver, BaseModule.config_setup would have populated self.config
        # We need to ensure that if config is available, it overrides defaults from __init__
        # This is a bit of a hybrid approach to allow standalone instantiation and AA integration.
        if hasattr(self, "config"):
            self._ytdlp_update_interval = self.config.get("YTDLP_UPDATE_INTERVAL", self._ytdlp_update_interval)
            self._bguils_po_token_method = self.config.get("BGUILS_PO_TOKEN_METHOD", self._bguils_po_token_method)
            self._proxy = self.config.get("PROXY", self._proxy)
            self._max_downloads = self.config.get("MAX_DOWNLOADS", self._max_downloads)
            self._allow_playlist = self.config.get("ALLOW_PLAYLIST", self._allow_playlist)
            self._subtitles = self.config.get("SUBTITLES", self._subtitles)
            self._live_from_start = self.config.get("LIVE_FROM_START", self._live_from_start)
            self._comments = self.config.get("COMMENTS", self._comments)
            self._livestreams = self.config.get("LIVESTREAMS", self._livestreams)
            self._ytdlp_args = self.config.get("YTDLP_ARGS", self._ytdlp_args)
            self._extractor_args = self.config.get("EXTRACTOR_ARGS", self._extractor_args)
            self._end_means_success = self.config.get("END_MEANS_SUCCESS", self._end_means_success)
            self.authentication = self.config.get("AUTHENTICATION", self.authentication) # from BaseModule
            self._dropin_paths = self.config.get("DROPIN_PATHS", self._dropin_paths) # custom key
            # self.tmp_dir is from BaseModule, a TemporaryDirectory object
            if hasattr(self, "tmp_dir") and hasattr(self.tmp_dir, "name"):
                 self._tmp_dir_path_for_orchestrator = self.tmp_dir.name


    def setup(self):
        self.check_for_extractor_updates()
        self.setup_po_tokens()

    def check_for_extractor_updates(self):
        """Checks whether yt-dlp or its plugins need updating and triggers a restart if so."""
        if self._ytdlp_update_interval < 0:
            return

        update_file = os.path.join("secrets" if os.path.exists("secrets") else "", ".ytdlp-update")
        next_check = None
        if os.path.exists(update_file):
            with open(update_file, "r") as f:
                next_check = datetime.datetime.fromisoformat(f.read())

        if next_check and next_check > datetime.datetime.now():
            return

        yt_dlp_updated = self.update_package("yt-dlp")
        bgutil_updated = self.update_package("bgutil-ytdlp-pot-provider")

        # Write the new timestamp
        with open(update_file, "w") as f:
            next_check = datetime.datetime.now() + datetime.timedelta(days=self._ytdlp_update_interval)
            f.write(next_check.isoformat())

        if yt_dlp_updated or bgutil_updated:
            if os.environ.get("AUTO_ARCHIVER_ALLOW_RESTART", "1") != "1":
                logger.warning("yt-dlp or plugin was updated — please restart auto-archiver manually")
            else:
                logger.warning("yt-dlp or plugin was updated — restarting auto-archiver")
                logger.warning(" ======= RESTARTING ======= ")
                os.execv(sys.executable, [sys.executable] + sys.argv)

    def update_package(self, package_name: str) -> bool:
        logger.info(f"Checking and updating {package_name}...")
        from importlib.metadata import version as get_version

        old_version = get_version(package_name)
        try:
            result = subprocess.run(["pip", "install", "--upgrade", package_name], check=True, capture_output=True)
            if f"Successfully installed {package_name}" in result.stdout.decode():
                new_version = importlib.metadata.version(package_name)
                logger.info(f"{package_name} updated from {old_version} to {new_version}")
                return True
            logger.info(f"{package_name} already up to date")
        except Exception as e:
            logger.error(f"Error updating {package_name}: {e}")
        return False

    def setup_po_tokens(self) -> None:
        """Setup Proof of Origin Token method conditionally.
        Uses provider: https://github.com/Brainicism/bgutil-ytdlp-pot-provider.
        """
        in_docker = os.environ.get("RUNNING_IN_DOCKER")
        if self._bguils_po_token_method == "disabled":
            # This allows disabling of the PO Token generation script in the Docker implementation.
            logger.warning("Proof of Origin Token generation is disabled.")
            return

        if self._bguils_po_token_method == "auto" and not in_docker:
            logger.info(
                "Proof of Origin Token method not explicitly set. "
                "If you're running an external HTTP server separately, you can safely ignore this message. "
                "To reduce the likelihood of bot detection, enable one of the methods described in the documentation: "
                "https://auto-archiver.readthedocs.io/en/settings_page/installation/authentication.html#proof-of-origin-tokens"
            )
            return

        # Either running in Docker, or "script" method is set beyond this point
        self.setup_token_generation_script()

    def setup_token_generation_script(self) -> None:
        """This function sets up the Proof of Origin Token generation script method for
        bgutil-ytdlp-pot-provider if enabled or in Docker."""
        missing_tools = [tool for tool in ("node", "yarn", "npx") if shutil.which(tool) is None]
        if missing_tools:
            logger.error(
                f"Cannot set up PO Token script; missing required tools: {', '.join(missing_tools)}. "
                "Install these tools or run bgutils via Docker. "
                "See: https://github.com/Brainicism/bgutil-ytdlp-pot-provider"
            )
            return
        try:
            from importlib.metadata import version as get_version

            plugin_version = get_version("bgutil-ytdlp-pot-provider")
            base_dir = os.path.expanduser("~/bgutil-ytdlp-pot-provider")
            server_dir = os.path.join(base_dir, "server")
            version_file = os.path.join(server_dir, ".VERSION")
            transpiled_script = os.path.join(server_dir, "build", "generate_once.js")

            # Skip setup if version is correct and transpiled script exists
            if os.path.isfile(transpiled_script) and os.path.isfile(version_file):
                with open(version_file) as vf:
                    if vf.read().strip() == plugin_version:
                        logger.info("PO Token script already set up and up to date.")
            else:
                # Remove an outdated directory and pull a new version
                if os.path.exists(base_dir):
                    shutil.rmtree(base_dir)
                os.makedirs(base_dir, exist_ok=True)

                zip_url = (
                    f"https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/refs/tags/{plugin_version}.zip"
                )
                zip_path = os.path.join(base_dir, f"{plugin_version}.zip")
                logger.info(f"Downloading bgutils release zip for version {plugin_version}...")
                urlretrieve(zip_url, zip_path)
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(base_dir)
                os.remove(zip_path)

                extracted_root = os.path.join(base_dir, f"bgutil-ytdlp-pot-provider-{plugin_version}")
                shutil.move(os.path.join(extracted_root, "server"), server_dir)
                shutil.rmtree(extracted_root)
                logger.info("Installing dependencies and transpiling PoT Generator script...")
                subprocess.run(["yarn", "install", "--frozen-lockfile"], cwd=server_dir, check=True)
                subprocess.run(["npx", "tsc"], cwd=server_dir, check=True)

                with open(version_file, "w") as vf:
                    vf.write(plugin_version)

            script_path = os.path.join(server_dir, "build", "generate_once.js")
            if not os.path.exists(script_path):
                logger.error("generate_once.js not found after transpilation.")
                return

            self._extractor_args.setdefault("youtubepot-bgutilscript", {})["script_path"] = script_path
            logger.info(f"PO Token script configured at: {script_path}")

        except Exception as e:
            logger.error(f"Failed to set up PO Token script: {e}")

    def suitable_extractors(self, url: str) -> Generator[str, None, None]:
        """
        Returns a list of valid extractors for the given URL"""
        for info_extractor in yt_dlp.YoutubeDL()._ies.values():
            if not info_extractor.working():
                continue

            # check if there's a dropin and see if that declares whether it's suitable
            dropin: GenericDropin = self.dropin_for_name(info_extractor.ie_key())
            if dropin and dropin.suitable(url, info_extractor):
                yield info_extractor
            elif info_extractor.suitable(url):
                yield info_extractor

    def suitable(self, url: str) -> bool:
        """
        Checks for valid URLs out of all ytdlp extractors.
        Returns False for the GenericIE, which as labelled by yt-dlp: 'Generic downloader that works on some sites'
        """
        return any(self.suitable_extractors(url))

    def download_additional_media(
        self, video_data: dict, info_extractor: InfoExtractor, metadata: Metadata
    ) -> Metadata:
        """
        Downloads additional media like images, comments, subtitles, etc.

        Creates a 'media' object and attaches it to the metadata object.
        """

        # Just get the main thumbnail. More thumbnails are available in
        # video_data['thumbnails'] should they be required
        thumbnail_url = video_data.get("thumbnail")
        if thumbnail_url:
            try:
                # Ensure self._tmp_dir_path_for_orchestrator is available (used by download() wrapper)
                # or a tmp_dir_path is passed directly (used by extract_data scenario)
                # For now, this method is called by _process_extraction_with_ytdlp, which should receive tmp_dir_path
                # We need to ensure tmp_dir_path is passed down to here or use self._tmp_dir_path_for_orchestrator
                # This part will be tricky with the refactor. For now, let's assume tmp_dir_path is made available.
                # This method will be heavily refactored/replaced.
                # Let's assume for now it's called from a context where tmp_dir_path is defined.
                # This method will be called from _process_extraction_with_ytdlp, which receives tmp_dir_path
                # So, download_from_url should be called with that tmp_dir_path.
                # For the purpose of this diff, I'll assume tmp_dir_path is passed to this function or accessible.
                # This will be more concretely addressed when refactoring this method itself.
                # For now, let's use a placeholder or rely on the fact that it will be refactored.
                # The call below is illustrative and will change.
                current_tmp_path = self._tmp_dir_path_for_orchestrator # Placeholder, this needs to be the tmp_dir_path for the current operation
                if current_tmp_path:
                    cover_image_path = self.download_from_url(thumbnail_url, tmp_dir_path=current_tmp_path)
                    # This Media object creation will change when returning generic dict
                    media = Media(cover_image_path)
                    metadata.add_media(media, id="cover")
                else:
                    logger.error("Temporary directory path not available for downloading additional media.")

            except Exception as e:
                logger.error(f"Error downloading cover image {thumbnail_url}: {e}")

        dropin = self.dropin_for_name(info_extractor.ie_key())
        if dropin:
            try:
                # This call will also need to be updated to work with generic dicts or a temporary Metadata object
                metadata = dropin.download_additional_media(video_data, info_extractor, metadata)
            except AttributeError:
                pass

        return metadata

    def keys_to_clean(self, info_extractor: InfoExtractor, video_data: dict) -> dict:
        """
        Clean up the ytdlp generic video data to make it more readable and remove unnecessary keys that ytdlp adds
        """

        base_keys = [
            "formats",
            "thumbnail",
            "display_id",
            "epoch",
            "requested_downloads",
            "duration_string",
            "thumbnails",
            "http_headers",
            "webpage_url_basename",
            "webpage_url_domain",
            "extractor",
            "extractor_key",
            "playlist",
            "playlist_index",
            "duration_string",
            "protocol",
            "requested_subtitles",
            "format_id",
            "acodec",
            "vcodec",
            "ext",
            "epoch",
            "_has_drm",
            "filesize",
            "audio_ext",
            "video_ext",
            "vbr",
            "abr",
            "resolution",
            "dynamic_range",
            "aspect_ratio",
            "cookies",
            "format",
            "quality",
            "preference",
            "artists",
            "channel_id",
            "subtitles",
            "tbr",
            "url",
            "original_url",
            "automatic_captions",
            "playable_in_embed",
            "live_status",
            "_format_sort_fields",
            "chapters",
            "requested_formats",
            "format_note",
            "audio_channels",
            "asr",
            "fps",
            "was_live",
            "is_live",
            "heatmap",
            "age_limit",
            "stretched_ratio",
        ]

        dropin = self.dropin_for_name(info_extractor.ie_key())
        if dropin:
            try:
                base_keys += dropin.keys_to_clean(video_data, info_extractor)
            except AttributeError:
                pass

        return base_keys

    def add_metadata(self, video_data: dict, info_extractor: InfoExtractor, url: str, result: Metadata) -> Metadata:
        """
        Creates a Metadata object from the given video_data
        """

        # first add the media
        result = self.download_additional_media(video_data, info_extractor, result)

        # keep both 'title' and 'fulltitle', but prefer 'title', falling back to 'fulltitle' if it doesn't exist
        if not result.get_title():
            result.set_title(video_data.pop("title", video_data.pop("fulltitle", "")))

        if not result.get("url"):
            result.set_url(url)

        if "description" in video_data and not result.get("content"):
            result.set_content(video_data.pop("description"))
        # extract comments if enabled
        if self._comments and video_data.get("comments", []) is not None:
            result.set(
                "comments",
                [
                    {
                        "text": c["text"],
                        "author": c["author"],
                        "timestamp": datetime.datetime.fromtimestamp(c.get("timestamp"), tz=datetime.timezone.utc),
                    }
                    for c in video_data.get("comments", [])
                ],
            )

        # then add the common metadata
        timestamp = video_data.pop("timestamp", None)
        if timestamp and not result.get("timestamp"):
            timestamp = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).isoformat()
            result.set_timestamp(timestamp)

        upload_date = video_data.pop("upload_date", None)
        if upload_date and not result.get("upload_date"):
            upload_date = get_datetime_from_str(upload_date, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
            result.set("upload_date", upload_date)

        # then clean away any keys we don't want
        for clean_key in self.keys_to_clean(info_extractor, video_data):
            video_data.pop(clean_key, None)

        # then add the rest of the video data
        for k, v in video_data.items():
            if v:
                result.set(k, v)

        return result

    def get_metadata_for_post(self, info_extractor: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL) -> Metadata:
        """
        Calls into the ytdlp InfoExtract subclass to use the private _extract_post method to get the post metadata.
        """

        ie_instance = info_extractor(downloader=ydl)
        dropin = self.dropin_for_name(info_extractor.ie_key())

        if not dropin:
            # TODO: add a proper link to 'how to create your own dropin'
            logger.debug(f"""Could not find valid dropin for {info_extractor.ie_key()}.
                     Why not try creating your own, and make sure it has a valid function called 'create_metadata'. Learn more: https://auto-archiver.readthedocs.io/en/latest/user_guidelines.html#""")
            return False

        post_data = dropin.extract_post(url, ie_instance)
        result = dropin.create_metadata(post_data, ie_instance, self, url)
        return self.add_metadata(post_data, info_extractor, url, result)

    def get_metadata_for_video(
        self, data: dict, info_extractor: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL
    ) -> Metadata:
        # this time download
        ydl.params["getcomments"] = self._comments
        # TODO: for playlist or long lists of videos, how to download one at a time so they can be stored before the next one is downloaded?
        try:
            # download=True here means yt-dlp will download to the path specified in ydl_options '-o'
            data = ydl.extract_info(url, ie_key=info_extractor.ie_key(), download=True)
        except MaxDownloadsReached:  # proceed as normal once MaxDownloadsReached is raised
            pass
        logger.success(data)

        if "entries" in data:
            entries = data.get("entries", [])
            if not len(entries):
                logger.warning("YoutubeDLArchiver could not find any video")
                return False
        else:
            entries = [data]
        result = Metadata()

        def _helper_get_filename(entry: dict) -> str:
            entry_url = entry.get("url")

            filename = ydl.prepare_filename(entry)
            base_filename, _ = os.path.splitext(filename)  # '/get/path/to/file' ignore '.ext'
            directory = os.path.dirname(base_filename)  # '/get/path/to'
            basename = os.path.basename(base_filename)  # 'file'
            for f in os.listdir(directory):
                if (
                    f.startswith(basename)
                    or (entry_url and os.path.splitext(f)[0] in entry_url)
                    and "video/" in (mimetypes.guess_type(f)[0] or "")
                ):
                    return os.path.join(directory, f)
            return False

        for entry in entries:
            try:
                filename = _helper_get_filename(entry)

                if not filename or not os.path.exists(filename):
                    # file was not downloaded or could not be retrieved, example: sensitive videos on YT without using cookies.
                    continue

                logger.debug(f"Using filename {filename} for entry {entry.get('id', 'unknown')}")

                new_media = Media(filename)
                for x in ["duration", "original_url", "fulltitle", "description", "upload_date"]:
                    if x in entry:
                        new_media.set(x, entry[x])

                # read text from subtitles if enabled
                if self._subtitles:
                    for lang, val in (data.get("requested_subtitles") or {}).items():
                        try:
                            subs = pysubs2.load(val.get("filepath"), encoding="utf-8")
                            text = " ".join([line.text for line in subs])
                            new_media.set(f"subtitles_{lang}", text)
                        except Exception as e:
                            logger.error(f"Error loading subtitle file {val.get('filepath')}: {e}")
                result.add_media(new_media)
            except Exception as e:
                logger.error(f"Error processing entry {entry}: {e}")
        if not len(result.media):
            logger.warning(f"No media found for entry {entry}, skipping.")
            return False

        return self.add_metadata(data, info_extractor, url, result)

    def dropin_for_name(self, dropin_name: str, package=__package__) -> GenericDropin:
        dropin_name = dropin_name.lower()

        if dropin_name == "generic":
            return None

        dropin_class_name = dropin_name.title()

        # Attempt to load from cache first
        if dropin_name in self._dropins:
            return self._dropins[dropin_name]

        def _load_and_cache_dropin(module_obj):
            # Ensure module has the expected class
            if not hasattr(module_obj, dropin_class_name):
                logger.warning(f"Dropin module {module_obj.__name__} does not have class {dropin_class_name}")
                return None

            dropin_instance = getattr(module_obj, dropin_class_name)()
            # TODO: The 'extractor' attribute on dropins might need careful handling
            # if dropins are to be made more independent or if self is not the right context.
            # For now, maintaining previous behavior.
            try: # dropin_instance might not have extractor attribute
                dropin_instance.extractor = self
            except AttributeError:
                logger.warning(f"Could not set extractor attribute for {dropin_name}")

            self._dropins[dropin_name] = dropin_instance
            return dropin_instance

        # Load from custom dropin paths first
        for path_dir in self._dropin_paths:
            dropin_file_path = os.path.join(path_dir, f"{dropin_name}.py")
            if os.path.exists(dropin_file_path):
                try:
                    spec = importlib.util.spec_from_file_location(f"custom_dropin.{dropin_name}", dropin_file_path)
                    if spec and spec.loader:
                        dropin_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(dropin_module)
                        loaded_dropin = _load_and_cache_dropin(dropin_module)
                        if loaded_dropin: return loaded_dropin
                except Exception as e:
                    logger.error(f"Failed to load custom dropin {dropin_name} from {dropin_file_path}: {e}")

        # Fallback to loading from the default package
        try:
            module = importlib.import_module(f".{dropin_name}", package=package)
            return _load_and_cache_dropin(module)
        except ModuleNotFoundError:
            logger.debug(f"No built-in dropin found for {dropin_name}")
        except Exception as e: # Catch other import errors
            logger.error(f"Error loading built-in dropin {dropin_name}: {e}")

        return None


    def download_for_extractor(self, info_extractor: InfoExtractor, url: str, ydl: yt_dlp.YoutubeDL) -> Metadata:
        """
        Tries to download the given url using the specified extractor.
        This method will be heavily refactored into _process_extraction_with_ytdlp.
        The current implementation is a placeholder and will be changed.
        """
        # when getting info without download, we also don't need the comments
        ydl.params["getcomments"] = False # This will be self._comments in the new structure, handled by ydl_opts
        result = False # This will be a dict or list[dict]

        dropin_submodule = self.dropin_for_name(info_extractor.ie_key())

        def _helper_for_successful_extract_info(data, info_extractor, url, ydl):
            # This logic will be part of _process_extraction_with_ytdlp
            if data.get("is_live", False) and not self._livestreams:
                logger.warning("Livestream detected, skipping due to 'livestreams' configuration setting")
                return False
            # it's a valid video, that the ytdlp can download out of the box
            return self.get_metadata_for_video(data, info_extractor, url, ydl) # This will change

        try:
            if dropin_submodule and dropin_submodule.skip_ytdlp_download(url, info_extractor):
                logger.debug(f"Skipping using ytdlp to download files for {info_extractor.ie_key()}")
                raise SkipYtdlp()

            # download=False here means only fetching info. Actual download happens in get_metadata_for_video or by dropin.
            # In the new structure, extract_info(download=True) will be the primary mode inside _process_extraction_with_ytdlp
            data = ydl.extract_info(url, ie_key=info_extractor.ie_key(), download=False)

            result = _helper_for_successful_extract_info(data, info_extractor, url, ydl)

        except MaxDownloadsReached: # This error is for ydl.download([url]), not extract_info
            # This path might not be hit if extract_info(download=False) is used.
            # If extract_info(download=True) is used, MaxDownloadsReached from yt-dlp needs to be handled.
            logger.info(f"Max downloads reached for {url}, processing what was downloaded.")
            # data might be partially populated or represent the state at interruption.
            # The logic here depends on how yt-dlp populates 'data' in this scenario.
            # For now, assume _helper_for_successful_extract_info can handle it.
            result = _helper_for_successful_extract_info(data, info_extractor, url, ydl)
        except Exception as e:
            if info_extractor.IE_NAME == "generic" and not dropin_submodule: # GenericIE without a dropin is often not useful
                logger.debug(f"Generic extractor without a dropin failed for {url}. Error: {e}")
                return False # Skip if GenericIE and no dropin to handle it.

            if not isinstance(e, SkipYtdlp): # If not intentionally skipped by dropin
                logger.debug(
                    f'Issue using "{info_extractor.IE_NAME}" extractor to get info (error: {repr(e)}), attempting to use dropin to get post data or custom extraction.'
                )
            # This block is for when extract_info(download=False) fails or is skipped.
            # Dropins might have their own extraction logic (e.g. extract_post).
            try:
                # This part will also be part of _process_extraction_with_ytdlp
                result = self.get_metadata_for_post(info_extractor, url, ydl) # This will change
            except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as post_e:
                logger.error(f"Dropin or post extraction failed for {url} with {info_extractor.IE_NAME}: {post_e}")
                return False
            except Exception as generic_e: # Catch other errors from dropin's get_metadata_for_post
                logger.debug(
                    'Attempt to extract using ytdlp extractor "{name}" failed:  \n  {error}',
                    name=info_extractor.IE_NAME,
                    error=str(generic_e),
                    exc_info=True,
                )
                return False

        if result:
            extractor_name = "yt-dlp"
            if info_extractor:
                extractor_name += f"_{info_extractor.ie_key()}"
            # This success/status setting will be handled by the download() wrapper or the caller of extract_data
            if self._end_means_success: # result is Metadata here, will change
                result.success(extractor_name)
            else:
                result.status = extractor_name

        return result


    def download(self, item: Metadata) -> Metadata | bool:
        url = item.get_url()

        if not self._tmp_dir_path_for_orchestrator:
            logger.error("GenericExtractor.download called without a temporary directory path for the orchestrator.")
            # Try to fallback to self.tmp_dir.name if available (from BaseModule context)
            if hasattr(self, "tmp_dir") and hasattr(self.tmp_dir, "name"):
                self._tmp_dir_path_for_orchestrator = self.tmp_dir.name
                logger.warning(f"Using self.tmp_dir.name ({self._tmp_dir_path_for_orchestrator}) as fallback.")
            else:
                item.status = "error_misconfigured_tmp_dir"
                return False

        extracted_data = self.extract_data(url, tmp_dir_path=self._tmp_dir_path_for_orchestrator)

        if not extracted_data:
            item.status = "error_no_data_extracted"
            return False

        # If extract_data returns a list (e.g. playlist), process the first item for now.
        # Proper playlist handling in Metadata object would require more changes.
        # For now, let's assume typical case is single dict or first of list.
        if isinstance(extracted_data, list):
            if not extracted_data:
                item.status = "error_empty_playlist_data"
                return False
            # TODO: how to handle multiple entries from a playlist into a single 'item: Metadata'?
            # This is a larger design question. For now, take the first.
            logger.warning("Playlist detected, processing only the first item for Metadata conversion.")
            data_to_convert = extracted_data[0]
            # TODO: ideally, download() should probably return list[Metadata] or handle it internally
        else:
            data_to_convert = extracted_data

        # Convert generic dict to Metadata
        item.set_title(data_to_convert.get("metadata", {}).get("title", ""))
        item.set_content(data_to_convert.get("metadata", {}).get("description", "") or json.dumps(data_to_convert.get("metadata"), ensure_ascii=False, indent=2))
        item.set_timestamp(data_to_convert.get("metadata", {}).get("timestamp")) # Assumes ISO format
        item.set_url(url) # Original URL

        # Add original URL from metadata if different (e.g. after redirects)
        original_url_meta = data_to_convert.get("metadata", {}).get("original_url")
        if original_url_meta and original_url_meta != url:
            item.set("original_url_from_yt-dlp", original_url_meta)

        for media_info in data_to_convert.get("media", []):
            if media_info.get("filepath"):
                # TODO: This assumes filepath is already in the orchestrator's tmp_dir.
                # If extract_data uses a different tmp_dir, files might need to be moved.
                # For now, assume _tmp_dir_path_for_orchestrator was used by extract_data.
                media_obj = Media(media_info["filepath"])
                # Add other relevant info from media_info to media_obj if needed
                # e.g. media_obj.set("type", media_info.get("type"))
                # e.g. media_obj.set("src_url", media_info.get("src_url"))
                item.add_media(media_obj, id=media_info.get("id")) # use 'id' if available (e.g. 'cover')
            elif media_info.get("content_binary"): # handle binary content directly
                # This would require saving it to a file in _tmp_dir_path_for_orchestrator
                # and then creating a Media object. This is an advanced case.
                logger.warning("Binary media content in extract_data output not yet fully handled in download wrapper.")


        extractor_name_info = data_to_convert.get("extractor_info", "yt-dlp_unknown")
        if self._end_means_success:
            item.success(extractor_name_info)
        else:
            item.status = extractor_name_info

        # Store raw extracted data in metadata if needed for debugging or further processing
        # item.set("raw_extracted_data", data_to_convert)

        return item

    def extract_data(self, url: str, tmp_dir_path: str) -> dict | list[dict] | None:
        """
        Extracts data using yt-dlp and returns it in a generic format.
        Downloads files to tmp_dir_path.
        """
        if not os.path.isdir(tmp_dir_path):
            try:
                os.makedirs(tmp_dir_path, exist_ok=True)
            except OSError as e:
                logger.error(f"Cannot create temporary directory {tmp_dir_path}: {e}")
                return None

        # TODO: this is a temporary hack until this issue is closed: https://github.com/yt-dlp/yt-dlp/issues/11025
        # This should ideally be handled by yt-dlp or as a pre-processing step if it's a common issue.
        # For now, applying it here as it was in the original download() method.
        processed_url = url
        if url.startswith("https://ya.ru"):
            processed_url = url.replace("https://ya.ru", "https://yandex.ru")
            logger.info(f"URL transformed: {url} -> {processed_url}")


        ydl_cli_options = self._build_ydl_options(tmp_dir_path, processed_url)

        try:
            # Parse options to get validated yt-dlp parameters dictionary
            *_, ydl_params = yt_dlp.parse_options(ydl_cli_options)
        except Exception as e: # yt-dlp can raise various errors during option parsing
            logger.error(f"Failed to parse yt-dlp options: {e}. Options: {ydl_cli_options}")
            return None

        # Always add these essential parameters for behavior control if not already present
        # from CLI args (though _build_ydl_options should handle most)
        ydl_params.setdefault("quiet", True) # Already in _build_ydl_options, but good to ensure
        ydl_params.setdefault("outtmpl", os.path.join(tmp_dir_path, "%(id)s.%(ext)s")) # Crucial
        ydl_params.setdefault("getcomments", self._comments) # For fetching comments if enabled
        # 'download=True' will be implicitly handled by calling extract_info without download=False
        # and relying on the output template.

        ydl = yt_dlp.YoutubeDL(ydl_params)

        for info_extractor_cls in self.suitable_extractors(processed_url):
            # Note: suitable_extractors yields classes, but yt-dlp instance uses instances.
            # ydl.extract_info can take ie_key, or we can instantiate the IE.
            # For _process_extraction_with_ytdlp, we'll pass the class and instantiate it there if needed,
            # or pass the ydl instance which has IEs registered.

            # The actual extraction logic is now deferred to _process_extraction_with_ytdlp
            # which needs to be implemented.
            # For now, we are calling the placeholder.
            # This will be the core of the next step.
            try:
                extraction_result = self._process_extraction_with_ytdlp(
                    info_extractor_cls, processed_url, ydl, tmp_dir_path
                )
                if extraction_result:
                    # TODO: Ensure the result from _process_extraction_with_ytdlp includes absolute paths
                    # for all downloaded media, using tmp_dir_path as the base.
                    return extraction_result
            except Exception as e:
                logger.error(f"Error during _process_extraction_with_ytdlp for {info_extractor_cls.IE_KEY if hasattr(info_extractor_cls, 'IE_KEY') else 'UnknownIE'} on {processed_url}: {e}", exc_info=True)
                # Try next suitable extractor
                continue

        logger.warning(f"No suitable extractor in yt-dlp successfully processed the URL: {url}")
        return None

    def _build_ydl_options(self, tmp_dir_path: str, current_url: str) -> list[str]:
        """
        Constructs the list of command-line options for yt-dlp.
        Uses current_url for auth decisions, which might have been modified (e.g. ya.ru).
        """
        ydl_options = [
            "--no-warnings", # Suppress yt-dlp warnings unless debugging
            # Output template using the provided tmp_dir_path
            "-o", os.path.join(tmp_dir_path, self._extractor_args.get("output_template", "%(id)s.%(ext)s")), # Allow override from extractor_args
            "--write-subs" if self._subtitles else "--no-write-subs",
            "--write-auto-subs" if self._subtitles and self._extractor_args.get("autosubs", True) else "--no-write-auto-subs",
            "--live-from-start" if self._live_from_start else "--no-live-from-start",
            # "--print-json", # Useful for debugging, but extract_info result is already a dict
            "--no-progress", # Unless verbose logging is on
            # Bitexact for ffmpeg postprocessor to ensure deterministic output (if ffmpeg is used)
            "--postprocessor-args", "ffmpeg:-bitexact",
        ]
        # Playlist handling
        if self._allow_playlist:
            ydl_options.append("--yes-playlist")
            if self._max_downloads != "inf":
                 try:
                    max_dl_int = int(self._max_downloads)
                    # --playlist-end is 1-based index
                    ydl_options.extend(["--playlist-end", str(max_dl_int if max_dl_int > 0 else 1)])
                 except ValueError:
                    logger.warning(f"Invalid MAX_DOWNLOADS '{self._max_downloads}' for playlist, expected integer.")
        else:
            ydl_options.append("--no-playlist")
            # If not allowing playlists, max_downloads applies to single video downloads if it's relevant (e.g. segmented)
            # but yt-dlp usually handles single videos as one download.
            # For clarity, ensure --max-downloads is also set for non-playlist scenarios if it's not 'inf'
            if self._max_downloads != "inf":
                try:
                    max_dl_int = int(self._max_downloads)
                    if max_dl_int > 0 : # Only add if it's a meaningful limit
                         ydl_options.extend(["--max-downloads", str(max_dl_int)])
                except ValueError:
                    logger.warning(f"Invalid MAX_DOWNLOADS '{self._max_downloads}', expected 'inf' or integer.")


        if self._proxy:
            ydl_options.extend(["--proxy", self._proxy])

        # Authentication
        auth = self.auth_for_site(current_url, extract_cookies=False) # Use potentially modified URL for auth context
        if auth:
            if "username" in auth and "password" in auth:
                ydl_options.extend(("--username", auth["username"], "--password", auth["password"]))
            # yt-dlp supports --cookies, --cookies-from-browser
            if "cookies_file" in auth:
                ydl_options.extend(("--cookies", auth["cookies_file"]))
            elif "cookies_from_browser" in auth:
                # Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]
                # e.g., "firefox:myprofile", "chrome"
                ydl_options.extend(("--cookies-from-browser", auth["cookies_from_browser"]))
            elif "cookie" in auth:
                 logger.warning("Direct 'cookie' string in auth is not directly used for yt-dlp CLI options. Use 'cookies_file' or 'cookies_from_browser'.")


        # Extractor specific arguments from self._extractor_args
        # These are typically like {'youtubepot-bgutilscript': {'script_path': '...'}}
        # or {'instagram': 'user:pass'}
        # yt-dlp format: --extractor-args "key1:val1;key2:val2" for dicts, or "key:simple_val"
        # The self.setup_po_tokens() method already formats 'youtubepot-bgutilscript' in self._extractor_args.
        for key, args_val in self._extractor_args.items():
            if key == "output_template" or key == "autosubs": continue # Handled above

            if isinstance(args_val, dict):
                # Example: {'param1': 'value1', 'param2': 'value2'} -> "key:param1=value1;param2=value2"
                # Note: yt-dlp's parsing of this can be tricky. Simpler key:value pairs are more robust.
                # For complex dicts, it might be better if the user provides the exact string for yt-dlp.
                # Current format for yt-dlp is more like: --extractor-args "ie_key:key1=val1,key2=val2"
                # This needs to align with how yt-dlp expects these.
                # For now, assuming simple key-value for extractor_args items, or pre-formatted strings.
                # If args_val is a dict, it's likely for a specific extractor (e.g., youtubepot-bgutilscript)
                # and should be passed as key:arg1=val1;arg2=val2
                # Example: --extractor-args "youtubepot-bgutilscript:script_path=/path/to/script"
                # This part is complex due to yt-dlp's varied arg parsing.
                # A common pattern for yt-dlp is --extractor-args IE_KEY:key=value
                # Let's assume self._extractor_args stores them ready for this if complex,
                # or simply as key:value strings.
                # The current code from download() was:
                # arg_str = ";".join(f"{k}={v}" for k, v in args.items()) -> this was for a single IE's args
                # ydl_options.extend(["--extractor-args", f"{key}:{arg_str}"])
                # This implies 'key' is the IE_KEY, and 'args' (now args_val) is a dict for it.
                if isinstance(args_val, dict) and all(isinstance(v, (str, int, float)) for v in args_val.values()):
                    # Format as key:sub_key1=val1;sub_key2=val2
                    sub_args_str = ";".join(f"{sub_k}={sub_v}" for sub_k, sub_v in args_val.items())
                    ydl_options.extend(["--extractor-args", f"{key}:{sub_args_str}"])
                elif isinstance(args_val, str): # Already a pre-formatted string for the extractor
                     ydl_options.extend(["--extractor-args", f"{key}:{args_val}"]) # Assumes key:value format
                else:
                    logger.warning(f"Unsupported format for extractor_args '{key}': {args_val}")


        # General yt-dlp arguments from self._ytdlp_args string
        if self._ytdlp_args:
            # Simple split by space. User needs to handle quoting if args have spaces.
            ydl_options.extend(self._ytdlp_args.split())

        # Remove quiet if verbose logging is desired (e.g. based on loguru level)
        # For now, always quiet unless overridden by ytdlp_args
        if "--verbose" not in ydl_options and "--quiet" not in ydl_options and self._ytdlp_args and "--quiet" not in self._ytdlp_args :
             ydl_options.append("--quiet")
        elif "--verbose" in ydl_options and "--quiet" in ydl_options:
            ydl_options.remove("--quiet") # verbose wins over quiet if both somehow specified

        logger.debug(f"yt-dlp CLI options prepared: {ydl_options}")
        return ydl_options


    def _process_extraction_with_ytdlp(self, info_extractor_cls: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL, tmp_dir_path: str) -> dict | list[dict] | None:
        """
        Core extraction logic using yt-dlp.
        Transforms yt-dlp's info_dict into a generic format.
        Downloads are handled by yt-dlp to tmp_dir_path based on ydl's outtmpl.
        """
        ie_key = info_extractor_cls.IE_KEY if hasattr(info_extractor_cls, "IE_KEY") else "unknown_ie"
        logger.debug(f"Processing with IE: {ie_key} for URL: {url} into {tmp_dir_path}")

        dropin = self.dropin_for_name(ie_key)

        try:
            if dropin and hasattr(dropin, "skip_ytdlp_download") and dropin.skip_ytdlp_download(url, info_extractor_cls):
                logger.info(f"Dropin for {ie_key} requested to skip yt-dlp download. Attempting custom dropin processing.")
                if hasattr(dropin, "extract_post") and hasattr(dropin, "create_metadata"):
                    # This path is similar to the old get_metadata_for_post
                    # The dropin needs to return data that can be formatted into the generic dict
                    # This is a complex interaction point. For now, assume dropin might provide a dict
                    # that's already somewhat aligned or can be adapted.
                    ie_instance = info_extractor_cls(downloader=ydl) # Dropins often expect an IE instance
                    post_data = dropin.extract_post(url, ie_instance)
                    # The dropin.create_metadata used to return a Metadata object.
                    # This needs to be adapted. For now, we'll call it and if it returns a dict, use it.
                    # This is a simplification and a point for future deeper refactoring of dropins.
                    temp_metadata_obj = Metadata() # Create a dummy metadata if dropin needs it
                    temp_metadata_obj.set_url(url)
                    dropin_result = dropin.create_metadata(post_data, ie_instance, self, temp_metadata_obj)

                    if isinstance(dropin_result, Metadata): # Adapt Metadata object
                        # Convert Metadata object from dropin to our generic dict format
                        generic_output_metadata = {
                            "title": dropin_result.get_title(),
                            "description": dropin_result.get("content_html") or dropin_result.get("content_text") or dropin_result.get("content"),
                            "timestamp": dropin_result.get_timestamp().isoformat() if dropin_result.get_timestamp() else None,
                            "original_url": dropin_result.get_url() or url,
                            "uploader": dropin_result.get("author"),
                            # Add any other relevant fields from dropin_result.properties
                        }
                        generic_output_metadata.update(dropin_result.properties) # Add remaining properties

                        media_items = []
                        for m in dropin_result.media:
                            # Dropin media items need to have absolute filepaths or be downloadable by self.download_from_url
                            # This is a complex part if dropins manage their own downloads to different locations.
                            # For now, assume filepath is set and valid, or src is provided for download.
                            media_fp = m.filename
                            if not os.path.isabs(media_fp) and m.get("src"): # If path not set or relative, try downloading
                                logger.info(f"Dropin media {m.get('src')} needs download.")
                                dl_filename = os.path.basename(m.get("src").split("?")[0]) # basic filename
                                media_fp = self.download_from_url(m.get("src"), to_filename=dl_filename, tmp_dir_path=tmp_dir_path)

                            if media_fp and os.path.exists(media_fp):
                                media_items.append({
                                    "filepath": media_fp,
                                    "type": self._guess_file_type(media_fp) or m.get("type"),
                                    "id": m.get("id")
                                })
                            elif m.get("content_binary"): # If dropin provides binary content directly
                                # This needs to be saved to a file in tmp_dir_path
                                logger.warning("Dropin provided binary content, saving not yet implemented in this path.")


                        return {
                            "metadata": generic_output_metadata,
                            "media": media_items,
                            "extractor_info": f"yt-dlp_{ie_key}_dropin_custom"
                        }
                    elif isinstance(dropin_result, dict): # Dropin already returns a compatible dict
                        return dropin_result
                    else:
                        logger.warning(f"Dropin for {ie_key} skip_ytdlp_download was true, but create_metadata did not return Metadata or dict.")
                        return None
                else:
                    logger.warning(f"Dropin for {ie_key} requested skip_ytdlp_download but lacks extract_post/create_metadata methods.")
                    return None

            # Main extraction call to yt-dlp
            # download=True is default if ydl is configured with an output template.
            # ydl.extract_info will download files according to outtmpl in ydl_params.
            info_dict = ydl.extract_info(url, ie_key=ie_key, download=True)

            if not info_dict:
                logger.warning(f"yt-dlp extract_info returned no data for {url} with {ie_key}.")
                return None

            # Handle potential playlists or multi-video posts
            entries_to_process = info_dict.get("entries", [info_dict] if info_dict else [])
            processed_results = []

            for entry_index, entry_data in enumerate(entries_to_process):
                if not entry_data: continue

                media_items = []
                entry_id = entry_data.get("id", f"entry_{entry_index}")

                # Main media file path determination
                # yt-dlp's 'requested_downloads' usually contains info about downloaded files.
                # 'filename' key is often relative if run from CLI, but absolute if outtmpl is absolute.
                # ydl.prepare_filename(entry_data) gives the expected path based on outtmpl.
                main_media_filepath = ydl.prepare_filename(entry_data)
                if not os.path.isabs(main_media_filepath): # Should be absolute due to outtmpl
                    main_media_filepath = os.path.join(tmp_dir_path, os.path.basename(main_media_filepath))

                if os.path.exists(main_media_filepath):
                    media_items.append({
                        "filepath": main_media_filepath,
                        "type": self._guess_file_type(main_media_filepath) or entry_data.get("vcodec", "video") # Basic guess
                    })
                else:
                    # Check 'requested_downloads' if main file not at expected path (e.g. if filename differs from ID.ext)
                    # This part can be complex as yt-dlp's output structure varies.
                    # For now, rely on prepare_filename and existence check.
                    logger.warning(f"Main media file {main_media_filepath} not found for entry {entry_id}. Check yt-dlp output template and download process.")


                # Thumbnails - yt-dlp can download these if requested via --write-thumbnail
                # If not, we might need to download them manually.
                # Assuming _build_ydl_options added --write-thumbnail if self._extractor_args["thumbnails"] = True (or similar config)
                for thumb_info in entry_data.get("thumbnails", []):
                    thumb_url = thumb_info.get("url")
                    thumb_id = thumb_info.get("id", "") # e.g. 'cover'
                    # If yt-dlp downloaded it, filepath might be in thumb_info or derivable
                    thumb_filepath_key = "filepath" # yt-dlp >=2023.10.13 may put filepath here
                    if thumb_filepath_key in thumb_info and os.path.exists(thumb_info[thumb_filepath_key]):
                         media_items.append({"filepath": os.path.abspath(thumb_info[thumb_filepath_key]), "type": "thumbnail", "id": thumb_id or "thumbnail"})
                    elif thumb_url: # Fallback to manual download
                        try:
                            thumb_ext = os.path.splitext(thumb_url.split("?")[0])[1] or ".jpg"
                            thumb_filename = f"{entry_id}_thumb_{thumb_id}{thumb_ext}"
                            downloaded_thumb_path = self.download_from_url(thumb_url, to_filename=thumb_filename, tmp_dir_path=tmp_dir_path)
                            if downloaded_thumb_path and os.path.exists(downloaded_thumb_path):
                                media_items.append({"filepath": downloaded_thumb_path, "type": "thumbnail", "id": thumb_id or "thumbnail"})
                        except Exception as e:
                            logger.error(f"Failed to download thumbnail {thumb_url} for {entry_id}: {e}")

                # Subtitles - yt-dlp downloads these if --write-subs or --write-auto-subs is on
                # 'requested_subtitles' in entry_data will list downloaded subtitle files.
                for lang, sub_info in (entry_data.get("requested_subtitles") or {}).items():
                    sub_filepath = sub_info.get("filepath") # yt-dlp usually makes this absolute
                    if sub_filepath and os.path.exists(sub_filepath):
                         # Ensure it's absolute relative to tmp_dir_path if not already
                        if not os.path.isabs(sub_filepath): sub_filepath = os.path.join(tmp_dir_path, sub_filepath)

                        sub_text_content = None
                        if self._extractor_args.get("read_subtitle_text", False): # Add config if text is needed
                            try:
                                subs = pysubs2.load(sub_filepath, encoding="utf-8")
                                sub_text_content = " ".join([line.text for line in subs])
                            except Exception as e:
                                logger.error(f"Error reading subtitle file {sub_filepath}: {e}")

                        media_items.append({
                            "filepath": sub_filepath,
                            "type": "subtitle",
                            "language": lang,
                            "id": f"sub_{lang}",
                            "text_content": sub_text_content # Optional
                        })


                # Prepare metadata part of the generic dict
                entry_metadata = {
                    "title": entry_data.get("title") or entry_data.get("fulltitle"),
                    "description": entry_data.get("description"),
                    "timestamp": datetime.datetime.fromtimestamp(entry_data["timestamp"], tz=datetime.timezone.utc).isoformat() if entry_data.get("timestamp") else None,
                    "upload_date": get_datetime_from_str(entry_data["upload_date"], "%Y%m%d").replace(tzinfo=datetime.timezone.utc).isoformat() if entry_data.get("upload_date") else None,
                    "original_url": entry_data.get("webpage_url") or url,
                    "uploader": entry_data.get("uploader"),
                    "uploader_id": entry_data.get("uploader_id"),
                    "channel": entry_data.get("channel"),
                    "channel_id": entry_data.get("channel_id"),
                    "duration": entry_data.get("duration"),
                    "tags": entry_data.get("tags"),
                    "categories": entry_data.get("categories"),
                    "view_count": entry_data.get("view_count"),
                    "like_count": entry_data.get("like_count"),
                    "comment_count": entry_data.get("comment_count"), # if comments are not extracted separately
                    "age_limit": entry_data.get("age_limit"),
                    "live_status": entry_data.get("live_status"),
                    # Add raw ytdlp json if configured? self._extractor_args.get("include_raw_ytdlp_info")
                    "raw_yt_dlp_info": entry_data if self._extractor_args.get("include_raw_yt_dlp_info", False) else None,
                }
                # Clean out None values from metadata for cleaner output
                entry_metadata = {k:v for k,v in entry_metadata.items() if v is not None}

                # Comments (if yt-dlp extracted them)
                if self._comments and entry_data.get("comments"):
                    entry_metadata["comments_data"] = [ # Basic formatting
                        {
                            "text": c.get("text"), "author": c.get("author"), "author_id": c.get("author_id"),
                            "timestamp": datetime.datetime.fromtimestamp(c["timestamp"], tz=datetime.timezone.utc).isoformat() if c.get("timestamp") else None,
                            "id": c.get("id"), "parent": c.get("parent")
                        } for c in entry_data["comments"]
                    ]

                # Allow dropin to modify or add metadata/media (advanced use case)
                if dropin and hasattr(dropin, "post_process_entry"):
                    # This is a new hypothetical dropin method for fine-grained control.
                    # It would take entry_metadata, media_items, and entry_data
                    # and return modified (entry_metadata, media_items)
                    # For now, this is a placeholder for future extensibility.
                    pass


                processed_results.append({
                    "metadata": entry_metadata,
                    "media": media_items,
                    "extractor_info": f"yt-dlp_{ie_key}"
                })

            if not processed_results:
                return None
            return processed_results if info_dict.get("entries") else processed_results[0]

        except MaxDownloadsReached:
            logger.warning(f"Max downloads reached for {url} with {ie_key}. Processing partially downloaded content if any.")
            # This error is typically raised by ydl.download(), not extract_info().
            # If extract_info itself triggers this (e.g. internal download calls),
            # then info_dict might be None or incomplete.
            # The current structure expects extract_info to complete and then we check files.
            # If MaxDownloadsReached happens *during* ydl.extract_info, it's an exception yt-dlp handles.
            # The data returned by extract_info in this case needs to be checked.
            # For now, assume if it's caught here, no valid full data was returned.
            return None
        except yt_dlp.utils.DownloadError as de:
            # Specific download errors (e.g. video unavailable, private, geo-restricted)
            logger.warning(f"yt-dlp DownloadError for {url} with {ie_key}: {de}")
            # Check if it's a "video unavailable" type error that a dropin might handle (e.g. for posts)
            if dropin and hasattr(dropin, "handle_download_error"):
                # Hypothetical dropin method to attempt recovery or alternative extraction
                # dropin_alt_result = dropin.handle_download_error(de, url, ie_key, tmp_dir_path, self)
                # if dropin_alt_result: return dropin_alt_result
                pass # No generic handling for now, just log and return None
            return None
        except Exception as e:
            logger.error(f"Generic error during yt-dlp processing for {url} with {ie_key}: {e}", exc_info=True)
            # This could be an error during info extraction or file processing.
            return None
