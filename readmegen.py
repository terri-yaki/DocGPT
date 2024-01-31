import os
import requests
from dotenv import load_dotenv
import base64
import openai

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_readme(selected_repo_url):
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview", #change to use different openAI models
        messages=[{"role": "user", "content": f"generate a readme file with markdown style for this repository: {selected_repo_url}, only the content, no other response."}],
    )
    return response.choices[0].message.content.strip()

def commit(access_token, selected_repo, readme_content):
    # GitHub API endpoint to update repository content
    api_url = f"{selected_repo['html_url']}/README.md"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    # Encode the README content to Base64 as required by GitHub API
    content_base64 = base64.b64encode(readme_content.encode()).decode()
    data = {
        "message": "Add generated README.md",
        "content": content_base64,
        "branch": "main"
    }
    response = requests.put(api_url, headers=headers, json=data)
    return response.status_code == 200