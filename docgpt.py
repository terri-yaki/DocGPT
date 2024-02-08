import os
import sys
import requests
from dotenv import load_dotenv
import webbrowser
import base64
import logging
from authpage import app as authpage
from threading import Thread
from readmegen import commit, generate_readme

load_dotenv()

def get_github_token(code):
    payload = {
        'client_id': os.getenv("GITHUB_CLIENT_ID"),
        'client_secret': os.getenv("GITHUB_CLIENT_SECRET"), #both from env
        'code': code
    }
    
    headers = {'Accept': 'application/json'} #formats
    response = requests.post('https://github.com/login/oauth/access_token', data=payload, headers=headers)
    if response.status_code != 200: #check status
        print(f"Error: {response.status_code}, {response.text}")
        return None
    return response.json().get('access_token')

def list_repositories(access_token):
    #List all repositories for the authenticated user.
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get('https://api.github.com/user/repos', headers=headers)
    repos = response.json()
    repos_without_readme = [repo for repo in repos if not has_readme(repo, access_token)] #list out repo w/o readme for every repo you find in repos list
    return repos_without_readme

def has_readme(repo, access_token):
    #Check if the specified repository has a readme.md file.
    headers = {'Authorization': f'token {access_token}'}
    url = f"{repo['contents_url'].replace('{+path}', 'README.md')}"

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # readme exists
        return True
    return False

def run_authpage():
    authpage.run(port=8000, debug=False)
    
def after_selection(access_token, selected_repo, readme_content, save_folder):
    user_confirmation = input("\nDo you want to commit this README to your repository? (yes/no): ")
    if user_confirmation.lower() == 'yes':
        success = commit(access_token, selected_repo, readme_content)
        if success:
            print("README successfully committed to the repository.").lower()
        else:
            user_input = input("Failed to commit README, would you like to save it instead? (yes/no): ")
            if user_input == 'yes':
                file_title = input("Enter a title for the readme file: ")
                file_name = file_title + ".txt"  # Create filename from title
                full_path = os.path.join(save_folder, file_name)
                with open(full_path, "w") as file:
                    file.write("\n".join(readme_content))
                print(f"Content saved as '{full_path}'.")
            else:
                print("Thanks for using DocGPT, see you next time!")

def main():
    save_folder = "saved_conversation/"
    Thread(target=run_authpage, daemon=True).start() #silent host server
    print(f"Hi, please visit the following URL and authorize the application:")
    print(f"https://github.com/login/oauth/authorize?client_id={os.getenv('GITHUB_CLIENT_ID')}&scope=repo")
    webbrowser.open(f"https://github.com/login/oauth/authorize?client_id={os.getenv('GITHUB_CLIENT_ID')}&scope=repo")

    code = input("Enter the code from GitHub: ")
    print("One second, fetching...")
    access_token = get_github_token(code)
    
    if not access_token:
        print("Failed to authenticate with GitHub.")
        return

    print("Successfully authenticated with GitHub.\nLoading your repositories...")
    repositories = list_repositories(access_token)

    if not repositories:
        print("No repositories found without a README.md.")
        return
    
    print("Here are the repositories without README.md")
    print("-------------------------------------------")
    print(f"Repository Name: ")
    for repo in repositories:
        print(f"{repo['name']} - URL: {repo['html_url']}")

    user_choice = input("Enter the name of the repository you want a README for, or 'all' for all repositories:").strip()
    if user_choice.lower() == 'all':       #ALL repo
        for repo in repositories:
            readme_content = generate_readme(repo)
            if commit(access_token, repo, readme_content):
                after_selection(access_token, selected_repo, readme_content, save_folder)
            else:
                print(f"Failed to create README for {repo['name']}")
                break
    else:
        selected_repo = next((repo for repo in repositories if repo['name'].lower() == user_choice.lower()), None)
        print("Analyzing and generating, please wait...")
        selected_repo_url = selected_repo['html_url']
        readme_content = generate_readme(selected_repo_url)
        
        print("Here's the document:\n" + "-------------------------------------------\n" + readme_content)

        after_selection(access_token, selected_repo, readme_content, save_folder)
        

if __name__ == "__main__":
    main()
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    requests.get('http://localhost:8000/shutdown') #close the localhost