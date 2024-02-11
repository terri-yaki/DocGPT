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
        messages=[{"role": "user", "content": f"generate a detail readme file in markdown style for this repository: {selected_repo_url}, only the related content, no other response."}],
    )
    return response.choices[0].message.content.strip()


def commit(access_token, selected_repo, readme_content, branch):
    # GitHub API endpoint to get or update repository content
    api_url = f"https://api.github.com/repos/{selected_repo['owner']['login']}/{selected_repo['name']}/contents/README.md"

    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(api_url, headers=headers)
    sha = response.json().get('sha') if response.status_code == 200 else None

    # Encode the README content to Base64 as required by GitHub API
    readme_content_base64 = base64.b64encode(readme_content.encode()).decode()
    
    data = {
        "message": "Updated README.md",
        "content": readme_content_base64,
        "branch": branch
    }

    if sha:
        data["sha"] = sha

    # request to update or create the README.md
    response = requests.put(api_url, headers=headers, json=data)
    if response.status_code == 200 or response.status_code == 201:  # 201 for created, 200 for updated
        return True
    else:
        print(f"Error committing README: {response.status_code}, {response.text}")
        return False
