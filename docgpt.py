import os
import requests
from dotenv import load_dotenv
import webbrowser
import logging
import keyring # Added keyring
from authpage import app as authpage
from threading import Thread
from readmegen import commit, generate_readme
import time # Added time for polling
from art import text2art # For banner

load_dotenv()

SERVICE_NAME = "docgpt_github_token" # Service name for keyring
AUTH_PORT_FILE = "auth_port.txt"
AUTH_CODE_FILE = "auth_code.txt"

def get_github_token(code, github_user="default_user"): # Added github_user parameter
    # Scope explanation:
    # The 'repo' scope is used to allow the application to:
    # 1. List repositories (both public and private).
    # 2. Check for the existence of README.md files in these repositories.
    # 3. Commit new README.md files to these repositories.
    # This scope provides comprehensive access to repositories, which is necessary
    # for the core functionality of DocGPT. If the application's requirements
    # change (e.g., to only support public repositories), this scope should be
    # reviewed and potentially narrowed (e.g., to 'public_repo').
    payload = {
        'client_id': os.getenv("GITHUB_CLIENT_ID"),
        'client_secret': os.getenv("GITHUB_CLIENT_SECRET"),
        'code': code
    }
    headers = {'Accept': 'application/json'}
    try:
        response = requests.post('https://github.com/login/oauth/access_token', data=payload, headers=headers, timeout=10)
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        access_token = response.json().get('access_token')
        if access_token and github_user:
            try:
                keyring.set_password(SERVICE_NAME, github_user, access_token)
            except keyring.errors.NoKeyringError:
                print("Warning: Keyring backend not found. Token will not be stored securely for future sessions.")
            except Exception as e: # Catch other potential keyring errors
                print(f"Warning: Failed to store token in keyring. {e}")
        return access_token
    except requests.exceptions.RequestException as e:
        print(f"Error obtaining GitHub token: {e}")
        return None
    except ValueError: # JSON decoding error
        print("Error: Could not decode JSON response from GitHub when obtaining token.")
        return None

def get_github_user(access_token):
    headers = {'Authorization': f'token {access_token}'}
    try:
        response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("login")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitHub user: {e}")
        return None
    except ValueError: # JSON decoding error
        print("Error: Could not decode JSON response from GitHub when fetching user.")
        return None

def list_repositories(access_token):
    headers = {'Authorization': f'token {access_token}'}
    try:
        response = requests.get('https://api.github.com/user/repos?per_page=100', headers=headers, timeout=15) # Increased timeout and per_page
        response.raise_for_status()
        repos = response.json()
        if not repos:
            return [] # Return empty list if no repos found
        
        print("\n---- Checking repositories for existing READMEs ----")
        repos_without_readme = []
        for i, repo in enumerate(repos):
            print(f"Checking ({i+1}/{len(repos)}): {repo['name']}...")
            if not has_readme(repo, access_token):
                repos_without_readme.append(repo)
        print("---- Finished checking repositories ----")
        return repos_without_readme
    except requests.exceptions.RequestException as e:
        print(f"Error listing repositories: {e}")
        return None # Indicate failure
    except ValueError: # JSON decoding error
        print("Error: Could not decode JSON response from GitHub when listing repositories.")
        return None

def has_readme(repo, access_token):
    headers = {'Authorization': f'token {access_token}'}
    url = repo['contents_url'].replace('{+path}', 'README.md')
    response = None # Initialize response
    try:
        response = requests.get(url, headers=headers, timeout=5) # Shorter timeout for this check
        response.raise_for_status() # Will raise an HTTPError for 4xx/5xx status codes
        return True # If no error, README exists (200 OK)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return False # README does not exist, this is not an application error
        else:
            # Other HTTP errors (e.g., 403 Forbidden, 500 Server Error)
            print(f"Warning: HTTP error checking README for {repo['name']} ({e.response.status_code}): {e}. Assuming no README.")
            return False
    except requests.exceptions.RequestException as e:
        # Network errors, timeouts, etc.
        print(f"Warning: Could not check README for {repo['name']} due to a network issue: {e}. Assuming no README.")
        return False # Assume no README on error to avoid blocking

def run_authpage(port):
    authpage.run(port=port, debug=False)

def after_selection(access_token, selected_repo, readme_content, save_folder):
    """
    Handles saving the README locally and then optionally committing it to GitHub.
    """
    if not readme_content or not isinstance(readme_content, str) or not readme_content.strip():
        print(f"Error: No README content generated for '{selected_repo.get('name', 'Unknown Repo')}'. Skipping save and commit.")
        return

    repo_name = selected_repo.get('name', 'unknown_repo')
    file_name = f"{repo_name}_README.md"
    
    try:
        if not os.path.exists(save_folder):
            os.makedirs(save_folder, exist_ok=True)
        full_path = os.path.join(save_folder, file_name)
        with open(full_path, "w", encoding='utf-8') as file: # Added encoding
            # If readme_content is a list of strings, join them. If it's a single string, it's fine.
            if isinstance(readme_content, list):
                file.write("\n".join(readme_content))
            else:
                file.write(readme_content)
        print(f"\n---- README Saved Locally ----\nContent for '{repo_name}' saved to {full_path}")
    except IOError as e:
        print(f"Error: Could not save README locally to {full_path}: {e}")
        # Ask if user wants to proceed with commit despite local save failure
        proceed_commit = input(f"Failed to save locally. Do you still want to try committing to GitHub? (yes/no): ").strip().lower()
        if proceed_commit != 'yes':
            return

    user_confirmation = input(f"\nDo you want to commit this README to the GitHub repository '{repo_name}'? (yes/no): ").strip().lower()
    if user_confirmation == 'yes':
        branch = input("Enter the branch name to commit to (leave blank for 'main'): ").strip()
        if not branch:
            branch = "main"
        
        print(f"\nAttempting to commit README to '{repo_name}' on branch '{branch}'...")
        # Assuming `commit` function in readmegen.py handles its own errors/exceptions
        success = commit(access_token, selected_repo, readme_content, branch) # commit function from readmegen
        if success:
            print(f"---- Commit Successful ----\nREADME successfully committed to '{repo_name}' on branch '{branch}'.")
        else:
            # `commit` function should ideally print its own errors from readmegen.py
            print(f"---- Commit Failed ----\nFailed to commit README for '{repo_name}'. Check previous messages for details.")
    else:
        print("Skipping GitHub commit.")

# Removed save_readme function as its logic is integrated into after_selection

def main():
    save_folder = "saved_conversation/"
    auth_port = None
    server_thread = None
    access_token = None
    github_user = "default_user" # Start with a placeholder

    # --- Banner ---
    banner = text2art("DocGPT", font="standard")
    print(banner)
    print(" Automated README Generator")
    print("--------------------------------------\n")
    # --- End Banner ---

    try:
        print("Attempting to retrieve stored GitHub token...")
        try:
            access_token = keyring.get_password(SERVICE_NAME, github_user) # Try with default first
            if not access_token: # If no token for "default_user", try with potentially known last user
                 # This part is a bit tricky as we don't explicitly store the last user outside keyring.
                 # For simplicity, if default_user fails, we might rely on user re-auth or a more sophisticated
                 # way to get the "last logged in user" if we were to implement that.
                 # Let's assume for now, if default_user has no token, we proceed to auth.
                 pass # Fall through to OAuth if no "default_user" token

        except keyring.errors.NoKeyringError:
            print("Warning: Keyring backend not found. Secure token storage will be unavailable for future sessions.")
        except Exception as e:
            print(f"Warning: Error accessing keyring: {e}")

        if access_token:
            print("Verifying stored token...")
            actual_github_user = get_github_user(access_token)
            if actual_github_user:
                if actual_github_user != github_user:
                    # If token was stored under "default_user" but belongs to "actual_github_user"
                    try:
                        keyring.set_password(SERVICE_NAME, actual_github_user, access_token)
                        # Try to delete the old placeholder if it was indeed a placeholder
                        if github_user == "default_user" and keyring.get_password(SERVICE_NAME, "default_user"):
                            keyring.delete_password(SERVICE_NAME, "default_user")
                    except Exception as e:
                        print(f"Warning: Could not update token storage with actual username: {e}")
                    github_user = actual_github_user
                print(f"Successfully authenticated as '{github_user}' using stored token.")
            else:
                print("Stored token is invalid or expired. Please re-authenticate.")
                access_token = None # Force re-authentication

        if not access_token:
            print("\n---- GitHub Authentication Required ----")
            # Start the auth server thread
            print("Starting local authentication server...")
            auth_server_started = False
            try:
                for _ in range(10): # Wait up to 10 seconds for port file
                    if os.path.exists(AUTH_PORT_FILE):
                        with open(AUTH_PORT_FILE, "r") as f:
                            auth_port = int(f.read().strip())
                        auth_server_started = True
                        break
                    time.sleep(1)
                if not auth_server_started or not auth_port:
                    raise IOError("Auth server did not create port file in time.")
            except (IOError, ValueError) as e:
                print(f"Error: Could not set up authentication server: {e}")
                print("Please ensure authpage.py is executable and can write to the current directory.")
                return # Critical failure

            server_thread = Thread(target=run_authpage, args=(auth_port,), daemon=True)
            server_thread.start()
            
            redirect_uri = f"http://localhost:{auth_port}/callback"
            auth_url = f"https://github.com/login/oauth/authorize?client_id={os.getenv('GITHUB_CLIENT_ID')}&scope=repo&redirect_uri={redirect_uri}"
            print(f"\nTo authorize DocGPT, please open the following URL in your web browser:")
            print(f"  {auth_url}")
            try:
                webbrowser.open(auth_url)
            except Exception as e:
                print(f"Warning: Could not open web browser automatically: {e}. Please copy the URL manually.")

            print("\nWaiting for authorization code from GitHub (up to 60 seconds)...")
            code = None
            code_retrieved = False
            try:
                for _ in range(60): # Poll for 60 seconds
                    if os.path.exists(AUTH_CODE_FILE):
                        with open(AUTH_CODE_FILE, "r") as f:
                            code = f.read().strip()
                        if code:
                            code_retrieved = True
                            print("Authorization code retrieved automatically.")
                            break
                    time.sleep(1)
            except IOError as e:
                print(f"Error reading authorization code file: {e}")
            
            if not code_retrieved:
                print("Timeout or error retrieving authorization code automatically.")
                try:
                    code = input("Please manually copy and paste the authorization code from your browser: ").strip()
                except KeyboardInterrupt:
                    print("\nAuthentication cancelled by user.")
                    return
            
            if not code:
                print("No authorization code provided. Authentication failed.")
                return

            print("\nFetching GitHub token...")
            temp_token = get_github_token(code, "default_user") # Initially store with "default_user"

            if temp_token:
                print("Verifying token and fetching user information...")
                current_user = get_github_user(temp_token)
                if current_user:
                    access_token = temp_token
                    github_user = current_user # Update to actual username
                    try:
                        # Re-store token with actual username and remove placeholder
                        keyring.set_password(SERVICE_NAME, github_user, access_token)
                        if keyring.get_password(SERVICE_NAME, "default_user"): # Check if placeholder exists
                           keyring.delete_password(SERVICE_NAME, "default_user")
                        print(f"---- Authentication Successful ----\nSuccessfully authenticated as '{github_user}'. Token stored securely.")
                    except keyring.errors.NoKeyringError:
                         print(f"---- Authentication Successful ----\nSuccessfully authenticated as '{github_user}'. Keyring not available, token not stored for future sessions.")
                    except Exception as e:
                         print(f"---- Authentication Successful ----\nSuccessfully authenticated as '{github_user}'. Warning: Could not update token in keyring: {e}")
                else:
                    print("Error: Successfully obtained token, but failed to get GitHub username. The token might be invalid or the user API failed.")
                    # Use the token for this session but it won't be stored with a specific user unless keyring was already used in get_github_token
                    access_token = temp_token 
            
            if not access_token:
                print("---- Authentication Failed ----\nCould not authenticate with GitHub. Please check your credentials and network.")
                return
        
        print("\n---- Loading Your Repositories ----")
        repositories = list_repositories(access_token)

        if repositories is None: # Explicit check for None indicating an error during fetch
            print("Error: Could not retrieve repositories from GitHub. Please check your connection and token.")
            return
        if not repositories:
            print("No repositories found that require a README.md, or all your repositories already have one.")
            return
        
        print("\n---- Repositories without README.md ----")
        for i, repo in enumerate(repositories):
            print(f"  {i+1}. {repo['name']} (URL: {repo['html_url']})")
        print("--------------------------------------")

        try:
            user_choice_input = input("Enter the number of the repository for README generation, or 'all' for all listed repositories: ").strip().lower()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return

        if user_choice_input == 'all':
            print("\n---- Batch README Generation for All Repositories ----")
            processed_count = 0
            for i, repo_data in enumerate(repositories):
                print(f"\nProcessing repository {i+1}/{len(repositories)}: '{repo_data['name']}'")
                print("Analyzing and generating README, please wait...")
                try:
                    # Use repo_data itself if it contains URL, or construct if needed.
                    # generate_readme might expect a URL or the full repo object. Assuming it can handle repo_data.
                    readme_content = generate_readme(repo_data) # Pass the repo object
                except Exception as e:
                    print(f"Error: Could not generate README for '{repo_data['name']}': {e}")
                    readme_content = None # Ensure it's None on error

                if readme_content:
                    # Display a snippet or confirmation rather than full content in 'all' mode for brevity
                    snippet = readme_content[:100].replace('\n', ' ')
                    print(f"README generated for '{repo_data['name']}'. First 100 chars: '{snippet}...'")
                    after_selection(access_token, repo_data, readme_content, save_folder)
                    processed_count += 1
                else:
                    print(f"Skipping README for '{repo_data['name']}' due to generation failure or empty content.")
                print("---- Moving to next repository ----" if i < len(repositories) -1 else "---- Batch processing complete ----")
            
            if processed_count == 0 and len(repositories) > 0:
                 print("\nNo READMEs were successfully generated or processed in batch mode.")
            elif processed_count > 0:
                 print(f"\nSuccessfully processed {processed_count} repositories.")

        else:
            try:
                choice_idx = int(user_choice_input) - 1
                if 0 <= choice_idx < len(repositories):
                    selected_repo = repositories[choice_idx]
                    print(f"\n---- Generating README for: {selected_repo['name']} ----")
                    print("Analyzing and generating, please wait...")
                    try:
                        # generate_readme might expect a URL or the full repo object.
                        # Assuming it can handle selected_repo directly or selected_repo['html_url']
                        readme_content = generate_readme(selected_repo) # Pass the repo object
                    except Exception as e:
                        print(f"Error: Could not generate README for '{selected_repo['name']}': {e}")
                        readme_content = None

                    if readme_content:
                        print("\n---- Generated README Content ----")
                        print(readme_content)
                        print("----------------------------------")
                        after_selection(access_token, selected_repo, readme_content, save_folder)
                    else:
                        print(f"Failed to generate README for '{selected_repo['name']}'.")
                else:
                    print("Error: Invalid selection. Please enter a number from the list.")
            except ValueError:
                print("Error: Invalid input. Please enter a number or 'all'.")
        
        print("\n---- DocGPT session finished. ----")

    except KeyboardInterrupt:
        print("\n---- Operation Cancelled by User ----")
    except Exception as e: # Catch-all for unexpected errors in main flow
        print(f"\n---- An Unexpected Error Occurred ----")
        print(f"Error: {e}")
        logging.exception("Unexpected error in main:") # Log traceback for debugging
    finally:
        if auth_port and server_thread and server_thread.is_alive():
            print(f"\nShutting down authentication server on port {auth_port}...")
            try:
                requests.get(f'http://localhost:{auth_port}/shutdown', timeout=5)
            except requests.exceptions.RequestException as e:
                print(f"Error during auth server shutdown: {e}")
        
        for temp_file in [AUTH_PORT_FILE, AUTH_CODE_FILE]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"Cleaned up temporary file: {temp_file}")
                except IOError as e: # More specific for file ops
                    print(f"Error deleting temporary file {temp_file}: {e}")
        print("\nExiting DocGPT application.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Perform any critical cleanup if main() fails catastrophically early
        if os.path.exists(AUTH_PORT_FILE):
            try:
                os.remove(AUTH_PORT_FILE)
            except OSError as err:
                print(f"Error deleting {AUTH_PORT_FILE} during critical cleanup: {err}")
        if os.path.exists(AUTH_CODE_FILE):
            try:
                os.remove(AUTH_CODE_FILE)
            except OSError as err:
                print(f"Error deleting {AUTH_CODE_FILE} during critical cleanup: {err}")
    finally:
        # Set werkzeug log level here, as it's a global setting for the logger
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)