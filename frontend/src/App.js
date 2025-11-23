import React, { useState, useEffect } from 'react';
import { Search, FileText, AlertCircle, CheckCircle, Loader2, Globe } from 'lucide-react';

export default function SEOAuditApp() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [serverWakingUp, setServerWakingUp] = useState(true);
  const [wakeUpLogs, setWakeUpLogs] = useState([]);
  const [retryLogs, setRetryLogs] = useState([]);
  const [sseConnection, setSseConnection] = useState(null);

  const API_BASE_URL = 'https://seo-audit-app-s1y0.onrender.com';

  // Normalize URL - add protocol if missing, handle www., and validate domain
  const normalizeUrl = (inputUrl) => {
    if (!inputUrl || !inputUrl.trim()) {
      return '';
    }

    // Trim whitespace
    let url = inputUrl.trim();

    // Remove leading/trailing whitespace again after trim
    url = url.replace(/^\s+|\s+$/g, '');

    // Check if URL is empty after trimming
    if (!url) {
      return '';
    }

    // Check if URL already has a protocol
    const hasProtocol = /^https?:\/\//i.test(url);
    
    if (hasProtocol) {
      // Remove trailing slashes (but keep the domain structure)
      url = url.replace(/\/+$/, '');
      // Check if URL is just protocol (e.g., "https://" or "http://")
      if (url === 'https://' || url === 'http://') {
        return '';
      }
    } else {
      // Remove any leading slashes that might be there
      url = url.replace(/^\/+/, '');
      // Remove trailing slashes
      url = url.replace(/\/+$/, '');
      
      // Check if URL is empty after removing slashes
      if (!url) {
        return '';
      }
      
      // Add https:// protocol
      url = `https://${url}`;
    }

    // Basic validation: ensure we have at least a domain
    // A valid URL should have at least one dot or be localhost
    const urlWithoutProtocol = url.replace(/^https?:\/\//i, '');
    if (!urlWithoutProtocol || (!urlWithoutProtocol.includes('.') && !urlWithoutProtocol.startsWith('localhost'))) {
      return '';
    }

    // Return normalized URL
    return url;
  };

  // Helper function to format timestamp
  const formatTimestamp = () => {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  // Helper function to add log entry
  const addLog = (message, type = 'info') => {
    const timestamp = formatTimestamp();
    setWakeUpLogs(prev => [...prev, { timestamp, message, type }]);
  };

  // Helper function to add retry log entry
  const addRetryLog = (message, type = 'info') => {
    const timestamp = formatTimestamp();
    setRetryLogs(prev => [...prev, { timestamp, message, type }]);
  };

  // Ping the backend on initial load to wake it up if it's sleeping
  // Render free tier can take 30-60 seconds to wake up, so we retry with exponential backoff
  useEffect(() => {
    // Reset logs on mount
    setWakeUpLogs([]);
    
    const wakeUpServer = async (retryCount = 0) => {
      const MAX_RETRIES = 5;
      const INITIAL_DELAY = 2000; // 2 seconds
      const MAX_DELAY = 30000; // 30 seconds max between retries
      
      try {
        setServerWakingUp(true);
        addLog(`Attempting to ping backend server... (Attempt ${retryCount + 1}/${MAX_RETRIES})`, 'info');
        addLog(`Target URL: ${API_BASE_URL}/ping`, 'info');
        
        const startTime = Date.now();
        const response = await fetch(`${API_BASE_URL}/ping`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          // Increase timeout for cold starts
          signal: AbortSignal.timeout(10000), // 10 second timeout
        });

        const endTime = Date.now();
        const duration = ((endTime - startTime) / 1000).toFixed(2);

        if (response.ok) {
          const data = await response.json();
          addLog(`✓ Server responded successfully (${duration}s)`, 'success');
          addLog(`Response: ${JSON.stringify(data)}`, 'success');
          addLog('Backend server is now awake and ready!', 'success');
          console.log('Server is awake:', data);
          
          // Wait a moment to show success message
          setTimeout(() => {
            setServerWakingUp(false);
          }, 1000);
          return; // Success - exit
        } else {
          // Server is responding but with error - might be waking up
          addLog(`⚠ Server responded with status ${response.status} (${duration}s)`, 'warning');
          addLog(`Response may indicate server is still waking up...`, 'warning');
          console.log(`Server waking up... (attempt ${retryCount + 1}/${MAX_RETRIES})`);
        }
      } catch (err) {
        // Network error - server is likely waking up (cold start)
        const errorMessage = err.name === 'AbortError' 
          ? 'Request timed out after 10 seconds'
          : err.message || 'Network error';
          
        addLog(`✗ Request failed: ${errorMessage}`, 'error');
        addLog(`Server may be in cold start (this is normal for Render free tier)`, 'error');
        
        console.log(`Server is waking up, please wait... (attempt ${retryCount + 1}/${MAX_RETRIES}):`, err.message);
        
        // Retry with exponential backoff if we haven't exceeded max retries
        if (retryCount < MAX_RETRIES - 1) {
          // Exponential backoff: 2s, 4s, 8s, 16s, 30s (capped at 30s)
          const delay = Math.min(INITIAL_DELAY * Math.pow(2, retryCount), MAX_DELAY);
          addLog(`Retrying in ${delay / 1000} seconds... (exponential backoff)`, 'info');
          console.log(`Retrying in ${delay / 1000} seconds...`);
          
          setTimeout(() => {
            wakeUpServer(retryCount + 1);
          }, delay);
          return; // Will retry
        } else {
          addLog(`Max retries (${MAX_RETRIES}) reached. You can still try submitting a URL - the server may wake up during the audit request.`, 'warning');
        }
      }
      
      // If we get here, we've exhausted retries or got an error
      // Still hide the loading message after a delay to allow user to try manually
      setTimeout(() => {
        setServerWakingUp(false);
      }, 2000);
    };

    // Add initial log
    addLog('Initializing backend wake-up sequence...', 'info');
    addLog('This may take 30-60 seconds if the server is in cold start (normal for Render free tier)', 'info');
    
    wakeUpServer();
  }, []);

  // Wake up server before audit request - MUST succeed before proceeding
  const wakeUpServerBeforeAudit = async () => {
    const MAX_RETRIES = 8; // Increased retries for better reliability
    const INITIAL_DELAY = 2000; // 2 seconds
    const MAX_DELAY = 30000; // 30 seconds max between retries
    
    addRetryLog('Checking if backend server is awake before starting audit...', 'info');
    addRetryLog('This may take 30-60 seconds if the server is in cold start', 'info');
    
    for (let retryCount = 0; retryCount < MAX_RETRIES; retryCount++) {
      try {
        addRetryLog(`Pinging server... (Attempt ${retryCount + 1}/${MAX_RETRIES})`, 'info');
        
        const startTime = Date.now();
        const response = await fetch(`${API_BASE_URL}/ping`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          signal: AbortSignal.timeout(15000), // 15 second timeout (increased for cold starts)
        });

        const endTime = Date.now();
        const duration = ((endTime - startTime) / 1000).toFixed(2);

        if (response.ok) {
          const data = await response.json();
          addRetryLog(`✓ Server is awake and ready! (responded in ${duration}s)`, 'success');
          addRetryLog(`Response: ${JSON.stringify(data)}`, 'success');
          console.log('Server is awake:', data);
          return true; // Server is awake - SUCCESS
        } else {
          addRetryLog(`⚠ Server responded with status ${response.status} (${duration}s) - may still be waking up...`, 'warning');
          // Continue to retry
        }
      } catch (err) {
        // Server is likely sleeping - will retry
        const errorMsg = err.name === 'AbortError' ? 'Request timed out after 15 seconds' : err.message || 'Network error';
        addRetryLog(`✗ Wake-up attempt failed: ${errorMsg}`, 'error');
        addRetryLog(`Server may be in cold start (this is normal for Render free tier)`, 'info');
        console.log(`Server wake-up attempt ${retryCount + 1}/${MAX_RETRIES} failed:`, err.message);
        
        // If not the last retry, wait before retrying
        if (retryCount < MAX_RETRIES - 1) {
          const delay = Math.min(INITIAL_DELAY * Math.pow(2, retryCount), MAX_DELAY);
          addRetryLog(`Retrying in ${delay / 1000} seconds... (exponential backoff)`, 'info');
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    
    // Max retries reached - server still not awake
    addRetryLog(`❌ Max wake-up retries (${MAX_RETRIES}) reached. Server may still be waking up.`, 'error');
    addRetryLog(`Please wait a moment and try again, or the server may wake up during the audit request.`, 'warning');
    return false; // Wake-up failed after all retries
  };

  const handleAudit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setRetryLogs([]); // Clear previous retry logs

    // Normalize the URL before sending
    const normalizedUrl = normalizeUrl(url);

    // Validate that we have a URL after normalization
    if (!normalizedUrl || normalizedUrl === 'https://') {
      setError('Please enter a valid website URL (e.g., example.com or https://example.com)');
      setLoading(false);
      return;
    }

    // Wake up server before proceeding with audit
    addRetryLog('Checking if backend server is awake...', 'info');
    const serverIsAwake = await wakeUpServerBeforeAudit();
    
    if (!serverIsAwake) {
      // Wake-up failed after all retries - wait a bit more before proceeding
      addRetryLog('Wake-up check completed but server may still be waking up. Proceeding with audit request (server may wake during request)...', 'warning');
      // Give server a bit more time
      await new Promise(resolve => setTimeout(resolve, 2000));
    }

    // Close any existing SSE connection
    if (sseConnection) {
      sseConnection.close();
      setSseConnection(null);
    }

    let eventSource = null;
    let requestId = null;

    try {
      // Generate request_id on frontend first (same format as backend UUID)
      requestId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      addRetryLog(`Connecting to SSE stream... (request_id: ${requestId})`, 'info');
      
      // Connect to SSE BEFORE starting audit to catch all events
      const sseUrl = `${API_BASE_URL}/api/audit/stream/${requestId}`;
      eventSource = new EventSource(sseUrl);
      setSseConnection(eventSource);
      
      // Wait a moment for SSE connection to establish or fail
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Handle SSE events
      eventSource.onmessage = (event) => {
          try {
            const eventData = JSON.parse(event.data);
            
            // Add timestamp if not present
            const timestamp = eventData.timestamp || formatTimestamp();
            
            // Handle different event types
            if (eventData.type === 'connected') {
              addRetryLog(`✓ SSE connection established`, 'success');
            } else if (eventData.type === 'audit_started') {
              addRetryLog(`Starting SEO audit for ${eventData.data.url}...`, 'info');
            } else if (eventData.type === 'quota_exhausted_retry' || eventData.type === 'rate_limit_retry') {
              const data = eventData.data;
              addRetryLog(
                `⚠️ ${data.agent_name}: ${data.message}`,
                'warning'
              );
              addRetryLog(
                `   Retry ${data.retry_attempt}/${data.max_retries} - Waiting ${data.total_wait_time}s (${data.retry_time_from_error ? `from error: ${data.retry_time_from_error}s` : `fallback`} + jitter: ${data.jitter}s)`,
                'info'
              );
            } else if (eventData.type === 'retry_complete') {
              addRetryLog(`✓ ${eventData.data.message}`, 'success');
            } else if (eventData.type === 'audit_completed') {
              addRetryLog(`✓ ${eventData.data.message}`, 'success');
            } else if (eventData.type === 'audit_error') {
              addRetryLog(`✗ Error: ${eventData.data.message}`, 'error');
            }
          } catch (err) {
            console.error('Error parsing SSE event:', err);
          }
      };
      
      eventSource.onerror = (err) => {
        console.error('SSE connection error:', err);
        addRetryLog(`⚠️ SSE connection error: ${err.message || 'Connection failed'}`, 'warning');
        // Don't close on error - it might reconnect, but also don't proceed if server is sleeping
      };
      
      // Wait a moment for SSE connection to establish (or fail)
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Send audit request with retry logic for connection failures
      const sendAuditRequest = async (attempt = 1, maxAttempts = 3) => {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
        
        addRetryLog(`Sending audit request to backend... (Attempt ${attempt}/${maxAttempts})`, 'info');
        
        try {
          const response = await fetch(`${API_BASE_URL}/api/audit`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: normalizedUrl, request_id: requestId }), // Send request_id if backend supports it
            signal: controller.signal,
          });
          
          clearTimeout(timeoutId);

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          return response;
        } catch (err) {
          clearTimeout(timeoutId);
          
          // If connection failed and we have retries left, try again after waking up
          if ((err.message && err.message.includes('Failed to fetch')) || err.name === 'AbortError') {
            if (attempt < maxAttempts) {
              addRetryLog(`✗ Audit request failed: ${err.message || err.name}`, 'error');
              addRetryLog(`Retrying after waking up server again... (Attempt ${attempt + 1}/${maxAttempts})`, 'warning');
              
              // Try to wake up server again before retrying
              await wakeUpServerBeforeAudit();
              
              // Wait a bit before retry
              await new Promise(resolve => setTimeout(resolve, 2000));
              
              // Retry the request
              return sendAuditRequest(attempt + 1, maxAttempts);
            }
          }
          
          // Re-throw if no retries left or different error
          throw err;
        }
      };
      
      // Send audit request with retry logic
      const response = await sendAuditRequest();

      const data = await response.json();
      
      addRetryLog(`✓ Audit request received response from backend`, 'success');
      
      // Use request_id from response if provided (backend may generate its own)
      if (data.request_id && data.request_id !== requestId) {
        requestId = data.request_id;
        addRetryLog(`Backend provided different request_id. Reconnecting SSE stream...`, 'info');
        // Close old connection and connect to new one
        if (eventSource) {
          eventSource.close();
        }
        const newSseUrl = `${API_BASE_URL}/api/audit/stream/${requestId}`;
        eventSource = new EventSource(newSseUrl);
        setSseConnection(eventSource);
        // Re-setup handlers...
        eventSource.onmessage = (event) => {
          try {
            const eventData = JSON.parse(event.data);
            if (eventData.type === 'connected') {
              addRetryLog(`✓ SSE connection established`, 'success');
            } else if (eventData.type === 'audit_started') {
              addRetryLog(`Starting SEO audit for ${eventData.data.url}...`, 'info');
            } else if (eventData.type === 'quota_exhausted_retry' || eventData.type === 'rate_limit_retry') {
              const data = eventData.data;
              addRetryLog(`⚠️ ${data.agent_name}: ${data.message}`, 'warning');
              addRetryLog(`   Retry ${data.retry_attempt}/${data.max_retries} - Waiting ${data.total_wait_time}s`, 'info');
            } else if (eventData.type === 'retry_complete') {
              addRetryLog(`✓ ${eventData.data.message}`, 'success');
            } else if (eventData.type === 'audit_completed') {
              addRetryLog(`✓ ${eventData.data.message}`, 'success');
            }
          } catch (err) {
            console.error('Error parsing SSE event:', err);
          }
        };
      }
      
      setResult(data);
    } catch (err) {
      // Close SSE connection on error
      if (eventSource) {
        eventSource.close();
        setSseConnection(null);
      }
      
      addRetryLog(`✗ Audit request failed: ${err.message || err.name}`, 'error');
      
      if (err.name === 'AbortError') {
        const errorMsg = 'Request timed out after 2 minutes. The backend may be waking up or the audit is taking longer than expected. Please try again.';
        setError(errorMsg);
        addRetryLog(errorMsg, 'error');
      } else if (err.message && (err.message.includes('Failed to fetch') || err.message.includes('Network'))) {
        const errorMsg = 'Failed to connect to the backend server after multiple retry attempts. The server may still be waking up (this can take 30-60 seconds on Render free tier). Please wait a moment and try again.';
        setError(errorMsg);
        addRetryLog(errorMsg, 'error');
        addRetryLog('💡 Tip: Wait 30-60 seconds after page load before submitting your first request on Render free tier.', 'info');
      } else {
        const errorMsg = err.message || 'Failed to perform SEO audit. Please try again.';
        setError(errorMsg);
        addRetryLog(`Error: ${errorMsg}`, 'error');
      }
      console.error('Audit error:', err);
    } finally {
      setLoading(false);
      // Don't close SSE immediately - let it close naturally or after timeout
      // Clean up SSE connection after 5 seconds of no activity
      if (eventSource) {
        setTimeout(() => {
          if (eventSource) {
            eventSource.close();
            setSseConnection(null);
          }
        }, 5000);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <Globe className="w-12 h-12 text-indigo-600 mr-3" />
            <h1 className="text-4xl font-bold text-gray-900">SEO Audit Tool</h1>
          </div>
          <p className="text-gray-600 text-lg">
            Analyze your website's SEO performance with AI-powered insights
          </p>
        </div>

        {/* Search Form */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <form onSubmit={handleAudit} className="space-y-6">
            <div>
              <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
                Website URL
              </label>
              <div className="relative">
                <input
                  type="text"
                  id="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="example.com or www.example.com"
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                />
                <Search className="absolute right-3 top-3.5 w-5 h-5 text-gray-400" />
              </div>
              <p className="mt-2 text-sm text-gray-500">
                You can enter just the domain name (e.g., example.com) or a full URL. Protocol (https://) is optional.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <FileText className="w-5 h-5 mr-2" />
                  Run SEO Audit
                </>
              )}
            </button>
          </form>
        </div>

        {/* Server Wake-up Message with Logs */}
        {serverWakingUp && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-8">
            <div className="flex items-start mb-4">
              <Loader2 className="w-6 h-6 text-blue-600 mr-3 flex-shrink-0 mt-0.5 animate-spin" />
              <div>
                <h3 className="text-blue-800 font-semibold mb-1">Waking up backend server</h3>
                <p className="text-blue-700 text-sm">
                  Connecting to Render backend service. This may take 30-60 seconds if the server is in cold start.
                </p>
              </div>
            </div>
            
            {/* Live Logs Display */}
            {wakeUpLogs.length > 0 && (
              <div className="mt-4 bg-gray-900 rounded-lg p-4 font-mono text-sm max-h-64 overflow-y-auto">
                <div className="text-gray-400 mb-2 text-xs font-semibold">
                  LIVE LOGS - Backend Wake-up Progress
                </div>
                <div className="space-y-1">
                  {wakeUpLogs.map((log, index) => (
                    <div key={index} className="flex items-start">
                      <span className="text-gray-500 mr-3 flex-shrink-0">
                        [{log.timestamp}]
                      </span>
                      <span
                        className={`${
                          log.type === 'success'
                            ? 'text-green-400'
                            : log.type === 'error'
                            ? 'text-red-400'
                            : log.type === 'warning'
                            ? 'text-yellow-400'
                            : 'text-gray-300'
                        }`}
                      >
                        {log.message}
                      </span>
                    </div>
                  ))}
                  {serverWakingUp && (
                    <div className="flex items-start text-gray-500">
                      <span className="mr-3">[...]</span>
                      <span className="animate-pulse">● Waiting for response...</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Show recent logs even after wake-up completes (for a short time) */}
        {!serverWakingUp && wakeUpLogs.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-8">
            <div className="flex items-start mb-3">
              <CheckCircle className="w-6 h-6 text-green-600 mr-3 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-green-800 font-semibold mb-1">Backend server is ready</h3>
                <p className="text-green-700 text-sm mb-3">
                  The backend server is now awake and ready to process your requests.
                </p>
                <details className="mt-3">
                  <summary className="text-green-700 text-sm cursor-pointer hover:text-green-800 font-medium">
                    View connection logs ({wakeUpLogs.length} entries)
                  </summary>
                  <div className="mt-3 bg-gray-900 rounded-lg p-4 font-mono text-sm max-h-48 overflow-y-auto">
                    <div className="space-y-1">
                      {wakeUpLogs.map((log, index) => (
                        <div key={index} className="flex items-start">
                          <span className="text-gray-500 mr-3 flex-shrink-0">
                            [{log.timestamp}]
                          </span>
                          <span
                            className={`${
                              log.type === 'success'
                                ? 'text-green-400'
                                : log.type === 'error'
                                ? 'text-red-400'
                                : log.type === 'warning'
                                ? 'text-yellow-400'
                                : 'text-gray-300'
                            }`}
                          >
                            {log.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </details>
              </div>
            </div>
          </div>
        )}

        {/* Retry Logs Display (during audit) */}
        {loading && retryLogs.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 mb-8">
            <div className="flex items-start mb-4">
              <Loader2 className="w-6 h-6 text-yellow-600 mr-3 flex-shrink-0 mt-0.5 animate-spin" />
              <div>
                <h3 className="text-yellow-800 font-semibold mb-1">Backend Retry Activity</h3>
                <p className="text-yellow-700 text-sm">
                  The backend is handling retries and rate limits. Progress is shown below.
                </p>
              </div>
            </div>
            
            {/* Live Retry Logs Display */}
            <div className="mt-4 bg-gray-900 rounded-lg p-4 font-mono text-sm max-h-64 overflow-y-auto">
              <div className="text-gray-400 mb-2 text-xs font-semibold">
                LIVE RETRY LOGS - Backend Retry Progress
              </div>
              <div className="space-y-1">
                {retryLogs.map((log, index) => (
                  <div key={index} className="flex items-start">
                    <span className="text-gray-500 mr-3 flex-shrink-0">
                      [{log.timestamp}]
                    </span>
                    <span
                      className={`${
                        log.type === 'success'
                          ? 'text-green-400'
                          : log.type === 'error'
                          ? 'text-red-400'
                          : log.type === 'warning'
                          ? 'text-yellow-400'
                          : 'text-gray-300'
                      }`}
                    >
                      {log.message}
                    </span>
                  </div>
                ))}
                {loading && (
                  <div className="flex items-start text-gray-500">
                    <span className="mr-3">[...]</span>
                    <span className="animate-pulse">● Waiting for next event...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-8">
            <div className="flex items-start">
              <AlertCircle className="w-6 h-6 text-red-600 mr-3 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-red-800 font-semibold mb-1">Error</h3>
                <p className="text-red-700">{error}</p>
                <p className="text-red-600 text-sm mt-2">
                  {serverWakingUp 
                    ? 'Server is still waking up. Please wait a moment and try again.' 
                    : 'If the backend was idle, it may take 30-60 seconds to wake up.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="flex items-center mb-6">
              <CheckCircle className="w-8 h-8 text-green-600 mr-3" />
              <h2 className="text-2xl font-bold text-gray-900">Audit Complete</h2>
            </div>

            <div className="space-y-6">
              {/* Display result data */}
              <div className="border border-gray-200 rounded-lg p-6">
                <h3 className="font-semibold text-lg mb-4 text-gray-900">Results</h3>
                <pre className="bg-gray-50 p-4 rounded-lg overflow-auto text-sm text-gray-700">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>

              {/* If result has specific fields, you can display them nicely */}
              {result.summary && (
                <div className="border border-gray-200 rounded-lg p-6">
                  <h3 className="font-semibold text-lg mb-3 text-gray-900">Summary</h3>
                  <p className="text-gray-700">{result.summary}</p>
                </div>
              )}

              {result.recommendations && (
                <div className="border border-gray-200 rounded-lg p-6">
                  <h3 className="font-semibold text-lg mb-3 text-gray-900">Recommendations</h3>
                  <ul className="space-y-2">
                    {result.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start">
                        <span className="text-indigo-600 mr-2">•</span>
                        <span className="text-gray-700">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Info Card */}
        {!result && !loading && !serverWakingUp && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 text-center">
            <p className="text-blue-800">
              Enter a website URL above to get started with your SEO audit
            </p>
          </div>
        )}
      </div>
    </div>
  );
}