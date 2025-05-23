# DocGPT: Automated README Generator

## Introduction

DocGPT is a command-line tool that uses OpenAI's GPT models to automatically generate `README.md` files for your GitHub repositories. It helps you quickly create baseline documentation for projects that are missing a README.

## Features

*   GitHub OAuth2 authentication for accessing your repositories.
*   Secure local storage of GitHub access tokens using the system's keyring.
*   Lists only repositories that currently do not have a `README.md` file.
*   Generates README content using an OpenAI GPT model (specifically, `gpt-4-1106-preview` by default, though this can be configured within the code).
*   Automatically saves all generated README files to a local `saved_conversation/` directory, named as `[repository_name]_README.md`.
*   Prompts the user to commit the generated README directly to the target GitHub repository.
*   User-friendly Command Line Interface (CLI) featuring an ASCII art banner.
*   Utilizes a dynamic port for the local authentication callback server to minimize port conflicts.

## Requirements

To use DocGPT, you will need:

*   Python 3.7 or higher.
*   An active OpenAI API Key.
*   A GitHub Account.
*   GitHub OAuth Application credentials (Client ID and Client Secret).
    *   To obtain these, create a new OAuth App in your GitHub account under "Developer settings".
    *   For the "Application name", you can use "DocGPT" or any name of your choice.
    *   For the "Homepage URL", you can use any valid URL (e.g., your GitHub profile).
    *   For the "Authorization callback URL": DocGPT uses a dynamic port for its local authentication server. When you run DocGPT and it requires authentication, it will print an authorization URL to your console. This URL contains a `redirect_uri` parameter (e.g., `http://localhost:PORT/callback`, where `PORT` is a number like 12345). You must copy this exact `redirect_uri` value and set it as the "Authorization callback URL" in your GitHub OAuth App settings. You may need to run DocGPT once to obtain this specific URI, update your OAuth app, and then re-run DocGPT if the initial authentication attempt fails due to a mismatch.

## Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/terri-yaki/DocGPT.git
    ```
2.  Navigate to the project directory:
    ```bash
    cd DocGPT
    ```
3.  (Recommended) Create and activate a Python virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate   # On Windows
    ```
4.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5.  Create a `.env` file in the root directory of the project (`DocGPT/.env`). Add your API keys and OAuth credentials to this file in the following format:
    ```env
    OPENAI_API_KEY="your_openai_api_key_here"
    GITHUB_CLIENT_ID="your_github_client_id_here"
    GITHUB_CLIENT_SECRET="your_github_client_secret_here"
    # Optional: Specify a preferred port for the authentication server.
    # If AUTH_PORT is set, ensure your GitHub OAuth App's Authorization callback URL
    # reflects this specific port (e.g., http://localhost:YOUR_AUTH_PORT/callback).
    # If not set, a dynamic port will be used, and the callback URL will be generated accordingly.
    # AUTH_PORT="8000"
    ```
    Replace the placeholder values with your actual credentials.

## Running the Application

1.  Ensure your virtual environment is activated (if you created one).
2.  Run the script from the root directory of the project:
    ```bash
    python docgpt.py
    ```
3.  **First-time Authentication:**
    *   If it's your first time running the application, or if your stored GitHub token is invalid or not found, DocGPT will guide you through the GitHub authentication process.
    *   A URL will be displayed in the console. Open this URL in your web browser.
    *   Log in to GitHub (if you aren't already) and authorize the "DocGPT" application.
    *   After authorization, the application will attempt to automatically capture the authorization code from the callback.
    *   If automatic capture fails (e.g., if you closed the browser page too quickly), an HTML page will usually display the authorization code. Copy this code from the browser and paste it into the terminal when prompted by DocGPT.
    *   Upon successful authentication, your GitHub token will be stored securely in your system's keyring for future sessions.

4.  **Repository Selection:**
    *   DocGPT will fetch and list all your GitHub repositories that do not currently have a `README.md` file.
    *   You will be prompted to enter the number corresponding to the repository for which you want to generate a README, or type `all` to generate READMEs for all listed repositories.

5.  **README Generation and Saving:**
    *   The script will then communicate with the OpenAI API to generate the README content for the selected repository/repositories.
    *   Once generated, the README content will be displayed in the console (for single repository mode) or a snippet will be shown (for 'all' mode).
    *   The generated README is automatically saved locally in the `saved_conversation/` directory, named as `[repository_name]_README.md`.

6.  **Committing to GitHub:**
    *   After saving the file locally, you will be asked if you wish to commit the generated README to your GitHub repository.
    *   If you respond 'yes', you will be prompted to enter a branch name. If you leave this blank, it will default to 'main'.
    *   DocGPT will then attempt to commit the README file to the specified branch of the remote repository.

## CLI Appearance

DocGPT features an ASCII art title banner for a more engaging command-line experience.

## Troubleshooting

*   **Keyring Issues:** On some systems, particularly headless Linux environments, `keyring` might require additional setup (e.g., installing `dbus-launch` and running the application within a DBus session). If you encounter issues related to token storage or retrieval, consult the `keyring` library's documentation for platform-specific requirements.
*   **OpenAI API Key Errors:** Ensure your `OPENAI_API_KEY` in the `.env` file is correct and that your OpenAI account has sufficient credits or a valid subscription.
*   **GitHub Authentication Errors:**
    *   Double-check that `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in your `.env` file are correct.
    *   Verify that the "Authorization callback URL" in your GitHub OAuth App settings exactly matches the `redirect_uri` used by DocGPT. DocGPT determines the port dynamically; the exact `redirect_uri` it uses will be part of the authorization URL printed to the console when authentication is required. You must use this value in your GitHub OAuth App.
*   **Dependency Version Conflicts:** This project has specific versions for Flask and its dependencies (Jinja2, MarkupSafe, itsdangerous, Werkzeug) listed in `requirements.txt`. If you encounter import errors, ensure you are using a virtual environment and that the exact versions from `requirements.txt` are installed correctly. Avoid manually upgrading these specific packages unless you are prepared to resolve potential incompatibilities with Flask 1.1.2.

## License

This project is currently distributed without an explicit license.

## Contributions

Contributions, issues, and feature requests are welcome. Please feel free to fork the repository, make changes, and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## Acknowledgments

DocGPT is built using Python, utilizing the OpenAI API for content generation and the GitHub API for repository interaction.
