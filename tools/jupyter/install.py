"""Installs the Quest kernel for the user's Jupyter (docs/jupyter.md step 2): a
kernelspec named quest whose kernel is this checkout's tools/jupyter/
quest_kernel.py, run by --python (the Python running this, by the path it was
started with, so that Homebrew's opt link survives an upgrade), with this
checkout's ./quest as its driver; and the Quest lexer (quest_lexer.py), as a
Pygments plugin in that Python, for nbconvert. --uninstall removes both.
tools/jupyter/install runs this with jupyterlab's Python.

    python install.py [--uninstall] [--name NAME] [--driver DRIVER] [--python PYTHON] [--prefix DIR]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from jupyter_client.kernelspec import KernelSpecManager, NoSuchKernel

HERE = Path(__file__).resolve().parent
ROOT_DIR = HERE.parent.parent


def kernelspec(driver: str, python: str = sys.executable) -> dict:
    return {
        "argv": [python, str(HERE / "quest_kernel.py"), "-f", "{connection_file}"],
        "display_name": "Quest",
        "language": "quest",
        "interrupt_mode": "signal",
        "env": {"QUEST_KERNEL_DRIVER": driver},
    }


# The lexer's distribution (quest_lexer.py), a Pygments plugin
LEXER_DISTRIBUTION = "quest_pygments"
LEXER_VERSION = "0.1"


def lexer_wheel(directory: Path) -> Path:
    """A wheel of quest_lexer.py whose entry point makes it Pygments' lexer
    named quest, built here, since the kernel's Python need not have
    setuptools."""
    info = f"{LEXER_DISTRIBUTION}-{LEXER_VERSION}.dist-info"
    files = {
        "quest_lexer.py": (HERE / "quest_lexer.py").read_bytes(),
        f"{info}/METADATA": (f"Metadata-Version: 2.1\nName: {LEXER_DISTRIBUTION}\nVersion: {LEXER_VERSION}\n"
                             "Summary: A Pygments lexer for Quest\n").encode(),
        f"{info}/WHEEL": b"Wheel-Version: 1.0\nGenerator: tools/jupyter/install.py\nRoot-Is-Purelib: true\n"
                         b"Tag: py3-none-any\n",
        f"{info}/entry_points.txt": b"[pygments.lexers]\nquest = quest_lexer:QuestLexer\n",
    }
    record = []
    for name, data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        record.append(f"{name},sha256={digest},{len(data)}")
    record.append(f"{info}/RECORD,,")
    files[f"{info}/RECORD"] = ("\n".join(record) + "\n").encode()
    wheel = directory / f"{LEXER_DISTRIBUTION}-{LEXER_VERSION}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return wheel


def pip(python: str, *args: str) -> int:
    return subprocess.run([python, "-m", "pip", "--disable-pip-version-check", *args]).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the Quest kernel for Jupyter")
    parser.add_argument("--uninstall", action="store_true", help="remove the kernel")
    parser.add_argument("--name", default="quest", help="the kernelspec's name (default quest)")
    parser.add_argument("--driver", default=str(ROOT_DIR / "quest"), help="the Quest driver (default ./quest)")
    parser.add_argument("--python", default=sys.executable, help="the Python to run the kernel (default this one)")
    parser.add_argument("--prefix", help="install under DIR: DIR/share/jupyter, and the lexer by pip --prefix")
    args = parser.parse_args()
    manager = KernelSpecManager()
    if args.uninstall:
        try:
            manager.remove_kernel_spec(args.name)
        except NoSuchKernel:
            print(f"no kernel named {args.name} is installed")
            return 1
        print(f"removed the kernel {args.name}")
        if pip(args.python, "uninstall", "--yes", LEXER_DISTRIBUTION) != 0:
            print("could not remove the Quest lexer")
            return 1
        return 0
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "kernel.json").write_text(json.dumps(kernelspec(args.driver, args.python), indent=2) + "\n")
        where = manager.install_kernel_spec(d, args.name, user=args.prefix is None, prefix=args.prefix)
    print(f"installed the kernel {args.name} in {where}, its driver {args.driver}")
    with tempfile.TemporaryDirectory() as d:
        where = ["--prefix", args.prefix] if args.prefix else []
        if pip(args.python, "install", "--quiet", "--no-deps", "--no-index", "--force-reinstall", *where,
               str(lexer_wheel(Path(d)))) != 0:
            print("could not install the Quest lexer")
            return 1
    print("installed the Quest lexer for Pygments, which nbconvert highlights Quest cells with")
    return 0


if __name__ == "__main__":
    sys.exit(main())
