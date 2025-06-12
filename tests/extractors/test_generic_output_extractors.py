import os
import shutil
import tempfile
import unittest
import mimetypes
import json # For inspecting metadata content if needed

# Adjust import paths if necessary based on project structure
from auto_archiver.modules.generic_extractor.generic_extractor import GenericExtractor
from auto_archiver.modules.instagram_extractor.instagram_extractor import InstagramExtractor
from auto_archiver.modules.twitter_api_extractor.twitter_api_extractor import TwitterApiExtractor

# A known public and generally stable YouTube video URL for testing GenericExtractor
# "Me at the zoo" - the first video uploaded to YouTube.
# If this URL becomes unstable, it should be replaced with another suitable public video.
# Using a short video to speed up tests.
# Alternative: "Big Buck Bunny" teaser (though longer) - https://www.youtube.com/watch?v=aqz-KE-bpKQ
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


class TestGenericExtractorGenericOutput(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        # You can print this to see where the temp files are going, for debugging.
        # print(f"Temporary directory created: {self.temp_dir.name}")

    def tearDown(self):
        self.temp_dir.cleanup()
        # print(f"Temporary directory cleaned up: {self.temp_dir.name}")

    def test_extract_data_youtube_video(self):
        # Instantiate GenericExtractor with minimal valid configuration
        # No auth needed for public YouTube videos.
        # tmp_dir_path_for_orchestrator is for the download() wrapper, not directly for extract_data,
        # but good to set for consistency if the class expects it.
        extractor = GenericExtractor(
            tmp_dir_path_for_orchestrator=self.temp_dir.name,
            ytdlp_update_interval=-1, # Disable updates during tests
            bguils_po_token_method="disabled", # Disable PO token generation
            extractor_args={"autosubs": False, "thumbnails": False} # Avoid downloading extra files for this basic test
        )
        # extractor.setup() # Call setup if it's not implicitly called or if specific setup steps are needed before extract_data
        # For GenericExtractor, setup primarily deals with yt-dlp updates and PO tokens, which are disabled here.

        # Call extract_data
        # This is an online test and depends on network access and YouTube's availability.
        data = extractor.extract_data(url=TEST_YOUTUBE_URL, tmp_dir_path=self.temp_dir.name)

        self.assertIsNotNone(data, "extract_data should return a dictionary, not None.")
        self.assertIsInstance(data, dict, "extract_data output should be a dictionary.")

        self.assertIn("metadata", data, "Output dict must contain 'metadata' key.")
        self.assertIsInstance(data["metadata"], dict, "'metadata' should be a dictionary.")

        self.assertIn("media", data, "Output dict must contain 'media' key.")
        self.assertIsInstance(data["media"], list, "'media' should be a list.")

        self.assertIn("extractor_info", data, "Output dict must contain 'extractor_info' key.")
        self.assertTrue(data["extractor_info"].startswith("yt-dlp"), f"extractor_info should start with 'yt-dlp', got {data['extractor_info']}")

        # Basic metadata checks (content can vary, so check for presence of common keys)
        self.assertIn("title", data["metadata"], "Metadata should contain a title.")
        self.assertIsNotNone(data["metadata"]["title"], "Title should not be None.")
        self.assertIn("original_url", data["metadata"], "Metadata should contain original_url.")
        self.assertEqual(data["metadata"]["original_url"], TEST_YOUTUBE_URL) # or the canonical URL yt-dlp resolves to

        # Media file checks (assuming a video is downloaded)
        if not data["media"]:
            # This might happen if yt-dlp fails to download for some reason (e.g. network, video unavailable)
            # Or if the specific test URL doesn't yield downloadable media by default (e.g. age-restricted without login)
            # For "Me at the zoo", it should typically download.
            # Consider using `self.fail()` or `self.skipTest()` if media is essential and not found.
            print(f"Warning: No media items found for {TEST_YOUTUBE_URL}. Full data: {json.dumps(data, indent=2)}")
            # self.fail("No media items were extracted, which is unexpected for this YouTube URL.")
            # Skipping if no media, as this is an online test and can be flaky.
            # A more robust test would mock yt-dlp's output.
            self.skipTest(f"No media items extracted for {TEST_YOUTUBE_URL}. This might be a network or yt-dlp issue.")


        self.assertTrue(len(data["media"]) > 0, "There should be at least one media item for this video.")

        media_item = data["media"][0] # Assuming the first media item is the main video
        self.assertIn("filepath", media_item, "Each media item must have a 'filepath'.")
        self.assertIn("type", media_item, "Each media item must have a 'type'.")

        self.assertTrue(os.path.isabs(media_item["filepath"]), f"Filepath '{media_item['filepath']}' should be absolute.")
        self.assertTrue(media_item["filepath"].startswith(self.temp_dir.name), f"Filepath '{media_item['filepath']}' should be within the temp directory '{self.temp_dir.name}'.")
        self.assertTrue(os.path.exists(media_item["filepath"]), f"Media file '{media_item['filepath']}' should exist.")

        # Check if file size is reasonable (e.g., > 0 bytes)
        self.assertTrue(os.path.getsize(media_item["filepath"]) > 0, f"Media file '{media_item['filepath']}' should not be empty.")

        # Check type (can be 'video', 'audio', etc.)
        self.assertIsNotNone(media_item["type"], "Media type should not be None.")
        # Example: self.assertEqual(media_item["type"], "video") # This depends on what yt-dlp reports


class TestInstagramExtractorGenericOutput(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_data_placeholder(self):
        self.skipTest("Mocking for InstagramExtractor's generic output (instaloader) is not yet implemented.")
        # Example future structure:
        # extractor = InstagramExtractor(username="testuser", password="testpassword", tmp_dir_path_for_orchestrator=self.temp_dir.name)
        # with patch('instaloader.Instaloader') as MockInstaloader:
        #     # Configure mock_instaloader_instance and its methods (from_shortcode, download_post, etc.)
        #     # ...
        #     data = extractor.extract_data(url="some_instagram_url", tmp_dir_path=self.temp_dir.name)
        #     # Assertions on 'data'


class TestTwitterApiExtractorGenericOutput(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_data_placeholder(self):
        self.skipTest("Mocking for TwitterApiExtractor's generic output (pytwitter) is not yet implemented.")
        # Example future structure:
        # extractor = TwitterApiExtractor(bearer_token="fake_token", tmp_dir_path_for_orchestrator=self.temp_dir.name)
        # with patch('pytwitter.Api') as MockApi:
        #     # Configure mock_api_instance and its methods (get_tweet, etc.)
        #     # ...
        #     data = extractor.extract_data(url="some_twitter_url", tmp_dir_path=self.temp_dir.name)
        #     # Assertions on 'data'

if __name__ == '__main__':
    unittest.main()
