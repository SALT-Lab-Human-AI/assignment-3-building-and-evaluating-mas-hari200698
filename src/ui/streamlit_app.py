"""
Streamlit Web Interface
Professional web UI for the multi-agent research system.

Features:
- Interactive query input with example queries
- Agent trace display (shows which agent is active)
- Citation/source display
- Safety event communication (blocked/sanitized)
- Query history

Run with: streamlit run src/ui/streamlit_app.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import yaml
import re
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

from src.autogen_orchestrator import AutoGenOrchestrator
from src.evaluation import LLMJudge
import asyncio

# Load environment variables
load_dotenv()


# Professional CSS styling
CUSTOM_CSS = """
<style>
    /* Import professional font */
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap');

    /* Global styles */
    .stApp {
        font-family: 'Source Sans Pro', sans-serif;
    }

    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }

    .main-header h1 {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }

    .main-header p {
        color: #a8c5e2;
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
        font-weight: 400;
    }

    /* Search section */
    .search-section {
        background: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    /* Example query buttons */
    .example-btn {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.9rem;
        color: #475569;
        text-align: left;
        width: 100%;
    }

    .example-btn:hover {
        background: #f1f5f9;
        border-color: #cbd5e1;
        color: #1e40af;
    }

    /* Response card */
    .response-card {
        background: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 12px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem;
        text-align: center;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e3a5f;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Agent trace styling */
    .agent-trace {
        background: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
        border-radius: 0 8px 8px 0;
    }

    .agent-planner { border-left-color: #3b82f6; }
    .agent-researcher { border-left-color: #10b981; }
    .agent-writer { border-left-color: #f59e0b; }
    .agent-critic { border-left-color: #8b5cf6; }

    /* Safety status badges */
    .safety-badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .safety-safe {
        background: #dcfce7;
        color: #166534;
    }

    .safety-blocked {
        background: #fef2f2;
        color: #dc2626;
    }

    .safety-sanitized {
        background: #fef3c7;
        color: #d97706;
    }

    /* Citation styling */
    .citation-item {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }

    .citation-item a {
        color: #2563eb;
        text-decoration: none;
    }

    .citation-item a:hover {
        text-decoration: underline;
    }

    /* Sidebar styling */
    .sidebar-section {
        background: #f8fafc;
        border-radius: 10px;
        padding: 1.25rem;
        margin: 1rem 0;
    }

    .sidebar-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.75rem;
    }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stButton > button[data-baseweb="button"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    }

    /* Text area styling */
    .stTextArea textarea {
        border-radius: 10px;
        border: 2px solid #e2e8f0;
        font-size: 1rem;
    }

    .stTextArea textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
</style>
"""


def load_config():
    """Load configuration file."""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def initialize_session_state():
    """Initialize Streamlit session state."""
    if 'history' not in st.session_state:
        st.session_state.history = []

    if 'orchestrator' not in st.session_state:
        config = load_config()
        try:
            st.session_state.orchestrator = AutoGenOrchestrator(config)
        except Exception as e:
            st.error(f"Failed to initialize orchestrator: {e}")
            st.session_state.orchestrator = None

    if 'show_traces' not in st.session_state:
        st.session_state.show_traces = True

    if 'show_safety_log' not in st.session_state:
        st.session_state.show_safety_log = True

    if 'safety_events_count' not in st.session_state:
        st.session_state.safety_events_count = 0

    if 'all_safety_events' not in st.session_state:
        st.session_state.all_safety_events = []

    if 'enable_judge' not in st.session_state:
        st.session_state.enable_judge = True  # Enabled by default

    if 'judge' not in st.session_state:
        st.session_state.judge = None

    if 'latest_result' not in st.session_state:
        st.session_state.latest_result = None

    if 'judge_results_cache' not in st.session_state:
        st.session_state.judge_results_cache = {}  # Cache: query_hash -> evaluation result


def process_query(query: str) -> Dict[str, Any]:
    """Process a query through the orchestrator."""
    orchestrator = st.session_state.orchestrator

    if orchestrator is None:
        return {
            "query": query,
            "error": "Orchestrator not initialized",
            "response": "Error: System not properly initialized.",
            "citations": [],
            "metadata": {},
            "safety": {}
        }

    try:
        result = orchestrator.process_query(query)
        citations = extract_citations(result)
        agent_traces = extract_agent_traces(result)

        safety_info = result.get("safety", {})
        new_events = safety_info.get("events", [])
        if new_events:
            st.session_state.all_safety_events.extend(new_events)
            st.session_state.safety_events_count = len(st.session_state.all_safety_events)

        metadata = result.get("metadata", {})
        metadata["agent_traces"] = agent_traces
        metadata["citations"] = citations

        return {
            "query": query,
            "response": result.get("response", ""),
            "citations": citations,
            "metadata": metadata,
            "safety": safety_info,
            "conversation_history": result.get("conversation_history", [])
        }

    except Exception as e:
        return {
            "query": query,
            "error": str(e),
            "response": f"An error occurred: {str(e)}",
            "citations": [],
            "metadata": {"error": True},
            "safety": {}
        }


def extract_citations(result: Dict[str, Any]) -> list:
    """Extract citations from research result."""
    citations = []

    for msg in result.get("conversation_history", []):
        content = msg.get("content", "")

        # Handle list content
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
        elif not isinstance(content, str):
            content = str(content)

        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
        citation_patterns = re.findall(r'\[Source: ([^\]]+)\]', content)

        for url in urls:
            if url not in citations:
                citations.append(url)

        for citation in citation_patterns:
            if citation not in citations:
                citations.append(citation)

    return citations[:15]


def extract_agent_traces(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract agent execution traces, consolidating consecutive messages from same agent."""
    traces = []
    conversation_history = result.get("conversation_history", [])

    print(f"[DEBUG] extract_agent_traces: Found {len(conversation_history)} messages in conversation_history")

    # Track the last agent to consolidate consecutive messages
    last_agent = None
    last_content_parts = []
    step_counter = 0

    def sanitize_content(content: str) -> str:
        """Remove HTML tags and limit content for safe display."""
        import re
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        # Remove markdown heading markers that might render as large text
        content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
        # Limit length
        if len(content) > 300:
            content = content[:300] + "..."
        return content.strip()

    def add_trace(agent: str, content_parts: list):
        nonlocal step_counter
        step_counter += 1
        combined_content = "\n".join(content_parts)
        preview = sanitize_content(combined_content[:500])
        traces.append({
            "step": step_counter,
            "agent": agent,
            "preview": preview,
            "full_content": combined_content
        })

    for i, msg in enumerate(conversation_history):
        agent = msg.get("source", "Unknown")
        content = msg.get("content", "")

        # Handle list content
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
        elif not isinstance(content, str):
            content = str(content)

        # Skip empty or tool-call-only content
        if not content.strip() or content.strip().startswith("🔧 Calling tool"):
            continue

        # Skip "user" messages - these are internal orchestrator prompts, not actual user input
        if agent.lower() == "user":
            continue

        # Consolidate consecutive messages from the same agent
        if agent == last_agent:
            # Same agent - append to existing content
            last_content_parts.append(content)
        else:
            # Different agent - save previous and start new
            if last_agent and last_content_parts:
                add_trace(last_agent, last_content_parts)
            last_agent = agent
            last_content_parts = [content]

    # Don't forget the last agent's content
    if last_agent and last_content_parts:
        add_trace(last_agent, last_content_parts)

    print(f"[DEBUG] extract_agent_traces: Returning {len(traces)} traces (consolidated from {len(conversation_history)} messages)")
    return traces


def render_header():
    """Render the main header."""
    st.markdown("""
        <div class="main-header">
            <h1>🔬 Multi-Agent Research Assistant</h1>
            <p>Powered by AutoGen • Intelligent Research Synthesis</p>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar."""
    with st.sidebar:
        st.markdown("## ⚙️ Settings")

        st.session_state.show_traces = st.checkbox(
            "Show Agent Traces",
            value=st.session_state.show_traces,
            help="Display step-by-step agent workflow"
        )

        st.session_state.show_safety_log = st.checkbox(
            "Show Safety Log",
            value=st.session_state.show_safety_log,
            help="Display all safety events"
        )

        st.session_state.enable_judge = st.checkbox(
            "🏛️ Enable LLM-as-a-Judge",
            value=st.session_state.enable_judge,
            help="Evaluate responses using LLM-as-a-Judge with multiple criteria"
        )

        st.markdown("---")

        # Statistics
        st.markdown("## 📊 Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Queries", len(st.session_state.history))
        with col2:
            st.metric("Safety Events", st.session_state.safety_events_count)

        st.markdown("---")

        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.history = []
            st.session_state.all_safety_events = []
            st.session_state.safety_events_count = 0
            st.session_state.query_input = ""
            st.session_state.latest_result = None
            st.rerun()

        # Export session button
        if st.session_state.history:
            if st.button("📥 Export Latest Session", use_container_width=True):
                import json
                from datetime import datetime

                # Get the latest session from history
                latest = st.session_state.history[-1]
                result = latest.get("result", {})

                # Format session data
                session_data = {
                    "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": latest.get("timestamp", datetime.now().isoformat()),
                    "query": latest.get("query", ""),
                    "workflow": {
                        "input_safety_check": {
                            "passed": result.get("safety", {}).get("input_check", {}).get("safe", True),
                            "violations": result.get("safety", {}).get("input_check", {}).get("violations", [])
                        },
                        "agents": [],
                        "output_safety_check": {
                            "passed": result.get("safety", {}).get("output_check", {}).get("safe", True),
                            "violations": result.get("safety", {}).get("output_check", {}).get("violations", []),
                            "sanitized": result.get("metadata", {}).get("output_sanitized", False)
                        }
                    },
                    "final_response": result.get("response", ""),
                    "metadata": {
                        "num_messages": result.get("metadata", {}).get("num_messages", 0),
                        "num_sources": len(result.get("citations", [])),
                        "agents_involved": result.get("metadata", {}).get("agents_involved", [])
                    },
                    "citations": result.get("citations", [])
                }

                # Extract agent traces
                conversation = result.get("conversation_history", [])
                step = 0
                for msg in conversation:
                    source = msg.get("source", "")
                    if source.lower() == "user":
                        continue
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(str(c) for c in content)
                    if not content or content.startswith("🔧"):
                        continue
                    step += 1
                    session_data["workflow"]["agents"].append({
                        "agent": source.title(),
                        "step": step,
                        "content": content[:2000]  # Limit content length
                    })

                # Save to file
                output_path = "samples/sample_session.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)

                st.success(f"✅ Exported to {output_path}")

        st.markdown("---")

        # System info
        st.markdown("## ℹ️ System Info")
        config = load_config()
        st.markdown(f"**Topic:** {config.get('system', {}).get('topic', 'HCI Research')}")
        model_name = config.get('models', {}).get('default', {}).get('name', 'Unknown')
        st.markdown(f"**Model:** `{model_name}`")


def set_example_query(example: str):
    """Callback to set example query."""
    st.session_state.query_input = example


def render_example_queries():
    """Render example query buttons that populate the search bar."""
    examples = [
        "What are the key principles of user-centered design?",
        "Explain recent advances in AR/VR usability research",
        "Compare approaches to AI transparency and explainability",
        "What are ethical considerations in AI for education?",
    ]

    st.markdown("##### Quick Examples")

    for example in examples:
        st.button(
            example,
            key=f"example_{hash(example)}",
            use_container_width=True,
            type="secondary",
            on_click=set_example_query,
            args=(example,)
        )


def render_response(result: Dict[str, Any]):
    """Render the query response."""

    # Check for errors
    if "error" in result and result.get("metadata", {}).get("error"):
        st.error(f"**Error:** {result['error']}")
        return

    # Safety status
    safety_info = result.get("safety", {})
    input_check = safety_info.get("input_check", {})
    output_check = safety_info.get("output_check", {})

    # Check if blocked
    if input_check and not input_check.get("safe", True):
        st.error("⛔ **Query Blocked by Safety Guardrails**")
        violations = input_check.get("violations", [])
        for v in violations:
            st.warning(f"• **{v.get('category', 'Safety').upper()}**: {v.get('reason', 'Unknown')}")
        st.markdown("---")
        st.markdown(result.get("response", "Query was blocked."))
        return

    # Main response
    st.markdown("### 📄 Research Results")
    st.markdown(result.get("response", ""))

    # Sanitization warning
    if output_check and not output_check.get("safe", True):
        st.warning("⚠️ Some content was modified by safety filters.")

    st.markdown("---")

    # Metrics row
    metadata = result.get("metadata", {})
    citations = result.get("citations", [])
    col1, col2, col3 = st.columns(3)

    with col1:
        # Use actual citations count for consistency
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(citations)}</div>
                <div class="metric-label">Sources</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{metadata.get('tool_calls', 0)}</div>
                <div class="metric-label">Tool Calls</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        agents = metadata.get('agents_involved', [])
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(agents)}</div>
                <div class="metric-label">Agents</div>
            </div>
        """, unsafe_allow_html=True)

    # Citations
    citations = result.get("citations", [])
    if citations:
        st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
        with st.expander(f"📚 Citations & Sources ({len(citations)})", expanded=False):
            for i, citation in enumerate(citations, 1):
                if citation.startswith("http"):
                    st.markdown(f"""
                        <div class="citation-item">
                            <strong>[{i}]</strong> <a href="{citation}" target="_blank">{citation}</a>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class="citation-item">
                            <strong>[{i}]</strong> {citation}
                        </div>
                    """, unsafe_allow_html=True)

    # Agent traces
    if st.session_state.show_traces:
        traces = metadata.get("agent_traces", [])
        agents = metadata.get("agents_involved", [])

        print(f"[DEBUG] render_response: traces={len(traces)}, agents={agents}")

        # Show agent workflow - collapsed by default since it's debug info
        if traces or agents:
            with st.expander(f"🔬 Agent Processing Log ({len(traces)} steps)", expanded=False):
                st.caption("💡 This shows the internal workflow of how agents processed your query. The final answer is displayed above.")

                if traces:
                    import html
                    import re

                    agent_colors = {
                        "Planner": "#3b82f6",
                        "Researcher": "#10b981",
                        "Writer": "#f59e0b",
                        "Critic": "#8b5cf6",
                        "User": "#64748b"
                    }
                    agent_icons = {
                        "Planner": "🎯",
                        "Researcher": "🔎",
                        "Writer": "✍️",
                        "Critic": "📋",
                        "User": "👤"
                    }

                    for trace in traces:
                        agent = trace.get("agent", "Unknown")
                        # Capitalize agent name properly
                        agent_display = agent.title() if agent else "Unknown"

                        full_content = trace.get("full_content", "")
                        preview = trace.get("preview", "")

                        # Clean preview for the header
                        preview_clean = re.sub(r'[#*_`]', '', preview)
                        preview_clean = re.sub(r'\[.*?\]\(.*?\)', '', preview_clean)
                        preview_clean = re.sub(r'https?://\S+', '[URL]', preview_clean)
                        preview_clean = ' '.join(preview_clean.split())[:80]
                        if len(preview_clean) >= 80:
                            preview_clean += "..."

                        color = agent_colors.get(agent_display, "#64748b")
                        icon = agent_icons.get(agent_display, "🔹")
                        step = trace.get('step', 0)

                        # Nested expander for each step
                        with st.expander(f"{icon} Step {step}: {agent_display} — {preview_clean}", expanded=False):
                            # Display full content with preserved formatting
                            # Use a code block for safe display of the content
                            st.markdown(f"**Agent:** {agent_display}")
                            st.markdown("**Full Output:**")
                            # Display in a scrollable container
                            st.markdown(f"""
                                <div style="
                                    background: #0f172a;
                                    border: 1px solid #334155;
                                    border-radius: 6px;
                                    padding: 12px;
                                    max-height: 400px;
                                    overflow-y: auto;
                                    font-family: 'Consolas', 'Monaco', monospace;
                                    font-size: 0.85rem;
                                    white-space: pre-wrap;
                                    color: #e2e8f0;
                                ">{html.escape(full_content)}</div>
                            """, unsafe_allow_html=True)

                elif agents:
                    st.info(f"**Agents involved:** {', '.join(agents)}")

    # LLM-as-a-Judge evaluation
    query = result.get("query", "")
    response_text = result.get("response", "")
    render_judge_evaluation(query, response_text, citations)


def render_judge_evaluation(query: str, response: str, citations: list):
    """Render LLM-as-a-Judge evaluation scores."""
    if not st.session_state.enable_judge:
        return

    # Skip evaluation if response is empty or an error
    if not response or not query:
        return
    if response.startswith("Error:") or response.startswith("An error occurred"):
        return
    if "not properly initialized" in response.lower():
        return

    # Create cache key from query hash
    cache_key = hash(query + response[:200])

    with st.expander("🏛️ LLM-as-a-Judge Evaluation", expanded=False):
        # Check cache first
        if cache_key in st.session_state.judge_results_cache:
            result = st.session_state.judge_results_cache[cache_key]
        else:
            # Initialize judge if needed
            if st.session_state.judge is None:
                try:
                    config = load_config()
                    st.session_state.judge = LLMJudge(config)
                except Exception as e:
                    st.error(f"Failed to initialize LLM Judge: {e}")
                    return

            judge = st.session_state.judge

            with st.spinner("🔍 Evaluating response quality..."):
                try:
                    # Run evaluation
                    sources = [{"url": c} if c.startswith("http") else {"title": c} for c in citations]

                    # Run async evaluation using nest_asyncio to handle nested event loops
                    import nest_asyncio
                    nest_asyncio.apply()

                    loop = asyncio.get_event_loop()
                    result = loop.run_until_complete(
                        judge.evaluate_multi_perspective(query, response, sources)
                    )

                    # Cache the result
                    st.session_state.judge_results_cache[cache_key] = result
                except Exception as e:
                    st.error(f"Evaluation failed: {str(e)}")
                    st.caption("The LLM Judge may be unavailable. Check your API keys.")
                    return

        # Display combined score (cached or fresh)
        combined_score = result.get("combined_score", 0.0)
        score_color = "#10b981" if combined_score >= 0.7 else "#f59e0b" if combined_score >= 0.5 else "#ef4444"

        st.markdown(f"""
            <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 12px; margin-bottom: 1rem;">
                <div style="font-size: 2.5rem; font-weight: 700; color: {score_color};">{combined_score:.0%}</div>
                <div style="color: #64748b; font-weight: 500;">Combined Quality Score</div>
            </div>
        """, unsafe_allow_html=True)

        # Display perspective scores
        perspectives = result.get("perspectives", {})
        col1, col2 = st.columns(2)

        with col1:
            academic = perspectives.get("academic", {})
            academic_score = academic.get("overall_score", 0.0)
            st.markdown("##### 📚 Academic Rigor")
            st.progress(academic_score)
            st.caption(f"Score: {academic_score:.2f}")

        with col2:
            practical = perspectives.get("practical", {})
            practical_score = practical.get("overall_score", 0.0)
            st.markdown("##### 🔧 Practical Utility")
            st.progress(practical_score)
            st.caption(f"Score: {practical_score:.2f}")

        st.markdown("---")

        # Criterion-level breakdown
        st.markdown("##### Criterion Scores")
        
        # Add column headers
        header_name, header_acad, header_prac, header_avg = st.columns([3, 2, 2, 2])
        with header_name:
            st.markdown("**Criterion**")
        with header_acad:
            st.markdown("**📚 Academic**")
        with header_prac:
            st.markdown("**🔧 Practical**")
        with header_avg:
            st.markdown("**Average**")

        criteria_names = ["relevance", "evidence_quality", "factual_accuracy", "safety_compliance", "clarity"]
        criteria_icons = {"relevance": "🎯", "evidence_quality": "📊", "factual_accuracy": "✓", "safety_compliance": "🛡️", "clarity": "💡"}

        for criterion in criteria_names:
            academic_data = academic.get("criterion_scores", {}).get(criterion, {})
            practical_data = practical.get("criterion_scores", {}).get(criterion, {})

            academic_val = academic_data.get("score", 0.0)
            practical_val = practical_data.get("score", 0.0)
            avg_val = (academic_val + practical_val) / 2

            icon = criteria_icons.get(criterion, "•")

            col_name, col_acad, col_prac, col_avg = st.columns([3, 2, 2, 2])
            with col_name:
                st.markdown(f"{icon} **{criterion.replace('_', ' ').title()}**")
            with col_acad:
                st.caption(f"📚 {academic_val:.2f}")
            with col_prac:
                st.caption(f"🔧 {practical_val:.2f}")
            with col_avg:
                st.caption(f"Avg: {avg_val:.2f}")

        # Analysis summary
        analysis = result.get("analysis", {})
        agreements = analysis.get("agreements", [])
        disagreements = analysis.get("disagreements", [])

        if agreements or disagreements:
            st.markdown("---")
            st.markdown("##### Analysis")
            
            if agreements:
                agreement_names = [a.get("criterion", "").replace("_", " ").title() for a in agreements]
                st.success(f"✅ **Perspectives agree on {len(agreements)} criteria:** {', '.join(agreement_names)}")
            
            if disagreements:
                disagreement_details = []
                for d in disagreements:
                    name = d.get("criterion", "").replace("_", " ").title()
                    acad = d.get("academic", 0)
                    prac = d.get("practical", 0)
                    disagreement_details.append(f"{name} (📚{acad:.2f} vs 🔧{prac:.2f})")
                st.warning(f"⚠️ **Perspectives differ on {len(disagreements)} criteria:** {', '.join(disagreement_details)}")


def render_safety_log():
    """Render the session safety log."""
    if not st.session_state.show_safety_log:
        return

    st.markdown("### 🛡️ Safety Log")

    # Filter to only show events with violations (not passed checks)
    violation_events = [e for e in st.session_state.all_safety_events
                       if not e.get("safe", True) or e.get("violations", [])]

    if not violation_events:
        st.success("✅ No safety issues detected in this session.")
    else:
        for i, event in enumerate(violation_events, 1):
            event_type = event.get("type", "unknown")
            is_safe = event.get("safe", True)
            violations = event.get("violations", [])
            content_preview = event.get("content_preview", "")

            # Show as warning/error with details
            status = "⚠️ WARNING" if is_safe else "🚫 BLOCKED"
            with st.expander(f"{status} Event {i}: {event_type.upper()} - {len(violations)} issue(s)", expanded=False):
                st.markdown(f"**Content:** `{content_preview}`")

                if violations:
                    st.markdown("**Issues Detected:**")
                    for v in violations:
                        validator = v.get("validator", "unknown")
                        reason = v.get("reason", "No reason provided")
                        severity = v.get("severity", "unknown")
                        severity_color = "🔴" if severity == "high" else "🟠" if severity == "medium" else "🟡"
                        st.markdown(f"- {severity_color} **{validator}**: {reason}")


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Multi-Agent Research Assistant",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Apply custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    initialize_session_state()

    # Render sidebar
    render_sidebar()

    # Render header
    render_header()

    # Main content layout
    col_main, col_side = st.columns([3, 1])

    with col_main:
        # Search section
        st.markdown("### 🔍 Research Query")

        # Initialize query_input in session state if not present
        if "query_input" not in st.session_state:
            st.session_state.query_input = ""

        # Query input - key links to session state directly
        query = st.text_area(
            "Enter your research query:",
            height=100,
            placeholder="e.g., What are the latest developments in explainable AI?",
            key="query_input",
            label_visibility="collapsed"
        )

        # Search button
        if st.button("🔍 Search", type="primary", use_container_width=True):
            if query.strip():
                with st.spinner("Processing query through multi-agent system..."):
                    result = process_query(query)

                    st.session_state.history.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "query": query,
                        "result": result
                    })

                    # Store latest result for display after rerun
                    st.session_state.latest_result = result

                # Rerun to update sidebar statistics
                st.rerun()
            else:
                st.warning("Please enter a research query.")

        # Display the latest result if available
        if hasattr(st.session_state, 'latest_result') and st.session_state.latest_result:
            st.markdown("---")
            render_response(st.session_state.latest_result)
            # Clear after displaying to prevent showing on next rerun without query
            # st.session_state.latest_result = None  # Keep it to persist display

        # Display history
        if st.session_state.history:
            with st.expander(f"📜 Query History ({len(st.session_state.history)})", expanded=False):
                for i, item in enumerate(reversed(st.session_state.history), 1):
                    timestamp = item.get("timestamp", "")
                    q = item.get("query", "")
                    st.markdown(f"**{i}.** `{timestamp}` — {q[:80]}...")

        # Safety log
        if st.session_state.show_safety_log:
            st.markdown("---")
            render_safety_log()

    with col_side:
        render_example_queries()

        st.markdown("---")

        st.markdown("##### How It Works")
        st.markdown("""
        <div style="font-size: 0.85rem; color: #64748b; line-height: 1.6;">
            <p>🎯 <strong>Planner</strong> breaks down your query</p>
            <p>🔎 <strong>Researcher</strong> gathers evidence</p>
            <p>✍️ <strong>Writer</strong> synthesizes findings</p>
            <p>📋 <strong>Critic</strong> verifies quality</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
