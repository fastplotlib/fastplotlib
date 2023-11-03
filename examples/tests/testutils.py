"""
Test suite utilities.
"""

from pathlib import Path
import subprocess
import sys
from itertools import chain


ROOT = Path(__file__).parents[2]  # repo root
examples_dir = ROOT / "examples" / "desktop"
screenshots_dir = examples_dir / "screenshots"
diffs_dir = examples_dir / "diffs"

# examples live in themed sub-folders
example_globs = [
    "image/*.py",
    "heatmap/*.py"
    "scatter/*.py",
    "line/*.py",
    "line_collection/*.py",
    "gridplot/*.py"
]


def get_wgpu_backend():
    """
    Query the configured wgpu backend driver.
    """
    code = "import wgpu.utils; info = wgpu.utils.get_default_device().adapter.request_adapter_info(); print(info['adapter_type'], info['backend_type'])"
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
    out = result.stdout.strip()
    err = result.stderr.strip()
    return err if "traceback" in err.lower() else out


wgpu_backend = get_wgpu_backend()
is_lavapipe = wgpu_backend.lower() == "cpu vulkan"


def find_examples(query=None, negative_query=None, return_stems=False):
    """Finds all modules to be tested."""
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

