"""
_version.py v1.2

Simple version string management, using a hard-coded version string
for simplicity and compatibility, while adding git info at runtime.
See https://github.com/pygfx/_version for more info.
This code is subject to The Unlicense (public domain).

Any updates to this file should be done in https://github.com/pygfx/_version

Usage in short:

* Add this file to the root of your library (next to the `__init__.py`).
* On a new release, you just update the __version__.
"""

import logging
import subprocess
from pathlib import Path


# This is the base version number, to be bumped before each release.
# The build system detects this definition when building a distribution.
__version__ = "0.5.1"

# Set this to your library name
project_name = "fastplotlib"


logger = logging.getLogger(project_name)

# Get whether this is a repo. If so, repo_dir is the path, otherwise None.
repo_dir = Path(__file__).parents[1]
repo_dir = repo_dir if repo_dir.joinpath(".git").is_dir() else None


def get_version():
    """Get the version string."""
    if repo_dir:
        return get_extended_version()
    else:
        return __version__


def get_extended_version():
    """Get an extended version string with information from git."""

    release, post, labels = get_version_info_from_git()

    # Sample first 3 parts of __version__
    base_release = ".".join(__version__.split(".")[:3])

    # Check release
    if not release:
        release = base_release
    elif release != base_release:
        logger.warning(
            f"{project_name} version from git ({release})"
            + f" and __version__ ({base_release}) don't match."
        )

    # Build the total version
    version = release
    if post and post != "0":
        version += f".post{post}"
        if labels:
            version += "+" + ".".join(labels)
    elif labels and labels[-1] == "dirty":
        version += "+" + ".".join(labels)

    return version


def get_version_info_from_git():
    """Get (release, post, labels) from Git.

    With `release` the version number from the latest tag, `post` the
    number of commits since that tag, and `labels` a tuple with the
    git-hash and optionally a dirty flag.
    """

    # Call out to Git
    command = [
        "git",
        "describe",
        "--long",
        "--always",
        "--tags",
        "--dirty",
        "--first-parent",
    ]
    try:
        p = subprocess.run(command, cwd=repo_dir, capture_output=True)
    except Exception as e:
        logger.warning(f"Could not get {project_name} version: {e}")
        p = None

    # Parse the result into parts
    if p is None:
        parts = (None, None, "unknown")
    else:
        output = p.stdout.decode(errors="ignore")
        if p.returncode:
            stderr = p.stderr.decode(errors="ignore")
            logger.warning(
                f"Could not get {project_name} version.\n\nstdout: "
                + output
                + "\n\nstderr: "
                + stderr
            )
            parts = (None, None, "unknown")
        else:
            parts = output.strip().lstrip("v").split("-")
            if len(parts) <= 2:
                # No tags (and thus no post). Only git hash and maybe 'dirty'.
                parts = (None, None, *parts)

    # Return unpacked parts
    release, post, *labels = parts
    return release, post, labels


def _to_tuple(v):
    """Convert __version__ to version_info tuple."""
    v = __version__.split("+")[0]  # remove hash
    return tuple(int(i) if i.isnumeric() else i for i in v.split("."))


# Apply the versioning
base_version = __version__
__version__ = get_version()
version_info = _to_tuple(__version__)


# The CLI part

CLI_USAGE = """
_version.py

help            - Show this message.
version         - Show the current version.
bump VERSION    - Bump the __version__ to the given VERSION.
update          - Self-update the _version.py module by downloading the
                  reference code and replacing version number and project name.
""".lstrip()

if __name__ == "__main__":
    import sys
    import urllib.request

    _, *args = sys.argv

    if not args:
        print(f"{project_name} v{__version__}")

    elif args[0] == "version":
        print(f"{project_name} v{__version__}")

    elif args[0] == "bump":
        if len(args) != 2:
            sys.exit("Expected a version number to bump to.")
        new_version = args[1].lstrip("v")  # allow '1.2.3' and 'v1.2.3'
        if not new_version.count(".") == 2:
            sys.exit("Expected two dots in new version string.")
        if not all(s.isnumeric() for s in new_version.split(".")):
            sys.exit("Expected only numbers in new version string.")
        with open(__file__, "rb") as f:
            text = ref_text = f.read().decode()
        text = text.replace(base_version, new_version, 1)
        with open(__file__, "wb") as f:
            f.write(text.encode())
        print(f"Bumped version from '{base_version}' to '{new_version}'.")

    elif args[0] == "update":
        u = "https://raw.githubusercontent.com/pygfx/_version/main/_version.py"
        with urllib.request.urlopen(u) as f:
            text = ref_text = f.read().decode()
        text = text.replace("0.0.0", base_version, 1)
        text = text.replace("PROJECT_NAME", project_name, 1)
        with open(__file__, "wb") as f:
            f.write(text.encode())
        print("Updated to the latest _version.py.")

    elif args[0].lstrip("-") in ["h", "help"]:
        print(CLI_USAGE)

    else:
        print(f"Unknown command for _version.py: {args[0]!r}")
        print("Use ``python _version.py help`` to see a list of options.")
