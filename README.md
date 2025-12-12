[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/r1tAQ0HC)
# Multi-Agent Research System - Assignment 3

A multi-agent system for deep research on HCI topics, featuring orchestrated agents, safety guardrails, and LLM-as-a-Judge evaluation.

## Overview

This is a fully implemented multi-agent research assistant system for HCI (Human-Computer Interaction) research. The system uses AutoGen framework with multiple specialized agents to:
- **Planner**: Break down research queries into actionable steps
- **Researcher**: Gather evidence from academic papers (Semantic Scholar) and web sources (Tavily)
- **Writer**: Synthesize findings into coherent, well-cited responses
- **Critic**: Evaluate quality and verify accuracy before finalizing
- **Safety Guardrails**: Protect against harmful inputs and outputs
- **LLM-as-a-Judge**: Multi-perspective evaluation with detailed metrics

## Project Structure

```
.
├── src/
│   ├── agents/
│   │   └── autogen_agents.py    # All 4 agents (Planner, Researcher, Writer, Critic)
│   ├── guardrails/
│   │   ├── safety_manager.py    # Main safety coordinator
│   │   ├── input_guardrail.py   # Input validation (prompt injection, toxic content)
│   │   └── output_guardrail.py  # Output validation (PII, harmful content, bias)
│   ├── tools/
│   │   ├── web_search.py        # Tavily/Brave web search
│   │   ├── paper_search.py      # Semantic Scholar academic search
│   │   └── citation_tool.py     # APA/MLA citation formatting
│   ├── evaluation/
│   │   ├── judge.py             # LLM-as-a-Judge (2 perspectives, 5 criteria)
│   │   └── evaluator.py         # Batch evaluation with error analysis
│   ├── ui/
│   │   ├── cli.py               # Command-line interface
│   │   └── streamlit_app.py     # Streamlit web interface
│   └── autogen_orchestrator.py  # Main orchestrator using AutoGen
├── data/
│   └── example_queries.json     # 10 diverse test queries
├── samples/                     # Sample outputs for demonstration
│   ├── sample_session.json      # Full agent session transcript
│   ├── sample_final_answer.md   # Synthesized response with citations
│   ├── sample_judge_output.json # LLM-as-a-Judge evaluation results
│   └── sample_guardrail_demo.json # Safety guardrail examples
├── logs/                        # Log files (created at runtime)
├── outputs/                     # Evaluation results (created at runtime)
├── config.yaml                  # System configuration
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── run_full_evaluation.py       # Script to run full evaluation
└── main.py                      # Main entry point
```

---

## 🎬 Demo & Sample Outputs

### End-to-End Demo (Single Command)

Run the complete multi-agent workflow from query to judge scoring:

**Option 1: Interactive Web UI (Recommended)**
```bash
# Start the Streamlit web interface
streamlit run src/ui/streamlit_app.py
```

**Option 2: Full Batch Evaluation**
```bash
# Run end-to-end evaluation on all 10 test queries
python run_full_evaluation.py
```

**Option 3: Command Line Interface**
```bash
# Single query via CLI
python main.py --query "What are the key principles of user-centered design?"
```

### Expected Output Flow

When running a query, the system executes this workflow:

1. **Input Safety Check** → Validates query for prompt injection, toxic content, relevance
2. **Planner Agent** → Creates research plan with actionable steps
3. **Researcher Agent** → Uses `web_search` and `paper_search` tools to gather sources
4. **Writer Agent** → Synthesizes findings with APA-style citations
5. **Critic Agent** → Evaluates quality and provides feedback
6. **Output Safety Check** → Scans response for PII, harmful content
7. **LLM-as-a-Judge** → Multi-perspective evaluation (Academic + Practical)

### Screenshots (Required for Documentation)

The following screenshots demonstrate the system:

| Screenshot | Description |
|------------|-------------|
| 1. **Main UI** | Streamlit home page with query input |
| 2. **Research Response** | Complete response with citations and metrics |
| 3. **Agent Processing Log** | Collapsed and expanded views of agent workflow |
| 4. **LLM-as-a-Judge Scores** | Evaluation results with both perspectives |
| 5. **Guardrail Block** | Example of blocked malicious query |
| 6. **Safety Log** | Safety events showing violations detected |

### Demo Query Used

The following query was used to demonstrate the complete workflow:

> **"What are the key principles of user-centered design in HCI?"**

This query triggers the full multi-agent pipeline: Planner creates a research strategy, Researcher gathers sources from web and academic papers, Writer synthesizes findings with APA citations, and Critic evaluates the response quality.

---

### Web Interface

![Streamlit Web UI](samples/demo_screenshot.png)

*The Streamlit home page where users enter research queries. The sidebar shows settings for agent traces, safety log, and LLM-as-a-Judge evaluation. Example queries are provided for quick testing.*

### Research Response with Metrics

![Response Example](samples/response_example.png)

*After processing the demo query, the system displays the synthesized response with:*
- *📚 **Sources**: Number of citations collected by the Researcher*
- *🔧 **Tool Calls**: Number of web/paper search API calls made*
- *👥 **Agents**: The 4 agents involved (Planner, Researcher, Writer, Critic)*

### Agent Processing Log

![Agent Traces - Collapsed](samples/agent_traces_1.png)

*The Agent Processing Log shows each step of the multi-agent workflow. Each agent's contribution is listed with a preview of their output. Users can click to expand any step for full details.*

![Agent Traces - Expanded](samples/agent_traces_expanded.png)

*Expanded view of the Researcher agent's output, showing the actual search results and sources gathered. This transparency allows users to verify the evidence used in the final response.*

### LLM-as-a-Judge Evaluation

![Judge Evaluation](samples/judge_evaluation.png)

*The LLM-as-a-Judge section evaluates the response quality from two perspectives:*
- *📚 **Academic Rigor** (0.88): Evaluates citation quality, evidence strength, and scholarly standards*
- *🔧 **Practical Utility** (0.88): Evaluates actionability, clarity, and real-world applicability*
- *Five criteria are scored: Relevance, Evidence Quality, Factual Accuracy, Safety Compliance, and Clarity*

### Safety Guardrails

The system detects and blocks various types of unsafe input:

#### Prompt Injection Detection

![Prompt Injection Blocked](samples/safety_injection_example.png)

*System detects and blocks prompt injection attempts ("Ignore all previous instructions...").*

![Prompt Injection Details](samples/safety_injection_example_expanded.png)

*Expanded safety log showing the specific violation detected and severity level.*

#### Off-Topic Query Blocking

![Guardrail Block](samples/guardrail_blocked.png)

*Example of a blocked off-topic query that is not related to HCI research.*

#### Safety Log

![Safety Log](samples/safety_log.png)

*Safety Log showing all detected violations with timestamps and policy categories.*

### Sample Artifacts (in `samples/` directory)

| File | Description |
|------|-------------|
| [`sample_session.json`](samples/sample_session.json) | Complete agent workflow transcript showing Planner → Researcher → Writer → Critic collaboration |
| [`sample_final_answer.md`](samples/sample_final_answer.md) | Final synthesized response with APA citations and references section |
| [`sample_judge_output.json`](samples/sample_judge_output.json) | LLM-as-a-Judge results with scores from both Academic and Practical perspectives |
| [`sample_guardrail_demo.json`](samples/sample_guardrail_demo.json) | Examples of blocked queries, sanitized outputs, and policy categories |

### Test Queries Used

The following queries are used for evaluation (from `data/example_queries.json`):

1. **Explainable AI**: "What are the key principles of explainable AI for novice users?"
2. **AR Usability**: "How has AR usability evolved in the past 5 years?"
3. **AI Ethics**: "What are ethical considerations in using AI for education?"
4. **UX Measurement**: "Compare different approaches to measuring user experience in mobile applications"
5. **Conversational AI**: "What are the latest developments in conversational AI for healthcare?"
6. **Accessibility**: "How do design patterns for accessibility differ across web and mobile platforms?"
7. **Data Visualization**: "What are best practices for visualizing uncertainty in data displays?"
8. **Voice Interfaces**: "How can voice interfaces be designed for elderly users?"
9. **AI Prototyping**: "What are emerging trends in AI-driven prototyping tools?"
10. **Cross-Cultural Design**: "How do cultural factors influence mobile app design?"

### Guardrail Demonstration

The system blocks or sanitizes unsafe content. Examples from [`sample_guardrail_demo.json`](samples/sample_guardrail_demo.json):

| Scenario | Query Example | Result | Policy Triggered |
|----------|--------------|--------|------------------|
| **Prompt Injection** | "Ignore all previous instructions..." | ⛔ Blocked | `prompt_injection` (high severity) |
| **Harmful Content** | "How can I hack into..." | ⛔ Blocked | `toxic_language` (high severity) |
| **PII in Output** | Response contains email/phone | ✂️ Sanitized | `pii_detection` (redacted) |
| **Off-Topic** | "What is the best pizza recipe..." | ⛔ Blocked | `relevance` (low severity) |

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- `uv` package manager (recommended) or `pip`
- Virtual environment

### 2. Installation

#### Installing uv (Recommended)

`uv` is a fast Python package installer and resolver. Install it first:

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: Using pip
pip install uv
```

#### Setting up the Project

Clone the repository and navigate to the project directory:

```bash
cd is-492-assignment-3
```

**Option A: Using uv (Recommended - Much Faster)**

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate     # On Windows

# Install dependencies
uv pip install -r requirements.txt
```

**Option B: Using standard pip**

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate   # On macOS/Linux
# OR
venv\Scripts\activate      # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Security Setup (Important!)

**Before committing any code**, set up pre-commit hooks to prevent API key leaks:

```bash
# Quick setup - installs hooks and runs security checks
./scripts/install-hooks.sh

# Or manually
pre-commit install
```

This will automatically scan for hardcoded API keys and secrets before each commit. See `SECURITY_SETUP.md` for full details.

### 4. API Keys Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required: At least one LLM API
GROQ_API_KEY=your_groq_api_key_here
# OR
OPENAI_API_KEY=your_openai_api_key_here

# Recommended: At least one search API
TAVILY_API_KEY=your_tavily_api_key_here
# OR
BRAVE_API_KEY=your_brave_api_key_here

# Optional: For academic paper search
SEMANTIC_SCHOLAR_API_KEY=your_key_here
```

#### Getting API Keys

- **Groq** (Recommended for students): [https://console.groq.com](https://console.groq.com) - Free tier available
- **OpenAI**: [https://platform.openai.com](https://platform.openai.com) - Paid, requires credits
- **Tavily**: [https://www.tavily.com](https://www.tavily.com) - Student free quota available
- **Brave Search**: [https://brave.com/search/api](https://brave.com/search/api)
- **Semantic Scholar**: [https://www.semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) - Free tier available

### 5. Configuration

Edit `config.yaml` to customize your system:

- Choose your research topic
- **Configure agent prompts** (see below)
- Set model preferences (Groq vs OpenAI)
- Define safety policies
- Configure evaluation criteria

#### Customizing Agent Prompts

You can customize agent behavior by setting the `system_prompt` in `config.yaml`:

```yaml
agents:
  planner:
    system_prompt: |
      You are an expert research planner specializing in HCI.
      Focus on recent publications and seminal works.
      After creating the plan, say "PLAN COMPLETE".
```

**Important**: Custom prompts must include handoff signals:
- **Planner**: Must include `"PLAN COMPLETE"`
- **Researcher**: Must include `"RESEARCH COMPLETE"`  
- **Writer**: Must include `"DRAFT COMPLETE"`
- **Critic**: Must include `"APPROVED - RESEARCH COMPLETE"` or `"NEEDS REVISION"`

Leave `system_prompt: ""` (empty) to use the default prompts.

## Implementation Status ✅

All core components have been fully implemented:

### Agents (in `src/agents/autogen_agents.py`)
- ✅ **Planner Agent**: Breaks down research queries into actionable steps
- ✅ **Researcher Agent**: Gathers evidence using web_search and paper_search tools
- ✅ **Writer Agent**: Synthesizes findings with proper citations
- ✅ **Critic Agent**: Evaluates quality and provides feedback

### Tools (in `src/tools/`)
- ✅ **Web Search**: Tavily and Brave API integration
- ✅ **Paper Search**: Semantic Scholar API integration
- ✅ **Citation Tool**: APA and MLA formatting support

### Orchestration (in `src/autogen_orchestrator.py`)
- ✅ AutoGen RoundRobinGroupChat for agent coordination
- ✅ Workflow: Input Safety → Plan → Research → Write → Critique → Output Safety
- ✅ Error handling and graceful fallbacks

### Safety Guardrails (in `src/guardrails/`)
- ✅ **Input Guardrail**: Prompt injection detection (25+ patterns), toxic language, relevance check
- ✅ **Output Guardrail**: PII detection (6 patterns), harmful content, bias detection
- ✅ **Safety Manager**: Refuse/sanitize actions, event logging to file

### Evaluation (in `src/evaluation/`)
- ✅ **LLM-as-a-Judge**: 2 perspectives (Academic, Practical), 5 criteria with rubrics
- ✅ **System Evaluator**: Batch evaluation, error analysis, comprehensive reporting
- ✅ **Test Dataset**: 10 diverse queries across 10 HCI categories

### User Interfaces (in `src/ui/`)
- ✅ **CLI**: Interactive command-line with agent traces, citations, safety display
- ✅ **Streamlit Web UI**: Professional interface with history, settings, workflow display

---

## Reproducing Results

Follow these steps to reproduce the evaluation results reported in the write-up:

### Step 1: Environment Setup

```bash
# Clone and navigate to project
cd assignment-3-building-and-evaluating-mas-hari200698

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys:
# GROQ_API_KEY=your_groq_key_here
# TAVILY_API_KEY=your_tavily_key_here
# SEMANTIC_SCHOLAR_API_KEY=your_key_here (optional)
```

### Step 3: Run Full Evaluation

```bash
# Run the complete evaluation pipeline
python run_full_evaluation.py
```

This will:
1. Load 10 test queries from `data/example_queries.json`
2. Process each query through the multi-agent system
3. Evaluate responses using LLM-as-a-Judge (both perspectives)
4. Generate comprehensive report with error analysis

### Step 4: View Results

Evaluation outputs are saved to the `outputs/` directory:
- `outputs/evaluation_report_YYYYMMDD_HHMMSS.json` - Full JSON report
- `outputs/evaluation_report_YYYYMMDD_HHMMSS.txt` - Human-readable summary

The report includes:
- Overall scores (combined, academic, practical perspectives)
- Per-criterion scores (relevance, evidence quality, factual accuracy, safety, clarity)
- Category analysis and topic coverage
- Error analysis with patterns and recommendations
- Interpretation of strengths and weaknesses

### Alternative: Run Individual Components

```bash
# Run CLI interface
python main.py --mode cli

# Run web interface
python main.py --mode web
# OR
streamlit run src/ui/streamlit_app.py

# Run evaluation only
python main.py --mode evaluate
```

### Expected Output

A successful evaluation run will produce:
- **10 evaluated queries** across diverse HCI topics
- **Combined score**: 0.0-1.0 scale (higher is better)
- **Per-perspective breakdown**: Academic vs. Practical scores
- **Error analysis**: Any API failures, rate limits, or parsing issues

## Running the System

### Command Line Interface

```bash
python main.py --mode cli
```

### Web Interface

```bash
python main.py --mode web
# OR directly:
streamlit run src/ui/streamlit_app.py
```

### Running Evaluation

```bash
python main.py --mode evaluate
```

This will:
- Load test queries from `data/example_queries.json`
- Run each query through your system
- Evaluate outputs using LLM-as-a-Judge
- Generate report in `outputs/`

## Testing

Run tests (if you create them):

```bash
pytest tests/
```

## Resources

### Documentation
- [uv Documentation](https://docs.astral.sh/uv/) - Fast Python package installer
- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Guardrails AI](https://docs.guardrailsai.com/)
- [NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/)
- [Tavily API](https://docs.tavily.com/)
- [Semantic Scholar API](https://api.semanticscholar.org/)
