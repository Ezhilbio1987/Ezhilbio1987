"""Turn a normalised edition into the HTML the browser lays out."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    # Artwork is SVG we generated ourselves, so it goes in unescaped; nothing
    # from the edition file is ever marked safe.
    env.filters["startswith"] = str.startswith
    return env


def render_html(edition: dict, out_path: Path) -> Path:
    """Write the edition HTML next to the assets it links."""
    from markupsafe import Markup

    def mark_svg(node):
        if isinstance(node, dict):
            if "svg" in node and isinstance(node["svg"], str):
                node["svg"] = Markup(node["svg"])
            for value in node.values():
                mark_svg(value)
        elif isinstance(node, list):
            for value in node:
                mark_svg(value)

    mark_svg(edition)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rel = Path(__import__("os").path.relpath(ASSETS, out_path.parent)).as_posix()
    html = _env().get_template("edition.html.j2").render(
        css_href=f"{rel}/css/newspaper.css",
        js_href=f"{rel}/js/fit.js",
        **edition,
    )
    out_path.write_text(html, encoding="utf-8")
    return out_path
