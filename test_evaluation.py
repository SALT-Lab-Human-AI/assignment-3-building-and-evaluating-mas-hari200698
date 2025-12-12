"""
Test script for LLM-as-a-Judge Evaluation (Phase 4)

This script tests the evaluation system including:
- Two independent judging perspectives (assignment requirement)
- Scoring rubrics and criteria
- Error analysis
- Report generation

Note: This requires Groq API access. If rate limited, wait and retry.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
import yaml
from dotenv import load_dotenv

from src.evaluation.judge import LLMJudge
from src.evaluation.evaluator import SystemEvaluator


def print_header(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def test_judge_initialization():
    """Test that the judge initializes correctly."""
    print_header("TEST 1: Judge Initialization")
    
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    judge = LLMJudge(config)
    
    # Check perspectives
    perspectives = judge.get_perspectives()
    print(f"\n✓ Judge initialized with {len(perspectives)} perspectives:")
    for name, info in perspectives.items():
        print(f"  - {name}: {info['name']}")
    
    # Check rubrics
    rubrics = judge.get_rubrics()
    print(f"\n✓ Scoring rubrics defined for {len(rubrics)} criteria:")
    for criterion in rubrics.keys():
        print(f"  - {criterion}")
    
    # Check criteria from config
    print(f"\n✓ Evaluation criteria loaded: {len(judge.criteria)}")
    for c in judge.criteria:
        print(f"  - {c['name']} (weight: {c['weight']})")
    
    print("\n✅ Judge initialization test PASSED")
    return True


async def test_single_perspective_evaluation():
    """Test single perspective evaluation."""
    print_header("TEST 2: Single Perspective Evaluation")
    
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    judge = LLMJudge(config)
    
    # Test query and response
    query = "What is usability in HCI?"
    response = """Usability in Human-Computer Interaction (HCI) refers to the ease with which 
users can learn and use a product to achieve their goals effectively, efficiently, and 
satisfactorily. According to Nielsen (1994), usability includes five key components:

1. Learnability - How easy is it for users to accomplish basic tasks the first time?
2. Efficiency - How quickly can users perform tasks once they've learned the design?
3. Memorability - How easily can users reestablish proficiency after a period of not using it?
4. Errors - How many errors do users make, and how easily can they recover?
5. Satisfaction - How pleasant is it to use the design?

ISO 9241-11 defines usability as the extent to which a product can be used by specified 
users to achieve specified goals with effectiveness, efficiency, and satisfaction."""
    
    print(f"\nQuery: {query}")
    print(f"\nResponse (truncated): {response[:150]}...")
    
    try:
        # Test academic perspective
        print("\n--- Testing Academic Perspective ---")
        result = await judge.evaluate(
            query=query,
            response=response,
            perspective="academic"
        )
        
        print(f"\n✓ Academic Perspective Score: {result['overall_score']:.3f}")
        print("  Criterion scores:")
        for criterion, score_data in result['criterion_scores'].items():
            print(f"    - {criterion}: {score_data['score']:.3f}")
        
        # Test practical perspective
        print("\n--- Testing Practical Perspective ---")
        result = await judge.evaluate(
            query=query,
            response=response,
            perspective="practical"
        )
        
        print(f"\n✓ Practical Perspective Score: {result['overall_score']:.3f}")
        print("  Criterion scores:")
        for criterion, score_data in result['criterion_scores'].items():
            print(f"    - {criterion}: {score_data['score']:.3f}")
        
        print("\n✅ Single perspective evaluation test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   This might be due to API rate limiting. Wait and retry.")
        return False


async def test_multi_perspective_evaluation():
    """Test multi-perspective evaluation (assignment requirement)."""
    print_header("TEST 3: Multi-Perspective Evaluation (Assignment Requirement)")
    
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    judge = LLMJudge(config)
    
    query = "What are best practices for accessible web design?"
    response = """Best practices for accessible web design include:

1. **Semantic HTML** - Use proper heading hierarchy and ARIA labels.
2. **Color Contrast** - Maintain WCAG 2.1 AA standard (4.5:1 for normal text).
3. **Keyboard Navigation** - Ensure all interactive elements are keyboard accessible.
4. **Alt Text** - Provide descriptive alt text for all images.
5. **Focus Indicators** - Make focus states visible for keyboard users.
6. **Responsive Design** - Support various screen sizes and zoom levels.

These practices align with WCAG 2.1 guidelines and help ensure websites 
are usable by people with various disabilities."""
    
    print(f"\nQuery: {query}")
    print(f"\nResponse (truncated): {response[:150]}...")
    
    try:
        result = await judge.evaluate_multi_perspective(
            query=query,
            response=response
        )
        
        print(f"\n✓ Combined Score: {result['combined_score']:.3f}")
        print(f"\n  Academic Perspective: {result['perspectives']['academic']['overall_score']:.3f}")
        print(f"  Practical Perspective: {result['perspectives']['practical']['overall_score']:.3f}")
        
        # Show analysis
        analysis = result['analysis']
        print(f"\n  Perspective Correlation: {analysis['perspective_correlation']:.1%}")
        
        if analysis['disagreements']:
            print("\n  Disagreements between perspectives:")
            for d in analysis['disagreements']:
                print(f"    - {d['criterion']}: Academic={d['academic']:.2f}, Practical={d['practical']:.2f}")
        else:
            print("\n  ✓ Perspectives largely agree on all criteria")
        
        print("\n✅ Multi-perspective evaluation test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   This might be due to API rate limiting. Wait and retry.")
        return False


async def test_evaluator_report_generation():
    """Test the evaluator's report generation (without orchestrator)."""
    print_header("TEST 4: Report Generation")
    
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize evaluator without orchestrator
    evaluator = SystemEvaluator(config, orchestrator=None)
    
    print("\n✓ Evaluator initialized")
    print("  Note: Running without orchestrator (placeholder responses)")
    
    # Check that test queries exist
    test_file = Path("data/example_queries.json")
    if test_file.exists():
        with open(test_file) as f:
            queries = len(yaml.safe_load(f))
        print(f"\n✓ Found {queries} test queries in {test_file}")
    else:
        print(f"\n⚠ Test queries file not found: {test_file}")
        return False
    
    print("\n  Running evaluation (this may take a moment)...")
    
    try:
        # Run evaluation with only 2 queries for speed
        config_copy = config.copy()
        config_copy["evaluation"] = config.get("evaluation", {}).copy()
        config_copy["evaluation"]["num_test_queries"] = 2
        
        evaluator = SystemEvaluator(config_copy, orchestrator=None)
        report = await evaluator.evaluate_system(
            test_queries_path="data/example_queries.json",
            use_multi_perspective=True
        )
        
        # Verify report structure
        print("\n✓ Report generated successfully")
        print(f"  - Total queries: {report.get('summary', {}).get('total_queries', 0)}")
        print(f"  - Success rate: {report.get('summary', {}).get('success_rate', 0):.1%}")
        
        if "scores" in report:
            scores = report["scores"]
            if "combined_average" in scores:
                print(f"  - Combined score: {scores['combined_average']:.3f}")
        
        if "interpretation" in report:
            interp = report["interpretation"]
            print(f"\n  Interpretation:")
            print(f"    {interp.get('summary', 'N/A')[:100]}...")
        
        if "error_analysis" in report:
            errors = report["error_analysis"]
            print(f"\n  Error analysis:")
            print(f"    Total errors: {errors.get('total_errors', 0)}")
        
        # Check output files
        output_dir = Path("outputs")
        if output_dir.exists():
            json_files = list(output_dir.glob("evaluation_*.json"))
            txt_files = list(output_dir.glob("evaluation_summary_*.txt"))
            print(f"\n✓ Output files created:")
            print(f"    JSON reports: {len(json_files)}")
            print(f"    Summary files: {len(txt_files)}")
        
        print("\n✅ Report generation test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   This might be due to API rate limiting. Wait and retry.")
        return False


async def main():
    """Run all evaluation tests."""
    load_dotenv()
    
    print("\n" + "📊 " * 20)
    print("       LLM-AS-A-JUDGE EVALUATION TEST SUITE")
    print("📊 " * 20)
    
    results = []
    
    # Test 1: Initialization (no API call)
    results.append(("Judge Initialization", await test_judge_initialization()))
    
    # Check if we should run API tests
    import os
    if not os.getenv("GROQ_API_KEY"):
        print("\n⚠️ GROQ_API_KEY not set - skipping API tests")
        print("   Set the key in .env file to run full tests")
    else:
        print("\n💡 Note: The following tests make API calls.")
        print("   If you hit rate limits, wait 1-2 minutes and retry.\n")
        
        # Test 2: Single perspective
        results.append(("Single Perspective", await test_single_perspective_evaluation()))
        
        # Test 3: Multi-perspective (assignment requirement)
        results.append(("Multi-Perspective", await test_multi_perspective_evaluation()))
        
        # Test 4: Report generation
        results.append(("Report Generation", await test_evaluator_report_generation()))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed\n")
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    if passed == total:
        print("\n✅ All tests passed! Phase 4 implementation is working.")
    else:
        print("\n⚠️ Some tests failed. Check errors above.")
        print("   API rate limits are the most common cause - wait and retry.")
    
    print("\n" + "=" * 70)
    print("  Phase 4 Implementation Features:")
    print("  ✓ Two independent judging perspectives (Academic & Practical)")
    print("  ✓ Detailed scoring rubrics for each criterion")
    print("  ✓ Multi-perspective evaluation with correlation analysis")
    print("  ✓ Error analysis and pattern identification")
    print("  ✓ Comprehensive report generation with interpretation")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())


