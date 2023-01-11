"""
Test suite utilities.
"""

from pathlib import Path
import subprocess
import sys
from itertools import chain


ROOT = Path(__file__).parents[2]  # repo root
examples_dir = ROOT / "examples"
screenshots_dir = examples_dir / "screenshots"
diffs_dir = screenshots_dir / "diffs"

# examples live in themed sub-folders
example_globs = ["*.py", "introductory/*.py", "feature_demo/*.py", "validation/*.py"]


def wgpu_backend_endswith(query):
    """
    Query the configured wgpu backend driver.
    """
    code = "import wgpu.utils; d = wgpu.utils.get_default_device(); print(d.adapter.properties['adapterType'], d.adapter.properties['backendType'])"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=ROOT,
    )
    return (
        result.stdout.strip().endswith(query)
        and "traceback" not in result.stderr.lower()
    )


is_lavapipe = wgpu_backend_endswith("CPU Vulkan")


def find_examples(query=None, negative_query=None, return_stems=False):
    result = []
    for example_path in chain(*(examples_dir.glob(x) for x in example_globs)):
        example_code = example_path.read_text(encoding="UTF-8")
        query_match = query is None or query in example_code
        negative_query_match = (
            negative_query is None or negative_query not in example_code
        )
        if query_match and negative_query_match:
            result.append(example_path)
    result = list(sorted(result))
    if return_stems:
        result = [r.stem for r in result]
    return result
