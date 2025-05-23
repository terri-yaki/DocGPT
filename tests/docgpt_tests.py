import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import sys
import io

# Ensure the app directory is in the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import docgpt
from docgpt import (
    get_github_token,
    get_github_user,
    list_repositories,
    has_readme,
    after_selection,
    main,
    SERVICE_NAME,
    AUTH_PORT_FILE,
    AUTH_CODE_FILE
)

# Mock keyring before it's imported by docgpt's main flow
# This is a common pattern: mock dependencies early.
# However, docgpt.py itself imports keyring. So, if keyring is used at module level
# in docgpt before main() is called (which it isn't heavily), this might be tricky.
# For functions directly using keyring, we can patch them there.
# For main(), we'll patch keyring methods directly.
mock_keyring = MagicMock()
# We need to allow 'keyring.errors.NoKeyringError' to be accessed as an attribute if docgpt tries to catch it.
mock_keyring.errors = MagicMock()
mock_keyring.errors.NoKeyringError = type('NoKeyringError', (Exception,), {})
mock_keyring.errors.PasswordDeleteError = type('PasswordDeleteError', (Exception,), {})


class TestDocGPT(unittest.TestCase):

    def setUp(self):
        # Patch external dependencies
        self.keyring_patcher = patch('docgpt.keyring', mock_keyring)
        self.requests_get_patcher = patch('requests.get')
        self.requests_post_patcher = patch('requests.post')
        self.open_patcher = patch('builtins.open', new_callable=mock_open)
        self.os_path_exists_patcher = patch('os.path.exists')
        self.os_remove_patcher = patch('os.remove')
        self.os_makedirs_patcher = patch('os.makedirs')
        self.webbrowser_open_patcher = patch('webbrowser.open')
        self.time_sleep_patcher = patch('time.sleep', return_value=None) # Avoid actual sleeps
        self.commit_patcher = patch('docgpt.commit') # from readmegen, used in after_selection
        self.generate_readme_patcher = patch('docgpt.generate_readme')

        self.mock_keyring = self.keyring_patcher.start()
        self.mock_requests_get = self.requests_get_patcher.start()
        self.mock_requests_post = self.requests_post_patcher.start()
        self.mock_open = self.open_patcher.start()
        self.mock_os_path_exists = self.os_path_exists_patcher.start()
        self.mock_os_remove = self.os_remove_patcher.start()
        self.mock_os_makedirs = self.os_makedirs_patcher.start()
        self.mock_webbrowser_open = self.webbrowser_open_patcher.start()
        self.mock_time_sleep = self.time_sleep_patcher.start()
        self.mock_commit = self.commit_patcher.start()
        self.mock_generate_readme = self.generate_readme_patcher.start()
        
        # Reset keyring mock calls for each test
        mock_keyring.reset_mock()

        # Environment variables
        self.env_patcher = patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_client_secret",
            "OPENAI_API_KEY": "test_openai_key" # Though not directly used by docgpt.py funcs here
        })
        self.env_patcher.start()

        # Suppress print output during tests by default
        self.stdout_patcher = patch('sys.stdout', new_callable=io.StringIO)
        self.mock_stdout = self.stdout_patcher.start()


    def tearDown(self):
        self.keyring_patcher.stop()
        self.requests_get_patcher.stop()
        self.requests_post_patcher.stop()
        self.open_patcher.stop()
        self.os_path_exists_patcher.stop()
        self.os_remove_patcher.stop()
        self.os_makedirs_patcher.stop()
        self.webbrowser_open_patcher.stop()
        self.time_sleep_patcher.stop()
        self.commit_patcher.stop()
        self.generate_readme_patcher.stop()
        self.env_patcher.stop()
        self.stdout_patcher.stop()

    # --- Token Handling Tests ---
    def test_get_github_token_success(self):
        self.mock_requests_post.return_value.status_code = 200
        self.mock_requests_post.return_value.json.return_value = {"access_token": "fake_token"}
        
        token = get_github_token("test_code", "test_user")
        
        self.assertEqual(token, "fake_token")
        self.mock_requests_post.assert_called_once()
        # Check if keyring.set_password was called if a user was provided
        self.mock_keyring.set_password.assert_called_with(SERVICE_NAME, "test_user", "fake_token")

    def test_get_github_token_no_user_no_keyring_set(self):
        self.mock_requests_post.return_value.status_code = 200
        self.mock_requests_post.return_value.json.return_value = {"access_token": "fake_token"}
        
        # Call with github_user=None or default "default_user" but check no specific user store
        # The function defaults github_user to "default_user", so it will try to store.
        # Let's test the "default_user" case
        token = get_github_token("test_code") # Uses default_user="default_user"
        
        self.assertEqual(token, "fake_token")
        self.mock_keyring.set_password.assert_called_with(SERVICE_NAME, "default_user", "fake_token")

    def test_get_github_token_failure_http_error(self):
        self.mock_requests_post.return_value.raise_for_status.side_effect = docgpt.requests.exceptions.HTTPError("API Error")
        self.mock_requests_post.return_value.status_code = 500 # Mocking a server error
        
        token = get_github_token("test_code", "test_user")
        
        self.assertIsNone(token)
        self.mock_keyring.set_password.assert_not_called()

    def test_get_github_token_failure_request_exception(self):
        self.mock_requests_post.side_effect = docgpt.requests.exceptions.RequestException("Network Error")
        
        token = get_github_token("test_code", "test_user")
        
        self.assertIsNone(token)
        self.mock_keyring.set_password.assert_not_called()

    def test_get_github_token_keyring_no_keyring_error(self):
        self.mock_requests_post.return_value.status_code = 200
        self.mock_requests_post.return_value.json.return_value = {"access_token": "fake_token_keyring_error"}
        self.mock_keyring.set_password.side_effect = mock_keyring.errors.NoKeyringError
        
        token = get_github_token("test_code", "test_user_keyring_error")
        
        self.assertEqual(token, "fake_token_keyring_error")
        self.mock_keyring.set_password.assert_called_once_with(SERVICE_NAME, "test_user_keyring_error", "fake_token_keyring_error")
        # Check for warning print:
        # output = self.mock_stdout.getvalue() # This might be tricky if stdout is suppressed widely
        # self.assertIn("Warning: Keyring backend not found", output)


    def test_get_github_user_success(self):
        self.mock_requests_get.return_value.status_code = 200
        self.mock_requests_get.return_value.json.return_value = {"login": "test_user_login"}
        
        user = get_github_user("fake_token")
        
        self.assertEqual(user, "test_user_login")
        self.mock_requests_get.assert_called_once_with('https://api.github.com/user', headers={'Authorization': 'token fake_token'}, timeout=10)

    def test_get_github_user_failure(self):
        self.mock_requests_get.return_value.raise_for_status.side_effect = docgpt.requests.exceptions.HTTPError("API Error")
        self.mock_requests_get.return_value.status_code = 401
        
        user = get_github_user("fake_token")
        self.assertIsNone(user)

    # More tests for main() and other functions will follow.

    # --- main() Token and Authentication Flow Tests ---

    @patch('docgpt.Thread') # Mock Thread to prevent actual thread start
    @patch('docgpt.input', return_value='test_code') # Mock input for auth code
    @patch('docgpt.list_repositories', return_value=[]) # Assume no repos to simplify test
    def test_main_uses_keyring_token_and_verifies_user(self, mock_list_repos, mock_input, mock_thread):
        self.mock_keyring.get_password.return_value = "stored_token"
        # Mock get_github_user to successfully return a username
        self.mock_requests_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"login": "actual_user"}) # For get_github_user
        ]
        
        main() # Call the main function

        self.mock_keyring.get_password.assert_any_call(SERVICE_NAME, "default_user")
        # It should try to get the user with the stored token
        self.mock_requests_get.assert_called_once_with('https://api.github.com/user', headers={'Authorization': 'token stored_token'}, timeout=10)
        # It should update the keyring with the actual username
        self.mock_keyring.set_password.assert_called_with(SERVICE_NAME, "actual_user", "stored_token")
        # It should try to delete the old "default_user" token
        self.mock_keyring.delete_password.assert_called_with(SERVICE_NAME, "default_user")
        # OAuth flow (input for code, requests.post for token) should NOT be called
        mock_input.assert_not_called()
        self.mock_requests_post.assert_not_called()
        # list_repositories should be called with the stored token
        mock_list_repos.assert_called_with("stored_token")


    @patch('docgpt.Thread')
    @patch('docgpt.input', return_value='test_code') # Mock input for auth code
    @patch('docgpt.list_repositories', return_value=[])
    def test_main_oauth_flow_when_no_keyring_token(self, mock_list_repos, mock_input, mock_thread):
        self.mock_keyring.get_password.return_value = None # No stored token
        self.mock_os_path_exists.side_effect = [True, False, True] # auth_port.txt exists, auth_code.txt doesn't initially, then does
        self.mock_open.side_effect = [
            mock_open(read_data="12345").return_value,  # For auth_port.txt
            mock_open(read_data="test_auth_code").return_value # For auth_code.txt
        ]
        # Mock token fetching and user verification
        self.mock_requests_post.return_value.status_code = 200
        self.mock_requests_post.return_value.json.return_value = {"access_token": "new_token"}
        self.mock_requests_get.return_value.status_code = 200
        self.mock_requests_get.return_value.json.return_value = {"login": "new_github_user"}

        main()

        self.mock_keyring.get_password.assert_any_call(SERVICE_NAME, "default_user")
        # OAuth flow should be triggered
        self.mock_webbrowser_open.assert_called_once() # Opens browser for auth
        # Check if auth_port.txt was read
        self.mock_open.assert_any_call(AUTH_PORT_FILE, "r")
        # Check if auth_code.txt was read (or input was called if it timed out)
        # Based on side_effect for os.path.exists, it should find auth_code.txt
        self.mock_open.assert_any_call(AUTH_CODE_FILE, "r")
        mock_input.assert_not_called() # Should not call input if file found
        
        # New token should be fetched
        self.mock_requests_post.assert_called_once() 
        # User should be fetched with the new token
        self.mock_requests_get.assert_called_once_with('https://api.github.com/user', headers={'Authorization': 'token new_token'}, timeout=10)
        # New token should be stored in keyring with the new_github_user
        self.mock_keyring.set_password.assert_any_call(SERVICE_NAME, "new_github_user", "new_token")
        # Also, it initially stores with "default_user" inside get_github_token if called that way
        # And then it tries to delete "default_user" after storing with actual user
        self.mock_keyring.delete_password.assert_any_call(SERVICE_NAME, "default_user")
        mock_list_repos.assert_called_with("new_token")

    @patch('docgpt.Thread')
    @patch('docgpt.input', return_value='test_code') # Mock input for auth code
    @patch('docgpt.list_repositories', return_value=[])
    def test_main_keyring_token_invalid_user_triggers_oauth(self, mock_list_repos, mock_input, mock_thread):
        self.mock_keyring.get_password.return_value = "stored_token_invalid_user"
        # Mock get_github_user to fail (e.g., token revoked, user not found)
        self.mock_requests_get.side_effect = [
            MagicMock(status_code=401, json=lambda: {"message": "Bad credentials"}), # For get_github_user (initial check)
            MagicMock(status_code=200, json=lambda: {"login": "new_user_after_oauth"}) # For get_github_user (after new token)
        ]
        self.mock_os_path_exists.side_effect = [True, True] # auth_port.txt, auth_code.txt
        self.mock_open.side_effect = [
            mock_open(read_data="12345").return_value,
            mock_open(read_data="test_auth_code_reauth").return_value
        ]
        self.mock_requests_post.return_value.status_code = 200 # For new token fetch
        self.mock_requests_post.return_value.json.return_value = {"access_token": "fresh_token"}


        main()

        self.mock_keyring.get_password.assert_any_call(SERVICE_NAME, "default_user")
        # First call to get_github_user (verifying stored token)
        self.mock_requests_get.assert_any_call('https://api.github.com/user', headers={'Authorization': 'token stored_token_invalid_user'}, timeout=10)
        
        # OAuth flow should be triggered because user validation failed
        self.mock_webbrowser_open.assert_called_once()
        self.mock_requests_post.assert_called_once() # New token fetched
        # Second call to get_github_user (with fresh_token)
        self.mock_requests_get.assert_any_call('https://api.github.com/user', headers={'Authorization': 'token fresh_token'}, timeout=10)
        
        self.mock_keyring.set_password.assert_any_call(SERVICE_NAME, "new_user_after_oauth", "fresh_token")
        mock_list_repos.assert_called_with("fresh_token")

    # --- Auth File Interaction Tests ---
    @patch('docgpt.Thread')
    @patch('docgpt.input', return_value='test_manual_code') # Fallback input
    @patch('docgpt.get_github_token') # Mock to prevent actual token logic
    @patch('docgpt.get_github_user')
    @patch('docgpt.list_repositories', return_value=[])
    def test_main_reads_auth_port_and_code_files(self, mock_list_repos, mock_get_user, mock_get_token, mock_input, mock_thread):
        self.mock_keyring.get_password.return_value = None # No stored token, trigger OAuth
        self.mock_os_path_exists.side_effect = [
            False, True, # For auth_port.txt loop (first not found, then found)
            False, True  # For auth_code.txt loop (first not found, then found)
        ]
        # Simulate file creation
        self.mock_open.side_effect = [
            mock_open(read_data="54321").return_value,  # auth_port.txt
            mock_open(read_data="file_auth_code").return_value # auth_code.txt
        ]
        mock_get_token.return_value = "token_from_file_code"
        mock_get_user.return_value = "user_from_file_code"

        main()

        # Verify auth_port.txt was checked and read
        self.mock_os_path_exists.assert_any_call(AUTH_PORT_FILE)
        self.mock_open.assert_any_call(AUTH_PORT_FILE, "r")
        
        # Verify auth_code.txt was checked and read
        self.mock_os_path_exists.assert_any_call(AUTH_CODE_FILE)
        self.mock_open.assert_any_call(AUTH_CODE_FILE, "r")
        
        # Input should NOT be called for auth code as file was found
        mock_input.assert_not_called()
        mock_get_token.assert_called_with("file_auth_code", "default_user")
        mock_list_repos.assert_called_with("token_from_file_code")
        # Check cleanup
        self.mock_os_remove.assert_any_call(AUTH_PORT_FILE)
        self.mock_os_remove.assert_any_call(AUTH_CODE_FILE)


    @patch('docgpt.Thread')
    @patch('docgpt.input', return_value='manual_auth_code') # Fallback for code
    @patch('docgpt.get_github_token')
    @patch('docgpt.get_github_user')
    @patch('docgpt.list_repositories', return_value=[])
    def test_main_auth_code_file_timeout_fallback_to_input(self, mock_list_repos, mock_get_user, mock_get_token, mock_input, mock_thread):
        self.mock_keyring.get_password.return_value = None # Trigger OAuth
        # Simulate auth_port.txt exists, but auth_code.txt never does
        self.mock_os_path_exists.side_effect = lambda path: True if path == AUTH_PORT_FILE else False
        self.mock_open.side_effect = [
            mock_open(read_data="54321").return_value,  # auth_port.txt
            # No mock for auth_code.txt open, as os.path.exists will be false
        ]
        mock_get_token.return_value = "token_from_manual_code"
        mock_get_user.return_value = "user_from_manual_code"

        main()
        
        # auth_code.txt would be checked multiple times (60 times due to loop)
        self.assertEqual(self.mock_os_path_exists.call_count, 1 + 60) # 1 for port, 60 for code
        self.mock_os_path_exists.assert_any_call(AUTH_CODE_FILE)
        
        # Fallback input for auth code should be called
        mock_input.assert_called_once_with("Please manually copy and paste the authorization code from your browser: ")
        mock_get_token.assert_called_with("manual_auth_code", "default_user")
        mock_list_repos.assert_called_with("token_from_manual_code")


    @patch('docgpt.Thread')
    @patch('docgpt.input', return_value='any_input')
    @patch('docgpt.list_repositories', return_value=[])
    def test_main_auth_port_file_timeout(self, mock_list_repos, mock_input, mock_thread):
        self.mock_keyring.get_password.return_value = None # Trigger OAuth
        # Simulate auth_port.txt never existing
        self.mock_os_path_exists.return_value = False
        
        main()

        # Check that auth_port.txt was polled (10 times)
        self.assertEqual(self.mock_os_path_exists.call_count, 10)
        self.mock_os_path_exists.assert_called_with(AUTH_PORT_FILE)
        
        # Webbrowser should not be opened, no token fetching if port is not found
        self.mock_webbrowser_open.assert_not_called()
        self.mock_requests_post.assert_not_called()
        mock_list_repos.assert_not_called() # Should exit before this

    @patch('docgpt.Thread')
    @patch('docgpt.input', return_value='test_code')
    @patch('docgpt.get_github_token', return_value="final_token")
    @patch('docgpt.get_github_user', return_value="final_user")
    @patch('docgpt.list_repositories', return_value=[])
    def test_main_temp_files_cleanup_on_success(self, mock_list_repos, mock_get_user, mock_get_token, mock_input, mock_thread):
        self.mock_keyring.get_password.return_value = None # Trigger OAuth
        # Simulate both files being created and read
        self.mock_os_path_exists.return_value = True 
        self.mock_open.side_effect = [
            mock_open(read_data="12345").return_value,  # auth_port.txt
            mock_open(read_data="test_auth_code").return_value  # auth_code.txt
        ]
        
        main()

        self.mock_os_remove.assert_any_call(AUTH_PORT_FILE)
        self.mock_os_remove.assert_any_call(AUTH_CODE_FILE)

    @patch('docgpt.Thread')
    @patch('docgpt.input', side_effect=KeyboardInterrupt) # Simulate user cancelling
    def test_main_temp_files_cleanup_on_keyboard_interrupt(self, mock_input, mock_thread):
        self.mock_keyring.get_password.return_value = None # Trigger OAuth
        # Simulate auth_port.txt was created
        self.mock_os_path_exists.side_effect = lambda path: path == AUTH_PORT_FILE
        self.mock_open.return_value = mock_open(read_data="12345").return_value
        
        with self.assertRaises(SystemExit) as cm: # Assuming KeyboardInterrupt leads to sys.exit or is caught
            main()
        
        # Even on KeyboardInterrupt, cleanup should be attempted
        # Depending on where KI is caught and how finally is structured.
        # The main() in docgpt.py has a try/finally that does this.
        self.mock_os_remove.assert_any_call(AUTH_PORT_FILE)
        # AUTH_CODE_FILE might not have been created or removed yet if KI happened early
        # So, we check for AUTH_PORT_FILE which is handled before input typically.
        # If the test needs to be more specific, we'd need to control os.path.exists for AUTH_CODE_FILE too.

    # --- CLI Interaction and README Handling Tests ---
    def test_after_selection_saves_locally_and_commits(self):
        self.mock_input.side_effect = ["yes", "my-feature-branch"] # Commit? Yes. Branch? my-feature-branch.
        self.mock_commit.return_value = True # Simulate successful commit
        
        repo_data = {"name": "test_repo", "html_url": "http://example.com/test_repo"}
        readme_content = "This is a test README."
        save_folder = "test_save_folder"

        after_selection("fake_token", repo_data, readme_content, save_folder)

        # Check local save
        self.mock_os_makedirs.assert_called_once_with(save_folder, exist_ok=True)
        expected_save_path = os.path.join(save_folder, "test_repo_README.md")
        self.mock_open.assert_called_once_with(expected_save_path, "w", encoding='utf-8')
        self.mock_open().write.assert_called_once_with(readme_content)
        
        # Check commit call
        self.mock_commit.assert_called_once_with("fake_token", repo_data, readme_content, "my-feature-branch")

    def test_after_selection_saves_locally_no_commit(self):
        self.mock_input.return_value = "no" # Commit? No.
        
        repo_data = {"name": "test_repo_no_commit"}
        readme_content = "README content for no commit."
        save_folder = "test_save_folder"

        after_selection("fake_token", repo_data, readme_content, save_folder)

        self.mock_os_makedirs.assert_called_once_with(save_folder, exist_ok=True)
        expected_save_path = os.path.join(save_folder, "test_repo_no_commit_README.md")
        self.mock_open.assert_called_once_with(expected_save_path, "w", encoding='utf-8')
        
        self.mock_commit.assert_not_called()

    def test_after_selection_empty_readme_content(self):
        repo_data = {"name": "test_repo_empty_readme"}
        
        after_selection("fake_token", repo_data, "", "test_save_folder") # Empty readme_content
        
        self.mock_open.assert_not_called() # Should not attempt to save
        self.mock_commit.assert_not_called() # Should not attempt to commit

    def test_after_selection_local_save_io_error_then_no_commit(self):
        self.mock_open.side_effect = IOError("Disk full")
        self.mock_input.return_value = "no" # User says no to commit after save failure
        
        repo_data = {"name": "test_repo_io_error"}
        readme_content = "Content that will fail to save."
        
        after_selection("fake_token", repo_data, readme_content, "test_save_folder")
        
        self.mock_open.assert_called_once() # Attempted to save
        self.mock_commit.assert_not_called() # User chose not to commit

    def test_after_selection_local_save_io_error_then_yes_commit(self):
        self.mock_open.side_effect = IOError("Disk full")
        # User says 'yes' to commit after save failure, then provides branch
        self.mock_input.side_effect = ["yes", "main"] 
        self.mock_commit.return_value = True

        repo_data = {"name": "test_repo_io_error_commit"}
        readme_content = "Content that will fail to save but commit."

        after_selection("fake_token", repo_data, readme_content, "test_save_folder")

        self.mock_open.assert_called_once() # Attempted to save
        self.mock_commit.assert_called_once_with("fake_token", repo_data, readme_content, "main")


    @patch('docgpt.Thread')
    @patch('docgpt.after_selection') # Mock after_selection to prevent its full execution
    def test_main_list_and_select_repo_by_number(self, mock_after_selection_call, mock_thread):
        self.mock_keyring.get_password.return_value = "stored_token"
        self.mock_requests_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"login": "actual_user"}), # get_github_user
            MagicMock(status_code=200, json=lambda: [ # list_repositories
                {"name": "repo1", "contents_url": "url1/{+path}", "html_url": "html_url1"},
                {"name": "repo2", "contents_url": "url2/{+path}", "html_url": "html_url2"}
            ]),
            MagicMock(status_code=404), # has_readme for repo1 (False)
            MagicMock(status_code=404)  # has_readme for repo2 (False)
        ]
        self.mock_input.return_value = "1" # User selects repo number 1
        self.mock_generate_readme.return_value = "Generated README for repo1"

        main()
        
        # Check that list_repositories was called, and then generate_readme and after_selection
        docgpt.list_repositories.assert_called_with("stored_token")
        self.mock_generate_readme.assert_called_with(
            {"name": "repo1", "contents_url": "url1/{+path}", "html_url": "html_url1"}
        )
        mock_after_selection_call.assert_called_with(
            "stored_token", 
            {"name": "repo1", "contents_url": "url1/{+path}", "html_url": "html_url1"},
            "Generated README for repo1",
            "saved_conversation/"
        )

    @patch('docgpt.Thread')
    @patch('docgpt.after_selection')
    def test_main_list_and_select_all_repos(self, mock_after_selection_call, mock_thread):
        self.mock_keyring.get_password.return_value = "stored_token"
        mock_repo1_data = {"name": "repo1", "contents_url": "url1/{+path}", "html_url": "html_url1"}
        mock_repo2_data = {"name": "repo2", "contents_url": "url2/{+path}", "html_url": "html_url2"}
        self.mock_requests_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"login": "actual_user"}), # get_github_user
            MagicMock(status_code=200, json=lambda: [mock_repo1_data, mock_repo2_data]), # list_repositories
            MagicMock(status_code=404), # has_readme for repo1
            MagicMock(status_code=404)  # has_readme for repo2
        ]
        self.mock_input.return_value = "all" # User selects 'all'
        self.mock_generate_readme.side_effect = ["README for repo1", "README for repo2"]

        main()

        self.mock_generate_readme.assert_any_call(mock_repo1_data)
        self.mock_generate_readme.assert_any_call(mock_repo2_data)
        self.assertEqual(self.mock_generate_readme.call_count, 2)
        
        mock_after_selection_call.assert_any_call("stored_token", mock_repo1_data, "README for repo1", "saved_conversation/")
        mock_after_selection_call.assert_any_call("stored_token", mock_repo2_data, "README for repo2", "saved_conversation/")
        self.assertEqual(mock_after_selection_call.call_count, 2)

    # --- Error Handling Tests ---
    def test_list_repositories_api_error(self):
        self.mock_requests_get.side_effect = docgpt.requests.exceptions.RequestException("API Network Error")
        
        repos = list_repositories("fake_token")
        
        self.assertIsNone(repos) # Function should return None on error
        # Verify error message was printed (requires capturing stdout or mocking print)
        # For simplicity, we'll assume print happens and focus on return value.

    def test_has_readme_api_error_non_404(self):
        # Test for non-404 HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = docgpt.requests.exceptions.HTTPError("Server Error", response=mock_response)
        self.mock_requests_get.return_value = mock_response
        
        # This mock is tricky because the function itself might try to access response.status_code
        # after an exception. Let's ensure the side_effect on raise_for_status is the primary path.
        
        repo_data = {"name": "error_repo", "contents_url": "http://example.com/api/error_repo/contents/{+path}"}
        has = has_readme(repo_data, "fake_token")
        
        self.assertFalse(has) # Should assume no README on error
        # Check stdout for warning (if not fully suppressed)
        # output = self.mock_stdout.getvalue()
        # self.assertIn("Warning: HTTP error checking README for error_repo (500)", output)

    def test_has_readme_network_error(self):
        # Test for general RequestException (network error)
        self.mock_requests_get.side_effect = docgpt.requests.exceptions.RequestException("Network problem")
        
        repo_data = {"name": "network_error_repo", "contents_url": "http://example.com/api/network_error_repo/contents/{+path}"}
        has = has_readme(repo_data, "fake_token")
        
        self.assertFalse(has) # Should assume no README on error
        # output = self.mock_stdout.getvalue()
        # self.assertIn("Warning: Could not check README for network_error_repo due to a network issue", output)


    @patch('docgpt.Thread')
    @patch('docgpt.input', side_effect=KeyboardInterrupt)
    def test_main_keyboard_interrupt_during_repo_selection(self, mock_input_ki, mock_thread):
        self.mock_keyring.get_password.return_value = "stored_token"
        self.mock_requests_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"login": "actual_user"}), # get_github_user
            MagicMock(status_code=200, json=lambda: [ # list_repositories
                {"name": "repo1", "contents_url": "url1/{+path}", "html_url": "html_url1"}
            ]),
            MagicMock(status_code=404) # has_readme for repo1
        ]
        # KeyboardInterrupt will be raised when input() is called for repo choice.
        
        with self.assertRaises(SystemExit) as cm: # Assuming this is how main exits or if we catch KI
             main() # Call the main function
        
        # We can check if the "Operation Cancelled" message is printed
        # output = self.mock_stdout.getvalue()
        # self.assertIn("---- Operation Cancelled by User ----", output)
        # Also verify cleanup is attempted for files (if any were created, though not in this path)
        # For this test, the main thing is that it doesn't crash badly.

    # --- Banner Test ---
    @patch('builtins.print') # Mock print specifically for this test
    @patch('docgpt.text2art') # Mock text2art from where it's imported in docgpt
    # Mock other parts of main to prevent full execution, focusing on banner
    @patch('docgpt.keyring.get_password', return_value=None) # No initial token
    @patch('docgpt.os.path.exists', return_value=False) # Simulate no auth files initially
    @patch('docgpt.input', return_value="test_code") # For any input prompts
    @patch('docgpt.get_github_token', return_value="fake_token_for_banner_test") # Avoid token logic
    @patch('docgpt.get_github_user', return_value="fake_user_for_banner_test") # Avoid user logic
    @patch('docgpt.list_repositories', return_value=[]) # Avoid repo listing
    @patch('docgpt.Thread') # Avoid starting the auth server thread
    def test_main_prints_banner_and_tagline(self, 
                                             mock_thread, 
                                             mock_list_repositories,
                                             mock_get_github_user, 
                                             mock_get_github_token, 
                                             mock_input, 
                                             mock_os_exists, 
                                             mock_keyring_get_password, 
                                             mock_text2art, 
                                             mock_print_banner): # Renamed mock_print to avoid conflict with builtins
        # Arrange
        sample_banner_output = "---DocGPT ASCII Art---"
        mock_text2art.return_value = sample_banner_output

        # Act
        # We expect main to run until it tries to do something significant after banner,
        # which should be prevented by the extensive mocks.
        try:
            main()
        except Exception as e:
            # If main() still tries to run too far and fails due to incomplete mocks for its entire flow
            self.fail(f"main() raised an unexpected exception during banner test: {e}")

        # Assert
        mock_text2art.assert_called_once_with("DocGPT", font="standard")
        
        # Verify the print calls related to the banner
        # The exact calls might include others from main, so we use assert_any_call
        # or check the call_args_list more carefully.
        
        # Using a list of expected calls for the banner part
        expected_banner_prints = [
            call(sample_banner_output),
            call(" Automated README Generator"),
            call("--------------------------------------\n")
        ]
        
        # Get all actual print calls
        actual_print_calls = mock_print_banner.call_args_list

        # Check if the expected banner print calls are present and in order at the beginning
        self.assertTrue(len(actual_print_calls) >= len(expected_banner_prints), 
                        f"Not enough print calls. Expected at least {len(expected_banner_prints)}, got {len(actual_print_calls)}")

        for i, expected_call in enumerate(expected_banner_prints):
            self.assertEqual(actual_print_calls[i], expected_call, 
                             f"Print call {i} does not match. Expected {expected_call}, got {actual_print_calls[i]}")

if __name__ == '__main__':
    unittest.main()
