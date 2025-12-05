"""
Vietnamese Benchmark Pipeline - Main Runner Script
Chạy toàn bộ quy trình tạo benchmark từ đầu đến cuối.

Pipeline:
1. Chunk PDFs → Text files (150-300 words each)
2. Generate Q&A pairs from chunks
3. Export to Excel for manual validation
4. (Optional) Run LLM-as-a-Judge evaluation

Usage:
    python run_pipeline.py                    # Chạy tất cả bước
    python run_pipeline.py --step chunk       # Chỉ chunk PDFs
    python run_pipeline.py --step generate    # Chỉ generate Q&A
    python run_pipeline.py --step export      # Chỉ export Excel
    python run_pipeline.py --step evaluate    # Chỉ evaluate với LLM
    python run_pipeline.py --source culture   # Chỉ xử lý văn hóa
    python run_pipeline.py --source law       # Chỉ xử lý pháp luật
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

# Base directory
BASE_DIR = r"D:/dichdata/vietnamese-culture-eval-2"

# Script paths
SCRIPTS = {
    "chunk": os.path.join(BASE_DIR, "data_sources", "chunk.py"),
    "generate": os.path.join(BASE_DIR, "data_generation", "generate_qa_benchmark.py"),
    "export": os.path.join(BASE_DIR, "data_generation", "export_validation_excel.py"),
    "evaluate": os.path.join(BASE_DIR, "data_generation", "llm_judge_scorer.py"),
}


def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_step(step_num: int, total: int, description: str):
    """Print step indicator."""
    print(f"\n[{step_num}/{total}] {description}")
    print("-" * 50)


def run_script(script_path: str, args: list = None) -> bool:
    """
    Run a Python script with optional arguments.

    Args:
        script_path: Path to the Python script
        args: List of command line arguments

    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(script_path):
        print(f"  ✗ Script not found: {script_path}")
        return False

    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    print(f"  Running: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, cwd=BASE_DIR)
        return result.returncode == 0
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False


def step_chunk(source: str = "all"):
    """Step 1: Chunk PDFs into text files."""
    print_header("STEP 1: CHUNKING PDFs")

    args = ["--source", source]
    success = run_script(SCRIPTS["chunk"], args)

    if success:
        print("\n  ✓ Chunking completed successfully")
    else:
        print("\n  ✗ Chunking failed")

    return success


def step_generate(source: str = "all"):
    """Step 2: Generate Q&A pairs from chunks."""
    print_header("STEP 2: GENERATING Q&A PAIRS")

    args = ["--source", source]
    success = run_script(SCRIPTS["generate"], args)

    if success:
        print("\n  ✓ Q&A generation completed successfully")
    else:
        print("\n  ✗ Q&A generation failed")

    return success


def step_export():
    """Step 3: Export to Excel for validation."""
    print_header("STEP 3: EXPORTING TO EXCEL")

    success = run_script(SCRIPTS["export"])

    if success:
        print("\n  ✓ Excel export completed successfully")
        print(f"  → Output: {os.path.join(BASE_DIR, 'vietnamese_benchmark_validation.xlsx')}")
    else:
        print("\n  ✗ Excel export failed")

    return success


def step_evaluate(limit: int = None):
    """Step 4: Run LLM-as-a-Judge evaluation."""
    print_header("STEP 4: LLM-AS-A-JUDGE EVALUATION")

    args = []
    if limit:
        args.extend(["--limit", str(limit)])

    success = run_script(SCRIPTS["evaluate"], args)

    if success:
        print("\n  ✓ Evaluation completed successfully")
    else:
        print("\n  ✗ Evaluation failed")

    return success


def run_full_pipeline(source: str = "all", skip_evaluate: bool = False, eval_limit: int = None):
    """Run the complete pipeline."""
    print_header("VIETNAMESE BENCHMARK PIPELINE")
    print(f"  Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Source: {source}")
    print(f"  Skip evaluation: {skip_evaluate}")

    total_steps = 3 if skip_evaluate else 4
    current_step = 0
    results = {}

    # Step 1: Chunk PDFs
    current_step += 1
    print_step(current_step, total_steps, "Chunking PDFs into text files")
    results["chunk"] = step_chunk(source)

    if not results["chunk"]:
        print("\n⚠ Chunking failed. Stopping pipeline.")
        return results

    # Step 2: Generate Q&A
    current_step += 1
    print_step(current_step, total_steps, "Generating Q&A pairs")
    results["generate"] = step_generate(source)

    if not results["generate"]:
        print("\n⚠ Q&A generation failed. Stopping pipeline.")
        return results

    # Step 3: Export Excel
    current_step += 1
    print_step(current_step, total_steps, "Exporting to Excel for validation")
    results["export"] = step_export()

    # Step 4: Evaluate (optional)
    if not skip_evaluate:
        current_step += 1
        print_step(current_step, total_steps, "Running LLM-as-a-Judge evaluation")
        results["evaluate"] = step_evaluate(eval_limit)

    # Summary
    print_header("PIPELINE SUMMARY")
    print(f"  End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    for step_name, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {step_name.capitalize():12} : {status}")

    print()

    all_success = all(results.values())
    if all_success:
        print("  ✓ All steps completed successfully!")
    else:
        print("  ⚠ Some steps failed. Please check the logs above.")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Vietnamese Benchmark Pipeline Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                        # Run full pipeline
  python run_pipeline.py --step chunk           # Only chunk PDFs
  python run_pipeline.py --step generate        # Only generate Q&A
  python run_pipeline.py --step export          # Only export Excel
  python run_pipeline.py --step evaluate        # Only run evaluation
  python run_pipeline.py --source culture       # Process only culture data
  python run_pipeline.py --skip-evaluate        # Skip LLM evaluation step
  python run_pipeline.py --eval-limit 10        # Evaluate only 10 questions
        """
    )

    parser.add_argument(
        '--step',
        choices=['chunk', 'generate', 'export', 'evaluate', 'all'],
        default='all',
        help='Which step to run (default: all)'
    )

    parser.add_argument(
        '--source',
        choices=['culture', 'law', 'all'],
        default='all',
        help='Which source to process (default: all)'
    )

    parser.add_argument(
        '--skip-evaluate',
        action='store_true',
        help='Skip the LLM evaluation step'
    )

    parser.add_argument(
        '--eval-limit',
        type=int,
        default=None,
        help='Limit number of questions to evaluate (for testing)'
    )

    args = parser.parse_args()

    # Run specific step or full pipeline
    if args.step == 'all':
        run_full_pipeline(
            source=args.source,
            skip_evaluate=args.skip_evaluate,
            eval_limit=args.eval_limit
        )
    elif args.step == 'chunk':
        step_chunk(args.source)
    elif args.step == 'generate':
        step_generate(args.source)
    elif args.step == 'export':
        step_export()
    elif args.step == 'evaluate':
        step_evaluate(args.eval_limit)


if __name__ == "__main__":
    main()
