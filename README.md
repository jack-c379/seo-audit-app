# SEO Audit Agent - Backend

A Python-based SEO audit agent built with Google's [ADK](https://google.github.io/adk-docs/) that performs comprehensive SEO analysis using a three-stage pipeline: page audit, SERP analysis, and optimization recommendations.

## Features

- **Page Auditor**: Analyzes on-page SEO elements including meta tags, headings, content structure, and links
- **SERP Analyst**: Performs competitive analysis by examining top-ranking pages for target keywords
- **Optimization Advisor**: Generates prioritized recommendations with actionable next steps

## Prerequisites

- Python 3.10+ (3.12+ recommended)
  - **Note:** Python 3.10+ is required for MCP tools. The setup script will automatically check for a compatible version.
  - On macOS, install via Homebrew: `brew install python@3.12`
  - Or download from [python.org](https://www.python.org/downloads/)
- Google API Key (for the ADK agent) - see https://makersuite.google.com/app/apikey
- Firecrawl API Key (optional, for web scraping) - see https://firecrawl.dev

## Getting Started

### 1. Install Python Dependencies

Run the setup script to create a virtual environment and install dependencies:

```bash
./scripts/setup-agent.sh
```

Or using npm (if you have package.json scripts):

```bash
npm run install:agent
```

This will:
- Check for Python 3.10 or higher
- Create a new virtual environment (`.venv`) in the project root
- Install all required Python packages

### 2. Set Up Environment Variables

Create a `.env` file in the root directory (or set environment variables):

```bash
# Required
GOOGLE_API_KEY=your-google-api-key-here

# Optional - for web scraping features
FIRECRAWL_API_KEY=your-firecrawl-api-key-here

# CORS Configuration (for production deployment)
# Comma-separated list of allowed origins
ALLOWED_ORIGINS=https://your-frontend-domain.com
```

### 3. Run the Agent

Start the agent server:

```bash
./scripts/run-agent.sh
```

Or directly:

```bash
cd agent
../.venv/bin/python agent.py
```

The agent will start a FastAPI server on `http://localhost:8000` (or the port specified by the `PORT` environment variable).

## Project Structure

```
seo-audit-app/
├── agent/
│   ├── agent.py          # Main agent implementation
│   └── requirements.txt  # Python dependencies
├── scripts/
│   ├── setup-agent.sh    # Setup script for virtual environment
│   └── run-agent.sh      # Script to run the agent
├── render.yaml           # Render deployment configuration
└── README.md            # This file
```

## Agent Pipeline

The agent uses a sequential pipeline with three sub-agents:

1. **PageAuditor**: Analyzes the target page for SEO elements
2. **SerpAnalyst**: Examines SERP results for competitive insights
3. **OptimizationAdvisor**: Generates comprehensive optimization recommendations

## API Endpoints

When the agent server is running, it exposes a FastAPI application:

- `POST /` - Main agent endpoint (used by ADK/AG-UI clients)
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /openapi.json` - OpenAPI schema

## Development

### Manual Virtual Environment Setup

If you prefer to set up the virtual environment manually:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
cd agent
pip install -r requirements.txt
```

### Running in Development Mode

The agent can be run directly for development:

```bash
cd agent
../.venv/bin/python agent.py
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions on Render.

Quick deployment steps:

1. Push code to a Git repository (GitHub, GitLab, etc.)
2. Connect repository to Render
3. Use `render.yaml` for automatic configuration
4. Set environment variables in Render dashboard:
   - `GOOGLE_API_KEY`
   - `ALLOWED_ORIGINS` (comma-separated frontend URLs)
   - `FIRECRAWL_API_KEY` (optional)

## Troubleshooting

### Python Version Error

If you see "MCP requires Python 3.10+":

```bash
# Check your Python version
python3 --version

# If you need to install Python 3.10+:
# On macOS:
brew install python@3.12

# Then recreate the virtual environment:
rm -rf .venv
./scripts/setup-agent.sh
```

### Module Import Errors

If you encounter import errors:

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
cd agent
pip install -r requirements.txt
```

### API Key Errors

Make sure your `GOOGLE_API_KEY` is set correctly:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

Or add it to a `.env` file in the root directory.

### Port Already in Use

If port 8000 is already in use:

```bash
# Use a different port
PORT=8001 ./scripts/run-agent.sh
```

## 📚 Documentation

- [ADK Documentation](https://google.github.io/adk-docs/) - Learn more about the ADK and its features
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI framework documentation
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation library

## License

This project is licensed under the MIT License - see the LICENSE file for details.
