"""set app version across all source files."""

import re
import sys
from pathlib import Path

FILES = {
    Path("pyeclaw/config.py"): (r'APP_VERSION = "[^"]*"', 'APP_VERSION = "{version}"'),
    Path("pyproject.toml"): (r'version = "[^"]*"', 'version = "{version}"'),
}


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/set_version.py <version>")
        sys.exit(1)

    version = sys.argv[1].lstrip("v")

    for path, (pattern, replacement) in FILES.items():
        if not path.exists():
            print(f"error: {path} not found")
            sys.exit(1)

        text = path.read_text(encoding="utf-8")
        updated = re.sub(pattern, replacement.format(version=version), text, count=1)

        if text == updated:
            print(f"warning: no match in {path}")
            continue

        path.write_text(updated, encoding="utf-8")
        print(f"  {path} -> {version}")

    print(f"version set to {version}")


if __name__ == "__main__":
    main()
