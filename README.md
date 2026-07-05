# OpenRouter Chat Application

Professional AI chat application with support for multiple models, rate limiting, profile management, and session tracking.

## Features

- Multi-model support (OpenRouter API)
- Rate limiting and backoff strategies
- Session management with statistics tracking
- Command history navigation
- Profile-based configuration
- Token counting and cost estimation
- YAML-based model registry
- CLI and Flask backend interfaces
- Docker containerization
- Comprehensive test coverage

## Quick Start

### Local Installation

```bash
git clone https://github.com/clashssd/openrouter-models-chatting
cd ~/openrouter-models-chatting/ai
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r ai/requirements.txt
```

### Set Environment Variables

```bash
export OPENROUTER_API_KEY="your_api_key_here"
export OPENROUTER_API_BASE="https://openrouter.ai/api/v1"
```

### Run Application

```bash
python -m ai.main
```

## Docker Usage

### Build and Run with Docker Compose

```bash
docker-compose up --build
```


## Configuration

### Models Registry

Edit `configs/models.yaml` to configure available models:

```yaml
models:
  gpt-4o:
    name: GPT-4o
    cost_per_1k_input: 0.005
    cost_per_1k_output: 0.015
    context_window: 128000
    features:
      - vision
      - function_calling
```

### Profiles

Create profiles in `configs/profiles.yaml`:

```yaml
profiles:
  default:
    name: default
    model: gpt-4o
    temperature: 0.7
  coding:
    name: coding
    model: gpt-4o
    temperature: 0.0
```

## CLI Commands

### Basic Chat

```bash
python -m ai.main
```

### Available Commands

| Command | Description |
|---------|-------------|
| `/clear` | Clear conversation history |
| `/profile <name>` | Switch profile |
| `/model <name>` | Switch model |
| `/export` | Export conversation |
| `/stats` | Show session statistics |
| `/help` | Show help message |
| `/exit` | Exit application |


## Installation from Source

```bash
cd ai/
pip install -e .
openrouter-checker
```

## Performance

- Efficient token counting without API calls
- Rate limiting prevents API throttling
- Session caching improves response times
- Lazy loading of models

## Troubleshooting

### Import Errors

Ensure all dependencies are installed:
```bash
pip install -r ai/requirements.txt
```

### API Errors

Check your API key and network connection:
```bash
export OPENROUTER_API_KEY="your_key"
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  https://openrouter.ai/api/v1/models
```

## Security

- Never commit `.env` files with secrets
- Use environment variables for API keys
- Validate all user inputs
- Keep dependencies updated

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
1. Check existing issues on GitHub
2. Review CONTRIBUTING.md for guidelines
3. Create detailed bug reports with reproduction steps

## Versioning

This project follows Semantic Versioning (SemVer):
- MAJOR.MINOR.PATCH (e.g., 1.0.0)
- See CHANGELOG.md for version history

## Contributing

See CONTRIBUTING.md for guidelines on:
- Setting up development environment
- Code standards and style
- Testing requirements
- Pull request process


