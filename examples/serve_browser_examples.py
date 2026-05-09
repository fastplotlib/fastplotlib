"""
Serve browser examples locally.
===============================


A little script to serve pygfx examples on localhost so you can try them in the browser.
This is an iteration of the same script in rendercanvas and wgpu-py although some changes:

* swapped in pathlib for os.path (mostly)
* avoided pyscript for now, but likely a good idea to use for webworker recovery etc.

Files are loaded from disk on each request, so you can leave the server running
and just update examples, update pygfx and build the wheel, etc.
"""

import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import flit

import fastplotlib


# sphinx_gallery_pygfx_docs = 'hidden'
# sphinx_gallery_pygfx_test = 'off'

# "hosted" upstream deps, will break in the future
wgpu_wheel = "https://wgpu-py--753.org.readthedocs.build/en/753/_static/wgpu-0.31.0-py3-none-any.whl" # very hacky way to serve this but it does work...
uharfbuzz_wheel = "https://pygfx--1273.org.readthedocs.build/1273/_static/uharfbuzz-0.54.1-cp310-abi3-pyodide_2025_0_wasm32.whl" # try to get it from the github release, so we don't need to include it... 
pygfx_wheel = "https://pygfx--1273.org.readthedocs.build/1273/_static/pygfx-0.16.0-py3-none-any.whl"

# the pygfx wheel will be listed after this. it might be possible to still get deps from pyproject.toml
fpl_deps = [wgpu_wheel, uharfbuzz_wheel, pygfx_wheel, "hsluv", "pylinalg", "jinja2", "httpx", "trimesh", "gltflib", "imageio"]

root = Path(__file__).parent.parent.absolute()

short_version = ".".join(str(i) for i in fastplotlib.version_info[:3])
wheel_name = f"fastplotlib-{short_version}-py3-none-any.whl"

example_files = list((root / "examples").glob("**/*.py"))

def get_html_index():
    """Create a landing page."""

    examples_list = [f"<li><a href='{str(name.relative_to(root / "examples")).replace('.py', '.html')}'>{name.relative_to(root / "examples")!s}</a></li>" for name in example_files]

    html = """<!doctype html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width,initial-scale=1.0">
        <title>fastplotlib browser examples</title>
        <script type="module" src="https://pyscript.net/releases/2025.11.2/core.js"></script>
    </head>
    <body>

    <a href='/build'>Rebuild the wheel</a><br><br>
    """

    html += "List of examples that might run in Pyodide:\n"
    html += f"<ul>{''.join(examples_list)}</ul><br>\n\n"

    html += "</body>\n</html>\n"
    return html


html_index = get_html_index()

# TODO: a pyodide example for the compute examples (so we can capture output?)
# modified from _pyodide_iframe.html from rendercanvas, and then again from pygfx
pyodide_compute_template = """
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>{example_script} via Pyodide</title>
    <script src="https://cdn.jsdelivr.net/pyodide/v0.29.4/full/pyodide.js"></script>
</head>
<base href="/">

<dialog id="loading" style='outline: none; border: none; background: transparent;'>
        <h1>Loading...</h1>
    </dialog>
<body>
    <a href="/">Back to list</a><br><br>
    <!-- TODO: can we get a rebuild and rerun this example button? like go to /build with a redirect or something? -->
    <p>
    {docstring}
    </p>
    <canvas id='canvas' style='width:calc(90% - 40px); height:640px; background-color: #ddd;'></canvas>
    <div id="output" style="white-space: per-line; overflow-y: auto; height:300px; background:#eee; padding:4px; margin:4px; border:1px solid #ccc;">
        <p>Output:</p>
    </div>
    <script type="text/javascript">
        async function main() {{
            let loading = document.getElementById('loading');
            loading.showModal();
            try {{
                let example_name = {example_script!r};
                pythonCode = await (await fetch(example_name)).text();
                // this env var is really only used for the pygfx examples - so maybe we make a script for that gallery instead?
                pyodide = await loadPyodide();
                pyodide.setStdout({{
                    batched: (s) => {{
                        // TODO: newline, scrollable, echo to console?
                        el = document.getElementById("output");
                        el.innerHTML += "<br>" + s.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        el.scrollTop = el.scrollHeight;  // scroll to bottom
                        console.log(s); // so we also have it formatted
                    }}
                }});

                await pyodide.loadPackage("micropip");
                const micropip = pyodide.pyimport("micropip");
                {dependencies}
                await pyodide.loadPackagesFromImports(pythonCode);
                // I feel like some errors around stack switching are worse now -.-
                pyodide.setDebug(true);
                let ret = await pyodide.runPythonAsync(pythonCode);
                console.log("Example finished:", ret);
                loading.close();
            }} catch (err) {{
                // TODO: this could be formatted better as this overlaps and is unreadable...
                loading.innerHTML = "Failed to load: " + err;
                console.error(err); // so we have it here too
            }}
        }}
        let pyodide; // make it global for the console -> pyodide.globals.get("py_var").toJs()
        main();
    </script>
</body>

</html>
"""


imageio_patch = """
from pyodide.http import pyfetch
from pyodide.ffi import run_sync

async def _imread_async(filename, **kwargs):
    # pyodide working version of iio.imread, uses fetch and waiting on it, also replaced the "imageio:"
    filename = str(filename) # maybe breaks some Path stuff?
    if filename.startswith("imageio:"):
        filename = filename.replace("imageio:", "https://raw.githubusercontent.com/imageio/imageio-binaries/master/images/")

    if "." in filename:
        kwargs["extension"] = "." + filename.rsplit(".", 1)[-1]

    response = await pyfetch(filename)
    res = iio.imread((await response.bytes()), **kwargs)
    return res

def _imread(filename:str, **kwargs):
    print(f"Loading image: {filename!r} with kwargs: {kwargs}")
    res = run_sync(_imread_async(filename, **kwargs))
    return res
"""

def patch_imageio_for_pyodide(python_code:str) -> str:
    if "iio.imread(" not in python_code:
        return python_code

    return imageio_patch + "\n\n" + python_code.replace("iio.imread(", "_imread(")



def build_wheel():
    toml_filename = (root / "pyproject.toml")
    # spews more and more with each build... might need to clear stdout or something?
    flit.main(["-f", str(toml_filename.resolve()), "build", "--no-use-vcs", "--format", "wheel"])
    wheel_filename = root / "dist" / wheel_name
    assert wheel_filename.is_file(), f"{wheel_name} does not exist"
    # also copy the wgpu wheel if it's in a repo nearby... so make it a bit less work to update both.


def get_docstring_from_py_file(fname):
    filename = root / "examples" / fname
    docstate = 0
    doc = ""
    with open(filename, "rb") as f:
        for line in f:
            line = line.decode()
            if docstate == 0:
                if line.lstrip().startswith('"""'):
                    docstate = 1
            else:
                if docstate == 1 and line.lstrip().startswith(("---", "===")):
                    docstate = 2
                    doc = ""
                elif '"""' in line:
                    doc += line.partition('"""')[0]
                    break
                else:
                    doc += line

    return doc.replace("\n", "<br>")


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.respond(200, html_index, "text/html")
        elif self.path == "/build":
            try:
                self.respond(200, "Building wheel...<br>", "text/html")
                build_wheel()
            except Exception as err:
                self.respond(500, str(err), "text/plain")
            else:
                html = f"<br>Wheel build: {wheel_name}<br><br><a href='/'>Back to list</a>"
                self.respond(200, html, "text/html")
        elif self.path.endswith(".whl"):
            requested_path = Path(self.path)
            filename = root / "dist" / requested_path.name
            if os.path.isfile(filename):
                with open(filename, "rb") as f:
                    data = f.read()
                self.respond(200, data, "application/octet-stream")
            else:
                self.respond(404, "wheel not found")
        elif self.path.endswith(".html"):
            # name = self.path.strip("/")
            pyname = self.path.replace(".html", ".py").lstrip("/")
            try:
                doc = get_docstring_from_py_file(pyname)
                deps = [*fpl_deps, f"/{wheel_name}"]
                html = pyodide_compute_template.format(
                    docstring=doc,
                    example_script=pyname,
                    # todo: refactor this to a list and maybe get other deps from pyodide.loadPackagesFromImports
                    dependencies="\n".join(
                        [f"await micropip.install({dep!r});" for dep in deps]
                    ),
                )
                self.respond(200, html, "text/html")
            except Exception as err:
                self.respond(404, f"example not found: {err}")
        elif self.path.endswith(".py"):
            filename = os.path.join(root, "examples", self.path.strip("/"))
            if os.path.isfile(filename):
                with open(filename, "rb") as f:
                    data = f.read()
                data = patch_imageio_for_pyodide(data.decode()).encode()
                self.respond(200, data, "text/plain")
            else:
                self.respond(404, "py file not found")

        # TODO: we could try to mount a virtual filesystem and fill it... but I think using fetch and serving the files could work easier.
        elif self.path.startswith("/home/data/"):
            requested_path = Path(self.path)
            # this is for the pyodide examples that need to load data files - we mount the examples/data folder to /home/data in pyodide, so we can serve those files here.
            filename = root / "examples" / "data" / requested_path.relative_to("/home/data")
            if os.path.isfile(filename):
                with open(filename, "rb") as f:
                    data = f.read()
                self.respond(200, data, "application/octet-stream")
            else:
                self.respond(404, "data file not found")

        else:
            self.respond(404, "not found")

    def respond(self, code, body, content_type="text/plain"):
        self.send_response(code)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        if isinstance(body, str):
            body = body.encode()
        self.wfile.write(body)


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[-1])
        except ValueError:
            pass

    build_wheel()
    print("Opening page in web browser ...")
    webbrowser.open(f"http://localhost:{port}/")
    HTTPServer(("", port), MyHandler).serve_forever()


