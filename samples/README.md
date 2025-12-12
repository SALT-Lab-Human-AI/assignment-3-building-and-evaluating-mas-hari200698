# Sample Outputs

This directory contains sample outputs demonstrating the multi-agent research system's capabilities.

## Files

### 1. `sample_session.json`
Complete agent workflow transcript showing:
- Input safety check results
- Each agent's contribution (Planner → Researcher → Writer → Critic)
- Tool calls made by the Researcher
- Final synthesized response
- Output safety check results
- Metadata (message count, sources, processing time)

**Query used:** "What are the key principles of user-centered design in HCI?"

### 2. `sample_final_answer.md`
The final synthesized response formatted as Markdown with:
- Overview section
- Numbered core principles with explanations
- Inline citations `[Source: Author, Year]`
- Separate references section
- Metadata table

### 3. `sample_judge_output.json`
LLM-as-a-Judge evaluation results including:
- **Raw judge prompts** used for evaluation
- **Academic perspective** scores (focus on rigor, citations, accuracy)
- **Practical perspective** scores (focus on usability, clarity, applicability)
- Per-criterion scores (relevance, evidence_quality, factual_accuracy, safety_compliance, clarity)
- Agreements and disagreements between perspectives
- Interpretation with strengths and areas for improvement

### 4. `sample_guardrail_demo.json`
Demonstration of safety guardrails with examples of:
- **Blocked queries**: Prompt injection, harmful content, off-topic requests
- **Sanitized outputs**: PII detection and redaction
- **Policy categories**: Description of each safety policy and its action

## How to Generate New Samples

Run the system with your own queries:

```bash
# Interactive CLI
python main.py --mode cli

# Web interface
streamlit run src/ui/streamlit_app.py

# Full evaluation (generates outputs/)
python run_full_evaluation.py
```

The evaluation outputs are saved to `outputs/` directory (gitignored by default).
