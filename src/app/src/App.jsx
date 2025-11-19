// src/App.jsx

import React, { useState } from 'react';
import ResultsDisplay from './components/ResultsDisplay';
import './App.css'; // Import global styles

// *** IMPORTANT: REPLACE THIS PLACEHOLDER ***
const API_ENDPOINT = "https://seo-audit-app-s1y0.onrender.com"; 
// Assuming your ADK agent has a /api/audit route that takes a URL parameter

function App() {
  const [targetUrl, setTargetUrl] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResults(null);
    setError(null);

    try {
      // 1. Send the URL to the ADK backend API
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // The body must match what your ADK agent is expecting to trigger the audit
        body: JSON.stringify({ url: targetUrl }), 
      });

      if (!response.ok) {
        throw new Error(`Audit failed with status: ${response.status}`);
      }
      
      // 2. The ADK should return the structured JSON data from set_model_response
      const data = await response.json(); 
      setResults(data); 

    } catch (err) {
      console.error('Audit API call error:', err);
      setError(`Error: ${err.message}. Check the backend console and CORS settings.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="audit-app">
      <header>
        <h1>🤖 AI SEO Audit Dashboard</h1>
        <p>Powered by Gemini and the Agent Development Kit (ADK).</p>
      </header>
      
      <form onSubmit={handleSubmit} className="input-form">
        <input
          type="url"
          value={targetUrl}
          onChange={(e) => setTargetUrl(e.target.value)}
          placeholder="https://www.yourwebsite.com"
          required
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Analyzing...' : 'Run Comprehensive Audit'}
        </button>
      </form>

      {/* Status Messages */}
      {loading && <p className="status loading">🔍 Running audit, please wait...</p>}
      {error && <p className="status error">{error}</p>}

      {/* Render the results if available */}
      {results && <ResultsDisplay results={results} />}
      
    </div>
  );
}

export default App;