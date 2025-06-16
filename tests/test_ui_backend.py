import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import os
import shutil

# Import the Flask app instance and schemas from the backend module
from auto_archiver.ui_backend import app as flask_app, EXTRACTOR_SCHEMAS, EXTRACTOR_MAP

# Import extractor classes for type checking and potentially for more complex mocking scenarios,
# though direct patching of their usage in ui_backend is the primary approach.
from auto_archiver.modules.generic_extractor.generic_extractor import GenericExtractor
from auto_archiver.modules.instagram_extractor.instagram_extractor import InstagramExtractor
from auto_archiver.modules.twitter_api_extractor.twitter_api_extractor import TwitterApiExtractor


class TestUIBackend(unittest.TestCase):

    def setUp(self):
        flask_app.testing = True
        self.client = flask_app.test_client()
        # This directory is for the final output specified by the user in the API call
        self.user_output_dir = tempfile.TemporaryDirectory(prefix="test_user_output_")
        # This directory simulates the temporary backend_tmp_dir used by extract_data
        self.backend_temp_dir_for_mocked_extractor = tempfile.TemporaryDirectory(prefix="test_backend_tmp_")

    def tearDown(self):
        self.user_output_dir.cleanup()
        self.backend_temp_dir_for_mocked_extractor.cleanup()

    def test_get_extractors_schema(self):
        response = self.client.get('/api/ui/extractors')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')

        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0) # Expecting at least one schema

        expected_ids = ["generic_extractor", "instagram_extractor", "twitter_api_extractor"]
        found_ids = []

        for item in data:
            self.assertIn('id', item)
            self.assertIn('name', item)
            self.assertIn('params', item)
            self.assertIsInstance(item['params'], list)
            found_ids.append(item['id'])
            # Check a param structure for one of them if needed
            if item['id'] == "generic_extractor" and item['params']:
                param = item['params'][0]
                self.assertIn('name', param)
                self.assertIn('label', param)
                self.assertIn('type', param)

        for expected_id in expected_ids:
            self.assertIn(expected_id, found_ids)

    @patch('auto_archiver.ui_backend.GenericExtractor')
    def test_extract_success_generic_extractor(self, mock_generic_extractor_class: MagicMock):
        # --- Mocking Setup ---
        mock_extractor_instance = MagicMock(spec=GenericExtractor)
        mock_generic_extractor_class.return_value = mock_extractor_instance

        # Create a dummy file that the mocked extract_data will "return"
        dummy_media_filename = "test_video.mp4"
        dummy_media_content = b"dummy video content"
        # This path is where the mocked extract_data supposedly downloaded the file
        mocked_download_filepath = os.path.join(self.backend_temp_dir_for_mocked_extractor.name, dummy_media_filename)
        with open(mocked_download_filepath, 'wb') as f:
            f.write(dummy_media_content)

        mock_extract_data_return = {
            "metadata": {"title": "Test Video", "original_url": "some_test_url"},
            "media": [{"filepath": mocked_download_filepath, "type": "video", "original_url": "video_source_url"}],
            "extractor_info": "yt-dlp_youtube"
        }
        mock_extractor_instance.extract_data.return_value = mock_extract_data_return

        # --- Prepare Payload ---
        payload = {
            "extractor_id": "generic_extractor",
            "url": "some_test_url",
            "output_path": self.user_output_dir.name,
            "config_values": {"allow_playlist": True, "subtitles": "false"} # mix types to test processing
        }

        # --- Make API Call ---
        response = self.client.post('/api/ui/extract', json=payload)

        # --- Assertions ---
        self.assertEqual(response.status_code, 200, f"Response data: {response.data.decode()}")
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'success')

        # Check extractor instantiation (processed config values)
        # The boolean "false" should be converted to False
        mock_generic_extractor_class.assert_called_once_with(allow_playlist=True, subtitles=False)

        # Check extract_data call
        # The tmp_dir_path will be a dynamic path from a TemporaryDirectory context manager in the endpoint
        # So, we check that it was called, but not the exact tmp_dir_path value.
        self.assertTrue(mock_extractor_instance.extract_data.called)
        call_args = mock_extractor_instance.extract_data.call_args
        self.assertEqual(call_args[1]['url'], payload['url']) # Check named 'url' arg
        self.assertTrue(os.path.isdir(call_args[1]['tmp_dir_path'])) # Check tmp_dir_path was a dir

        # Verify data structure in response
        self.assertIn('data', response_data)
        self.assertEqual(response_data['data']['metadata']['title'], "Test Video")
        self.assertTrue(len(response_data['data']['media']) == 1)

        # Check file movement and updated filepath in response
        final_media_item = response_data['data']['media'][0]
        expected_final_filepath = os.path.join(self.user_output_dir.name, dummy_media_filename)
        self.assertEqual(final_media_item['filepath'], expected_final_filepath)
        self.assertTrue(os.path.exists(expected_final_filepath))
        # Verify content was moved
        with open(expected_final_filepath, 'rb') as f:
            content = f.read()
            self.assertEqual(content, dummy_media_content)
        self.assertFalse(os.path.exists(mocked_download_filepath)) # Original should be moved

    def test_extract_invalid_extractor_id(self):
        payload = {
            "extractor_id": "non_existent_extractor",
            "url": "some_url",
            "output_path": self.user_output_dir.name,
            "config_values": {}
        }
        response = self.client.post('/api/ui/extract', json=payload)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Unknown extractor ID", response_data['message'])

    def test_extract_missing_output_path(self):
        payload = {
            "extractor_id": "generic_extractor",
            "url": "some_url",
            # "output_path": self.user_output_dir.name, # Missing
            "config_values": {}
        }
        response = self.client.post('/api/ui/extract', json=payload)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Missing 'output_path'", response_data['message'])

    def test_extract_output_path_not_absolute(self):
        payload = {
            "extractor_id": "generic_extractor",
            "url": "some_url",
            "output_path": "relative/path",
            "config_values": {}
        }
        response = self.client.post('/api/ui/extract', json=payload)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("'output_path' must be an absolute path", response_data['message'])


    @patch('auto_archiver.ui_backend.GenericExtractor')
    def test_extract_extractor_instantiation_fails(self, mock_generic_extractor_class: MagicMock):
        mock_generic_extractor_class.side_effect = Exception("Test Extractor Init Failed")

        payload = {
            "extractor_id": "generic_extractor",
            "url": "some_url",
            "output_path": self.user_output_dir.name,
            "config_values": {}
        }
        response = self.client.post('/api/ui/extract', json=payload)
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Failed to instantiate extractor: Test Extractor Init Failed", response_data['message'])

    @patch('auto_archiver.ui_backend.GenericExtractor')
    def test_extract_extract_data_returns_none(self, mock_generic_extractor_class: MagicMock):
        mock_extractor_instance = MagicMock()
        mock_generic_extractor_class.return_value = mock_extractor_instance
        mock_extractor_instance.extract_data.return_value = None # Simulate extractor finding nothing

        payload = {
            "extractor_id": "generic_extractor",
            "url": "some_url_that_returns_nothing",
            "output_path": self.user_output_dir.name,
            "config_values": {}
        }
        response = self.client.post('/api/ui/extract', json=payload)
        # The backend returns 500 if extract_data is None, as it's considered an issue if nothing is processed.
        # A 200 with status:"error" or empty data could also be a valid design.
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Extractor returned no data", response_data['message'])

    @patch('auto_archiver.ui_backend.GenericExtractor')
    def test_extract_file_move_preserves_uniqueness(self, mock_generic_extractor_class: MagicMock):
        mock_extractor_instance = MagicMock()
        mock_generic_extractor_class.return_value = mock_extractor_instance

        # Create two dummy files with the same basename in the "backend" temp dir
        common_basename = "video.mp4"
        mocked_dl_filepath1 = os.path.join(self.backend_temp_dir_for_mocked_extractor.name, "A_" + common_basename)
        mocked_dl_filepath2 = os.path.join(self.backend_temp_dir_for_mocked_extractor.name, "B_" + common_basename) # different source names

        # Create a file that already exists in the output_path with the common_basename
        # to force renaming for at least one of the new files.
        pre_existing_file_path = os.path.join(self.user_output_dir.name, common_basename)
        with open(pre_existing_file_path, 'wb') as f:
            f.write(b"pre-existing content")

        with open(mocked_dl_filepath1, 'wb') as f:
            f.write(b"content1")
        # For the second file, we will make its *original* basename clash after moving the first one.
        # No, the test is about clashing basenames from the *source* if they were to be moved *naively*.
        # The backend code should handle this by creating unique names in the *destination*.
        # Let's simulate extract_data returning two files that would have the same destination name if not handled.
        # The current backend code uses os.path.basename on the source, so this test needs careful setup.
        # The backend creates unique names based on the *original* basename.

        # To test uniqueness, we need two files that, after `os.path.basename`, would be identical.
        # The current code `destination_filename = os.path.basename(original_temp_filepath)`
        # means we need different `original_temp_filepath` that result in same basename.
        # This is hard to simulate without complex mocking of `extract_data` output structure.
        # A simpler test: ensure if a file *already exists* in output_path, the new one is renamed.

        # Let's simplify: mock one file whose basename clashes with pre_existing_file_path.
        mock_extract_data_return = {
            "metadata": {"title": "Test"},
            "media": [
                {"filepath": mocked_dl_filepath1, "type": "video"} # This file is A_video.mp4
            ],
            "extractor_info": "yt-dlp_test"
        }
        # Rename mocked_dl_filepath1 to have the clashing basename for the purpose of this test
        clashing_temp_path = os.path.join(self.backend_temp_dir_for_mocked_extractor.name, common_basename)
        shutil.copy(mocked_dl_filepath1, clashing_temp_path) # Now we have backend_tmp/video.mp4
        mock_extract_data_return["media"][0]["filepath"] = clashing_temp_path


        mock_extractor_instance.extract_data.return_value = mock_extract_data_return

        payload = {
            "extractor_id": "generic_extractor", "url": "url1",
            "output_path": self.user_output_dir.name, "config_values": {}
        }
        response = self.client.post('/api/ui/extract', json=payload)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'success')

        final_media_item = response_data['data']['media'][0]
        # Expected: user_output_dir/video_1.mp4 because user_output_dir/video.mp4 already exists
        expected_renamed_filepath = os.path.join(self.user_output_dir.name, "video_1.mp4")
        self.assertEqual(final_media_item['filepath'], expected_renamed_filepath)
        self.assertTrue(os.path.exists(expected_renamed_filepath))
        with open(expected_renamed_filepath, 'rb') as f:
            self.assertEqual(f.read(), b"content1")

        # Ensure the pre-existing file is untouched
        self.assertTrue(os.path.exists(pre_existing_file_path))
        with open(pre_existing_file_path, 'rb') as f:
            self.assertEqual(f.read(), b"pre-existing content")


if __name__ == '__main__':
    unittest.main()
