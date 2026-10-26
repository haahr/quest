"""Host C Compiler Driver and Binary Execution Runner."""

from __future__ import annotations

import functools
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from quest.syntax.sources import BYTE_ENCODING


def find_c_compiler() -> str:
    """Locates host C compiler (clang preferred, fallback to gcc)."""
    for candidate in ("clang", "gcc"):
        path = shutil.which(candidate)
        if path is not None:
            return path
    raise RuntimeError("No C compiler (clang or gcc) found in PATH")


@functools.lru_cache(maxsize=None)
def traceback_flags(compiler: str) -> tuple[str, ...]:
    """Flags that keep tracebacks' frames (docs/exceptions.md §5.3): GCC moves the cold paths of functions, which
    hold the calls that raise, into separate sections that tracebacks cannot attribute to the functions. (Clang does
    not, and gcc on macOS is clang.)"""
    try:
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return ()
    if "Free Software Foundation" in version:
        return ("-fno-reorder-blocks-and-partition",)
    return ()


def get_runtime_dir() -> Path:
    """Returns absolute path to repository runtime/ directory."""
    # This file is bootstrap/python/quest/codegen/c/compiler_runner.py
    repo_root = Path(__file__).resolve().parents[5]
    runtime_dir = repo_root / "runtime"
    if not runtime_dir.exists():
        raise RuntimeError(f"Runtime directory not found at {runtime_dir}")
    return runtime_dir


def detect_gc_flags(nogc: bool = False) -> list[str]:
    """Detects Boehm GC include/lib flags, falling back to -DQUEST_NOGC."""
    if nogc:
        return ["-DQUEST_NOGC"]

    candidates = [
        Path("/opt/homebrew/opt/bdw-gc"),
        Path("/usr/local/opt/bdw-gc"),
        Path("/usr"),
    ]
    for prefix in candidates:
        inc = prefix / "include"
        lib = prefix / "lib"
        if (inc / "gc.h").exists():
            flags = [f"-I{inc}"]
            if (lib / "libgc.dylib").exists() or (lib / "libgc.so").exists() or (lib / "libgc.a").exists():
                flags.extend([f"-L{lib}", "-lgc"])
                return flags

    # Fallback to nogc if not found
    return ["-DQUEST_NOGC"]


@functools.cache
def detect_readline_flags() -> tuple[str, ...]:
    """Detects the line editor quest_readline.c is compiled with (docs/self-hosted-repl.md §1.1): GNU readline where
    it is installed, else libedit's readline-compatible API, else none (-DQUEST_NOREADLINE). QUEST_READLINE, if set,
    chooses one: gnu, edit, or none."""
    choice = os.environ.get("QUEST_READLINE", "")
    if choice not in ("", "gnu", "edit", "none"):
        raise RuntimeError(f"QUEST_READLINE must be gnu, edit, or none, not '{choice}'")
    if choice in ("", "gnu"):
        for prefix in (Path("/opt/homebrew/opt/readline"), Path("/usr/local/opt/readline"), Path("/usr")):
            inc = prefix / "include"
            lib = prefix / "lib"
            # GNU readline's own headers, which libedit's compatibility headers do not have
            if (inc / "readline" / "rlconf.h").exists() and any(
                (lib / f"libreadline.{suffix}").exists() for suffix in ("dylib", "so", "a")
            ):
                return (f"-I{inc}", "-DQUEST_GNU_READLINE", f"-L{lib}", "-lreadline")
        if choice == "gnu":
            raise RuntimeError("QUEST_READLINE=gnu, but GNU readline is not installed")
    if choice in ("", "edit"):
        if _sdk_has("readline/readline.h"):
            return ("-ledit",)
        if choice == "edit":
            raise RuntimeError("QUEST_READLINE=edit, but libedit's readline.h is not installed")
    return ("-DQUEST_NOREADLINE",)


def _sdk_has(header: str) -> bool:
    """Whether the system's headers (on macOS, the SDK's) include header."""
    roots = [Path("/usr/include")]
    try:
        sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True, text=True, check=False).stdout.strip()
        if sdk:
            roots.append(Path(sdk) / "usr" / "include")
    except OSError:
        pass
    return any((root / header).exists() for root in roots)


def runtime_sources(runtime_dir: Path) -> list[str]:
    """The runtime's C files, which every program is compiled with."""
    return [str(runtime_dir / name) for name in ("quest_runtime.c", "quest_serialization.c", "quest_readline.c")]


def compile_c_source(
    c_source: str,
    output_binary: Optional[Path | str] = None,
    nogc: bool = False,
    compiler_path: Optional[str] = None,
    extra_flags: Optional[list[str]] = None,
    output_path: Optional[Path | str] = None,
    extra_objects: Optional[list[Path | str]] = None,
) -> Path:
    """Compiles a generated C source string into an executable binary."""
    out_target = output_path if output_path is not None else output_binary
    if out_target is None:
        raise ValueError("output_binary or output_path must be specified")
    target_bin = Path(out_target)
    compiler = compiler_path or find_c_compiler()
    runtime_dir = get_runtime_dir()

    # Create temporary .c file for the source
    with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False, encoding="utf-8") as f:
        f.write(c_source)
        temp_c_path = Path(f.name)

    try:
        cmd = [
            compiler,
            "-std=c99",
            "-pedantic-errors",
            "-Wno-overlength-strings",
            "-Wall",
            "-Wextra",
            "-O2",
            *traceback_flags(compiler),
            f"-I{runtime_dir}",
            *runtime_sources(runtime_dir),
            str(temp_c_path),
        ]
        if extra_objects:
            cmd.extend(str(obj) for obj in extra_objects)
        cmd.extend([
            "-o",
            str(target_bin),
        ])
        cmd.extend(detect_gc_flags(nogc=nogc))
        cmd.extend(detect_readline_flags())
        if extra_flags:
            cmd.extend(extra_flags)

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"C compilation failed with exit code {proc.returncode}:\n"
                f"Command: {' '.join(cmd)}\n"
                f"{proc.stderr}"
            )
        return target_bin
    finally:
        if temp_c_path.exists():
            temp_c_path.unlink()


def run_binary(
    binary_path: Path,
    args: Optional[list[str]] = None,
    env: Optional[dict[str, str]] = None,
    input_data: Optional[str] = None,
    timeout: float = 10.0,
) -> subprocess.CompletedProcess[str]:
    """Executes a compiled binary and returns stdout/stderr/returncode, a character per byte."""
    cmd = [str(binary_path)] + (args or [])
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding=BYTE_ENCODING,
        env=env,
        input=input_data,
        timeout=timeout,
    )


def compile_c_to_object(
    c_path: Path | str,
    output_object_path: Path | str,
    include_paths: Optional[list[Path | str]] = None,
    nogc: bool = False,
    compiler_path: Optional[str] = None,
    extra_flags: Optional[list[str]] = None,
) -> Path:
    """Compiles a C source file into an object file (.o)."""
    target_obj = Path(output_object_path)
    compiler = compiler_path or find_c_compiler()
    runtime_dir = get_runtime_dir()

    cmd = [
        compiler,
        "-std=c99",
        "-pedantic-errors",
        "-Wno-overlength-strings",
        "-Wall",
        "-Wextra",
        "-O2",
        *traceback_flags(compiler),
        f"-I{runtime_dir}",
    ]
    if include_paths:
        for p in include_paths:
            cmd.append(f"-I{p}")
    gc_flags = detect_gc_flags(nogc=nogc)
    for flag in gc_flags:
        if flag.startswith("-I") or flag.startswith("-D"):
            cmd.append(flag)
    if extra_flags:
        cmd.extend(extra_flags)
    cmd.extend([
        "-c",
        str(c_path),
        "-o",
        str(target_obj),
    ])

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"C object compilation failed with exit code {proc.returncode}:\n"
            f"Command: {' '.join(cmd)}\n"
            f"{proc.stderr}"
        )
    return target_obj


def link_objects(
    objects: list[Path | str],
    output_binary: Path | str,
    nogc: bool = False,
    compiler_path: Optional[str] = None,
    extra_flags: Optional[list[str]] = None,
) -> Path:
    """Links object files and runtime C sources into an executable binary."""
    target_bin = Path(output_binary)
    target_bin.parent.mkdir(parents=True, exist_ok=True)
    compiler = compiler_path or find_c_compiler()
    runtime_dir = get_runtime_dir()

    cmd = [
        compiler,
        "-std=c99",
        "-pedantic-errors",
        "-Wno-overlength-strings",
        "-Wall",
        "-Wextra",
        "-O2",
        *traceback_flags(compiler),
        f"-I{runtime_dir}",
        *runtime_sources(runtime_dir),
    ]
    cmd.extend(str(obj) for obj in objects)
    cmd.extend([
        "-o",
        str(target_bin),
    ])
    cmd.extend(detect_gc_flags(nogc=nogc))
    cmd.extend(detect_readline_flags())
    if extra_flags:
        cmd.extend(extra_flags)

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Linker failed with exit code {proc.returncode}:\n"
            f"Command: {' '.join(cmd)}\n"
            f"{proc.stderr}"
        )
    return target_bin


