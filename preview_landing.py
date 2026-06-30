"""Generate static HTML preview of the new landing page (for screenshot in browser)."""

from __future__ import annotations

import re
from pathlib import Path

from landing import (
    _cta_html,
    _features_html,
    _flow_html,
    _footer_html,
    _hero_html,
    _navbar_html,
    _stats_html,
)

CSS_PATH = Path(__file__).parent / "static" / "assets" / "dasher" / "streamlit-overrides.css"


def main() -> None:
    full_css = CSS_PATH.read_text(encoding="utf-8")
    match = re.search(r"/\* ={3,}\s*\n\s*LANDING PAGE.*$", full_css, re.DOTALL)
    landing_css = match.group(0) if match else ""

    html_doc = f"""<!doctype html>
<html lang=\"id\"><head>
<meta charset=\"utf-8\"><title>Preview Landing laris.AI</title>
<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css\">
<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.47.0/tabler-icons.min.css\">
<style>
body {{ margin:0; padding:0; }}
{landing_css}
</style></head>
<body>
{_navbar_html()}
{_hero_html()}
{_stats_html()}
{_features_html()}
{_flow_html()}
{_cta_html()}
{_footer_html()}
</body></html>
"""
    out = Path(__file__).parent / "_preview_landing.html"
    out.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {out} ({len(html_doc)} bytes)")


if __name__ == "__main__":
    main()
