"""
Input Guardrail
Checks user inputs for safety violations.

Implements:
- Prompt injection detection
- Toxic/harmful language detection
- Off-topic query detection
- Query length validation
"""

from typing import Dict, Any, List
import re
import logging


class InputGuardrail:
    """
    Guardrail for checking input safety.
    
    This class implements multiple validation checks to ensure
    user inputs are safe and appropriate for the research system.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize input guardrail.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger("guardrails.input")
        
        # Configuration options
        self.min_query_length = config.get("min_query_length", 5)
        self.max_query_length = config.get("max_query_length", 2000)
        self.research_topic = config.get("research_topic", "human-computer interaction")
        
        # Prompt injection patterns to detect
        self.injection_patterns = [
            # Direct instruction override attempts
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
            r"disregard\s+(all\s+)?(previous|prior|above)",
            r"forget\s+(everything|all|previous)",
            r"override\s+(system|previous|safety)",
            r"bypass\s+(safety|security|filter)",
            
            # Role manipulation attempts
            r"you\s+are\s+now\s+(a|an)",
            r"pretend\s+(to\s+be|you\s+are)",
            r"act\s+as\s+(if|a|an)",
            r"roleplay\s+as",
            r"from\s+now\s+on\s+you",
            
            # System prompt extraction
            r"(show|reveal|display|print|output)\s+(me\s+)?(your|the|system)\s+(prompt|instructions)",
            r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions|rules)",
            
            # Jailbreak keywords
            r"jailbreak",
            r"dan\s+mode",
            r"developer\s+mode",
            r"sudo",
            r"admin\s+mode",
            
            # Delimiter injection
            r"<\|.*?\|>",  # Special tokens
            r"\[INST\]",
            r"\[/INST\]",
            r"<<SYS>>",
            r"<</SYS>>",
        ]
        
        # Compile patterns for efficiency
        self.compiled_injection_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns
        ]
        
        # Toxic/harmful keywords (expanded list)
        self.harmful_keywords = [
            # Violence
            "kill", "murder", "attack", "hurt", "harm", "destroy",
            "weapon", "bomb", "explosive", "assassinate",
            
            # Hacking/illegal
            "hack", "exploit", "crack", "steal", "phishing",
            "malware", "virus", "ransomware", "ddos",
            
            # Hate speech indicators
            "hate", "racist", "sexist", "discriminate",
            
            # Self-harm (be careful with research context)
            "suicide method", "how to hurt myself",
        ]
        
        # Research-relevant keywords to determine if query is on-topic
        self.research_keywords = [
            # HCI-related
            "hci", "human-computer", "human computer", "interaction",
            "user experience", "ux", "usability", "interface",
            "accessibility", "design", "user interface", "ui",
            "ergonomic", "cognitive", "perception", "attention",
            
            # Research-related
            "research", "study", "paper", "literature", "review",
            "methodology", "experiment", "survey", "analysis",
            "theory", "framework", "model", "evaluation",
            "finding", "result", "conclusion", "abstract",
            
            # Technology-related
            "software", "application", "app", "website", "system",
            "technology", "computer", "digital", "mobile", "web",
            "ai", "machine learning", "data", "algorithm",
            
            # General academic
            "what is", "how does", "explain", "define", "compare",
            "difference", "relationship", "impact", "effect",
            "trend", "future", "best practice", "guideline",
        ]

    def validate(self, query: str) -> Dict[str, Any]:
        """
        Validate input query by running all safety checks.

        Args:
            query: User input to validate

        Returns:
            Validation result with:
            - valid: bool indicating if query passed all checks
            - violations: list of violations found
            - sanitized_input: potentially cleaned query
        """
        violations = []
        
        # Run all checks
        length_violations = self._check_length(query)
        violations.extend(length_violations)
        
        injection_violations = self._check_prompt_injection(query)
        violations.extend(injection_violations)
        
        toxic_violations = self._check_toxic_language(query)
        violations.extend(toxic_violations)
        
        relevance_violations = self._check_relevance(query)
        violations.extend(relevance_violations)
        
        # Log violations if any
        if violations:
            self.logger.warning(f"Input validation found {len(violations)} violation(s)")
            for v in violations:
                self.logger.warning(f"  - {v['validator']}: {v['reason']} (severity: {v['severity']})")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "sanitized_input": query  # Could be modified in future
        }

    def _check_length(self, text: str) -> List[Dict[str, Any]]:
        """
        Check if query length is within acceptable bounds.
        
        Args:
            text: The query text to check
            
        Returns:
            List of violations (empty if valid)
        """
        violations = []
        
        if len(text.strip()) < self.min_query_length:
            violations.append({
                "validator": "length",
                "reason": f"Query too short (minimum {self.min_query_length} characters)",
                "severity": "low"
            })

        if len(text) > self.max_query_length:
            violations.append({
                "validator": "length",
                "reason": f"Query too long (maximum {self.max_query_length} characters)",
                "severity": "medium"
            })
            
        return violations

    def _check_prompt_injection(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for prompt injection attempts.
        
        Detects patterns commonly used to manipulate LLM behavior,
        such as instruction override attempts or jailbreak keywords.

        Args:
            text: The query text to check
            
        Returns:
            List of violations found
        """
        violations = []
        
        for i, pattern in enumerate(self.compiled_injection_patterns):
            matches = pattern.findall(text)
            if matches:
                # Get the original pattern for logging
                original_pattern = self.injection_patterns[i]
                violations.append({
                    "validator": "prompt_injection",
                    "reason": f"Potential prompt injection detected",
                    "severity": "high",
                    "pattern_matched": original_pattern[:50] + "..." if len(original_pattern) > 50 else original_pattern
                })
                # Only report one injection violation to avoid spam
                break
        
        return violations

    def _check_toxic_language(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for toxic/harmful language.
        
        Detects keywords associated with harmful content.
        Note: This is a simple keyword-based check. For production,
        consider using ML-based toxicity detection.

        Args:
            text: The query text to check
            
        Returns:
            List of violations found
        """
        violations = []
        text_lower = text.lower()
        
        found_keywords = []
        for keyword in self.harmful_keywords:
            # Check for whole word matches to reduce false positives
            # e.g., "attack" in "heart attack research" might be okay
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                found_keywords.append(keyword)
        
        if found_keywords:
            # Check if it's in a research context
            is_research_context = any(
                rk in text_lower for rk in ["research", "study", "paper", "literature", "academic"]
            )
            
            if is_research_context and len(found_keywords) == 1:
                # Single keyword in research context - log but don't block
                self.logger.info(f"Potentially harmful keyword '{found_keywords[0]}' found in research context - allowing")
            else:
                violations.append({
                    "validator": "toxic_language",
                    "reason": f"Query contains potentially harmful keywords: {', '.join(found_keywords[:3])}",
                    "severity": "high" if len(found_keywords) > 1 else "medium",
                    "keywords_found": found_keywords[:5]  # Limit to 5
                })

        return violations

    def _check_relevance(self, query: str) -> List[Dict[str, Any]]:
        """
        Check if query is relevant to the system's purpose.
        
        The system is designed for research queries. This check
        ensures queries are related to the configured topic.

        Args:
            query: The query text to check
            
        Returns:
            List of violations found
        """
        violations = []
        query_lower = query.lower()
        
        # Count how many research-relevant keywords are present
        # Use word boundary matching to avoid false positives (e.g., "ai" in "Champaign")
        relevance_score = 0
        for keyword in self.research_keywords:
            # Use word boundary regex for single words, substring for phrases
            if ' ' in keyword:
                # Multi-word phrase: use substring match
                if keyword in query_lower:
                    relevance_score += 1
            else:
                # Single word: use word boundary match
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query_lower):
                    relevance_score += 1
        
        # If no research keywords found at all, it might be off-topic
        if relevance_score == 0:
            # Flag as off-topic - the query doesn't contain any research-relevant terms
            violations.append({
                "validator": "relevance",
                "reason": "Query appears to be off-topic for research assistance",
                "severity": "medium"  # Raised from low to medium
            })
        
        return violations

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the validation rules in place.
        
        Returns:
            Dictionary describing the validation rules
        """
        return {
            "checks": [
                "length_validation",
                "prompt_injection_detection", 
                "toxic_language_detection",
                "relevance_check"
            ],
            "config": {
                "min_query_length": self.min_query_length,
                "max_query_length": self.max_query_length,
                "num_injection_patterns": len(self.injection_patterns),
                "num_harmful_keywords": len(self.harmful_keywords),
                "num_research_keywords": len(self.research_keywords)
            }
        }
