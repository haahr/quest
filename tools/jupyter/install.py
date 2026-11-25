"""Installs the Quest kernel for the user's Jupyter (docs/jupyter-kernel.md
section 3): a kernelspec named quest whose kernel is this checkout's
tools/jupyter/quest_kernel.py, run by --python (the Python running this, by the
path it was started with, so that Homebrew's opt link survives an upgrade), with
the release tools/release --install installed (~/.local/bin/quest) as its
driver, or --driver's; the Quest lexer (quest_lexer.py), as a Pygments
plugin in that Python, for nbconvert; and the JupyterLab extension (lab/),
which highlights and indents Quest in JupyterLab's editor, built with npm and
JupyterLab's builder and copied into Jupyter's labextensions directory (unless
--no-lab). --uninstall removes all three. tools/jupyter/install runs this with
jupyterlab's Python.

The installed release, not this checkout's ./quest, is the default because
./quest rebuilds its stages whenever the compiler's sources change, and a stage
build waits while any worktree's check or timing holds the machine-wide lock,
so a notebook's cell could wait for half an hour. The installed release changes
only when tools/release --install installs another, which a restarted kernel
then runs. --driver ./quest gives a kernel this checkout's compiler instead.

    python install.py [--uninstall] [--name NAME] [--driver DRIVER] [--python PYTHON] [--prefix DIR] [--no-lab]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from jupyter_client.kernelspec import KernelSpecManager, NoSuchKernel
from jupyter_core.paths import jupyter_data_dir

HERE = Path(__file__).resolve().parent
ROOT_DIR = HERE.parent.parent
# Where tools/release --install writes its command, by default
INSTALLED_DRIVER = Path.home() / ".local" / "bin" / "quest"


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


# The JupyterLab extension (lab/package.json), and where its build goes
LAB_DIR = HERE / "lab"
LAB_NAME = "quest-jupyterlab"


def lab_destination(prefix: str | None) -> Path:
    """Where JupyterLab finds the extension: the user's Jupyter data directory,
    or the prefix's, under labextensions."""
    data = Path(prefix) / "share" / "jupyter" if prefix else Path(jupyter_data_dir())
    return data / "labextensions" / LAB_NAME


def install_lab_extension(python: str, prefix: str | None) -> str | None:
    """Builds the extension with npm (its dependencies, the first time) and
    jupyter labextension build, from --python's Jupyter, and copies the build
    to lab_destination. Returns what went wrong, or None."""
    labextension = Path(python).parent / "jupyter-labextension"
    if shutil.which("npm") is None:
        return "no npm to build it with"
    if not labextension.is_file():
        return f"no {labextension} to build it with"
    if subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=LAB_DIR).returncode != 0:
        return "npm install failed"
    built = subprocess.run([str(labextension), "build", "."], cwd=LAB_DIR, capture_output=True, text=True)
    if built.returncode != 0:
        return f"jupyter labextension build failed:\n{built.stdout}{built.stderr}"
    destination = lab_destination(prefix)
    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(LAB_DIR / "labextension", destination)
    return None


def pip(python: str, *args: str) -> int:
    return subprocess.run([python, "-m", "pip", "--disable-pip-version-check", *args]).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the Quest kernel for Jupyter")
    parser.add_argument("--uninstall", action="store_true", help="remove the kernel")
    parser.add_argument("--name", default="quest", help="the kernelspec's name (default quest)")
    parser.add_argument("--driver", help=f"the Quest driver (default {INSTALLED_DRIVER}, the installed release; "
                        "./quest for this checkout's compiler)")
    parser.add_argument("--python", default=sys.executable, help="the Python to run the kernel (default this one)")
    parser.add_argument("--prefix", help="install under DIR: DIR/share/jupyter, and the lexer by pip --prefix")
    parser.add_argument("--no-lab", action="store_true", help="leave out the JupyterLab extension, which needs npm")
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
        destination = lab_destination(args.prefix)
        if destination.is_dir():
            shutil.rmtree(destination)
            print(f"removed the JupyterLab extension from {destination}")
        return 0
    if args.driver is None:
        if not INSTALLED_DRIVER.is_file():
            print(f"no installed release at {INSTALLED_DRIVER}: run tools/release --install, or name a driver "
                  "with --driver (--driver ./quest for this checkout's compiler)")
            return 1
        args.driver = str(INSTALLED_DRIVER)
    else:
        args.driver = str(Path(args.driver).absolute())
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
    if args.no_lab:
        return 0
    problem = install_lab_extension(args.python, args.prefix)
    if problem is not None:
        print(f"could not install the JupyterLab extension: {problem} (--no-lab leaves it out)")
        return 1
    print(f"installed the JupyterLab extension in {lab_destination(args.prefix)}, which highlights and indents "
          "Quest in JupyterLab's editor; reload JupyterLab's page to load it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
