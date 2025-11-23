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
import random
from datetime import datetime
import random
from datetime import datetime

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

# Retry configuration
MAX_RETRIES = 3  # Maximum number of retries for rate limit errors
MAX_QUOTA_RETRIES = 2  # Maximum number of retries for quota exhaustion
MAX_JITTER = 3  # Maximum jitter (random delay) in seconds to add to retry times
FALLBACK_RETRY_DELAY = 5  # Fallback delay if retry time cannot be extracted from error message

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
    """Create error handler with dynamic retry times extracted from error messages."""
    retry_state = {}
    quota_retry_state = {}  # Track quota exhaustion retries
    
    def extract_retry_time(error_text: str) -> Optional[float]:
        """
        Extract retry time from error message.
        
        Looks for patterns like:
        - "Please retry in 3.66431747s"
        - "retry in 5.2 seconds"
        - "retry after 10s"
        
        Returns the time in seconds as float, or None if not found.
        """
        # Multiple patterns to match different error message formats
        patterns = [
            r'retry in (\d+(?:\.\d+)?)\s*s(?:econds?)?',  # "retry in 3.5s" or "retry in 3.5 seconds"
            r'retry after (\d+(?:\.\d+)?)\s*s(?:econds?)?',  # "retry after 5s"
            r'Please retry in (\d+(?:\.\d+)?)\s*s',  # "Please retry in 3.66431747s"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def add_jitter(base_delay: float, max_jitter: float = MAX_JITTER) -> float:
        """
        Add random jitter (0 to max_jitter seconds) to the delay.
        This helps prevent thundering herd problems when multiple requests retry simultaneously.
        
        Args:
            base_delay: Base delay in seconds
            max_jitter: Maximum jitter to add (default: 3 seconds)
        
        Returns:
            Delay with jitter added
        """
        jitter = random.uniform(0, max_jitter)
        return base_delay + jitter
    
    def format_timestamp() -> str:
        """Format current timestamp for logging."""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
    
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
        error_repr = repr(error).lower()
        full_error_text = f"{error_str} {error_repr}"
        
        # Check for quota exhaustion (non-retryable) - more comprehensive detection
        is_quota_exhausted = (
            'resource_exhausted' in full_error_text or 
            'quota exceeded' in full_error_text or
            'current quota' in full_error_text or
            'you exceeded your current quota' in full_error_text or
            'free_tier_input_token_count' in full_error_text or
            'free_tier' in full_error_text and 'quota' in full_error_text
        )
        
        # Also check for 429 with specific quota-related keywords
        is_429_quota = (
            '429' in error_str and (
                'resource_exhausted' in full_error_text or
                'quota' in full_error_text and 'exceeded' in full_error_text
            )
        )
        
        if is_quota_exhausted or is_429_quota:
            # Extract retry time from error message
            extracted_retry_time = extract_retry_time(full_error_text)
            
            # Extract quota limit information
            quota_match = re.search(r'limit[:\s]+(\d+(?:,\d+)*)', full_error_text)
            quota_limit = quota_match.group(1) if quota_match else "250,000 tokens/minute (free tier)"
            
            # Get agent instance ID for tracking quota retries
            agent_obj = context.get('agent') if context else None
            agent_id = id(agent_obj) if agent_obj else 0
            quota_retry_count = quota_retry_state.get(agent_id, 0)
            
            # Try retry if under max retries
            if quota_retry_count < MAX_QUOTA_RETRIES:
                quota_retry_count += 1
                quota_retry_state[agent_id] = quota_retry_count
                
                # Use extracted retry time, or fallback to 30 seconds
                base_delay = extracted_retry_time if extracted_retry_time is not None else 30.0
                if base_delay < 1.0:  # Ensure minimum 1 second
                    base_delay = 1.0
                
                # Add jitter (0 to 3 seconds)
                jitter = random.uniform(0, MAX_JITTER)
                total_delay = base_delay + jitter
                
                timestamp = format_timestamp()
                
                retry_time_msg = f"Retry time from error: {extracted_retry_time:.2f}s" if extracted_retry_time else f"Using fallback delay: {base_delay:.2f}s"
                
                logger.warning(
                    f"\n{'='*70}\n"
                    f"[{timestamp}] ⚠️  {agent_name}: QUOTA EXHAUSTED - Retrying\n"
                    f"{'='*70}\n"
                    f"You've exceeded your Gemini API quota limit.\n"
                    f"\nQuota Details:\n"
                    f"  • Limit: {quota_limit}\n"
                    f"  • Free tier resets every 60 seconds\n"
                    f"\n🔄 Retry Information:\n"
                    f"  • Retry attempt: {quota_retry_count}/{MAX_QUOTA_RETRIES}\n"
                    f"  • {retry_time_msg}\n"
                    f"  • Jitter added: +{jitter:.2f}s (random 0-{MAX_JITTER}s)\n"
                    f"  • Total wait time: {total_delay:.2f} seconds\n"
                    f"\n⏱️  Waiting {total_delay:.2f} seconds before retry...\n"
                    f"{'='*70}\n"
                )
                
                # Wait with extracted time + jitter
                time.sleep(total_delay)
                
                logger.info(f"[{format_timestamp()}] Retrying after {total_delay:.2f}s wait...")
                
                # Re-raise to trigger retry
                raise error
            else:
                # Max quota retries exceeded
                quota_retry_state[agent_id] = 0  # Reset for next request cycle
                
                timestamp = format_timestamp()
                wait_time_str = f"{extracted_retry_time:.2f}s" if extracted_retry_time else "30s+"
                
                logger.error(
                    f"\n{'='*70}\n"
                    f"[{timestamp}] ❌ {agent_name}: QUOTA EXHAUSTED - Max Retries Exceeded\n"
                    f"{'='*70}\n"
                    f"You've exceeded your Gemini API quota limit.\n"
                    f"Already retried {MAX_QUOTA_RETRIES} times.\n"
                    f"\nQuota Details:\n"
                    f"  • Limit: {quota_limit}\n"
                    f"  • Free tier resets every 60 seconds\n"
                    f"  • Suggested wait time from error: {wait_time_str}\n"
                    f"\n💡 Solutions:\n"
                    f"  1. ⏱️  Wait 1-2 minutes for quota to fully reset\n"
                    f"  2. 📊 Check your current usage: https://ai.dev/usage?tab=rate-limit\n"
                    f"  3. 🚀 Upgrade your plan: https://ai.google.dev/gemini-api/docs/rate-limits\n"
                    f"  4. 🔑 Use a different API key with available quota\n"
                    f"  5. 📅 Wait longer - free tier quota resets every minute\n"
                    f"\nThe free tier allows 250,000 input tokens per minute per model.\n"
                    f"If you need higher limits, consider upgrading to a paid plan.\n"
                    f"{'='*70}\n"
                )
                # Don't retry anymore - raise error
                raise error
        
        # Check for 429 rate limit error (temporary, retryable)
        # Only treat as rate limit if it's NOT quota exhaustion
        is_rate_limit = (
            '429' in error_str and 
            not is_quota_exhausted and 
            not is_429_quota and
            'resource_exhausted' not in full_error_text
        )
        
        # Check for other retryable errors
        other_retryable = any(kw in error_str for kw in 
                            ['503', 'overloaded', 'unavailable'])
        
        if is_rate_limit:
            # Extract retry time from error message
            extracted_retry_time = extract_retry_time(full_error_text)
            
            # Get agent instance ID for tracking retries
            agent_obj = context.get('agent') if context else None
            agent_id = id(agent_obj) if agent_obj else 0
            current_retry = retry_state.get(agent_id, 0)
            
            if current_retry < MAX_RETRIES:
                current_retry += 1
                retry_state[agent_id] = current_retry
                
                # Use extracted retry time from error message, or fallback delay
                base_delay = extracted_retry_time if extracted_retry_time is not None else FALLBACK_RETRY_DELAY
                if base_delay < 1.0:  # Ensure minimum 1 second
                    base_delay = 1.0
                
                # Add jitter (0 to 3 seconds)
                jitter = random.uniform(0, MAX_JITTER)
                total_delay = base_delay + jitter
                
                timestamp = format_timestamp()
                
                retry_time_msg = f"Retry time from error: {extracted_retry_time:.2f}s" if extracted_retry_time else f"Using fallback delay: {base_delay:.2f}s"
                
                logger.warning(
                    f"\n{'='*70}\n"
                    f"[{timestamp}] ⚠️  {agent_name}: RATE LIMIT (429) - Retrying\n"
                    f"{'='*70}\n"
                    f"Rate limit exceeded. The API has temporarily limited requests.\n"
                    f"\n🔄 Retry Information:\n"
                    f"  • Retry attempt: {current_retry}/{MAX_RETRIES}\n"
                    f"  • {retry_time_msg}\n"
                    f"  • Jitter added: +{jitter:.2f}s (random 0-{MAX_JITTER}s)\n"
                    f"  • Total wait time: {total_delay:.2f} seconds\n"
                    f"\n⏱️  Waiting {total_delay:.2f} seconds before retry...\n"
                    f"{'='*70}\n"
                )
                
                # Sleep with extracted time + jitter
                time.sleep(total_delay)
                
                logger.info(f"[{format_timestamp()}] Retrying after {total_delay:.2f}s wait...")
                
                # Re-raise to trigger ADK's retry mechanism
                raise error
            else:
                timestamp = format_timestamp()
                logger.error(
                    f"\n{'='*70}\n"
                    f"[{timestamp}] ❌ {agent_name}: RATE LIMIT - Max Retries Exceeded\n"
                    f"{'='*70}\n"
                    f"Rate limit exceeded and max retries ({MAX_RETRIES}) reached.\n"
                    f"Please wait a few minutes before trying again.\n"
                    f"{'='*70}\n"
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
        
        # Add a lightweight ping endpoint to wake up the server
        @app.get("/ping")
        async def ping():
            """Lightweight health check endpoint to wake up the server."""
            return {"status": "ok", "message": "Server is awake"}
        
        # Add /api/audit endpoint for the frontend
        class AuditRequest(BaseModel):
            url: str
        
        @app.post("/api/audit")
        async def audit_url(audit_request: AuditRequest):
            """
            SEO audit endpoint that accepts a URL and runs the audit agent.
            
            Expected request body:
            {
                "url": "https://example.com"
            }
            
            Returns the agent's audit results.
            """
            try:
                url = audit_request.url
                if not url or not url.strip():
                    return {"error": "URL is required", "status": "error"}, 400
                
                logger.info(f"Received audit request for URL: {url}")
                
                # Create a message/prompt for the agent
                # ADK SequentialAgent can be called directly with a message
                agent_message = f"Perform a comprehensive SEO audit for the website: {url}\n\nAnalyze the page structure, SEO elements, keywords, and provide recommendations."
                
                # Call the agent directly - ADK agents can be invoked synchronously
                # Run in executor to avoid blocking the async event loop
                import asyncio
                from concurrent.futures import ThreadPoolExecutor
                
                def run_agent():
                    try:
                        # ADK SequentialAgent can be called like a function with a message
                        result = root_agent(agent_message)
                        return result
                    except Exception as e:
                        logger.error(f"Error calling agent: {e}", exc_info=True)
                        raise
                
                # Run agent in executor
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, run_agent)
                
                # Format the response
                # The result might be a string (markdown) or dict depending on agent output
                if isinstance(result, str):
                    # If it's a string (markdown report), wrap it in a structured format
                    return {
                        "status": "success",
                        "url": url,
                        "result": result,
                        "summary": result[:500] + "..." if len(result) > 500 else result,
                        "recommendations": []
                    }
                else:
                    # If it's already structured (dict)
                    return {
                        "status": "success",
                        "url": url,
                        "result": result,
                        "summary": result.get("summary", "") if isinstance(result, dict) else "",
                        "recommendations": result.get("recommendations", []) if isinstance(result, dict) else []
                    }
                
            except Exception as e:
                logger.error(f"Error in /api/audit endpoint: {e}", exc_info=True)
                return {
                    "error": str(e),
                    "status": "error",
                    "message": "Failed to perform SEO audit. Please try again."
                }, 500
        
        # Add CORS middleware to allow Next.js frontend to connect
        # Build allowed origins list
        allowed_origins = [
            "http://localhost:3000",  # Next.js dev server
            "http://localhost:3001",  # Alternative Next.js port
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]
        
        # Add production origins from environment variable (comma-separated)
        # Set ALLOWED_ORIGINS in Render dashboard: https://your-frontend.vercel.app,https://another-domain.com
        production_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
        if production_origins:
            for origin in production_origins.split(","):
                origin = origin.strip()
                if origin and origin not in allowed_origins:
                    allowed_origins.append(origin)
                    logger.info(f"Added CORS origin from environment: {origin}")
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
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
        # Get port for display
        port = int(os.getenv("PORT", "8000"))
        print("\n📡 Server will be available at:")
        print(f"   http://0.0.0.0:{port}")
        if os.getenv("RENDER") or os.getenv("PORT"):
            print(f"   (Render will assign public URL)")
        print("\n💡 To use with ADK web UI, run:")
        print("   cd .. && adk web")
        print("\n💡 To use with Next.js frontend:")
        print("   npm run dev")
        print("="*70)
        print("\nStarting server...\n")
        
        # Start the server
        # Use PORT from environment (Render sets this automatically), fallback to 8000 for local dev
        port = int(os.getenv("PORT", "8000"))
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
        
    except ImportError as e:
        logger.error(f"Failed to import server dependencies: {e}")
        logger.error("Make sure fastapi, uvicorn, and ag-ui-adk are installed in your virtual environment.")
        logger.error("Run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)