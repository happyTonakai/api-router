# API Router

A simple API router that supports multiple API keys with round-robin rotation for Gemini, OpenRouter, and ModelScope. Thank you for the free API keys!

## Features

- **Multiple API Keys**: Configure multiple API keys for each provider
- **Round-Robin Rotation**: Automatically cycles through available API keys
- **Dynamic Provider Support**: Add any API provider in config.yaml - no code changes needed
- **Transparent Proxy**: Forwards requests without modifying the original API structure
- **Configuration**: Easy setup via YAML config file

## Setup

1. Install dependencies:
```bash
uv add flask requests pyyaml gunicorn
```

2. Configure your API keys in `config.yaml`:
```yaml
# Add your API providers here
# Each provider needs:
# - keys: list of API keys (will be rotated in round-robin fashion)
# - base_url: the base URL for the provider's API

gemini:
  keys:
    - "your-gemini-api-key-1"
    - "your-gemini-api-key-2"
    - "your-gemini-api-key-3"
  base_url: "https://generativelanguage.googleapis.com"

openrouter:
  keys:
    - "your-openrouter-api-key-1"
    - "your-openrouter-api-key-2"
    - "your-openrouter-api-key-3"
  base_url: "https://openrouter.ai"

# Example: Add another provider like OpenAI
# openai:
#   keys:
#     - "your-openai-api-key-1"
#     - "your-openai-api-key-2"
#   base_url: "https://api.openai.com"
```

3. Run the server:
```bash
uv run server.py
```

## Usage

Once running, the server will be available at `http://localhost:9999`

### Gemini API
- Endpoint: `http://localhost:9999/gemini/v1/models/gemini-pro:generateContent`
- All Gemini API endpoints are supported

### OpenRouter API
- Endpoint: `http://localhost:9999/openrouter/api/v1/chat/completions`
- All OpenRouter API endpoints are supported

### Custom Providers
- Any provider added to config.yaml will be available at:
  `http://localhost:9999/{provider_name}/{api_endpoint}`
- For example, if you add "openai" to config.yaml:
  `http://localhost:9999/openai/v1/chat/completions`

### Health Check
- Endpoint: `http://localhost:9999/`
- Returns server status and available providers

## How It Works

1. The server receives a request to `/{provider}/...` where provider is any configured in config.yaml
2. It selects the next available API key for that provider (round-robin)
3. It forwards the request to the original API endpoint with the selected key
4. It returns the response from the original API

## Adding New Providers

To add a new API provider:

1. Add the provider to `config.yaml`:
```yaml
your_provider:
  keys:
    - "your-api-key-1"
    - "your-api-key-2"
  base_url: "https://api.your-provider.com"
```

2. Restart the server
3. Use the provider at: `http://localhost:9999/your_provider/...`

The router will automatically detect and support the new provider without any code changes.

## Configuration

The `config.yaml` file allows you to configure:

- **API Keys**: List of API keys for each provider
- **Base URLs**: The base URL for each provider's API

Add as many keys as you want for each provider, and the router will automatically rotate through them.