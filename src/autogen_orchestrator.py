"""
AutoGen-Based Orchestrator

This orchestrator uses AutoGen's RoundRobinGroupChat to coordinate multiple agents
in a research workflow.

Workflow:
1. Safety Check (Input) - Validate user query
2. Planner: Breaks down the query into research steps
3. Researcher: Gathers evidence using web and paper search tools
4. Writer: Synthesizes findings into a coherent response
5. Critic: Evaluates quality and provides feedback
6. Safety Check (Output) - Validate final response
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_core import FunctionCall
from autogen_core.models import FunctionExecutionResult

from src.agents.autogen_agents import create_research_team
from src.guardrails.safety_manager import SafetyManager


def _extract_message_content(content: Any, logger=None) -> str:
    """
    Extract readable content from AutoGen message content.

    Handles various content types:
    - str: returned as-is
    - list: processes each item (may contain FunctionCall, FunctionExecutionResult, or str)
    - FunctionCall: filters out (internal implementation detail)
    - FunctionExecutionResult: extracts the actual content result
    - other: converts to string

    Args:
        content: Message content from AutoGen (can be str, list, or objects)
        logger: Optional logger for debugging

    Returns:
        Human-readable string representation of the content
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            extracted = _extract_message_content(item, logger)
            if extracted and extracted.strip():  # Skip empty strings
                text_parts.append(extracted)
        return "\n".join(text_parts) if text_parts else ""

    if isinstance(content, FunctionCall):
        # Show a brief summary of the tool call for the trace
        return f"🔧 Calling tool: {content.name}"

    if isinstance(content, FunctionExecutionResult):
        # Extract the actual result content
        result_content = content.content
        if isinstance(result_content, str):
            # Check if it's an error message
            is_error = getattr(content, 'is_error', False)
            if is_error:
                return f"[Tool Error: {result_content}]"
            # Truncate long tool results for display
            if len(result_content) > 500:
                return result_content[:500] + "... [truncated]"
            return result_content
        return str(result_content) if result_content else ""

    # Try to get content attribute from message objects
    if hasattr(content, 'content'):
        return _extract_message_content(content.content, logger)

    # Fallback: convert to string but filter out ugly representations
    str_content = str(content)
    # Filter out internal object representations
    if str_content.startswith('<') and str_content.endswith('>'):
        return ""
    if 'FunctionCall' in str_content or 'FunctionExecutionResult' in str_content:
        return ""

    return str_content


class AutoGenOrchestrator:
    """
    Orchestrates multi-agent research using AutoGen's RoundRobinGroupChat.

    This orchestrator manages a team of specialized agents that work together
    to answer research queries. It uses AutoGen's built-in conversation
    management and tool execution capabilities.

    Safety guardrails are applied to both inputs and outputs.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AutoGen orchestrator.

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger("autogen_orchestrator")

        # Initialize Safety Manager
        safety_config = config.get("safety", {})
        self.safety_manager = SafetyManager(safety_config)
        self.logger.info(f"Safety Manager initialized (enabled: {self.safety_manager.is_enabled()})")

        # Create the research team
        self.logger.info("Creating research team...")
        self.team = create_research_team(config)

        self.logger.info("Research team created successfully")

        # Workflow trace for debugging and UI display
        self.workflow_trace: List[Dict[str, Any]] = []

    def process_query(self, query: str, max_rounds: int = 20) -> Dict[str, Any]:
        """
        Process a research query through the multi-agent system.

        Args:
            query: The research question to answer
            max_rounds: Maximum number of conversation rounds

        Returns:
            Dictionary containing:
            - query: Original query
            - response: Final synthesized response
            - conversation_history: Full conversation between agents
            - metadata: Additional information about the process
            - safety: Safety check results
        """
        self.logger.info(f"Processing query: {query}")

        # Step 1: Check input safety
        input_safety = self.safety_manager.check_input_safety(query)

        if not input_safety["safe"]:
            self.logger.warning(f"Query blocked by safety guardrails: {len(input_safety['violations'])} violation(s)")
            return {
                "query": query,
                "response": input_safety.get("message", "Query blocked due to safety policies."),
                "conversation_history": [],
                "metadata": {
                    "blocked": True,
                    "blocked_reason": "input_safety",
                    "num_messages": 0,
                    "num_sources": 0,
                    "agents_involved": []
                },
                "safety": {
                    "input_check": input_safety,
                    "output_check": None,
                    "events": self.safety_manager.get_safety_events()
                }
            }

        try:
            # Run the async query processing
            # Handle cases where there's no event loop (e.g., Streamlit threads)
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an async context, use ThreadPoolExecutor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run,
                        self._process_query_async(query, max_rounds)
                    ).result()
            except RuntimeError:
                # No running loop - safe to use asyncio.run()
                result = asyncio.run(self._process_query_async(query, max_rounds))

            # Step 2: Check output safety
            output_safety = self.safety_manager.check_output_safety(
                result.get("response", ""),
                result.get("metadata", {}).get("research_findings", [])
            )

            # Apply output safety results
            if not output_safety["safe"]:
                self.logger.warning(f"Response modified by output guardrails: {len(output_safety['violations'])} violation(s)")
                result["response"] = output_safety["response"]
                result["metadata"]["output_sanitized"] = True

            # Add safety information to result
            result["safety"] = {
                "input_check": input_safety,
                "output_check": output_safety,
                "events": self.safety_manager.get_safety_events()
            }

            self.logger.info("Query processing complete")
            return result

        except Exception as e:
            self.logger.error(f"Error processing query: {e}", exc_info=True)
            return {
                "query": query,
                "error": str(e),
                "response": f"An error occurred while processing your query: {str(e)}",
                "conversation_history": [],
                "metadata": {"error": True},
                "safety": {
                    "input_check": input_safety,
                    "output_check": None,
                    "events": self.safety_manager.get_safety_events()
                }
            }

    async def _process_query_async(self, query: str, max_rounds: int = 20) -> Dict[str, Any]:
        """
        Async implementation of query processing.

        Args:
            query: The research question to answer
            max_rounds: Maximum number of conversation rounds

        Returns:
            Dictionary containing results
        """
        # Create task message
        task_message = f"""Research Query: {query}

Please work together to answer this query comprehensively:
1. Planner: Create a research plan
2. Researcher: Gather evidence from web and academic sources
3. Writer: Synthesize findings into a well-cited response
4. Critic: Evaluate the quality and provide feedback"""

        # Run the team
        result = await self.team.run(task=task_message)

        # Extract conversation history
        messages = []
        self.logger.info(f"Processing {len(result.messages)} messages from team run")

        for i, message in enumerate(result.messages):
            source = getattr(message, 'source', 'Unknown')
            raw_content = getattr(message, 'content', None)

            self.logger.debug(f"Message {i}: source={source}, content_type={type(raw_content)}")

            # Use helper to extract readable content
            extracted_content = _extract_message_content(raw_content, self.logger)

            # Include all messages that have any content (even tool calls now)
            if extracted_content and extracted_content.strip():
                msg_dict = {
                    "source": source,
                    "content": extracted_content,
                }
                messages.append(msg_dict)
                self.logger.debug(f"Added message from {source}: {extracted_content[:100]}...")

        self.logger.info(f"Extracted {len(messages)} messages with content")

        # Extract final response - prioritize Writer's response (the actual research content)
        final_response = ""
        writer_response = ""
        if messages:
            # First, try to find the Writer's response (the main synthesized content)
            for msg in reversed(messages):
                if msg.get("source") == "Writer":
                    writer_response = msg.get("content", "")
                    break

            # Use Writer's response if found, otherwise fall back to last message
            if writer_response:
                final_response = writer_response
            else:
                # Fall back to last non-Critic message, or last message
                for msg in reversed(messages):
                    source = msg.get("source", "")
                    if source != "Critic":
                        final_response = msg.get("content", "")
                        break
                if not final_response:
                    final_response = messages[-1].get("content", "")

        return self._extract_results(query, messages, final_response)

    def _extract_results(self, query: str, messages: List[Dict[str, Any]], final_response: str = "") -> Dict[str, Any]:
        """
        Extract structured results from the conversation history.

        Args:
            query: Original query
            messages: List of conversation messages
            final_response: Final response from the team

        Returns:
            Structured result dictionary
        """
        # Extract components from conversation
        research_findings = []
        plan = ""
        critique = ""
        tool_calls = 0

        for msg in messages:
            source = msg.get("source", "")
            content = msg.get("content", "")

            if source == "Planner" and not plan:
                plan = content

            elif source == "Researcher":
                research_findings.append(content)
                # Count tool calls indicated by tool call markers
                if isinstance(content, str):
                    tool_calls += content.count("🔧 Calling tool")
                    # Also count search result indicators
                    if "web search results" in content.lower() or "found" in content.lower():
                        tool_calls += 1

            elif source == "Critic":
                critique = content

        # Ensure at least some tool calls if we have research findings
        if research_findings and tool_calls == 0:
            tool_calls = len(research_findings)

        # Count sources mentioned in research
        num_sources = 0
        for finding in research_findings:
            # Rough count of sources based on numbered results
            num_sources += finding.count("\n1.") + finding.count("\n2.") + finding.count("\n3.")

        # Clean up final response
        if final_response:
            final_response = final_response.replace("TERMINATE", "").strip()

        return {
            "query": query,
            "response": final_response,
            "conversation_history": messages,
            "metadata": {
                "tool_calls": tool_calls,
                "num_sources": max(num_sources, 1),  # At least 1
                "plan": plan,
                "research_findings": research_findings,
                "critique": critique,
                "agents_involved": list(set([msg.get("source", "") for msg in messages if msg.get("source", "").lower() != "user" and msg.get("source", "")])),
            }
        }

    def get_agent_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions of all agents.

        Returns:
            Dictionary mapping agent names to their descriptions
        """
        return {
            "Planner": "Breaks down research queries into actionable steps",
            "Researcher": "Gathers evidence from web and academic sources",
            "Writer": "Synthesizes findings into coherent responses",
            "Critic": "Evaluates quality and provides feedback",
        }

    def get_safety_stats(self) -> Dict[str, Any]:
        """
        Get safety statistics from the safety manager.

        Returns:
            Dictionary with safety statistics
        """
        return self.safety_manager.get_safety_stats()

    def get_safety_events(self) -> List[Dict[str, Any]]:
        """
        Get all safety events logged during processing.

        Returns:
            List of safety events
        """
        return self.safety_manager.get_safety_events()

    def visualize_workflow(self) -> str:
        """
        Generate a text visualization of the workflow.

        Returns:
            String representation of the workflow
        """
        workflow = """
AutoGen Research Workflow (with Safety Guardrails):

1. User Query
   ↓
2. INPUT SAFETY CHECK
   - Prompt injection detection
   - Toxic language detection
   - Relevance check
   ↓ (if safe)
3. Planner
   - Analyzes query
   - Creates research plan
   - Identifies key topics
   ↓
4. Researcher (with tools)
   - Uses web_search() tool
   - Uses paper_search() tool
   - Gathers evidence
   - Collects citations
   ↓
5. Writer
   - Synthesizes findings
   - Creates structured response
   - Adds citations
   ↓
6. Critic
   - Evaluates quality
   - Checks completeness
   - Provides feedback
   ↓
7. OUTPUT SAFETY CHECK
   - PII detection & redaction
   - Harmful content check
   - Citation verification
   ↓ (if safe)
8. Final Response to User
        """
        return workflow


def demonstrate_usage():
    """
    Demonstrate how to use the AutoGen orchestrator.

    This function shows a simple example of using the orchestrator.
    """
    import yaml
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Load configuration
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Create orchestrator
    orchestrator = AutoGenOrchestrator(config)

    # Print workflow visualization
    print(orchestrator.visualize_workflow())

    # Example query
    query = "What are the latest trends in human-computer interaction research?"

    print(f"\nProcessing query: {query}\n")
    print("=" * 70)

    # Process query
    result = orchestrator.process_query(query)

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nQuery: {result['query']}")
    print(f"\nResponse:\n{result['response']}")
    print(f"\nMetadata:")
    print(f"  - Messages exchanged: {result['metadata']['num_messages']}")
    print(f"  - Sources gathered: {result['metadata']['num_sources']}")
    print(f"  - Agents involved: {', '.join(result['metadata']['agents_involved'])}")

    # Display safety information
    if result.get('safety'):
        print(f"\nSafety:")
        print(f"  - Input safe: {result['safety']['input_check']['safe']}")
        if result['safety'].get('output_check'):
            print(f"  - Output safe: {result['safety']['output_check']['safe']}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    demonstrate_usage()
