# CopilotKit <> ADK Starter

This is a starter template for building AI agents using Google's [ADK](https://google.github.io/adk-docs/) and [CopilotKit](https://copilotkit.ai). It provides a modern Next.js application with an integrated investment analyst agent that can research stocks, analyze market data, and provide investment insights.

## Prerequisites

- Node.js 18+
- Python 3.10+ (3.12+ recommended)
  - **Note:** Python 3.10+ is required for MCP tools. The setup script will automatically check for a compatible version.
  - On macOS, install via Homebrew: `brew install python@3.12`
  - Or download from [python.org](https://www.python.org/downloads/)
- Google Makersuite API Key (for the ADK agent) (see https://makersuite.google.com/app/apikey)
- Any of the following package managers:
  - pnpm (recommended)
  - npm
  - yarn
  - bun

> **Note:** This repository ignores lock files (package-lock.json, yarn.lock, pnpm-lock.yaml, bun.lockb) to avoid conflicts between different package managers. Each developer should generate their own lock file using their preferred package manager. After that, make sure to delete it from the .gitignore.

## Getting Started

1. Install dependencies using your preferred package manager:
```bash
# Using pnpm (recommended)
pnpm install

# Using npm
npm install

# Using yarn
yarn install

# Using bun
bun install
```

2. Install Python dependencies for the ADK agent:
```bash
# Using pnpm
pnpm install:agent

# Using npm
npm run install:agent

# Using yarn
yarn install:agent

# Using bun
bun run install:agent
```

> **Note:** This will automatically setup a `.venv` (virtual environment) inside the `agent` directory using Python 3.10+.
>
> The setup script will:
> - Check for Python 3.10 or higher
> - Create a new virtual environment if one doesn't exist
> - Remove and recreate an existing virtual environment if it uses Python < 3.10
>
> To activate the virtual environment manually, you can run:
> ```bash
> source agent/.venv/bin/activate
> ```


3. Set up your Google API key:
```bash
export GOOGLE_API_KEY="your-google-api-key-here"
```

4. Start the development server:
```bash
# Using pnpm
pnpm dev

# Using npm
npm run dev

# Using yarn
yarn dev

# Using bun
bun run dev
```

This will start both the UI and agent servers concurrently.

## Available Scripts
The following scripts can also be run using your preferred package manager:
- `dev` - Starts both UI and agent servers in development mode
- `dev:debug` - Starts development servers with debug logging enabled
- `dev:ui` - Starts only the Next.js UI server
- `dev:agent` - Starts only the ADK agent server
- `build` - Builds the Next.js application for production
- `start` - Starts the production server
- `lint` - Runs ESLint for code linting
- `install:agent` - Installs Python dependencies for the agent

## Documentation

The main UI component is in `src/app/page.tsx`. You can:
- Modify the theme colors and styling
- Add new frontend actions
- Customize the CopilotKit sidebar appearance

## 📚 Documentation

- [ADK Documentation](https://google.github.io/adk-docs/) - Learn more about the ADK and its features
- [CopilotKit Documentation](https://docs.copilotkit.ai) - Explore CopilotKit's capabilities
- [Next.js Documentation](https://nextjs.org/docs) - Learn about Next.js features and API


## Contributing

Feel free to submit issues and enhancement requests! This starter is designed to be easily extensible.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Agent Connection Issues
If you see "I'm having trouble connecting to my tools", make sure:
1. The ADK agent is running on port 8000
2. Your Google API key is set correctly
3. Both servers started successfully

### Python Dependencies
If you encounter Python import errors or version-related errors:

1. **Python Version Error (MCP requires Python 3.10+):**
   ```bash
   # Check your Python version
   python3 --version
   
   # If you need to install Python 3.10+:
   # On macOS:
   brew install python@3.12
   
   # Then recreate the virtual environment:
   cd agent
   rm -rf .venv
   npm run install:agent
   ```

2. **General Python import errors:**
   ```bash
   cd agent
   source .venv/bin/activate
   pip install -r requirements.txt
   ```