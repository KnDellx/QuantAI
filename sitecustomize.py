"""Install project-local runtime compatibility hooks for Python commands."""

import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() == "cp1252":
    sys.stdout.reconfigure(encoding="utf-8")
