"""Quest Testing Infrastructure.

Provides the end-to-end golden test runner and diagnostic error testing
framework.
"""

from __future__ import annotations

from quest.testing.errors import (
    ActualDiagnostic,
    ExpectedDiagnostic,
    extract_expected_diagnostics,
    parse_actual_diagnostics,
    run_error_test,
)
from quest.testing.runner import (
    PhaseTask,
    TestDirectives,
    main,
    parse_test_directives,
    record_telemetry,
    run_all_tests,
    run_single_golden_test,
)

__all__ = [
    "ActualDiagnostic",
    "ExpectedDiagnostic",
    "PhaseTask",
    "TestDirectives",
    "extract_expected_diagnostics",
    "main",
    "parse_actual_diagnostics",
    "parse_test_directives",
    "record_telemetry",
    "run_all_tests",
    "run_error_test",
    "run_single_golden_test",
]
