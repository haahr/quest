# Sourced by the launchers (./questboot and tools/check, c-diff, externals, and
# release): sets PY to the Python to run, $PYTHON if it is set, else Homebrew's
# Python 3.11, else the first python3.11 or python3 on the PATH.
if [ -n "$PYTHON" ]; then
    PY="$PYTHON"
elif [ -x "/opt/homebrew/opt/python@3.11/libexec/bin/python" ]; then
    PY="/opt/homebrew/opt/python@3.11/libexec/bin/python"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    PY="/opt/homebrew/bin/python3"
elif command -v python3.11 >/dev/null 2>&1; then
    PY="python3.11"
else
    PY="python3"
fi
