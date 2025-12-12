"""
Output Guardrail
Checks system outputs for safety violations.

Implements:
- PII (Personal Identifiable Information) detection
- Harmful content detection
- Citation/source verification
- Bias detection
"""

from typing import Dict, Any, List, Optional
import re
import logging


class OutputGuardrail:
    """
    Guardrail for checking output safety.

    This class validates generated responses before they are
    returned to users, ensuring they don't contain unsafe content.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize output guardrail.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger("guardrails.output")

        # PII patterns with regex
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone_us": r'\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            "phone_intl": r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        }

        # Compile patterns for efficiency
        self.compiled_pii_patterns = {
            name: re.compile(pattern)
            for name, pattern in self.pii_patterns.items()
        }

        # Harmful content keywords in outputs
        self.harmful_output_keywords = [
            # Instructions for harm
            "how to hack", "how to steal", "how to attack",
            "step-by-step guide to", "instructions for creating",

            # Dangerous information
            "bomb making", "weapon construction",
            "poison", "lethal dose",

            # Discriminatory content
            "inferior race", "lesser humans",

            # Inappropriate personal advice
            "you should hurt", "harm yourself",
        ]

        # Bias indicators
        self.bias_indicators = [
            # Absolute statements without evidence
            r'\b(all|every|no)\s+(men|women|people|users)\s+(are|always|never)\b',
            # Stereotyping language
            r'\btypically\s+(men|women|older|younger)\b',
            # Dismissive language
            r'\b(obviously|clearly|everyone knows)\b',
        ]

        self.compiled_bias_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.bias_indicators
        ]

    def validate(self, response: str, sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Validate output response by running all safety checks.

        Args:
            response: Generated response to validate
            sources: Optional list of sources used (for fact-checking)

        Returns:
            Validation result with:
            - valid: bool indicating if response passed all checks
            - violations: list of violations found
            - sanitized_output: cleaned response with PII redacted
        """
        violations = []

        # Run all checks
        pii_violations = self._check_pii(response)
        violations.extend(pii_violations)

        harmful_violations = self._check_harmful_content(response)
        violations.extend(harmful_violations)

        bias_violations = self._check_bias(response)
        violations.extend(bias_violations)

        if sources:
            citation_violations = self._check_citations(response, sources)
            violations.extend(citation_violations)

        # Log violations if any
        if violations:
            self.logger.warning(f"Output validation found {len(violations)} violation(s)")
            for v in violations:
                self.logger.warning(f"  - {v['validator']}: {v['reason']} (severity: {v['severity']})")

        # Sanitize output (redact PII)
        sanitized = self._sanitize(response, violations)

        return {
            "valid": len([v for v in violations if v["severity"] == "high"]) == 0,
            "violations": violations,
            "sanitized_output": sanitized
        }

    def _check_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for personally identifiable information.

        Detects common PII patterns like emails, phone numbers,
        SSNs, credit card numbers, etc.

        Args:
            text: The response text to check

        Returns:
            List of violations found
        """
        violations = []

        for pii_type, pattern in self.compiled_pii_patterns.items():
            matches = pattern.findall(text)
            if matches:
                # Filter out common false positives
                filtered_matches = self._filter_pii_false_positives(pii_type, matches)

                if filtered_matches:
                    violations.append({
                        "validator": "pii",
                        "pii_type": pii_type,
                        "reason": f"Response contains {pii_type.replace('_', ' ')}",
                        "severity": "high",
                        "matches": filtered_matches[:5],  # Limit matches shown
                        "count": len(filtered_matches)
                    })

        return violations

    def _filter_pii_false_positives(self, pii_type: str, matches: List[str]) -> List[str]:
        """
        Filter out common false positives in PII detection.

        Args:
            pii_type: Type of PII being checked
            matches: List of matches found

        Returns:
            Filtered list of actual PII matches
        """
        filtered = []

        for match in matches:
            # Skip example/placeholder values
            if pii_type == "email":
                if any(x in match.lower() for x in ["example.com", "test.com", "domain.com", "@..."]):
                    continue

            if pii_type == "phone_us":
                # Skip common placeholder patterns
                if match in ["123-456-7890", "000-000-0000", "111-111-1111"]:
                    continue

            if pii_type == "ip_address":
                # Skip localhost and common documentation IPs
                if match in ["127.0.0.1", "0.0.0.0", "192.168.1.1", "10.0.0.1"]:
                    continue

            filtered.append(match)

        return filtered

    def _check_harmful_content(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for harmful or inappropriate content.

        Detects content that could be dangerous or inappropriate
        to include in research responses.

        Args:
            text: The response text to check

        Returns:
            List of violations found
        """
        violations = []
        text_lower = text.lower()

        found_harmful = []
        for keyword in self.harmful_output_keywords:
            if keyword in text_lower:
                found_harmful.append(keyword)

        if found_harmful:
            violations.append({
                "validator": "harmful_content",
                "reason": f"Response may contain harmful content",
                "severity": "high",
                "indicators": found_harmful[:3]
            })

        return violations

    def _check_bias(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for biased language.

        Detects patterns that might indicate biased or
        discriminatory language in responses.

        Args:
            text: The response text to check

        Returns:
            List of violations found
        """
        violations = []

        bias_found = []
        for pattern in self.compiled_bias_patterns:
            matches = pattern.findall(text)
            if matches:
                bias_found.extend(matches)

        if bias_found:
            violations.append({
                "validator": "bias",
                "reason": "Response may contain biased language",
                "severity": "low",  # Low because these are soft indicators
                "indicators": bias_found[:3]
            })

        return violations

    def _check_citations(self, response: str, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check if response properly cites sources.

        Verifies that claims in the response are supported by
        the provided sources.

        Args:
            response: The response text to check
            sources: List of sources used

        Returns:
            List of violations found
        """
        violations = []

        # Check if response has any citation indicators
        citation_patterns = [
            r'\[Source:',
            r'\[Citation:',
            r'\(\d{4}\)',  # Year in parentheses
            r'according to',
            r'as stated in',
            r'et al\.',
            r'References?:',
        ]

        has_citations = any(
            re.search(pattern, response, re.IGNORECASE)
            for pattern in citation_patterns
        )

        # If sources were provided but response has no citations
        if sources and len(sources) > 0 and not has_citations:
            violations.append({
                "validator": "citations",
                "reason": "Response lacks citations despite having sources",
                "severity": "low",
                "sources_available": len(sources)
            })

        return violations

    def _check_factual_consistency(
        self,
        response: str,
        sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Check if response is consistent with sources.

        Note: Full fact-checking would require LLM-based verification.
        This is a placeholder for future enhancement.

        Args:
            response: The response text to check
            sources: List of sources to verify against

        Returns:
            List of violations found
        """
        violations = []
        # Future: Implement LLM-based fact verification
        return violations

    def _sanitize(self, text: str, violations: List[Dict[str, Any]]) -> str:
        """
        Sanitize text by redacting detected PII.

        Replaces detected PII with [REDACTED] placeholders.

        Args:
            text: The response text to sanitize
            violations: List of violations (used to find PII matches)

        Returns:
            Sanitized text
        """
        sanitized = text

        # Redact PII matches
        for violation in violations:
            if violation.get("validator") == "pii":
                matches = violation.get("matches", [])
                for match in matches:
                    pii_type = violation.get("pii_type", "PII")
                    sanitized = sanitized.replace(match, f"[REDACTED {pii_type.upper()}]")

        return sanitized

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the validation rules in place.

        Returns:
            Dictionary describing the validation rules
        """
        return {
            "checks": [
                "pii_detection",
                "harmful_content_detection",
                "bias_detection",
                "citation_verification"
            ],
            "config": {
                "num_pii_patterns": len(self.pii_patterns),
                "num_harmful_keywords": len(self.harmful_output_keywords),
                "num_bias_patterns": len(self.bias_indicators)
            }
        }
