import unittest
from unittest.mock import MagicMock, patch
import readmegen, docgpt

class UnitTests(unittest.TestCase):
    
    @patch('openai.ChatCompletion.create')
    def test_generate_readme(self, mock_create):
        mock_create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="Mock README content"))])
        
        selected_repo_url = "https://github.com/example/repo"
        readme_content = readmegen.generate_readme(selected_repo_url)
        
        self.assertEqual(readme_content, "Mock README content")
        mock_create.assert_called_once()

    @patch('requests.put')
    def test_commit(self, mock_put):
        mock_put.return_value = MagicMock(status_code=200)
        
        access_token = "mock_access_token"
        selected_repo = {"html_url": "https://github.com/example/repo"}
        readme_content = "Sample README content"
        
        success = readmegen.commit(access_token, selected_repo, readme_content)
        
        self.assertTrue(success)
        mock_put.assert_called_once()

if __name__ == '__main__':
    unittest.main()
