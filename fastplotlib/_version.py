"""
Versioning: we use a hard-coded version number, because it's simple and always
works. For dev installs we add extra version info from Git.
"""

import logging
import subprocess
from pathlib import Path


# This is the reference version number, to be bumped before each release.
# The build system detects this definition when building a distribution.
__version__ = "0.6.0"

# Allow using nearly the same code in different projects
project_name = "fastplotlib"


logger = logging.getLogger(project_name.lower())

# Get whether this is a repo. If so, repo_dir is the path, otherwise repo_dir is None.
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
            f"{project_name} version from git ({release}) and __version__ ({base_release}) don't match."
        )

    # Build the total version
    version = release
    if post and post != "0":
        version += f".post{post}"
    if labels:
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
                # No tags (and thus also no post). Only git hash and maybe 'dirty'
                parts = (None, None, *parts)

    # Return unpacked parts
    release, post, *labels = parts
    return release, post, labels


__version__ = get_version()

version_info = tuple(
    int(i) if i.isnumeric() else i for i in __version__.split("+")[0].split(".")
)
