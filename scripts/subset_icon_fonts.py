"""Shrink the icon fonts to the icons MarketHub actually uses.

Font Awesome and Bootstrap Icons ship thousands of icons (~400 KB of
fonts); the site uses about a hundred. This script finds every `fa-*` and
`bi-*` class used in templates/, static/js/ and api/, looks up each icon's
code point in the vendor CSS, and writes subset .woff2 files (a few KB each)
into static/vendor/. The full fonts are kept in assets/icon-fonts/.

Run it again after using an icon that wasn't used before:

    pip install fonttools brotli
    python scripts/subset_icon_fonts.py
"""
import re
from pathlib import Path

from fontTools import subset

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "assets" / "icon-fonts"
FA_CSS = ROOT / "static/vendor/fontawesome/css/all.min.css"
BI_CSS = ROOT / "static/vendor/bootstrap-icons/bootstrap-icons.min.css"
FA_FONTS = ROOT / "static/vendor/fontawesome/webfonts"
BI_FONTS = ROOT / "static/vendor/bootstrap-icons/fonts"

# Kept even when not used yet: cheap, and handy for small template changes.
EXTRA_FA = (
    "fa-star-half-alt fa-star-half-stroke fa-check fa-xmark fa-times fa-plus fa-minus "
    "fa-heart fa-spinner fa-chevron-left fa-chevron-right fa-chevron-down fa-chevron-up "
    "fa-arrow-left fa-arrow-right fa-truck fa-circle-check fa-check-circle fa-trash-alt "
    "fa-edit fa-pen-to-square fa-download fa-print fa-filter fa-sort"
).split()
EXTRA_BI = "bi-star bi-star-fill bi-star-half bi-check bi-x bi-plus bi-dash".split()


def used_classes(prefix):
    pattern = re.compile(rf"\b{prefix}-[a-z0-9]+(?:-[a-z0-9]+)*")
    names = set()
    for folder, globs in (("templates", ["*.html"]), ("static/js", ["*.js"]), ("api", ["*.py", "*.html"])):
        for glob in globs:
            for path in (ROOT / folder).rglob(glob):
                names.update(pattern.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return names


def code_points(css, names, pattern):
    points, missing = set(), []
    for name in sorted(names):
        match = re.search(pattern % re.escape(name), css)
        if match:
            points.add(int(match.group(1), 16))
        else:
            missing.append(name)
    return points, missing


def write_subset(source, target, points):
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.notdef_outline = True
    font = subset.load_font(str(source), options)
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=points | {0x20})
    subsetter.subset(font)
    subset.save_font(font, str(target), options)
    print(f"{target.relative_to(ROOT)}: {source.stat().st_size // 1024} KB -> {target.stat().st_size // 1024} KB")


def main():
    # FA 6 CSS: .fa-cart-shopping,.fa-shopping-cart{--fa:"\f07a"} (or content:"\f07a")
    fa_points, fa_missing = code_points(
        FA_CSS.read_text(), used_classes("fa") | set(EXTRA_FA),
        r'\.%s(?=[,{:])[^{]*\{[^}]*?(?:--fa|content):\s*"\\([0-9a-f]+)',
    )
    bi_points, bi_missing = code_points(
        BI_CSS.read_text(), used_classes("bi") | set(EXTRA_BI),
        r'\.%s::?before\s*\{\s*content:\s*"\\([0-9a-f]+)"',
    )
    print(f"Font Awesome: {len(fa_points)} icons; not icons (size/style classes or typos): {fa_missing}")
    print(f"Bootstrap Icons: {len(bi_points)} icons; not found: {bi_missing}")
    for name in ("fa-solid-900", "fa-brands-400", "fa-regular-400"):
        write_subset(FULL / f"{name}.woff2", FA_FONTS / f"{name}.woff2", fa_points)
    write_subset(FULL / "bootstrap-icons.woff2", BI_FONTS / "bootstrap-icons.woff2", bi_points)


if __name__ == "__main__":
    main()
