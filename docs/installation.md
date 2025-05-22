# Installation Guide

## Prerequisites

- Python 3.10 or higher
- A valid GitHub API token (default) or Google Gemini API key
- Access to an MCP server (Python script, remote service, or custom implementation)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/cloaky233/mcca.git
cd mcca
```

### 2. Set Up a Virtual Environment

#### On macOS/Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

#### On Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. API Keys Setup

Create a `.env` file in the root directory and add your API key:

#### For GitHub's GPT model (default):
```
GITHUB_TOKEN=your_github_token_here
```

#### For Google Gemini (alternative):
```
GEMINI_API_KEY=your_gemini_key_here
```

## Configuration

Create a `config.json` file with your MCP server configurations:

```json
{
  "context_servers": {
    "MyServer": {
      "command": {
        "path": "python",
        "args": ["path/to/server_script.py"],
        "env": {
          "CUSTOM_ENV_VAR": "value"
        }
      },
      "settings": {}
    }
  }
}
```

## Running the Client

### Command Line Interface

```bash
# Basic usage (auto-selects server if only one is available)
python cli.py config.json

# Specify a particular server
python cli.py config.json server_name
```

### Web Interface

```bash
# Start the Streamlit web interface
streamlit run app.py
```
