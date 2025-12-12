"""
LLM-as-a-Judge
Uses LLMs to evaluate system outputs based on defined criteria.

Implements TWO INDEPENDENT JUDGING PERSPECTIVES (Assignment Requirement):
1. Academic Perspective - Focus on research rigor, citations, accuracy
2. Practical Perspective - Focus on usefulness, clarity, actionability

Example usage:
    judge = LLMJudge(config)

    # Single perspective evaluation
    result = await judge.evaluate(query, response, sources)

    # Multi-perspective evaluation (recommended)
    result = await judge.evaluate_multi_perspective(query, response, sources)
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import json
import os

# Try to import both clients
try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMJudge:
    """
    LLM-based judge for evaluating system responses.

    Supports two independent judging perspectives as required by assignment:
    1. Academic Perspective - Evaluates research quality
    2. Practical Perspective - Evaluates practical utility
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM judge.

        Args:
            config: Configuration dictionary (from config.yaml)
        """
        self.config = config
        self.logger = logging.getLogger("evaluation.judge")

        # Load judge model configuration from config.yaml (models.judge)
        self.model_config = config.get("models", {}).get("judge", {})
        self.provider = self.model_config.get("provider", "groq")

        # Load evaluation criteria from config.yaml (evaluation.criteria)
        self.criteria = config.get("evaluation", {}).get("criteria", [])

        # Initialize client based on provider
        self.client = None
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            if api_key and OpenAI:
                self.client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
            else:
                self.logger.warning("OPENAI_API_KEY not found or openai not installed")
        else:  # groq
            api_key = os.getenv("GROQ_API_KEY")
            if api_key and Groq:
                self.client = Groq(api_key=api_key)
            else:
                self.logger.warning("GROQ_API_KEY not found or groq not installed")

        # Define the two judging perspectives (Assignment Requirement: ≥2 independent judging prompts)
        self.perspectives = {
            "academic": {
                "name": "Academic Rigor Perspective",
                "description": "Evaluates from a researcher's viewpoint focusing on scholarly quality",
                "system_prompt": """You are an academic reviewer evaluating research responses.
Focus on: citation quality, evidence strength, factual accuracy, methodological soundness,
and scholarly rigor. Be critical but fair. Provide scores based on academic standards."""
            },
            "practical": {
                "name": "Practical Utility Perspective",
                "description": "Evaluates from a practitioner's viewpoint focusing on real-world usefulness",
                "system_prompt": """You are a UX practitioner evaluating research responses for practical use.
Focus on: actionable insights, clarity, real-world applicability, completeness,
and whether the information helps solve actual problems. Be practical and results-oriented."""
            }
        }

        # Detailed scoring rubrics for each criterion
        self.scoring_rubrics = {
            "relevance": {
                "0.0-0.2": "Response is completely off-topic or unrelated to the query",
                "0.2-0.4": "Response partially addresses the query but misses key aspects",
                "0.4-0.6": "Response addresses the main query but lacks depth or completeness",
                "0.6-0.8": "Response thoroughly addresses the query with good coverage",
                "0.8-1.0": "Response perfectly addresses all aspects of the query comprehensively"
            },
            "evidence_quality": {
                "0.0-0.2": "No citations or evidence provided",
                "0.2-0.4": "Few citations, sources are unreliable or irrelevant",
                "0.4-0.6": "Some citations present but quality is mixed",
                "0.6-0.8": "Good citations from credible sources, well-integrated",
                "0.8-1.0": "Excellent citations from authoritative sources, properly attributed"
            },
            "factual_accuracy": {
                "0.0-0.2": "Contains multiple factual errors or misinformation",
                "0.2-0.4": "Contains some factual errors or unverified claims",
                "0.4-0.6": "Mostly accurate but some claims need verification",
                "0.6-0.8": "Factually accurate with minor uncertainties",
                "0.8-1.0": "Highly accurate, all claims are well-supported"
            },
            "safety_compliance": {
                "0.0-0.2": "Contains harmful, biased, or inappropriate content",
                "0.2-0.4": "Contains potentially problematic content",
                "0.4-0.6": "Generally safe but may have minor issues",
                "0.6-0.8": "Safe and appropriate content throughout",
                "0.8-1.0": "Exemplary safety compliance, no concerns"
            },
            "clarity": {
                "0.0-0.2": "Incomprehensible or extremely poorly organized",
                "0.2-0.4": "Difficult to understand, poor structure",
                "0.4-0.6": "Understandable but could be clearer",
                "0.6-0.8": "Clear and well-organized",
                "0.8-1.0": "Exceptionally clear, logical, and well-structured"
            }
        }

        self.logger.info(f"LLMJudge initialized with {len(self.criteria)} criteria and {len(self.perspectives)} perspectives")

    async def evaluate(
        self,
        query: str,
        response: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        ground_truth: Optional[str] = None,
        perspective: str = "academic"
    ) -> Dict[str, Any]:
        """
        Evaluate a response using a single perspective.

        Args:
            query: The original query
            response: The system's response
            sources: Sources used in the response
            ground_truth: Optional ground truth/expected response
            perspective: Which perspective to use ("academic" or "practical")

        Returns:
            Dictionary with scores for each criterion and overall score
        """
        self.logger.info(f"Evaluating response with {perspective} perspective")

        results = {
            "query": query,
            "perspective": perspective,
            "overall_score": 0.0,
            "criterion_scores": {},
            "feedback": [],
        }

        total_weight = sum(c.get("weight", 1.0) for c in self.criteria)
        weighted_score = 0.0

        # Evaluate each criterion
        for criterion in self.criteria:
            criterion_name = criterion.get("name", "unknown")
            weight = criterion.get("weight", 1.0)

            self.logger.info(f"Evaluating criterion: {criterion_name}")

            score = await self._judge_criterion(
                criterion=criterion,
                query=query,
                response=response,
                sources=sources,
                ground_truth=ground_truth,
                perspective=perspective
            )

            results["criterion_scores"][criterion_name] = score
            weighted_score += score.get("score", 0.0) * weight

        # Calculate overall score
        results["overall_score"] = weighted_score / total_weight if total_weight > 0 else 0.0

        return results

    async def evaluate_multi_perspective(
        self,
        query: str,
        response: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a response using BOTH perspectives (Assignment Requirement).

        This provides a more comprehensive evaluation by considering
        both academic rigor and practical utility.

        Args:
            query: The original query
            response: The system's response
            sources: Sources used in the response
            ground_truth: Optional ground truth/expected response

        Returns:
            Dictionary with scores from both perspectives and combined score
        """
        self.logger.info("Evaluating response with multiple perspectives")

        # Evaluate from both perspectives
        academic_result = await self.evaluate(
            query, response, sources, ground_truth, perspective="academic"
        )

        practical_result = await self.evaluate(
            query, response, sources, ground_truth, perspective="practical"
        )

        # Combine results
        combined_score = (
            academic_result["overall_score"] * 0.5 +
            practical_result["overall_score"] * 0.5
        )

        # Identify agreements and disagreements between perspectives
        agreements = []
        disagreements = []

        for criterion in self.criteria:
            name = criterion.get("name", "unknown")
            academic_score = academic_result["criterion_scores"].get(name, {}).get("score", 0)
            practical_score = practical_result["criterion_scores"].get(name, {}).get("score", 0)

            diff = abs(academic_score - practical_score)
            if diff < 0.2:
                agreements.append({
                    "criterion": name,
                    "academic": academic_score,
                    "practical": practical_score
                })
            else:
                disagreements.append({
                    "criterion": name,
                    "academic": academic_score,
                    "practical": practical_score,
                    "difference": diff
                })

        return {
            "query": query,
            "combined_score": combined_score,
            "perspectives": {
                "academic": academic_result,
                "practical": practical_result
            },
            "analysis": {
                "agreements": agreements,
                "disagreements": disagreements,
                "perspective_correlation": 1.0 - (len(disagreements) / max(len(self.criteria), 1))
            }
        }

    async def _judge_criterion(
        self,
        criterion: Dict[str, Any],
        query: str,
        response: str,
        sources: Optional[List[Dict[str, Any]]],
        ground_truth: Optional[str],
        perspective: str = "academic"
    ) -> Dict[str, Any]:
        """
        Judge a single criterion from a specific perspective.

        Args:
            criterion: Criterion configuration
            query: Original query
            response: System response
            sources: Sources used
            ground_truth: Optional ground truth
            perspective: Judging perspective

        Returns:
            Score and feedback for this criterion
        """
        criterion_name = criterion.get("name", "unknown")
        description = criterion.get("description", "")

        # Create judge prompt with perspective and detailed rubric
        prompt = self._create_judge_prompt(
            criterion_name=criterion_name,
            description=description,
            query=query,
            response=response,
            sources=sources,
            ground_truth=ground_truth,
            perspective=perspective
        )

        # Call LLM API to get judgment
        try:
            judgment = await self._call_judge_llm(prompt, perspective)
            score_value, reasoning = self._parse_judgment(judgment)

            score = {
                "score": score_value,
                "reasoning": reasoning,
                "criterion": criterion_name,
                "perspective": perspective
            }
        except Exception as e:
            self.logger.error(f"Error judging criterion {criterion_name}: {e}")
            score = {
                "score": 0.5,  # Default to middle score on error
                "reasoning": f"Error during evaluation: {str(e)}",
                "criterion": criterion_name,
                "perspective": perspective
            }

        return score

    def _create_judge_prompt(
        self,
        criterion_name: str,
        description: str,
        query: str,
        response: str,
        sources: Optional[List[Dict[str, Any]]],
        ground_truth: Optional[str],
        perspective: str = "academic"
    ) -> str:
        """
        Create a detailed prompt for the judge LLM with scoring rubric.
        """
        # Get rubric for this criterion
        rubric = self.scoring_rubrics.get(criterion_name, {})
        rubric_text = "\n".join([f"  {range_}: {desc}" for range_, desc in rubric.items()])

        prompt = f"""Evaluate the following response for the criterion: **{criterion_name}**

## Criterion Description
{description}

## Scoring Rubric (0.0 to 1.0 scale)
{rubric_text if rubric_text else "Use your judgment to score from 0.0 (worst) to 1.0 (best)"}

## Query
{query}

## Response to Evaluate
{response}
"""

        if sources and len(sources) > 0:
            source_summary = f"\n## Sources Provided\n{len(sources)} sources were used in generating this response."
            prompt += source_summary

        if ground_truth:
            prompt += f"\n## Expected/Ground Truth Response\n{ground_truth}"

        prompt += """

## Instructions
1. Carefully read the response and evaluate it against the criterion
2. Use the scoring rubric to determine an appropriate score
3. Provide detailed reasoning for your score
4. Be consistent and fair in your evaluation

## Required Output Format (JSON)
Respond ONLY with valid JSON in this exact format:
```json
{
    "score": <float between 0.0 and 1.0>,
    "reasoning": "<detailed explanation of your score, referencing specific parts of the response>"
}
```
"""

        return prompt

    async def _call_judge_llm(self, prompt: str, perspective: str = "academic") -> str:
        """
        Call LLM API to get judgment with perspective-specific system prompt.
        """
        if not self.client:
            raise ValueError(f"LLM client not initialized. Check API keys for provider: {self.provider}")

        try:
            # Load model settings from config.yaml (models.judge)
            model_name = self.model_config.get("name", "gpt-4o-mini" if self.provider == "openai" else "llama-3.1-8b-instant")
            temperature = self.model_config.get("temperature", 0.3)
            max_tokens = self.model_config.get("max_tokens", 1024)

            # Get perspective-specific system prompt
            perspective_config = self.perspectives.get(perspective, self.perspectives["academic"])
            system_prompt = perspective_config["system_prompt"]

            self.logger.debug(f"Calling {self.provider} API with model: {model_name}, perspective: {perspective}")

            # Call LLM API (works for both OpenAI and Groq since they have compatible APIs)
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt + "\n\nAlways respond with valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response = chat_completion.choices[0].message.content
            self.logger.debug(f"Received response: {response[:100]}...")

            return response

        except Exception as e:
            self.logger.error(f"Error calling Groq API: {e}")
            raise

    def _parse_judgment(self, judgment: str) -> Tuple[float, str]:
        """
        Parse LLM judgment response into score and reasoning.
        """
        try:
            # Clean up the response - remove markdown code blocks if present
            judgment_clean = judgment.strip()
            if judgment_clean.startswith("```json"):
                judgment_clean = judgment_clean[7:]
            elif judgment_clean.startswith("```"):
                judgment_clean = judgment_clean[3:]
            if judgment_clean.endswith("```"):
                judgment_clean = judgment_clean[:-3]
            judgment_clean = judgment_clean.strip()

            # Parse JSON
            result = json.loads(judgment_clean)
            score = float(result.get("score", 0.5))
            reasoning = result.get("reasoning", "No reasoning provided")

            # Validate score is in range [0, 1]
            score = max(0.0, min(1.0, score))

            return score, reasoning

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.logger.error(f"Raw judgment: {judgment[:200]}")
            # Try to extract score from text
            return self._extract_score_from_text(judgment)
        except Exception as e:
            self.logger.error(f"Error parsing judgment: {e}")
            return 0.5, f"Error parsing judgment: {str(e)}"

    def _extract_score_from_text(self, text: str) -> Tuple[float, str]:
        """
        Fallback: Try to extract a score from unstructured text.
        """
        import re

        # Look for patterns like "score: 0.7" or "0.8/1.0"
        patterns = [
            r'"score":\s*([\d.]+)',
            r'score[:\s]+(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*/\s*1\.0',
            r'(\d+\.?\d*)\s*out of\s*1',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    if score > 1.0:
                        score = score / 10.0  # Convert 7 to 0.7
                    score = max(0.0, min(1.0, score))
                    return score, f"Extracted from text: {text[:100]}..."
                except ValueError:
                    continue

        # Default fallback
        return 0.5, f"Could not parse judgment, defaulting to 0.5. Raw: {text[:100]}..."

    def get_perspectives(self) -> Dict[str, Dict[str, str]]:
        """Get information about available judging perspectives."""
        return self.perspectives

    def get_rubrics(self) -> Dict[str, Dict[str, str]]:
        """Get the scoring rubrics for each criterion."""
        return self.scoring_rubrics


async def example_single_perspective():
    """
    Example 1: Single perspective evaluation
    """
    import yaml
    from dotenv import load_dotenv

    load_dotenv()

    # Load config
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)

    judge = LLMJudge(config)

    print("=" * 70)
    print("EXAMPLE 1: Single Perspective Evaluation (Academic)")
    print("=" * 70)

    query = "What are the key principles of user-centered design?"
    response = """User-centered design (UCD) is based on several key principles:

1. **Early focus on users** - Understanding user needs from the start (Norman & Draper, 1986).
2. **Iterative design** - Continuous refinement based on user feedback.
3. **Empirical measurement** - Testing with real users to validate designs.
4. **Integrated design** - All aspects of usability evolve together.

These principles ensure that products meet actual user needs rather than assumed requirements."""

    print(f"\nQuery: {query}")
    print(f"\nResponse: {response[:200]}...")

    result = await judge.evaluate(
        query=query,
        response=response,
        perspective="academic"
    )

    print(f"\n\nOverall Score: {result['overall_score']:.3f}")
    print("\nCriterion Scores:")
    for criterion, score_data in result['criterion_scores'].items():
        print(f"  {criterion}: {score_data['score']:.3f}")
        print(f"    Reasoning: {score_data['reasoning'][:80]}...")


async def example_multi_perspective():
    """
    Example 2: Multi-perspective evaluation (Assignment Requirement)
    """
    import yaml
    from dotenv import load_dotenv

    load_dotenv()

    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)

    judge = LLMJudge(config)

    print("\n" + "=" * 70)
    print("EXAMPLE 2: Multi-Perspective Evaluation")
    print("=" * 70)

    query = "What are best practices for mobile app accessibility?"
    response = """Mobile app accessibility best practices include:

1. **Screen reader compatibility** - Ensure all UI elements have proper labels.
2. **Touch target size** - Minimum 44x44 pixels for interactive elements (WCAG).
3. **Color contrast** - 4.5:1 ratio for normal text, 3:1 for large text.
4. **Keyboard navigation** - Support for external keyboards.
5. **Captions and alternatives** - Provide text alternatives for media.

Following these practices helps ensure apps are usable by people with disabilities."""

    print(f"\nQuery: {query}")
    print(f"\nResponse: {response[:200]}...")

    result = await judge.evaluate_multi_perspective(
        query=query,
        response=response
    )

    print(f"\n\nCombined Score: {result['combined_score']:.3f}")
    print(f"\nAcademic Perspective Score: {result['perspectives']['academic']['overall_score']:.3f}")
    print(f"Practical Perspective Score: {result['perspectives']['practical']['overall_score']:.3f}")

    print(f"\nPerspective Agreement: {result['analysis']['perspective_correlation']:.1%}")

    if result['analysis']['disagreements']:
        print("\nDisagreements between perspectives:")
        for d in result['analysis']['disagreements']:
            print(f"  {d['criterion']}: Academic={d['academic']:.2f}, Practical={d['practical']:.2f}")


if __name__ == "__main__":
    import asyncio

    print("Running LLMJudge Examples\n")
    print("These examples demonstrate the two judging perspectives")
    print("as required by the assignment.\n")

    # Run examples
    asyncio.run(example_single_perspective())
    asyncio.run(example_multi_perspective())
