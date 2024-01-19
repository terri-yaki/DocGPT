import os
import sys
import requests
from dotenv import load_dotenv
import webbrowser
from authpage import app as authpage
from threading import Thread

load_dotenv()

def get_github_token(code):
    payload = {
        'client_id': os.getenv("GITHUB_CLIENT_ID"),
        'code': code
    }
    
    headers = {'Accept': 'application/json'}
    response = requests.post('https://github.com/login/oauth/access_token', data=payload, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}, {response.text}")
        return None
    return response.json().get('access_token')

def list_repositories(access_token):
    """
    List all repositories for the authenticated user.
    """
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get('https://api.github.com/user/repos', headers=headers)
    repos = response.json()
    repos_without_readme = [repo for repo in repos if not has_readme(repo, access_token)]
    return repos_without_readme

def has_readme(repo, access_token):
    """
    Check if the specified repository has a README.md file.
    """
    headers = {'Authorization': f'token {access_token}'}
    url = f"{repo['contents_url'].replace('{+path}', 'README.md')}"

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # README exists
        return True
    return False

def run_authpage():
    authpage.run(port=8000, debug=False)

def main():
    Thread(target=run_authpage, daemon=True).start()
    print(f"Hi, please visit the following URL and authorize the application:")
    print(f"https://github.com/login/oauth/authorize?client_id={os.getenv('GITHUB_CLIENT_ID')}&scope=repo")
    webbrowser.open(f"https://github.com/login/oauth/authorize?client_id={os.getenv('GITHUB_CLIENT_ID')}&scope=repo")

    code = input("Enter the code from GitHub: ")
    access_token = get_github_token(code)
    
    for i in range(5):
        if not access_token:
            print("Failed to authenticate with GitHub.")
            i += 1
            if i == 5:
                return

    print("Successfully authenticated with GitHub.")
    repositories = list_repositories(access_token)

    if not repositories:
        print("No repositories found without a README.md.")
        return
    
    print("Here are the repositories without README.md")
    print(f"Repository Name: ")
    for repo in repositories:
        print(f"{repo['name']} - URL: {repo['html_url']}")

if __name__ == "__main__":
    main()