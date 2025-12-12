"""
Command Line Interface
Interactive CLI for the multi-agent research system.

Features:
- Interactive query input
- Agent trace display
- Citation/source display
- Safety event communication (blocked/sanitized)
- Command support (help, quit, clear, stats)
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any, List
import yaml
import logging
from datetime import datetime
from dotenv import load_dotenv

from src.autogen_orchestrator import AutoGenOrchestrator

# Load environment variables
load_dotenv()


class CLI:
    """
    Command-line interface for the research assistant.

    Displays:
    - Agent traces showing workflow
    - Citations and sources
    - Safety events (blocked/sanitized queries)
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize CLI.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Setup logging
        self._setup_logging()

        # Initialize AutoGen orchestrator
        try:
            self.orchestrator = AutoGenOrchestrator(self.config)
            self.logger = logging.getLogger("cli")
            self.logger.info("AutoGen orchestrator initialized successfully")
        except Exception as e:
            self.logger = logging.getLogger("cli")
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            raise

        self.running = True
        self.query_count = 0
        self.safety_events_count = 0
        self.blocked_queries_count = 0
        self.all_safety_events: List[Dict[str, Any]] = []

    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.get("logging", {})
        log_level = log_config.get("level", "INFO")
        log_format = log_config.get(
            "format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format
        )

    def run(self):
        """Main CLI loop (synchronous)."""
        self._print_welcome()

        while self.running:
            try:
                # Get user input
                query = input("\n📝 Enter your research query (or 'help' for commands): ").strip()

                if not query:
                    continue

                # Handle commands
                if query.lower() in ['quit', 'exit', 'q']:
                    self._print_goodbye()
                    break
                elif query.lower() == 'help':
                    self._print_help()
                    continue
                elif query.lower() == 'clear':
                    self._clear_screen()
                    continue
                elif query.lower() == 'stats':
                    self._print_stats()
                    continue
                elif query.lower() == 'safety':
                    self._print_safety_log()
                    continue

                # Process query
                print("\n" + "=" * 70)
                print("🔄 Processing your query through agents...")
                print("=" * 70)

                try:
                    # Process through orchestrator
                    result = self.orchestrator.process_query(query)
                    self.query_count += 1

                    # Track safety events
                    safety_info = result.get("safety", {})
                    events = safety_info.get("events", [])
                    if events:
                        self.all_safety_events.extend(events)
                        self.safety_events_count = len(self.all_safety_events)

                    # Check if blocked
                    input_check = safety_info.get("input_check", {})
                    if input_check and not input_check.get("safe", True):
                        self.blocked_queries_count += 1

                    # Display result
                    self._display_result(result)

                except Exception as e:
                    print(f"\n❌ Error processing query: {e}")
                    logging.exception("Error processing query")

            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted by user.")
                self._print_goodbye()
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logging.exception("Error in CLI loop")

    def _print_welcome(self):
        """Print welcome message."""
        print("\n" + "=" * 70)
        print(f"  🤖 {self.config['system']['name']}")
        print(f"  📚 Topic: {self.config['system']['topic']}")
        print("=" * 70)
        print("\n✨ Welcome! Ask me anything about your research topic.")
        print("📋 Type 'help' for available commands, or 'quit' to exit.")
        print("🛡️ Safety guardrails are active to ensure appropriate content.\n")

    def _print_help(self):
        """Print help message."""
        print("\n" + "-" * 50)
        print("📋 AVAILABLE COMMANDS")
        print("-" * 50)
        print("  help    - Show this help message")
        print("  clear   - Clear the screen")
        print("  stats   - Show system statistics")
        print("  safety  - Show safety event log")
        print("  quit    - Exit the application")
        print("-" * 50)
        print("\n💡 Or enter a research query to get started!")

    def _print_goodbye(self):
        """Print goodbye message."""
        print("\n" + "=" * 70)
        print("👋 Thank you for using the Multi-Agent Research Assistant!")
        print(f"   📊 Queries processed: {self.query_count}")
        print(f"   🛡️ Safety events: {self.safety_events_count}")
        print("=" * 70 + "\n")

    def _clear_screen(self):
        """Clear the terminal screen."""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')

    def _print_stats(self):
        """Print system statistics."""
        print("\n" + "-" * 50)
        print("📊 SYSTEM STATISTICS")
        print("-" * 50)
        print(f"  • Queries processed:  {self.query_count}")
        print(f"  • Queries blocked:    {self.blocked_queries_count}")
        print(f"  • Safety events:      {self.safety_events_count}")
        print("-" * 50)
        print(f"  • System:  {self.config.get('system', {}).get('name', 'Unknown')}")
        print(f"  • Topic:   {self.config.get('system', {}).get('topic', 'Unknown')}")
        print(f"  • Model:   {self.config.get('models', {}).get('default', {}).get('name', 'Unknown')}")
        print("-" * 50)

    def _print_safety_log(self):
        """Print all safety events."""
        print("\n" + "-" * 50)
        print("🛡️ SAFETY EVENT LOG")
        print("-" * 50)

        if not self.all_safety_events:
            print("  ✅ No safety events recorded in this session.")
        else:
            for i, event in enumerate(self.all_safety_events, 1):
                event_type = event.get("type", "unknown")
                timestamp = event.get("timestamp", "")
                details = event.get("details", {})

                # Determine icon
                if event_type == "input_blocked":
                    icon = "⛔"
                elif event_type == "output_sanitized":
                    icon = "✂️"
                elif "validated" in event_type:
                    icon = "✅"
                else:
                    icon = "ℹ️"

                print(f"\n  {icon} Event {i}: {event_type}")
                if timestamp:
                    print(f"     Time: {timestamp}")

                violations = details.get("violations", [])
                if violations:
                    for v in violations:
                        print(f"     • {v.get('category', 'N/A')}: {v.get('reason', 'Unknown')}")

        print("-" * 50)

    def _display_result(self, result: Dict[str, Any]):
        """Display query result with formatting and safety info."""

        # Get safety information
        safety_info = result.get("safety", {})
        input_check = safety_info.get("input_check", {})
        output_check = safety_info.get("output_check", {})

        # Check if query was blocked
        if input_check and not input_check.get("safe", True):
            self._display_blocked_query(result, input_check)
            return

        # Display main response
        print("\n" + "=" * 70)
        print("📄 RESPONSE")
        print("=" * 70)

        # Check for errors
        if "error" in result and result.get("metadata", {}).get("error"):
            print(f"\n❌ Error: {result['error']}")
            return

        # Display response
        response = result.get("response", "")
        print(f"\n{response}\n")

        # Check if output was sanitized
        if output_check and not output_check.get("safe", True):
            self._display_sanitization_warning(output_check)

        # Display citations
        citations = self._extract_citations(result)
        if citations:
            print("\n" + "-" * 70)
            print("📚 CITATIONS & SOURCES")
            print("-" * 70)
            for i, citation in enumerate(citations, 1):
                print(f"  [{i}] {citation}")

        # Display metadata
        metadata = result.get("metadata", {})
        if metadata:
            print("\n" + "-" * 70)
            print("📊 METADATA")
            print("-" * 70)
            print(f"  • Messages exchanged: {metadata.get('num_messages', 0)}")
            print(f"  • Sources gathered:   {metadata.get('num_sources', 0)}")
            agents = metadata.get('agents_involved', [])
            print(f"  • Agents involved:    {', '.join(agents) if agents else 'N/A'}")

        # Display agent traces
        if self._should_show_traces():
            self._display_agent_traces(result.get("conversation_history", []))

        # Display safety summary
        self._display_safety_summary(safety_info)

        print("=" * 70 + "\n")

    def _display_blocked_query(self, result: Dict[str, Any], input_check: Dict[str, Any]):
        """Display blocked query message."""
        print("\n" + "=" * 70)
        print("⛔ QUERY BLOCKED BY SAFETY GUARDRAILS")
        print("=" * 70)

        violations = input_check.get("violations", [])
        print("\n🚫 Your query was blocked for the following reasons:\n")

        for i, v in enumerate(violations, 1):
            category = v.get("category", "safety").upper()
            reason = v.get("reason", "Unknown violation")
            print(f"  {i}. [{category}] {reason}")

        print("\n" + "-" * 70)
        print("💡 Please rephrase your query to avoid:")
        print("   • Harmful or offensive content")
        print("   • Prompt injection attempts")
        print("   • Off-topic requests")
        print("-" * 70)

        # Show the response message
        response = result.get("response", "Query blocked due to safety policies.")
        print(f"\n📝 {response}")

        print("=" * 70 + "\n")

    def _display_sanitization_warning(self, output_check: Dict[str, Any]):
        """Display warning about sanitized output."""
        print("\n" + "-" * 70)
        print("⚠️ OUTPUT SANITIZED BY SAFETY GUARDRAILS")
        print("-" * 70)

        violations = output_check.get("violations", [])
        print("The response was modified for the following reasons:\n")

        for v in violations:
            category = v.get("category", "safety").upper()
            reason = v.get("reason", "Unknown modification")
            print(f"  ✂️ [{category}] {reason}")

        print("-" * 70)

    def _display_safety_summary(self, safety_info: Dict[str, Any]):
        """Display a brief safety summary."""
        events = safety_info.get("events", [])

        if events:
            print("\n" + "-" * 70)
            print("🛡️ SAFETY CHECK SUMMARY")
            print("-" * 70)

            for event in events:
                event_type = event.get("type", "unknown")

                if event_type == "input_validated":
                    print("  ✅ Input: Validated")
                elif event_type == "input_blocked":
                    print("  ⛔ Input: Blocked")
                elif event_type == "output_validated":
                    print("  ✅ Output: Validated")
                elif event_type == "output_sanitized":
                    print("  ✂️ Output: Sanitized")
                else:
                    print(f"  ℹ️ {event_type}")

    def _extract_citations(self, result: Dict[str, Any]) -> list:
        """Extract citations/URLs from conversation history."""
        citations = []
        import re

        for msg in result.get("conversation_history", []):
            content = msg.get("content", "")

            # Handle case where content might be a list or other type
            if isinstance(content, list):
                content = " ".join(str(item) for item in content)
            elif not isinstance(content, str):
                content = str(content)

            # Find URLs
            urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)

            # Find [Source: ...] patterns
            sources = re.findall(r'\[Source: ([^\]]+)\]', content)

            for url in urls:
                if url not in citations:
                    citations.append(url)

            for source in sources:
                if source not in citations:
                    citations.append(source)

        return citations[:15]  # Limit to 15

    def _should_show_traces(self) -> bool:
        """Check if agent traces should be displayed."""
        return self.config.get("ui", {}).get("verbose", False)

    def _display_agent_traces(self, conversation_history: list):
        """Display agent workflow traces."""
        if not conversation_history:
            return

        print("\n" + "-" * 70)
        print("🔍 AGENT WORKFLOW TRACES")
        print("-" * 70)

        # Agent color/emoji mapping
        agent_icons = {
            "Planner": "🟦",
            "Researcher": "🟩",
            "Writer": "🟨",
            "Critic": "🟪",
            "user": "⬜"
        }

        for i, msg in enumerate(conversation_history, 1):
            agent = msg.get("source", "Unknown")
            content = msg.get("content", "")

            icon = agent_icons.get(agent, "⬛")

            # Truncate long content
            preview = content[:200] + "..." if len(content) > 200 else content
            preview = preview.replace("\n", " ")

            print(f"\n  Step {i}: {icon} {agent}")
            print(f"  {'-' * 40}")
            print(f"  {preview}")


def main():
    """Main entry point for CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-Agent Research Assistant CLI"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    # Run CLI (synchronous - process_query handles its own async internally)
    cli = CLI(config_path=args.config)
    cli.run()


if __name__ == "__main__":
    main()
