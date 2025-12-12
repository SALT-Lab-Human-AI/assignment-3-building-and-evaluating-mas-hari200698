"""
System Evaluator
Runs batch evaluations and generates comprehensive reports with error analysis.

Features:
- Multi-perspective evaluation (Academic + Practical)
- Error analysis and pattern identification
- Detailed reporting with interpretation
- Support for orchestrator integration

Example usage:
    evaluator = SystemEvaluator(config, orchestrator=my_orchestrator)
    report = await evaluator.evaluate_system("data/example_queries.json")
"""

from typing import Dict, Any, List, Optional
import json
import logging
from pathlib import Path
from datetime import datetime
import asyncio

from .judge import LLMJudge


class SystemEvaluator:
    """
    Evaluates the multi-agent system using test queries and LLM-as-a-Judge.

    Supports multi-perspective evaluation and comprehensive error analysis
    as required by the assignment.
    """

    def __init__(self, config: Dict[str, Any], orchestrator=None):
        """
        Initialize evaluator.

        Args:
            config: Configuration dictionary (from config.yaml)
            orchestrator: The orchestrator to evaluate
        """
        self.config = config
        self.orchestrator = orchestrator
        self.logger = logging.getLogger("evaluation.evaluator")

        # Load evaluation configuration
        eval_config = config.get("evaluation", {})
        self.enabled = eval_config.get("enabled", True)
        self.max_test_queries = eval_config.get("num_test_queries", None)
        self.use_multi_perspective = eval_config.get("use_multi_perspective", True)

        # Initialize judge
        self.judge = LLMJudge(config)

        # Evaluation results
        self.results: List[Dict[str, Any]] = []

        # Error tracking for analysis
        self.errors: List[Dict[str, Any]] = []

        self.logger.info(f"SystemEvaluator initialized (enabled={self.enabled}, multi_perspective={self.use_multi_perspective})")

    async def evaluate_system(
        self,
        test_queries_path: str = "data/example_queries.json",
        use_multi_perspective: bool = True
    ) -> Dict[str, Any]:
        """
        Run full system evaluation with multi-perspective support.

        Args:
            test_queries_path: Path to test queries JSON file
            use_multi_perspective: Whether to use both judging perspectives

        Returns:
            Comprehensive evaluation report with error analysis
        """
        if not self.enabled:
            self.logger.warning("Evaluation is disabled in config.yaml")
            return {"error": "Evaluation is disabled in configuration"}

        self.logger.info("Starting system evaluation")
        self.results = []
        self.errors = []

        # Load test queries
        test_queries = self._load_test_queries(test_queries_path)
        if not test_queries:
            return {"error": "No test queries found"}

        self.logger.info(f"Loaded {len(test_queries)} test queries")

        # Evaluate each query
        for i, test_case in enumerate(test_queries, 1):
            self.logger.info(f"Evaluating query {i}/{len(test_queries)}: {test_case.get('query', '')[:50]}...")

            try:
                result = await self._evaluate_query(test_case, use_multi_perspective)
                self.results.append(result)
            except Exception as e:
                self.logger.error(f"Error evaluating query {i}: {e}")
                error_entry = {
                    "query_id": test_case.get("id", i),
                    "query": test_case.get("query", ""),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                self.errors.append(error_entry)
                self.results.append({
                    "query": test_case.get("query", ""),
                    "error": str(e)
                })

        # Generate comprehensive report
        report = self._generate_report(use_multi_perspective)

        # Add error analysis
        report["error_analysis"] = self._analyze_errors()

        # Save results
        self._save_results(report)

        return report

    async def _evaluate_query(
        self,
        test_case: Dict[str, Any],
        use_multi_perspective: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate a single test query with optional multi-perspective evaluation.

        Args:
            test_case: Test case with query and optional ground truth
            use_multi_perspective: Whether to use both perspectives

        Returns:
            Evaluation result for this query
        """
        query = test_case.get("query", "")
        ground_truth = test_case.get("ground_truth")
        expected_topics = test_case.get("expected_topics", [])
        category = test_case.get("category", "general")

        # Run through orchestrator if available
        if self.orchestrator:
            try:
                response_data = self.orchestrator.process_query(query)
            except Exception as e:
                self.logger.error(f"Error processing query through orchestrator: {e}")
                response_data = {
                    "query": query,
                    "response": f"Error: {str(e)}",
                    "metadata": {"error": str(e)}
                }
        else:
            self.logger.warning("No orchestrator provided, using placeholder response")
            response_data = {
                "query": query,
                "response": "Placeholder response - orchestrator not connected",
                "metadata": {"num_sources": 0}
            }

        # Evaluate response using LLM-as-a-Judge
        if use_multi_perspective:
            evaluation = await self.judge.evaluate_multi_perspective(
                query=query,
                response=response_data.get("response", ""),
                sources=response_data.get("metadata", {}).get("sources", []),
                ground_truth=ground_truth
            )
        else:
            evaluation = await self.judge.evaluate(
                query=query,
                response=response_data.get("response", ""),
                sources=response_data.get("metadata", {}).get("sources", []),
                ground_truth=ground_truth
            )

        # Check topic coverage if expected topics provided
        topic_coverage = self._check_topic_coverage(
            response_data.get("response", ""),
            expected_topics
        )

        return {
            "query_id": test_case.get("id"),
            "query": query,
            "category": category,
            "response": response_data.get("response", ""),
            "evaluation": evaluation,
            "metadata": response_data.get("metadata", {}),
            "ground_truth": ground_truth,
            "expected_topics": expected_topics,
            "topic_coverage": topic_coverage
        }

    def _check_topic_coverage(
        self,
        response: str,
        expected_topics: List[str]
    ) -> Dict[str, Any]:
        """
        Check how many expected topics are covered in the response.
        """
        if not expected_topics:
            return {"coverage_rate": 1.0, "covered": [], "missing": []}

        response_lower = response.lower()
        covered = []
        missing = []

        for topic in expected_topics:
            if topic.lower() in response_lower:
                covered.append(topic)
            else:
                missing.append(topic)

        coverage_rate = len(covered) / len(expected_topics) if expected_topics else 1.0

        return {
            "coverage_rate": coverage_rate,
            "covered": covered,
            "missing": missing,
            "total_expected": len(expected_topics)
        }

    def _load_test_queries(self, path: str) -> List[Dict[str, Any]]:
        """
        Load test queries from JSON file.
        """
        path_obj = Path(path)
        if not path_obj.exists():
            self.logger.warning(f"Test queries file not found: {path}")
            return []

        with open(path_obj, 'r') as f:
            queries = json.load(f)

        # Limit number of queries if configured
        if self.max_test_queries and len(queries) > self.max_test_queries:
            self.logger.info(f"Limiting to {self.max_test_queries} queries")
            queries = queries[:self.max_test_queries]

        return queries

    def _generate_report(self, use_multi_perspective: bool = True) -> Dict[str, Any]:
        """
        Generate comprehensive evaluation report with statistics and interpretation.
        """
        if not self.results:
            return {"error": "No results to report"}

        # Basic statistics
        total_queries = len(self.results)
        successful = [r for r in self.results if "error" not in r]
        failed = [r for r in self.results if "error" in r]

        # Aggregate scores
        if use_multi_perspective:
            scores_data = self._aggregate_multi_perspective_scores(successful)
        else:
            scores_data = self._aggregate_single_perspective_scores(successful)

        # Category analysis
        category_scores = self._analyze_by_category(successful)

        # Topic coverage analysis
        topic_analysis = self._analyze_topic_coverage(successful)

        # Find best and worst
        best_result, worst_result = self._find_extremes(successful, use_multi_perspective)

        # Generate interpretation
        interpretation = self._generate_interpretation(scores_data, category_scores, topic_analysis)

        report = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "multi_perspective": use_multi_perspective,
                "total_queries_available": total_queries,
                "criteria_used": [c["name"] for c in self.judge.criteria]
            },
            "summary": {
                "total_queries": total_queries,
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful) / total_queries if total_queries > 0 else 0.0
            },
            "scores": scores_data,
            "category_analysis": category_scores,
            "topic_coverage": topic_analysis,
            "best_result": best_result,
            "worst_result": worst_result,
            "interpretation": interpretation,
            "detailed_results": self.results
        }

        return report

    def _aggregate_multi_perspective_scores(self, results: List[Dict]) -> Dict[str, Any]:
        """Aggregate scores from multi-perspective evaluation."""
        combined_scores = []
        academic_scores = []
        practical_scores = []
        criterion_scores = {"academic": {}, "practical": {}}

        for result in results:
            eval_data = result.get("evaluation", {})

            if "combined_score" in eval_data:
                combined_scores.append(eval_data["combined_score"])

                # Academic perspective
                academic = eval_data.get("perspectives", {}).get("academic", {})
                if academic.get("overall_score"):
                    academic_scores.append(academic["overall_score"])
                    for crit, score_data in academic.get("criterion_scores", {}).items():
                        if crit not in criterion_scores["academic"]:
                            criterion_scores["academic"][crit] = []
                        criterion_scores["academic"][crit].append(score_data.get("score", 0))

                # Practical perspective
                practical = eval_data.get("perspectives", {}).get("practical", {})
                if practical.get("overall_score"):
                    practical_scores.append(practical["overall_score"])
                    for crit, score_data in practical.get("criterion_scores", {}).items():
                        if crit not in criterion_scores["practical"]:
                            criterion_scores["practical"][crit] = []
                        criterion_scores["practical"][crit].append(score_data.get("score", 0))

        # Calculate averages
        avg_combined = sum(combined_scores) / len(combined_scores) if combined_scores else 0
        avg_academic = sum(academic_scores) / len(academic_scores) if academic_scores else 0
        avg_practical = sum(practical_scores) / len(practical_scores) if practical_scores else 0

        # Average by criterion for each perspective
        avg_by_criterion = {
            "academic": {k: sum(v)/len(v) if v else 0 for k, v in criterion_scores["academic"].items()},
            "practical": {k: sum(v)/len(v) if v else 0 for k, v in criterion_scores["practical"].items()}
        }

        return {
            "combined_average": avg_combined,
            "by_perspective": {
                "academic": avg_academic,
                "practical": avg_practical
            },
            "by_criterion": avg_by_criterion,
            "score_distribution": {
                "combined": self._calculate_distribution(combined_scores),
                "academic": self._calculate_distribution(academic_scores),
                "practical": self._calculate_distribution(practical_scores)
            }
        }

    def _aggregate_single_perspective_scores(self, results: List[Dict]) -> Dict[str, Any]:
        """Aggregate scores from single-perspective evaluation."""
        overall_scores = []
        criterion_scores = {}

        for result in results:
            eval_data = result.get("evaluation", {})
            if eval_data.get("overall_score"):
                overall_scores.append(eval_data["overall_score"])

            for crit, score_data in eval_data.get("criterion_scores", {}).items():
                if crit not in criterion_scores:
                    criterion_scores[crit] = []
                criterion_scores[crit].append(score_data.get("score", 0))

        avg_overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0
        avg_by_criterion = {k: sum(v)/len(v) if v else 0 for k, v in criterion_scores.items()}

        return {
            "overall_average": avg_overall,
            "by_criterion": avg_by_criterion,
            "score_distribution": self._calculate_distribution(overall_scores)
        }

    def _calculate_distribution(self, scores: List[float]) -> Dict[str, Any]:
        """Calculate score distribution statistics."""
        if not scores:
            return {"min": 0, "max": 0, "median": 0, "std_dev": 0}

        sorted_scores = sorted(scores)
        n = len(sorted_scores)

        mean = sum(scores) / n
        variance = sum((x - mean) ** 2 for x in scores) / n
        std_dev = variance ** 0.5

        median = sorted_scores[n // 2] if n % 2 == 1 else (sorted_scores[n//2 - 1] + sorted_scores[n//2]) / 2

        return {
            "min": min(scores),
            "max": max(scores),
            "mean": mean,
            "median": median,
            "std_dev": std_dev,
            "count": n
        }

    def _analyze_by_category(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze scores by query category."""
        category_results = {}

        for result in results:
            category = result.get("category", "general")
            if category not in category_results:
                category_results[category] = []

            eval_data = result.get("evaluation", {})
            score = eval_data.get("combined_score") or eval_data.get("overall_score", 0)
            category_results[category].append(score)

        category_stats = {}
        for category, scores in category_results.items():
            category_stats[category] = {
                "average": sum(scores) / len(scores) if scores else 0,
                "count": len(scores),
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0
            }

        return category_stats

    def _analyze_topic_coverage(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze topic coverage across all results."""
        coverage_rates = []
        all_missing = []

        for result in results:
            topic_cov = result.get("topic_coverage", {})
            if topic_cov.get("coverage_rate") is not None:
                coverage_rates.append(topic_cov["coverage_rate"])
            all_missing.extend(topic_cov.get("missing", []))

        # Find most commonly missed topics
        missing_counts = {}
        for topic in all_missing:
            missing_counts[topic] = missing_counts.get(topic, 0) + 1

        commonly_missed = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "average_coverage": sum(coverage_rates) / len(coverage_rates) if coverage_rates else 0,
            "commonly_missed_topics": commonly_missed
        }

    def _find_extremes(self, results: List[Dict], use_multi_perspective: bool) -> tuple:
        """Find best and worst performing queries."""
        if not results:
            return None, None

        def get_score(r):
            eval_data = r.get("evaluation", {})
            return eval_data.get("combined_score") or eval_data.get("overall_score", 0)

        best = max(results, key=get_score)
        worst = min(results, key=get_score)

        return (
            {"query": best.get("query", ""), "score": get_score(best), "category": best.get("category")},
            {"query": worst.get("query", ""), "score": get_score(worst), "category": worst.get("category")}
        )

    def _analyze_errors(self) -> Dict[str, Any]:
        """
        Analyze errors for patterns and insights (Assignment Requirement).
        """
        if not self.errors:
            return {"total_errors": 0, "patterns": [], "recommendations": []}

        # Count error types
        error_types = {}
        for error in self.errors:
            error_type = error.get("error_type", "Unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # Identify patterns
        patterns = []
        if "RateLimitError" in error_types:
            patterns.append("API rate limiting detected - consider adding delays between queries")
        if "TimeoutError" in error_types:
            patterns.append("Timeout errors detected - consider increasing timeout or simplifying queries")
        if "JSONDecodeError" in error_types:
            patterns.append("JSON parsing errors - LLM responses may not be following expected format")

        # Generate recommendations
        recommendations = []
        if len(self.errors) > len(self.results) * 0.2:
            recommendations.append("High error rate (>20%) - review system configuration")
        if error_types:
            most_common = max(error_types.items(), key=lambda x: x[1])
            recommendations.append(f"Focus on fixing {most_common[0]} errors ({most_common[1]} occurrences)")

        return {
            "total_errors": len(self.errors),
            "error_types": error_types,
            "patterns": patterns,
            "recommendations": recommendations,
            "error_details": self.errors[:5]  # First 5 errors for detail
        }

    def _generate_interpretation(
        self,
        scores: Dict,
        category_scores: Dict,
        topic_analysis: Dict
    ) -> Dict[str, Any]:
        """
        Generate human-readable interpretation of results (Assignment Requirement).
        """
        interpretations = []
        strengths = []
        weaknesses = []

        # Overall performance interpretation
        if "combined_average" in scores:
            avg = scores["combined_average"]
        else:
            avg = scores.get("overall_average", 0)

        if avg >= 0.8:
            interpretations.append("Overall system performance is excellent.")
            strengths.append("High quality responses across most criteria")
        elif avg >= 0.6:
            interpretations.append("Overall system performance is good with room for improvement.")
        elif avg >= 0.4:
            interpretations.append("System performance is moderate - significant improvements needed.")
            weaknesses.append("Response quality needs enhancement")
        else:
            interpretations.append("System performance is below expectations - major revisions required.")
            weaknesses.append("Overall response quality is poor")

        # Perspective comparison (if multi-perspective)
        if "by_perspective" in scores:
            academic = scores["by_perspective"].get("academic", 0)
            practical = scores["by_perspective"].get("practical", 0)

            if abs(academic - practical) > 0.15:
                if academic > practical:
                    interpretations.append("System performs better on academic rigor than practical utility.")
                    weaknesses.append("Practical applicability of responses")
                else:
                    interpretations.append("System performs better on practical utility than academic rigor.")
                    weaknesses.append("Academic rigor and citation quality")
            else:
                interpretations.append("System performs consistently across both academic and practical perspectives.")
                strengths.append("Balanced performance across perspectives")

        # Category insights
        if category_scores:
            best_cat = max(category_scores.items(), key=lambda x: x[1]["average"])
            worst_cat = min(category_scores.items(), key=lambda x: x[1]["average"])

            if best_cat[1]["average"] - worst_cat[1]["average"] > 0.2:
                interpretations.append(f"Performance varies significantly by category: best in '{best_cat[0]}', weakest in '{worst_cat[0]}'.")
                weaknesses.append(f"'{worst_cat[0]}' category queries")
                strengths.append(f"'{best_cat[0]}' category queries")

        # Topic coverage insights
        if topic_analysis.get("average_coverage", 1) < 0.7:
            interpretations.append("Topic coverage is incomplete - responses often miss expected topics.")
            weaknesses.append("Comprehensive topic coverage")

        return {
            "summary": " ".join(interpretations),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": [
                "Focus on improving weakest criteria",
                "Add more diverse training examples for weak categories",
                "Ensure responses cover all expected topics"
            ] if weaknesses else ["Maintain current performance levels"]
        }

    def _save_results(self, report: Dict[str, Any]):
        """Save evaluation results to files."""
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed JSON results
        results_file = output_dir / f"evaluation_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        self.logger.info(f"Evaluation results saved to {results_file}")

        # Save human-readable summary
        summary_file = output_dir / f"evaluation_summary_{timestamp}.txt"
        self._write_summary_file(summary_file, report)
        self.logger.info(f"Summary saved to {summary_file}")

    def _write_summary_file(self, path: Path, report: Dict):
        """Write human-readable summary file."""
        with open(path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("MULTI-AGENT SYSTEM EVALUATION REPORT\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Generated: {report.get('timestamp', 'N/A')}\n")
            f.write(f"Multi-perspective evaluation: {report.get('configuration', {}).get('multi_perspective', False)}\n\n")

            # Summary section
            summary = report.get("summary", {})
            f.write("SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Queries: {summary.get('total_queries', 0)}\n")
            f.write(f"Successful: {summary.get('successful', 0)}\n")
            f.write(f"Failed: {summary.get('failed', 0)}\n")
            f.write(f"Success Rate: {summary.get('success_rate', 0):.1%}\n\n")

            # Scores section
            scores = report.get("scores", {})
            f.write("SCORES\n")
            f.write("-" * 40 + "\n")

            if "combined_average" in scores:
                f.write(f"Combined Average: {scores['combined_average']:.3f}\n")
                f.write(f"Academic Perspective: {scores.get('by_perspective', {}).get('academic', 0):.3f}\n")
                f.write(f"Practical Perspective: {scores.get('by_perspective', {}).get('practical', 0):.3f}\n")
            else:
                f.write(f"Overall Average: {scores.get('overall_average', 0):.3f}\n")

            f.write("\nScores by Criterion:\n")
            by_criterion = scores.get("by_criterion", {})
            if "academic" in by_criterion:
                f.write("  Academic Perspective:\n")
                for crit, score in by_criterion["academic"].items():
                    f.write(f"    {crit}: {score:.3f}\n")
                f.write("  Practical Perspective:\n")
                for crit, score in by_criterion["practical"].items():
                    f.write(f"    {crit}: {score:.3f}\n")
            else:
                for crit, score in by_criterion.items():
                    f.write(f"  {crit}: {score:.3f}\n")

            # Interpretation section
            interp = report.get("interpretation", {})
            f.write("\nINTERPRETATION\n")
            f.write("-" * 40 + "\n")
            f.write(f"{interp.get('summary', 'N/A')}\n\n")

            if interp.get("strengths"):
                f.write("Strengths:\n")
                for s in interp["strengths"]:
                    f.write(f"  + {s}\n")

            if interp.get("weaknesses"):
                f.write("\nWeaknesses:\n")
                for w in interp["weaknesses"]:
                    f.write(f"  - {w}\n")

            # Error analysis section
            errors = report.get("error_analysis", {})
            if errors.get("total_errors", 0) > 0:
                f.write("\nERROR ANALYSIS\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Errors: {errors['total_errors']}\n")
                for pattern in errors.get("patterns", []):
                    f.write(f"  ! {pattern}\n")

            f.write("\n" + "=" * 70 + "\n")


async def run_evaluation_demo():
    """
    Demo function to test the evaluation system.
    """
    import yaml
    from dotenv import load_dotenv

    load_dotenv()

    print("=" * 70)
    print("EVALUATION SYSTEM DEMO")
    print("=" * 70)

    # Load config
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)

    # Initialize evaluator without orchestrator (for testing)
    evaluator = SystemEvaluator(config, orchestrator=None)

    print("\nRunning evaluation on test queries...")
    print("Note: Using placeholder responses since no orchestrator connected\n")

    # Run evaluation
    report = await evaluator.evaluate_system(
        test_queries_path="data/example_queries.json",
        use_multi_perspective=True
    )

    # Display summary
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)

    summary = report.get("summary", {})
    print(f"\nTotal Queries: {summary.get('total_queries', 0)}")
    print(f"Successful: {summary.get('successful', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.1%}")

    scores = report.get("scores", {})
    if "combined_average" in scores:
        print(f"\nCombined Score: {scores['combined_average']:.3f}")
        print(f"Academic Score: {scores.get('by_perspective', {}).get('academic', 0):.3f}")
        print(f"Practical Score: {scores.get('by_perspective', {}).get('practical', 0):.3f}")

    interp = report.get("interpretation", {})
    print(f"\nInterpretation: {interp.get('summary', 'N/A')}")

    print(f"\nResults saved to outputs/")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_evaluation_demo())
