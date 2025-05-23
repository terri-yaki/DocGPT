# DocGPT

DocGPT is a script designed to use the use GPT models for generating read me documentation. This repository allows users to create comprehensive documentation by leveraging the power of generative pre-trained transformers (GPT). Whether you're looking to autogenerate for your repo or write up technical explanations, DocGPT aims to facilitate these tasks with the help of OpenAI's language models.

## Getting Started

To get started with DocGPT, you will need to clone the repository and set up your environment to run the code.

```bash
git clone https://github.com/terri-yaki/DocGPT.git
cd DocGPT
```

Please make sure you have Python installed on your system and then install the required packages using pip:

```bash
pip install -r requirements.txt
```

## Usage

To use DocGPT, follow these steps:

1. Create .env file in the base directory: 

```
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
OPENAI_API_KEY=
```

2. Run the Python script:

```bash
py docgpt.py
```

3. Change the GPT model of your choice:

```python
Default model:
model="gpt-4-1106-preview", #change to use different openAI models
from readmegen.py L:12
```

4. For generating read me documentation, just follow the application


## Features

- **Readme Generation**: Automatically generate markdown readme document for your repository.
- **Scan through undocumented repository**: Only show undocumented repository on the list.


## Contributions

Contributions are welcome! If you have a suggestion for an improvement or want to contribute code, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a pull request.

