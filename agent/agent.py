"""
SEO Audit Agent - ADK Agent for comprehensive SEO auditing

IMPORTANT: This file should be run using the project's run script, not directly:
  - Use: npm run dev:agent
  - Or: ./scripts/run-agent.sh
  
Running python agent.py directly will fail because it needs the virtual environment.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import os
import sys
import logging
import time
import re

# Check Python version FIRST - MCP requires Python 3.10+
if sys.version_info < (3, 10):
    print("="*70, file=sys.stderr)
    print("ERROR: Python 3.10+ is required but you're using Python {}.{}.".format(
        sys.version_info.major, sys.version_info.minor), file=sys.stderr)
    print("="*70, file=sys.stderr)
    print(f"\nCurrent Python: {sys.executable}", file=sys.stderr)
    print(f"Python version: {sys.version}", file=sys.stderr)
    print("\nSOLUTION: Run the agent using one of these methods:", file=sys.stderr)
    print("  1. npm run dev:agent", file=sys.stderr)
    print("  2. ./scripts/run-agent.sh", file=sys.stderr)
    print("  3. cd .. && source .venv/bin/activate && cd agent && python agent.py", file=sys.stderr)
    print("\nThese methods will use Python 3.12 from the parent .venv directory.", file=sys.stderr)
    print("="*70, file=sys.stderr)
    sys.exit(1)

# Automatically detect and use parent .venv if not already in venv
# This allows agent.py to work when run directly from IDE or terminal
_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_AGENT_DIR)
_PARENT_VENV_DIR = os.path.join(_PARENT_DIR, ".venv", "lib")

# Check if parent .venv exists and find the correct Python version site-packages
if os.path.exists(_PARENT_VENV_DIR):
    # Find any Python version directory in .venv/lib
    try:
        python_dirs = [d for d in os.listdir(_PARENT_VENV_DIR) if d.startswith("python")]
        if python_dirs:
            # Use the first Python version found (should be only one)
            _PARENT_VENV_SITE_PACKAGES = os.path.join(_PARENT_VENV_DIR, python_dirs[0], "site-packages")
            if os.path.exists(_PARENT_VENV_SITE_PACKAGES):
                sys.path.insert(0, _PARENT_VENV_SITE_PACKAGES)
    except (OSError, IndexError):
        pass

# Check if running in virtual environment before importing ADK packages
# This provides a helpful error message if run with system Python
try:
    # Type ignore comments are used because IDE linter can't see packages in parent .venv
    # Runtime imports work correctly when using parent .venv Python interpreter
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams  # type: ignore
    from mcp.client.stdio import StdioServerParameters  # type: ignore
    from google.adk.agents import LlmAgent, SequentialAgent  # type: ignore
    from google.adk.tools import google_search  # type: ignore
    from google.adk.tools.agent_tool import AgentTool  # type: ignore
except ModuleNotFoundError as e:
    print("="*70, file=sys.stderr)
    print("ERROR: Module not found. You need to use the virtual environment.", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print(f"\nMissing module: {e.name}", file=sys.stderr)
    print(f"Python path: {sys.executable}", file=sys.stderr)
    print(f"Checked parent venv: {_PARENT_VENV_DIR}", file=sys.stderr)
    print("\nSOLUTION: Run the agent using one of these methods:", file=sys.stderr)
    print("  1. npm run dev:agent", file=sys.stderr)
    print("  2. ./scripts/run-agent.sh", file=sys.stderr)
    print("  3. cd .. && source .venv/bin/activate && cd agent && python agent.py", file=sys.stderr)
    print("\nThe virtual environment (.venv) is in the parent directory.", file=sys.stderr)
    print("="*70, file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retry configuration for 429 errors
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # seconds
BACKOFF_MULTIPLIER = 2  # exponential backoff

# ============================================================================
# Data Models
# ============================================================================

class HeadingItem(BaseModel):
    tag: str = Field(..., description="Heading tag (h1, h2, h3)")
    text: str = Field(..., description="Heading text content")

class LinkCounts(BaseModel):
    internal: int = Field(..., description="Internal link count")
    external: int = Field(..., description="External link count")
    total: int = Field(..., description="Total link count")

class TargetKeywords(BaseModel):
    primary_keyword: str
    secondary_keywords: List[str] = Field(default_factory=list)
    search_intent: str
    supporting_topics: List[str] = Field(default_factory=list)

class AuditResults(BaseModel):
    title_tag: str
    meta_description: str
    primary_heading: str
    secondary_headings: List[HeadingItem]
    word_count: Optional[int]
    content_summary: str
    link_counts: LinkCounts
    technical_findings: List[str]
    content_opportunities: List[str]

class PageAuditOutput(BaseModel):
    audit_results: AuditResults
    target_keywords: TargetKeywords

class SerpAnalysis(BaseModel):
    keyword: str
    results: List[dict]
    patterns: dict = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)

# ============================================================================
# Error Handling with 429 Retry Logic
# ============================================================================

def create_error_handler(agent_name: str):
    """Create error handler with exponential backoff for 429 rate limit errors."""
    retry_state = {}
    
    def handler(error: Exception = None, callback_context: Dict = None, **kwargs) -> None:
        """
        Handle model errors with retry logic for rate limits.
        
        Args:
            error: The exception that occurred (may be passed as positional or keyword)
            callback_context: Context dictionary provided by ADK framework
            **kwargs: Additional keyword arguments (to handle framework variations)
        """
        # Handle error passed as keyword argument or positional
        if error is None:
            error = kwargs.get('error', kwargs.get('exception', None))
        
        # Get context from callback_context or kwargs
        context = callback_context
        if context is None:
            context = kwargs.get('context', kwargs.get('callback_context', {}))
        
        if error is None:
            logger.warning(f"{agent_name}: Error handler called without error information")
            return
        
        error_str = str(error).lower()
        
        # Check for quota exhaustion (non-retryable)
        is_quota_exhausted = (
            'resource_exhausted' in error_str or 
            'quota exceeded' in error_str or
            'current quota' in error_str
        )
        
        if is_quota_exhausted:
            # Extract retry delay if available
            retry_match = re.search(r'retry in (\d+(?:\.\d+)?)', error_str)
            wait_time = retry_match.group(1) if retry_match else "unknown"
            
            logger.error(
                f"\n{'='*70}\n"
                f"{agent_name}: QUOTA EXHAUSTED\n"
                f"{'='*70}\n"
                f"You've exceeded your Gemini API quota limit.\n"
                f"Wait time: {wait_time} seconds\n\n"
                f"Solutions:\n"
                f"1. Wait {wait_time}s and try again\n"
                f"2. Check usage: https://ai.dev/usage?tab=rate-limit\n"
                f"3. Upgrade plan: https://ai.google.dev/gemini-api/docs/rate-limits\n"
                f"4. Use a different API key with available quota\n"
                f"{'='*70}\n"
            )
            # Don't retry - quota issues require waiting or upgrading
            raise error
        
        # Check for 429 rate limit error (temporary, retryable)
        is_rate_limit = '429' in error_str and not is_quota_exhausted
        
        # Check for other retryable errors
        other_retryable = any(kw in error_str for kw in 
                            ['503', 'overloaded', 'unavailable'])
        
        if is_rate_limit:
            # Get agent instance ID for tracking retries
            agent_obj = context.get('agent') if context else None
            agent_id = id(agent_obj) if agent_obj else 0
            current_retry = retry_state.get(agent_id, 0)
            
            if current_retry < MAX_RETRIES:
                # Calculate exponential backoff delay
                delay = INITIAL_RETRY_DELAY * (BACKOFF_MULTIPLIER ** current_retry)
                retry_state[agent_id] = current_retry + 1
                
                logger.warning(
                    f"{agent_name}: Rate limit (429) hit. "
                    f"Retry {current_retry + 1}/{MAX_RETRIES} after {delay}s delay..."
                )
                
                # Sleep with exponential backoff
                time.sleep(delay)
                
                # Re-raise to trigger ADK's retry mechanism
                raise error
            else:
                logger.error(
                    f"{agent_name}: Max retries ({MAX_RETRIES}) exceeded for rate limit. "
                    f"Please wait a few minutes before trying again."
                )
                retry_state[agent_id] = 0  # Reset for next request
                raise error
                
        elif other_retryable:
            logger.warning(f"{agent_name}: API overloaded. System will retry. Error: {error}")
        else:
            logger.error(f"{agent_name}: Error - {error}")
    
    return handler

# ============================================================================
# Tool Setup
# ============================================================================

# Validate API key
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    logger.warning("FIRECRAWL_API_KEY not set. Scraping may fail.")

# Firecrawl MCP toolset
firecrawl_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=["-y", "firecrawl-mcp"],
            env={"FIRECRAWL_API_KEY": FIRECRAWL_API_KEY}
        ),
        timeout=120.0
    ),
    tool_filter=['firecrawl_scrape']
)

# ============================================================================
# Agent Pipeline
# ============================================================================

# Agent 1: Page Auditor
page_auditor = LlmAgent(
    name="PageAuditor",
    model="gemini-2.5-flash",
    instruction="""You must extract and validate the URL from the user's message before scraping.

CRITICAL URL REQUIREMENTS:
1. URL MUST start with http:// or https://
2. URL MUST be a complete, valid URL (e.g., https://example.com/page)
3. If user provides incomplete URL (e.g., "example.com"), add "https://" prefix
4. If user provides path only (e.g., "/page"), ask for complete URL

STEP 1: Extract URL from user message
- Look for patterns like: "audit https://...", "analyze example.com", URLs in quotes
- Validate URL format
- If URL missing http/https, prepend "https://"
- Example transforms:
  * "example.com" → "https://example.com"
  * "www.site.com/page" → "https://www.site.com/page"
  * "https://site.com" → "https://site.com" (already valid)

STEP 2: Call firecrawl_scrape with EXACT parameters:
{
  "url": "<the validated URL with https://>",
  "formats": ["markdown", "html", "links"],
  "onlyMainContent": true,
  "timeout": 90000
}

STEP 3: Analyze scraped data
- Extract: title tag, meta description, headings (h1, h2, h3)
- Count: words, internal links, external links
- Identify: technical issues, content gaps

STEP 4: Infer SEO elements
- Primary keyword (from title/h1/content)
- Secondary keywords (from h2s/content)
- Search intent (informational/commercial/navigational/transactional)
- Supporting topics

STEP 5: Return structured JSON matching PageAuditOutput schema

If URL is invalid or missing, respond with error message asking user to provide valid URL.""",
    tools=[firecrawl_toolset],
    output_schema=PageAuditOutput,
    output_key="page_audit",
    after_model_callback=create_error_handler("PageAuditor")
)

# Agent 2: SERP Analyst
search_executor = LlmAgent(
    name="SearchExecutor",
    model="gemini-2.5-flash",
    instruction="Execute Google search for keyword. Return JSON array of results (title, url, snippet).",
    tools=[google_search],
    after_model_callback=create_error_handler("SearchExecutor")
)

serp_analyst = LlmAgent(
    name="SerpAnalyst",
    model="gemini-2.5-flash",
    instruction="""Read primary keyword from state['page_audit']['target_keywords']['primary_keyword'].
    Call SearchExecutor to get search results.
    Analyze: rank, title, URL, snippet patterns, content formats, themes.
    Return structured SerpAnalysis JSON.""",
    tools=[AgentTool(search_executor)],
    output_schema=SerpAnalysis,
    output_key="serp_analysis",
    after_model_callback=create_error_handler("SerpAnalyst")
)

# Agent 3: Optimization Advisor
optimization_advisor = LlmAgent(
    name="OptimizationAdvisor",
    model="gemini-2.5-flash",
    instruction="""Review state['page_audit'] and state['serp_analysis'].
    
    Generate Markdown report:
    # SEO Audit Report
    - Executive Summary
    - Technical & On-Page Findings
    - Keyword Analysis
    - Competitive SERP Analysis
    - Prioritized Recommendations (P0/P1/P2)
    - Next Steps
    
    Return ONLY Markdown, no JSON or preamble.""",
    after_model_callback=create_error_handler("OptimizationAdvisor")
)

# Sequential pipeline
seo_audit_pipeline = SequentialAgent(
    name="SeoAuditPipeline",
    description="Three-stage SEO audit: page audit → SERP analysis → optimization report",
    sub_agents=[page_auditor, serp_analyst, optimization_advisor]
)

# Root agent
root_agent = seo_audit_pipeline

# ============================================================================
# Server Startup (when run directly)
# ============================================================================

if __name__ == "__main__":
    """
    Start the FastAPI server when agent.py is run directly.
    
    This creates a web server on port 8000 that exposes the agent
    via ADK's web interface. The agent can then be accessed by:
    - ADK web UI (adk web command)
    - HTTP requests to http://localhost:8000/
    - Next.js frontend via CopilotKit
    """
    try:
        from ag_ui_adk import create_adk_app  # type: ignore
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        
        # Create FastAPI app with ADK agent
        app = create_adk_app(root_agent)
        
        # Add CORS middleware to allow Next.js frontend to connect
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",  # Next.js dev server
                "http://localhost:3001",  # Alternative Next.js port
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Print startup information
        print("="*70)
        print("🤖 SEO Audit Agent Server Starting")
        print("="*70)
        print(f"Agent: {root_agent.name}")
        print(f"Description: {root_agent.description}")
        if hasattr(root_agent, 'sub_agents'):
            print(f"Sub-agents: {len(root_agent.sub_agents)}")
            for i, sub_agent in enumerate(root_agent.sub_agents, 1):
                print(f"  {i}. {sub_agent.name}")
        print("\n📡 Server will be available at:")
        print("   http://localhost:8000")
        print("\n💡 To use with ADK web UI, run:")
        print("   cd .. && adk web")
        print("\n💡 To use with Next.js frontend:")
        print("   npm run dev")
        print("="*70)
        print("\nStarting server...\n")
        
        # Start the server
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        
    except ImportError as e:
        logger.error(f"Failed to import server dependencies: {e}")
        logger.error("Make sure fastapi, uvicorn, and ag-ui-adk are installed in your virtual environment.")
        logger.error("Run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)