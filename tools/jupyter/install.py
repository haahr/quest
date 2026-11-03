"""Installs the Quest kernel for the user's Jupyter (docs/jupyter.md step 2): a
kernelspec named quest whose kernel is this checkout's tools/jupyter/
quest_kernel.py, run by --python (the Python running this, by the path it was
started with, so that Homebrew's opt link survives an upgrade), with this
checkout's ./quest as its driver. --uninstall removes it. tools/jupyter/install
runs this with jupyterlab's Python.

    python install.py [--uninstall] [--name NAME] [--driver DRIVER] [--python PYTHON] [--prefix DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the Quest kernel for Jupyter")
    parser.add_argument("--uninstall", action="store_true", help="remove the kernel")
    parser.add_argument("--name", default="quest", help="the kernelspec's name (default quest)")
    parser.add_argument("--driver", default=str(ROOT_DIR / "quest"), help="the Quest driver (default ./quest)")
    parser.add_argument("--python", default=sys.executable, help="the Python to run the kernel (default this one)")
    parser.add_argument("--prefix", help="install under DIR/share/jupyter, not for the user")
    args = parser.parse_args()
    manager = KernelSpecManager()
    if args.uninstall:
        try:
            manager.remove_kernel_spec(args.name)
        except NoSuchKernel:
            print(f"no kernel named {args.name} is installed")
            return 1
        print(f"removed the kernel {args.name}")
        return 0
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "kernel.json").write_text(json.dumps(kernelspec(args.driver, args.python), indent=2) + "\n")
        where = manager.install_kernel_spec(d, args.name, user=args.prefix is None, prefix=args.prefix)
    print(f"installed the kernel {args.name} in {where}, its driver {args.driver}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
