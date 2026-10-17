#!/bin/zsh
# Launch the work timer. Finds a python3 that actually has pyobjc, because the
# system one and the homebrew one are not always the same story.

HERE=${0:A:h}

for candidate in /opt/anaconda3/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
  if [[ -x "$candidate" ]] && "$candidate" -c 'import AppKit' >/dev/null 2>&1; then
    exec "$candidate" "$HERE/main.py" "$@"
  fi
done

echo "No python3 with pyobjc found." >&2
echo "Fix: python3 -m pip install pyobjc-framework-Cocoa" >&2
exit 1
