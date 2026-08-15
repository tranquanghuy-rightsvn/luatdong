#!/usr/bin/env python3
"""Chuyển template Jinja2 (di sản từ app Flask cũ) sang template placeholder thuần.

CHẠY MỘT LẦN duy nhất khi khởi tạo dự án. Sau đó `templates/*.html` là NGUỒN
THIẾT KẾ SỐNG — sửa tay trực tiếp, không chạy lại script này (nếu chạy lại phải
thêm --force, và mọi tuỳ biến tay sẽ mất).

Cú pháp template sau khi chuyển:
  {{PLACEHOLDER}}            — giá trị vô hướng, build.py thay bằng chuỗi
  <!--@NAME--> ... <!--/@NAME-->
                             — vùng lặp: build.py lấy phần bên trong làm mẫu 1
                               phần tử, lặp cho từng bản ghi rồi thay cả vùng
                               (kể cả marker). Danh sách rỗng → vùng biến mất.

Dùng: python3 scripts/scaffold_templates.py [--force]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"

# Đánh dấu template đã chuyển xong để không lỡ tay chạy lại
DONE_MARK = "<!--@SCAFFOLDED-->"

# --- Placeholder trong thân vòng lặp (bản ghi bài viết) ---
LOOP_VARS = [
    (r"\{\{\s*post\.url\s*\}\}", "{{URL}}"),
    (r"\{\{\s*post\.image\s*\}\}", "{{IMAGE}}"),
    (r"\{\{\s*post\.title\s*\}\}", "{{TITLE}}"),
    (r"\{\{\s*post\.description\s*\|\s*truncate\([^)]*\)\s*\}\}", "{{DESC}}"),
    (r"\{\{\s*post\.description\s*\}\}", "{{DESC}}"),
    (r"\{\{\s*post\.created_at\s*\}\}", "{{CREATED_AT}}"),
]

# --- Placeholder vô hướng ở phạm vi trang (áp SAU khi đã bóc hết vòng lặp) ---
PAGE_VARS = [
    (r"\{\{\s*post\.title\s*\}\}", "{{TITLE}}"),
    (r"\{\{\s*post\.description\s*\}\}", "{{DESCRIPTION}}"),
    (r"\{\{\s*post\.image\s*\}\}", "{{IMAGE}}"),
    (r"\{\{\s*post\.url\s*\}\}", "{{URL}}"),
    (r"\{\{\s*post\.created_at\s*\}\}", "{{CREATED_AT}}"),
    (r"\{\{\s*category_url\s*\}\}", "{{CATEGORY_URL}}"),
    (r"\{\{\s*category\s*\}\}", "{{CATEGORY}}"),
    (r"\{\{\s*content\s*\}\}", "{{CONTENT}}"),
    (r"\{\{\s*image\s*\}\}", "{{IMAGE}}"),
]


def loopify(body: str) -> str:
    """Đổi biến trong thân vòng lặp sang placeholder phần tử."""
    for pat, rep in LOOP_VARS:
        body = re.sub(pat, rep, body)
    return body


def wrap_for(html: str, expr: str, name: str) -> str:
    """{% for post in <expr> %}BODY{% endfor %}  →  <!--@NAME-->BODY<!--/@NAME-->"""
    pat = re.compile(
        r"\{%\s*for\s+post\s+in\s+" + re.escape(expr) + r"\s*%\}(.*?)\{%\s*endfor\s*%\}",
        re.S,
    )
    if not pat.search(html):
        raise SystemExit(f"  ✗ không tìm thấy vòng lặp `{expr}` (template đã đổi?)")
    return pat.sub(lambda m: f"<!--@{name}-->{loopify(m.group(1))}<!--/@{name}-->", html, count=1)


def wrap_if(html: str, expr: str, name: str) -> str:
    """{% if <expr> %}BODY{% endif %}  →  <!--@NAME-->BODY<!--/@NAME-->"""
    pat = re.compile(
        r"\{%\s*if\s+" + re.escape(expr) + r"\s*%\}(.*?)\{%\s*endif\s*%\}", re.S
    )
    if not pat.search(html):
        raise SystemExit(f"  ✗ không tìm thấy khối `if {expr}`")
    return pat.sub(lambda m: f"<!--@{name}-->{m.group(1)}<!--/@{name}-->", html, count=1)


def finish(html: str) -> str:
    for pat, rep in PAGE_VARS:
        html = re.sub(pat, rep, html)
    leftovers = re.findall(r"\{%.*?%\}", html, re.S)
    if leftovers:
        raise SystemExit(f"  ✗ còn sót cú pháp Jinja: {leftovers[:3]}")
    return html


# ---------------------------------------------------------------- post.html
def scaffold_post(html: str) -> str:
    html = wrap_for(html, "related_posts", "RELATED")
    html = wrap_if(html, "related_posts", "RELATED_BLOCK")
    html = wrap_for(html, "suggested_posts[:3]", "SUGGESTED_A")
    html = wrap_for(html, "suggested_posts[3:6]", "SUGGESTED_B")
    html = wrap_if(html, "suggested_posts", "SUGGESTED_BLOCK")
    return finish(html)


# ------------------------------------------------------------ category.html
def scaffold_category(html: str) -> str:
    html = wrap_for(html, "sorted_posts[:4]", "TOP4")

    # Khối "nhóm 12 bài" dùng {% set %} + range() — rút gọn thành 1 vùng GROUP
    # với 4 vùng con, build.py tự chia bài thành từng nhóm 12.
    start = html.index("{% set total_posts")
    end = html.rindex("{% endfor %}") + len("{% endfor %}")
    block = html[start:end]

    block = re.sub(r"\{%\s*set[^%]*%\}\s*", "", block)
    block = re.sub(r"\{%\s*if\s+idx\s*<\s*total_posts\s*%\}\s*", "", block)
    block = re.sub(r"\s*\{%\s*endif\s*%\}", "", block)
    block = block.replace("{% for group_idx in range(groups_count) %}", "<!--@GROUP-->", 1)

    for lo, hi, name in ((0, 3, "ITEM_A"), (3, 6, "ITEM_B"), (6, 9, "ITEM_C"), (9, 12, "ITEM_D")):
        pat = re.compile(
            r"\{%\s*for\s+i\s+in\s+range\(" + str(lo) + r",\s*" + str(hi) + r"\)\s*%\}(.*?)\{%\s*endfor\s*%\}",
            re.S,
        )
        if not pat.search(block):
            raise SystemExit(f"  ✗ không tìm thấy range({lo}, {hi}) trong khối nhóm")
        block = pat.sub(
            lambda m: f"<!--@{name}-->{loopify(m.group(1))}<!--/@{name}-->", block, count=1
        )

    # {% endfor %} còn lại là của vòng group
    block = re.sub(r"\{%\s*endfor\s*%\}\s*$", "<!--/@GROUP-->", block)
    return finish(html[:start] + block + html[end:])


# ------------------------------------------------------------ homepage.html
def scaffold_homepage(html: str) -> str:
    html = wrap_for(html, "new_posts[:4]", "NEW")
    for cat in (1, 2, 3, 4):
        html = wrap_for(html, f"posts_{cat}[:3]", f"CAT{cat}_A")
        html = wrap_for(html, f"posts_{cat}[3:6]", f"CAT{cat}_B")
    html = wrap_for(html, "posts_5[:3]", "CAT5")
    html = wrap_for(html, "posts_6[:3]", "CAT6")

    # Carousel ảnh đang hardcode 10 thẻ <img> → thành vùng động lấy từ Sự kiện
    car = re.compile(
        r'(<div id="carouselSmall" class="carousel slide"[^>]*>\s*<div class="carousel-inner">)(.*?)(</div>)',
        re.S,
    )
    if not car.search(html):
        raise SystemExit("  ✗ không tìm thấy #carouselSmall để gắn vùng GALLERY")
    html = car.sub(
        r'\1\n<!--@GALLERY-->'
        '\n                <div class="carousel-item{{ACTIVE}}">'
        '\n                  <img src="{{IMAGE}}" class="d-block w-100" alt="{{ALT}}" loading="lazy">'
        '\n                </div>'
        '\n<!--/@GALLERY-->\n              \\3',
        html,
        count=1,
    )
    return finish(html)


# -------------------------------------------------------------- images.html
def scaffold_images(html: str) -> str:
    pat = re.compile(r"\{%\s*for\s+image\s+in\s+images\s*%\}(.*?)\{%\s*endfor\s*%\}", re.S)
    if not pat.search(html):
        raise SystemExit("  ✗ không tìm thấy vòng lặp ảnh")
    html = pat.sub(lambda m: f"<!--@GALLERY-->{m.group(1)}<!--/@GALLERY-->", html, count=1)
    return finish(html)


# ------------------------------------------------------------- sitemap.xml
def scaffold_sitemap(xml: str) -> str:
    pat = re.compile(r"\{%\s*for\s+post\s+in\s+posts\s*%\}(.*?)\{%\s*endfor\s*%\}", re.S)
    xml = pat.sub(lambda m: f"<!--@URLS-->{loopify(m.group(1))}<!--/@URLS-->", xml, count=1)
    return finish(xml)


JOBS = [
    ("post.html", scaffold_post),
    ("category.html", scaffold_category),
    ("homepage.html", scaffold_homepage),
    ("images.html", scaffold_images),
    ("sitemap.xml", scaffold_sitemap),
]


def main() -> None:
    force = "--force" in sys.argv
    for name, fn in JOBS:
        path = TPL / name
        src = path.read_text(encoding="utf-8")
        if DONE_MARK in src and not force:
            print(f"  ⏭  {name} đã chuyển rồi, bỏ qua (dùng --force để ghi đè)")
            continue
        out = fn(src)
        path.write_text(DONE_MARK + "\n" + out, encoding="utf-8")
        print(f"  ✓ {name}")


if __name__ == "__main__":
    main()
