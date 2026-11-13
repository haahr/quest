"""Where the tests, their goldens, and the two compilers' drivers are, for the
runner (testing/runner.py) and the modules it uses."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]

TESTS_SOURCE_DIR = ROOT_DIR / "tests" / "source"
# The example programs the documentation walks through, run as golden tests too
# (docs/testing.md §2.1)
EXAMPLES_DIR = ROOT_DIR / "examples"
TESTS_GOLDEN_DIR = ROOT_DIR / "tests" / "golden"
TESTS_ERRORS_DIR = ROOT_DIR / "tests" / "errors"
DRIVER_SCRIPT = ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"

# The self-hosted compiler's driver (docs/testing.md §2.3)
SELF_HOSTED_DRIVER = ROOT_DIR / "questlang" / "driver" / "main.quest"

# The programs the self-hosted driver's -e runs, and the bootstrap's transcript
# of them (docs/testing.md §2.3), which tests/eval/generate.py writes
EVAL_CASES = ROOT_DIR / "tests" / "eval" / "cases.quest"
EVAL_GOLDEN = TESTS_GOLDEN_DIR / "self-hosted" / "eval.out"

# REPL transcripts: each tests/repl/NAME.quest is the input to quest -i, and
# tests/golden/repl/NAME.out what it writes (docs/testing.md §2.7);
# tests/repl/files holds what they load
TESTS_REPL_DIR = ROOT_DIR / "tests" / "repl"
TESTS_REPL_GOLDEN_DIR = TESTS_GOLDEN_DIR / "repl"
