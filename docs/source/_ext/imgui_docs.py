"""
Sphinx directives for the imgui element reference.

``imgui-signature`` and ``imgui-flags`` take everything they show from the installed ``imgui_bundle``, so the
reference cannot drift from it. Signatures come from the pybind11 docstrings, which carry the real defaults and
overloads. The flag enums come from the type stub.

``imgui-example`` draws its body offscreen and inlines the resulting image, so the code that is shown is the code that
produced the image. Images are rendered during the docs build into ``docs/source/_imgui_images``, they are not part of
the repo.
"""

import ast
import re
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList

import imgui_bundle
from imgui_bundle import imgui, imgui_ctx, icons_fontawesome_6 as fa

IMAGES_DIR = Path(__file__).parents[1].joinpath("_imgui_images")

FONT_SIZE = 14

# the canvas is grown when an element needs more room, each image is cropped to what was drawn
CANVAS_SIZE = (400, 300)

# alpha of a pixel that imgui has drawn to, the canvas is transparent everywhere else
DRAWN_ALPHA = 8

# pybind11 writes fully qualified types into the docstrings, they are noise here
TYPE_SUBSTITUTIONS = [
    ("imgui_bundle._imgui_bundle.imgui.", ""),
    ("collections.abc.", ""),
    ("ndarray[writable=False]", "numpy.ndarray"),
    ("types.CapsuleType", "capsule"),
]


def escape_rst(text: str) -> str:
    """
    Escape the characters that rst reads as markup. The imgui comments are C++ prose and contain things such as
    ``*p_selected`` and ``\0``.
    """
    for character in "\\*`_|":
        text = text.replace(character, f"\\{character}")

    return text


def size_option(argument: str) -> tuple[float, float]:
    """a ``width, height`` directive option"""
    width, height = argument.replace(",", " ").split()
    return float(width), float(height)


class Stub:
    """the imgui_bundle type stub, the source of the flag enums and of the flag type of each parameter"""

    def __init__(self):
        path = Path(imgui_bundle.__file__).parent.joinpath("imgui", "__init__.pyi")
        self._lines = path.read_text().splitlines()
        tree = ast.parse("\n".join(self._lines))

        self._defs: dict[str, list[ast.FunctionDef]] = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                self._defs.setdefault(node.name, []).append(node)

        self._enums = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

    def flag_parameters(self, name: str) -> list[tuple[str, str]]:
        """
        ``(parameter, enum)`` for each parameter of an element that takes flags. The runtime signature types these
        as ``int``, the stub annotates them with the alias of their enum.
        """
        parameters = {}
        for node in self._defs.get(name, []):
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            for argument in arguments:
                if argument.annotation is None:
                    continue

                annotation = ast.unparse(argument.annotation)
                if annotation.endswith("Flags") and f"{annotation}_" in self._enums:
                    parameters[argument.arg] = f"{annotation}_"

        return list(parameters.items())

    def flag_enum(self, name: str) -> tuple[str, list[tuple[str, str, str]]]:
        """the docstring of a flag enum and its ``(member, value, description)`` entries"""
        node = self._enums[name]
        docstring = ast.get_docstring(node) or ""

        members = []
        for member in node.body:
            if not isinstance(member, ast.Assign):
                continue

            # the value and the description are in the trailing comment(s) of the assignment
            comment = " ".join(self._lines[member.lineno - 1 : member.end_lineno])
            match = re.search(r"#\s*\(=\s*([^)]+)\)\s*(?:#\s*(.+))?$", comment)
            value, description = match.groups() if match else ("", "")
            members.append(
                (member.targets[0].id, (value or "").strip(), escape_rst((description or "").strip()))
            )

        return docstring, members


def runtime_entry(name: str) -> tuple[list[tuple[str, str]], str]:
    """
    ``([(signature, description), ...], binding_defaults)`` from the pybind11 docstring of an element.

    An overloaded element is documented twice in its docstring, first as a list of signatures and then as numbered
    sections that each carry the description of that overload. The numbered sections are used when present.
    """
    doc = getattr(imgui, name).__doc__ or ""
    for old, new in TYPE_SUBSTITUTIONS:
        doc = doc.replace(old, new)

    signatures, defaults, description = [], [], []
    section = None
    overloaded = "Overloaded function." in doc

    for line in doc.splitlines():
        line = line.strip()
        if not line or line == "Overloaded function.":
            continue

        numbered = re.match(rf"^\d+\.\s*``?({name}\(.*)``$", line)
        plain = re.match(rf"^{name}\(", line)

        if numbered or plain:
            if overloaded and plain:
                # the signature list above the numbered sections, the sections are used instead
                continue
            signatures.append([numbered.group(1) if numbered else line, []])
            section = "signature"
        elif line.startswith("Python bindings defaults:"):
            section = "defaults"
        elif section == "defaults" and line.startswith("If "):
            defaults.append(line)
        elif signatures:
            section = "description"
            signatures[-1][1].append(line)
        else:
            section = "description"
            description.append(line)

    entries = [(s, escape_rst(" ".join(d))) for s, d in signatures]

    # an element that takes a sequence also has an ImVec overload of the same thing, a tuple or a list is what the
    # docs use so the ImVec twin is dropped
    if any("Sequence[" in signature for signature, _ in entries):
        entries = [(s, d) for s, d in entries if "ImVec" not in s]

    return entries, escape_rst(" ".join(defaults))


class ElementRenderer:
    """
    Renders imgui elements offscreen, one image per example.

    The device and canvas are shared, each example gets its own imgui context so that state such as an open popup or
    a held mouse button cannot leak from one example into the next.
    """

    def __init__(self):
        import os

        os.environ["WGPU_FORCE_OFFSCREEN"] = "1"

        import wgpu
        from rendercanvas.auto import RenderCanvas

        self._wgpu = wgpu
        self._canvas = RenderCanvas(size=CANVAS_SIZE)
        adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
        self._device = adapter.request_device_sync()

        self._code = ""
        self._namespace = {}
        self._host_window = True
        self._width = None
        self._size = imgui.ImVec2(0, 0)

    def _new_context(self):
        from wgpu.utils.imgui import ImguiRenderer

        renderer = ImguiRenderer(self._device, self._canvas)

        # the same fonts as ImguiFigure, so the images match a fastplotlib UI
        assets = Path(imgui_bundle.__file__).parent.joinpath("assets", "fonts")
        io = imgui.get_io()
        font = io.fonts.add_font_from_file_ttf(
            str(assets.joinpath("Roboto", "Roboto-Regular.ttf")), FONT_SIZE, imgui.ImFontConfig()
        )
        config = imgui.ImFontConfig()
        config.merge_mode = True
        io.fonts.add_font_from_file_ttf(
            str(assets.joinpath("Font_Awesome_6_Free-Solid-900.otf")), FONT_SIZE, config
        )
        imgui.push_font(font, font.legacy_size)

        renderer.set_gui(self._draw)

        def draw_frame():
            # the imgui renderer loads the canvas instead of clearing it, so what the previous example drew
            # would still be there
            self._clear()
            renderer.render()

        self._canvas.request_draw(draw_frame)

    def _clear(self):
        """
        Clear the canvas to transparent black, which is what lets an image be cropped to the region imgui drew to.
        The alpha channel is dropped when the image is saved, leaving the background black.
        """
        context = self._canvas.get_wgpu_context()
        view = context.get_current_texture().create_view()

        encoder = self._device.create_command_encoder()
        render_pass = encoder.begin_render_pass(
            color_attachments=[
                {
                    "view": view,
                    "resolve_target": None,
                    "clear_value": (0, 0, 0, 0),
                    "load_op": self._wgpu.LoadOp.clear,
                    "store_op": self._wgpu.StoreOp.store,
                }
            ],
        )
        render_pass.end()
        self._device.queue.submit([encoder.finish()])

    def _draw(self):
        if not self._host_window:
            # the example creates its own window(s), e.g. begin_main_menu_bar
            exec(self._code, self._namespace)
            self._size = imgui.ImVec2(*self._canvas.get_logical_size())
            return

        imgui.set_next_window_pos((0, 0))
        if self._width is not None:
            # the height stays auto-sized
            imgui.set_next_window_size((self._width, 0))
        imgui.begin(
            "##element",
            flags=imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_saved_settings
            | imgui.WindowFlags_.always_auto_resize,
        )

        try:
            exec(self._code, self._namespace)
        finally:
            # imgui is left in a broken state for the rest of the build if the window is not ended
            self._size = imgui.get_window_size()
            imgui.end()

    def _frames(self, n: int = 1):
        import numpy as np

        for _ in range(n):
            frame = np.asarray(self._canvas.draw())
        return frame

    def _interact(self, actions: str, frames: int):
        """
        Feed input into imgui, one action per line. imgui applies queued input events over consecutive frames, so
        each step is rendered before the next one is queued.

            hover x y | press x y | release | click x y | right_click x y | double_click x y
            drag x0 y0 x1 y1 | type "text" | key <imgui.Key member> | wheel dx dy
        """
        io = imgui.get_io()

        def move(x, y):
            io.add_mouse_pos_event(float(x), float(y))
            self._frames()

        def button(index, down):
            io.add_mouse_button_event(index, down)
            self._frames()

        frame = self._frames()

        for action in re.split(r"[\n;]", actions):
            action = action.strip()
            if not action:
                continue

            match action.split(maxsplit=1):
                case ["hover", args]:
                    move(*args.split())
                case ["press", args]:
                    move(*args.split())
                    button(0, True)
                case ["release"]:
                    button(0, False)
                case ["click", args]:
                    move(*args.split())
                    button(0, True)
                    button(0, False)
                case ["right_click", args]:
                    move(*args.split())
                    button(1, True)
                    button(1, False)
                case ["double_click", args]:
                    move(*args.split())
                    for _ in range(2):
                        button(0, True)
                        button(0, False)
                case ["drag", args]:
                    x0, y0, x1, y1 = args.split()
                    move(x0, y0)
                    button(0, True)
                    # the button is left down so that the element is drawn in its active state
                    move(x1, y1)
                case ["type", args]:
                    for character in args.strip().strip('"\''):
                        io.add_input_character(ord(character))
                    self._frames()
                case ["key", args]:
                    key = getattr(imgui.Key, args.strip())
                    io.add_key_event(key, True)
                    self._frames()
                    io.add_key_event(key, False)
                    self._frames()
                case ["wheel", args]:
                    dx, dy = args.split()
                    io.add_mouse_wheel_event(float(dx), float(dy))
                    self._frames()
                case _:
                    raise ValueError(f"unknown imgui-example interact action: {action}")

            frame = self._frames()

        return self._frames(frames)

    def render(
        self,
        code: str,
        file_name: str,
        frames: int,
        interact: str,
        host_window: bool,
        width: int | None,
        size: tuple[float, float] | None,
    ) -> Path:
        import numpy as np
        import imageio.v3 as iio

        self._code = code
        self._host_window = host_window
        self._width = width
        self._namespace = {"imgui": imgui, "imgui_ctx": imgui_ctx, "fa": fa, "np": np}

        self._canvas.set_logical_size(*(size or CANVAS_SIZE))
        self._new_context()

        def draw_all():
            # the host window is auto-sized, so its size is only final after the first frame
            if interact:
                return self._interact(interact, frames)
            return self._frames(frames)

        frame = draw_all()

        # grow the canvas and draw again if the element does not fit, it would be clipped otherwise
        canvas_width, canvas_height = self._canvas.get_logical_size()
        if self._size.x > canvas_width or self._size.y > canvas_height:
            self._canvas.set_logical_size(
                max(self._size.x, canvas_width), max(self._size.y, canvas_height)
            )
            frame = draw_all()

        # crop to everything imgui drew, which includes windows the example opened, such as a menu or a combo
        # popup, since those are not part of the host window
        drawn = np.argwhere(frame[..., 3] > DRAWN_ALPHA)
        if len(drawn) == 0:
            raise ValueError(
                f"imgui-example drew nothing, an element that draws only on interaction needs the matching "
                f"`interact` option:\n{code}"
            )
        (y0, x0), (y1, x1) = drawn.min(axis=0), drawn.max(axis=0)

        IMAGES_DIR.mkdir(exist_ok=True)
        path = IMAGES_DIR.joinpath(file_name)

        # imgui blends onto the transparent black canvas, so the rgb channels are already composited against black
        iio.imwrite(path, frame[y0 : y1 + 1, x0 : x1 + 1, :3])

        return path


_stub = None
_renderer = None
_image_names = dict()
_current_element = None


def stub() -> Stub:
    global _stub
    if _stub is None:
        _stub = Stub()
    return _stub


def renderer() -> ElementRenderer:
    global _renderer
    if _renderer is None:
        _renderer = ElementRenderer()
    return _renderer


def image_name(name: str) -> str:
    """keep the image name unique, an element can have more than one example"""
    _image_names[name] = _image_names.get(name, 0) + 1
    count = _image_names[name]

    return name if count == 1 else f"{name}_{count}"


def parse(directive: Directive, rst: list[str]) -> list[nodes.Node]:
    """parse generated rst in the context of the directive"""
    node = nodes.section()
    node.document = directive.state.document
    directive.state.nested_parse(StringList(rst), directive.content_offset, node)
    return node.children


class ImguiSignature(Directive):
    """the signature, description, and wrapped C++ signature of an imgui element"""

    required_arguments = 1

    def run(self):
        global _current_element

        name = self.arguments[0]
        _current_element = name
        signatures, binding_defaults = runtime_entry(name)

        rst = []
        if len(signatures) > 1:
            rst += ["**Overloads**", ""]

        for signature, description in signatures:
            rst += [f".. py:function:: imgui.{signature}", "    :no-index:", ""]
            if description:
                rst += [f"    {description}", ""]

        for parameter, enum in stub().flag_parameters(name):
            rst += [f"``{parameter}`` takes :ref:`imgui.{enum} <imgui.{enum}>`", ""]

        if binding_defaults:
            rst += [f".. note:: {binding_defaults}", ""]

        return parse(self, rst)


class ImguiExample(Directive):
    """an imgui example, shown as code and as the image that it renders"""

    has_content = True
    option_spec = {
        "interact": directives.unchanged,
        "name": directives.unchanged,
        "frames": directives.positive_int,
        "width": directives.positive_int,
        "size": size_option,
        "window": directives.unchanged,
    }

    def run(self):
        code = "\n".join(self.content)

        # the images of an element are named after it, an element can have more than one example
        name = self.options.get("name", _current_element or "example")

        path = renderer().render(
            code=code,
            file_name=f"{image_name(name)}.png",
            frames=self.options.get("frames", 3),
            interact=self.options.get("interact", ""),
            host_window=self.options.get("window") != "none",
            width=self.options.get("width"),
            size=self.options.get("size"),
        )

        literal = nodes.literal_block(code, code, language="python")
        image = nodes.image(uri=f"/_imgui_images/{path.name}", alt=name)

        return [literal, image]


class ImguiFlags(Directive):
    """a table of the members of an imgui flag or style enum"""

    required_arguments = 1

    def run(self):
        name = self.arguments[0]
        docstring, members = stub().flag_enum(name)

        # the page provides the label and the heading, a directive cannot emit a section title
        rst = []
        if docstring:
            rst += [escape_rst(docstring.splitlines()[0]), ""]

        rst += [
            ".. list-table::",
            "    :widths: 35 65",
            "    :header-rows: 1",
            "",
            "    * - member",
            "      - description",
        ]
        for member, _, description in members:
            rst += [
                f"    * - ``{name}.{member}``",
                f"      - {description}" if description else "      -",
            ]
        rst.append("")

        return parse(self, rst)


def setup(app):
    app.add_directive("imgui-signature", ImguiSignature)
    app.add_directive("imgui-example", ImguiExample)
    app.add_directive("imgui-flags", ImguiFlags)

    return {"version": imgui_bundle.__version__, "parallel_read_safe": False}
