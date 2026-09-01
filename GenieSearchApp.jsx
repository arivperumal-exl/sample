/**
 * Genie Agent Search App - Dummy/Demo Version (React)
 * =====================================================
 * Mirrors the Streamlit demo:
 *   - A central search box for asking questions
 *   - Left-sidebar filters: Unique ID, Line of Business (LOB) -- multi-select
 *   - Each LOB maps to its own "Genie" agent
 *   - A question can be routed to ONE agent or FANNED OUT to MULTIPLE agents
 *     at once (when more than one LOB is selected), with individual answers
 *     merged into a combined summary + per-agent tabs.
 *
 * Setup (Vite example):
 *   npm create vite@latest genie-demo -- --template react
 *   cd genie-demo
 *   # replace src/App.jsx with this file, add App.css alongside it
 *   npm install
 *   npm run dev
 *
 * Replace `callGenieAgent` with a real fetch() to your Genie/agent backend
 * (e.g. Databricks Genie API via a small server proxy) once ready.
 */

import { useState } from "react";
import "./App.css";

// ---------------------------------------------------------------------------
// 1. CONFIG / DUMMY DATA
// ---------------------------------------------------------------------------

// Dummy Unique IDs (e.g. customer/policy/account IDs) shown in the filter.
const DUMMY_UNIQUE_IDS = ["ALL", "UID-1001", "UID-1002", "UID-1003", "UID-1004"];

// Each Line of Business (LOB) is served by its own Genie agent.
// Map LOB -> Genie space/agent id (dummy values, swap with real ones).
const LOB_AGENT_MAP = {
  "Auto Insurance": "genie_space_auto_001",
  "Home Insurance": "genie_space_home_002",
  "Life Insurance": "genie_space_life_003",
  "Health Insurance": "genie_space_health_004",
};

const LOB_OPTIONS = Object.keys(LOB_AGENT_MAP);

// ---------------------------------------------------------------------------
// 2. GENIE AGENT CALL (DUMMY IMPLEMENTATION)
// ---------------------------------------------------------------------------

/**
 * Dummy stand-in for a real Genie agent call. Simulates network latency and
 * returns a canned response so the UI flow can be demoed end-to-end.
 *
 * In production, replace the body with something like:
 *   const res = await fetch(`/api/genie/${agentId}/ask`, {
 *     method: "POST",
 *     headers: { "Content-Type": "application/json" },
 *     body: JSON.stringify({ question, uniqueId }),
 *   });
 *   return await res.json();
 */
function callGenieAgent(agentId, question, uniqueId) {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        agentId,
        answer:
          `[DUMMY RESPONSE from \`${agentId}\`]\n\n` +
          `You asked: "${question}"\n` +
          `Filtered by Unique ID: ${uniqueId}\n\n` +
          `(This is placeholder text. Wire this function to the real ` +
          `Genie agent API to get live answers.)`,
        sql: `SELECT * FROM dummy_table WHERE id = '${uniqueId}' LIMIT 10;`,
      });
    }, 600); // simulate latency
  });
}

/** Pick the correct Genie agent for a single Line of Business and call it. */
async function routeQuestionToAgent(lob, question, uniqueId) {
  const agentId = LOB_AGENT_MAP[lob];
  const result = await callGenieAgent(agentId, question, uniqueId);
  return { ...result, lob };
}

/**
 * Fan the same question out to MULTIPLE Genie agents at once (one per
 * selected LOB) and gather all responses. Each agent only knows about its
 * own LOB's data, so this is how a cross-LOB question (e.g. "compare auto
 * and home claims for this customer") gets answered: ask each relevant
 * agent independently (in parallel via Promise.all), then merge the answers
 * in the UI.
 */
async function askMultipleGenies(lobs, question, uniqueId) {
  const results = await Promise.all(
    lobs.map((lob) => routeQuestionToAgent(lob, question, uniqueId))
  );
  // Promise.all preserves input order already, but keep this explicit
  // in case routeQuestionToAgent is later changed to resolve out of order.
  const order = Object.fromEntries(lobs.map((lob, i) => [lob, i]));
  return [...results].sort((a, b) => order[a.lob] - order[b.lob]);
}

/**
 * Dummy stand-in for a final "combine" step. In production you could send
 * all the individual agent answers to an LLM to synthesize one cohesive
 * answer to the original cross-LOB question. Here we just summarize them.
 */
function synthesizeCombinedAnswer(results) {
  if (results.length <= 1) return "";
  const bullets = results
    .map((r) => {
      const lastLine = r.answer.trim().split("\n").pop();
      return `- **${r.lob}**: ${lastLine}`;
    })
    .join("\n");
  return `**Combined summary across ${results.length} lines of business:**\n\n${bullets}`;
}

// ---------------------------------------------------------------------------
// 3. SIMPLE MARKDOWN-ISH RENDERER (bold + line breaks only, no dependency)
// ---------------------------------------------------------------------------
function renderMiniMarkdown(text) {
  return text.split("\n").map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={j}>{part.slice(2, -2)}</strong>
      ) : (
        part
      )
    );
    return (
      <div key={i}>
        {parts.length ? parts : " "}
      </div>
    );
  });
}

// ---------------------------------------------------------------------------
// 4. REACT APP
// ---------------------------------------------------------------------------
export default function App() {
  const [selectedUniqueId, setSelectedUniqueId] = useState(DUMMY_UNIQUE_IDS[0]);
  const [selectedLobs, setSelectedLobs] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null); // array of per-agent results
  const [warning, setWarning] = useState("");
  const [activeTab, setActiveTab] = useState(0);

  const toggleLob = (lob) => {
    setSelectedLobs((prev) =>
      prev.includes(lob) ? prev.filter((l) => l !== lob) : [...prev, lob]
    );
  };

  const handleSearch = async () => {
    setWarning("");
    setResults(null);

    if (selectedLobs.length === 0) {
      setWarning("Please choose at least one Line of Business from the left filter.");
      return;
    }
    if (!question.trim()) {
      setWarning("Please enter a question.");
      return;
    }

    setLoading(true);
    try {
      const res = await askMultipleGenies(selectedLobs, question, selectedUniqueId);
      setResults(res);
      setActiveTab(0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="genie-app">
      {/* ---- Sidebar: Filters ---- */}
      <aside className="genie-sidebar">
        <h2>Filters</h2>

        <label className="genie-label" htmlFor="uniqueId">
          Unique ID
        </label>
        <select
          id="uniqueId"
          className="genie-select"
          value={selectedUniqueId}
          onChange={(e) => setSelectedUniqueId(e.target.value)}
        >
          {DUMMY_UNIQUE_IDS.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>

        <label className="genie-label">Line of Business</label>
        <div className="genie-checkbox-list">
          {LOB_OPTIONS.map((lob) => (
            <label key={lob} className="genie-checkbox-item">
              <input
                type="checkbox"
                checked={selectedLobs.includes(lob)}
                onChange={() => toggleLob(lob)}
              />
              {lob}
            </label>
          ))}
        </div>
        <p className="genie-hint">
          Select more than one to ask a question across multiple lines of
          business at once.
        </p>

        <hr />
        {selectedLobs.length > 0 ? (
          <>
            <p className="genie-hint" style={{ fontWeight: 600 }}>
              Active agent(s):
            </p>
            <ul className="genie-agent-list">
              {selectedLobs.map((lob) => (
                <li key={lob}>
                  {lob} → <code>{LOB_AGENT_MAP[lob]}</code>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="genie-hint">No agent selected yet.</p>
        )}
      </aside>

      {/* ---- Main area ---- */}
      <main className="genie-main">
        <h1>Ask Genie</h1>

        <div className="genie-search-row">
          <input
            className="genie-search-input"
            type="text"
            placeholder="Ask a question about your data..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button className="genie-search-btn" onClick={handleSearch} disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        {warning && <div className="genie-warning">{warning}</div>}

        {results && (
          <div className="genie-results">
            {results.length > 1 && (
              <>
                <h2>Combined Answer</h2>
                <div className="genie-combined">
                  {renderMiniMarkdown(synthesizeCombinedAnswer(results))}
                </div>
              </>
            )}

            <h2>{results.length === 1 ? "Answer" : "Per-Agent Answers"}</h2>

            <div className="genie-tabs">
              {results.map((r, i) => (
                <button
                  key={r.lob}
                  className={`genie-tab ${i === activeTab ? "active" : ""}`}
                  onClick={() => setActiveTab(i)}
                >
                  {r.lob}
                </button>
              ))}
            </div>

            {results[activeTab] && (
              <div className="genie-tab-panel">
                <p className="genie-hint">
                  Agent: <code>{results[activeTab].agentId}</code>
                </p>
                <pre className="genie-answer-text">{results[activeTab].answer}</pre>
                <details>
                  <summary>Generated SQL (debug)</summary>
                  <pre className="genie-sql">{results[activeTab].sql}</pre>
                </details>
              </div>
            )}
          </div>
        )}

        <footer className="genie-footer">
          Demo UI only. Search box → routes to the Genie agent(s) mapped to the
          selected line(s) of business, filtered by the chosen Unique ID.
          Selecting multiple lines of business fans the question out to each
          agent concurrently and merges their answers.
        </footer>
      </main>
    </div>
  );
}
