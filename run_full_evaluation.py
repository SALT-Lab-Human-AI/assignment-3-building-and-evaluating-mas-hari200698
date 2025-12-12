"""
Run Full Evaluation with Orchestrator
This script runs the complete evaluation on all 10 test queries.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
import yaml
from dotenv import load_dotenv
from src.autogen_orchestrator import AutoGenOrchestrator
from src.evaluation.evaluator import SystemEvaluator

async def main():
    # Load environment
    load_dotenv()

    # Load config
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)

    print("=" * 70)
    print("RUNNING FULL EVALUATION WITH ORCHESTRATOR")
    print("=" * 70)

    # Initialize orchestrator
    print("\n1. Initializing AutoGen orchestrator...")
    try:
        orchestrator = AutoGenOrchestrator(config)
        print("   [OK] Orchestrator initialized")
    except Exception as e:
        print(f"   [ERROR] Failed to initialize orchestrator: {e}")
        return

    # Initialize evaluator with orchestrator
    print("\n2. Initializing evaluator...")
    evaluator = SystemEvaluator(config, orchestrator=orchestrator)
    print("   [OK] Evaluator initialized")

    # Run evaluation on all 10 queries
    print("\n3. Running evaluation on all test queries...")
    print("   This will take several minutes...")
    print("   Progress will be shown for each query.\n")

    try:
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
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1%}")

        scores = report.get("scores", {})
        if "combined_average" in scores:
            print(f"\nCombined Score: {scores['combined_average']:.3f}")
            print(f"Academic Perspective: {scores.get('by_perspective', {}).get('academic', 0):.3f}")
            print(f"Practical Perspective: {scores.get('by_perspective', {}).get('practical', 0):.3f}")

        # Show interpretation
        interp = report.get("interpretation", {})
        if interp:
            print(f"\nInterpretation:")
            print(f"  {interp.get('summary', 'N/A')}")

            if interp.get('strengths'):
                print(f"\n  Strengths:")
                for s in interp['strengths']:
                    print(f"    [+] {s}")

            if interp.get('weaknesses'):
                print(f"\n  Weaknesses:")
                for w in interp['weaknesses']:
                    print(f"    [-] {w}")

        # Show error analysis
        errors = report.get("error_analysis", {})
        if errors and errors.get('total_errors', 0) > 0:
            print(f"\nError Analysis:")
            print(f"  Total Errors: {errors['total_errors']}")
            if errors.get('patterns'):
                print(f"  Patterns:")
                for p in errors['patterns']:
                    print(f"    [!] {p}")

        print("\n" + "=" * 70)
        print("Results saved to outputs/ directory")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Error during evaluation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
