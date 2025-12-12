"""
Safety Manager
Coordinates safety guardrails and logs safety events.

This module provides a unified interface for managing both
input and output safety checks in the multi-agent system.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json
import os

from src.guardrails.input_guardrail import InputGuardrail
from src.guardrails.output_guardrail import OutputGuardrail


class SafetyManager:
    """
    Manages safety guardrails for the multi-agent system.
    
    Coordinates input and output guardrails, logs safety events,
    and handles violations according to configured policies.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize safety manager.

        Args:
            config: Safety configuration from config.yaml
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.log_events = config.get("log_events", True)
        self.logger = logging.getLogger("safety")

        # Safety event log
        self.safety_events: List[Dict[str, Any]] = []

        # Prohibited categories
        self.prohibited_categories = config.get("prohibited_categories", [
            "harmful_content",
            "personal_attacks",
            "misinformation",
            "off_topic_queries"
        ])

        # Violation response strategy
        self.on_violation = config.get("on_violation", {
            "action": "refuse",
            "message": "I cannot process this request due to safety policies."
        })
        
        # Safety log file path
        self.safety_log_file = config.get("safety_log_file")
        
        # Initialize guardrails
        self.input_guardrail = InputGuardrail(config)
        self.output_guardrail = OutputGuardrail(config)
        
        self.logger.info("SafetyManager initialized with input and output guardrails")

    def check_input_safety(self, query: str) -> Dict[str, Any]:
        """
        Check if input query is safe to process.

        Args:
            query: User query to check

        Returns:
            Dictionary with:
            - safe: bool indicating if query is safe
            - violations: list of violations found
            - sanitized_query: potentially cleaned query
            - message: refusal message if unsafe
        """
        if not self.enabled:
            return {"safe": True, "violations": [], "sanitized_query": query}

        # Use InputGuardrail to validate
        result = self.input_guardrail.validate(query)
        
        is_safe = result["valid"]
        violations = result["violations"]
        
        # Log safety event if violations found
        if violations and self.log_events:
            self._log_safety_event("input", query, violations, is_safe)

        response = {
            "safe": is_safe,
            "violations": violations,
            "sanitized_query": result.get("sanitized_input", query)
        }
        
        # Add refusal message if not safe
        if not is_safe:
            action = self.on_violation.get("action", "refuse")
            if action == "refuse":
                response["message"] = self._get_refusal_message(violations)
            elif action == "redirect":
                response["message"] = "Your query has been flagged. Please rephrase your question."
        
        return response

    def check_output_safety(self, response: str, sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Check if output response is safe to return.

        Args:
            response: Generated response to check
            sources: Optional list of sources used

        Returns:
            Dictionary with:
            - safe: bool indicating if response is safe
            - violations: list of violations found
            - response: sanitized or original response
        """
        if not self.enabled:
            return {"safe": True, "violations": [], "response": response}

        # Use OutputGuardrail to validate
        result = self.output_guardrail.validate(response, sources)
        
        is_safe = result["valid"]
        violations = result["violations"]
        
        # Log safety event if violations found
        if violations and self.log_events:
            self._log_safety_event("output", response[:500], violations, is_safe)

        output = {
            "safe": is_safe,
            "violations": violations,
            "response": result.get("sanitized_output", response)
        }

        # Apply configured violation response
        if not is_safe:
            action = self.on_violation.get("action", "refuse")
            if action == "sanitize":
                # Use sanitized output (PII redacted)
                output["response"] = result.get("sanitized_output", response)
            elif action == "refuse":
                output["response"] = self.on_violation.get(
                    "message",
                    "I cannot provide this response due to safety policies."
                )

        return output

    def _get_refusal_message(self, violations: List[Dict[str, Any]]) -> str:
        """
        Generate an appropriate refusal message based on violations.
        
        Args:
            violations: List of violations found
            
        Returns:
            Human-readable refusal message
        """
        if not violations:
            return self.on_violation.get("message", "Request cannot be processed.")
        
        # Check for specific violation types
        violation_types = [v.get("validator") for v in violations]
        
        if "prompt_injection" in violation_types:
            return "Your request appears to contain prompt manipulation attempts. Please ask a legitimate research question."
        
        if "toxic_language" in violation_types:
            return "Your request contains content that cannot be processed. Please rephrase your question appropriately."
        
        if "length" in violation_types:
            return "Your request is either too short or too long. Please provide a clear research question."
        
        if "relevance" in violation_types:
            return "This system is designed for research queries. Please ask a question related to research or academic topics."
        
        return self.on_violation.get("message", "I cannot process this request due to safety policies.")

    def _log_safety_event(
        self,
        event_type: str,
        content: str,
        violations: List[Dict[str, Any]],
        is_safe: bool
    ):
        """
        Log a safety event.

        Args:
            event_type: "input" or "output"
            content: The content that was checked
            violations: List of violations found
            is_safe: Whether content passed safety checks
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "safe": is_safe,
            "violations": violations,
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
            "violation_count": len(violations),
            "severity_summary": self._get_severity_summary(violations)
        }

        self.safety_events.append(event)
        
        # Log to standard logger
        if is_safe:
            self.logger.info(f"Safety check passed: {event_type}")
        else:
            self.logger.warning(
                f"Safety event: {event_type} - {len(violations)} violation(s) - "
                f"severities: {event['severity_summary']}"
            )

        # Write to safety log file if configured
        if self.safety_log_file and self.log_events:
            self._write_to_log_file(event)

    def _get_severity_summary(self, violations: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Summarize violations by severity.
        
        Args:
            violations: List of violations
            
        Returns:
            Dictionary with count per severity level
        """
        summary = {"high": 0, "medium": 0, "low": 0}
        for v in violations:
            severity = v.get("severity", "low")
            if severity in summary:
                summary[severity] += 1
        return summary

    def _write_to_log_file(self, event: Dict[str, Any]):
        """
        Write safety event to log file.
        
        Args:
            event: Safety event to log
        """
        try:
            # Ensure directory exists
            log_dir = os.path.dirname(self.safety_log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                
            with open(self.safety_log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write safety log: {e}")

    def get_safety_events(self) -> List[Dict[str, Any]]:
        """Get all logged safety events."""
        return self.safety_events

    def get_safety_stats(self) -> Dict[str, Any]:
        """
        Get statistics about safety events.

        Returns:
            Dictionary with safety statistics
        """
        total = len(self.safety_events)
        input_events = sum(1 for e in self.safety_events if e["type"] == "input")
        output_events = sum(1 for e in self.safety_events if e["type"] == "output")
        violations = sum(1 for e in self.safety_events if not e["safe"])
        
        # Count by severity
        high_severity = sum(
            e.get("severity_summary", {}).get("high", 0) 
            for e in self.safety_events
        )
        
        return {
            "total_events": total,
            "input_checks": input_events,
            "output_checks": output_events,
            "violations": violations,
            "violation_rate": violations / total if total > 0 else 0,
            "high_severity_count": high_severity,
            "events_logged": self.log_events
        }

    def clear_events(self):
        """Clear safety event log."""
        self.safety_events = []
        self.logger.info("Safety events cleared")

    def is_enabled(self) -> bool:
        """Check if safety manager is enabled."""
        return self.enabled
    
    def get_guardrail_summary(self) -> Dict[str, Any]:
        """
        Get summary of all guardrail configurations.
        
        Returns:
            Dictionary with guardrail summaries
        """
        return {
            "enabled": self.enabled,
            "input_guardrail": self.input_guardrail.get_validation_summary(),
            "output_guardrail": self.output_guardrail.get_validation_summary(),
            "on_violation": self.on_violation,
            "prohibited_categories": self.prohibited_categories
        }
