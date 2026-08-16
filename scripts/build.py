#!/usr/bin/env python3
"""Sinh toàn bộ site tĩnh từ data/ + templates/ — chạy trên GitHub Actions.

    data/posts.json                 index tổng (GAS ghi, commit CHỐT của mọi thao tác)
    data/news/<slug>/detail.json    nội dung đầy đủ 1 bài (GAS ghi)
              ↓  build.py
    html/<slug>.html                trang bài viết
    html/<category>.html            trang danh mục (8 trang)
    html/index.html                 trang chủ
    html/hinh-anh.html              thư viện ảnh (gom từ danh mục Sự kiện)
    html/sitemap.xml                sitemap
    html/data/posts.json            index rút gọn cho trang tìm kiếm (không có content)
    html/_redirects                 redirect cho Cloudflare Pages

KHÔNG sửa tay bất kỳ file nào trong danh sách sinh ra ở trên — build sau ghi đè.
Chỗ sửa thiết kế là templates/.

Chỉ dùng thư viện chuẩn của Python, không cài gì thêm.

Dùng:
    python3 scripts/build.py            # build toàn bộ
    python3 scripts/build.py --check    # chỉ kiểm tra dữ liệu, không ghi file
"""

import html as html_lib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TPL = ROOT / "templates"
OUT = ROOT / "html"

SITE_URL = "https://luatdonghanoi.vn"

# --- Danh mục set cứng (không quản lý qua CMS) --------------------------------
# Thứ tự trong list = thứ tự hiển thị trên menu.
# `home_block` = tên vùng khối tương ứng trên trang chủ (None = không lên trang chủ).
CATEGORIES = [
    {"id": "1", "name": "Doanh nghiệp",      "slug": "doanh-nghiep.html",       "home": ("CAT1_A", "CAT1_B")},
    {"id": "3", "name": "Dân sự",            "slug": "dan-su.html",             "home": ("CAT3_A", "CAT3_B")},
    {"id": "4", "name": "Hình sự",           "slug": "hinh-su.html",            "home": ("CAT4_A", "CAT4_B")},
    {"id": "2", "name": "Sở hữu trí tuệ",    "slug": "so-huu-tri-tue.html",     "home": ("CAT2_A", "CAT2_B")},
    {"id": "5", "name": "Hỏi đáp pháp luật", "slug": "hoi-dap-phap-luat.html",  "home": ("CAT5",)},
    {"id": "6", "name": "Văn bản pháp luật", "slug": "van-ban-phap-luat.html",  "home": ("CAT6",)},
    {"id": "7", "name": "Tổng hợp án lệ",    "slug": "tong-hop-an-le.html",     "home": ("CAT7",)},
    {"id": "0", "name": "Sự kiện",           "slug": "su-kien.html",            "home": None},
]
BY_ID = {c["id"]: c for c in CATEGORIES}

# Danh mục "Sự kiện" là đặc biệt: ảnh trong nội dung bài được gom vào trang
# Hình ảnh và 10 ảnh mới nhất lên carousel trang chủ.
GALLERY_CATEGORY = "0"
HOME_GALLERY_LIMIT = 10

PLACEHOLDER = re.compile(r"\{\{([A-Z_0-9]+)\}\}")


# ------------------------------------------------------------------ tiện ích
def esc(value) -> str:
    """Escape cho nội dung nhúng vào HTML/thuộc tính. Luôn dùng cho dữ liệu người nhập."""
    return html_lib.escape(str(value or ""), quote=True)


def fill(template: str, values: dict) -> str:
    """Thay {{KEY}} bằng values[KEY]. Thiếu key → lỗi rõ ràng, không âm thầm để trống."""
    def sub(m):
        key = m.group(1)
        if key not in values:
            raise KeyError(f"Template dùng {{{{{key}}}}} nhưng build.py không truyền giá trị")
        return values[key]
    return PLACEHOLDER.sub(sub, template)


def region(name: str):
    return re.compile(r"<!--@" + name + r"-->(.*?)<!--/@" + name + r"-->", re.S)


def render_region(doc: str, name: str, items: list, mapper) -> str:
    """Lặp vùng <!--@NAME--> theo `items`. Danh sách rỗng → vùng biến mất hoàn toàn."""
    pat = region(name)
    m = pat.search(doc)
    if not m:
        raise SystemExit(f"✗ Không tìm thấy vùng @{name} trong template — thiết kế đã đổi mốc neo?")
    item_tpl = m.group(1)
    body = "".join(fill(item_tpl, mapper(it, i)) for i, it in enumerate(items))
    return doc[: m.start()] + body + doc[m.end():]


def drop_region_if_empty(doc: str, name: str, keep: bool) -> str:
    """Giữ nguyên nội dung vùng bao (bỏ marker) nếu keep, ngược lại xoá cả vùng."""
    pat = region(name)
    m = pat.search(doc)
    if not m:
        raise SystemExit(f"✗ Không tìm thấy vùng bao @{name}")
    return doc[: m.start()] + (m.group(1) if keep else "") + doc[m.end():]


def truncate(text: str, length: int = 250, end: str = "...") -> str:
    """Cắt cứng như filter `truncate(250, True)` của Jinja mà template cũ đang dùng."""
    text = str(text or "")
    if len(text) <= length + 5:
        return text
    return text[: length - len(end)] + end


def normalize_src(src: str) -> str:
    """Đưa mọi kiểu đường dẫn ảnh về dạng gốc `images/...`.

    Nội dung bài viết cũ lẫn lộn 3 kiểu: tuyệt đối (https://luatdonghanoi.vn/...),
    tương đối ngược (../images/...) và tương đối thẳng (images/...). Trang thư
    viện ảnh và trang chủ đều nằm ở gốc site nên chỉ dạng thứ ba là đúng.
    """
    src = src.strip()
    for prefix in (SITE_URL + "/", "http://luatdonghanoi.vn/"):
        if src.startswith(prefix):
            return src[len(prefix):]
    if src.startswith(("http://", "https://", "data:")):
        return src           # ảnh host ở nơi khác — để nguyên
    return re.sub(r"^(?:\.\.?/)+|^/", "", src)


def post_fields(post: dict, index: int = 0) -> dict:
    return {
        "URL": esc(post.get("url")),
        "IMAGE": esc(post.get("image")),
        "TITLE": esc(post.get("title")),
        "DESC": esc(post.get("description")),
        "CREATED_AT": esc(post.get("created_at")),
    }


def post_fields_short(post: dict, index: int = 0) -> dict:
    """Như post_fields nhưng cắt mô tả — khối "bài mới nhất" trên trang chủ."""
    return {**post_fields(post, index), "DESC": esc(truncate(post.get("description")))}


def read_template(name: str) -> str:
    return (TPL / name).read_text(encoding="utf-8").replace("<!--@SCAFFOLDED-->\n", "", 1)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ------------------------------------------------------------------ nạp dữ liệu
def load_index() -> list:
    src = DATA / "posts.json"
    if not src.exists():
        raise SystemExit("✗ Thiếu data/posts.json — CMS chưa ghi dữ liệu nào?")
    posts = json.loads(src.read_text(encoding="utf-8"))
    for p in posts:
        p["id"] = int(p.get("id", 0))
    return sorted(posts, key=lambda p: p["id"], reverse=True)


def load_detail(post: dict) -> dict:
    """Bản ghi đầy đủ (có content). Thiếu file detail → bỏ qua bài đó, không làm sập build."""
    slug = post["url"].removesuffix(".html")
    path = DATA / "news" / slug / "detail.json"
    if not path.exists():
        print(f"  ! bỏ qua {post['url']}: thiếu {path.relative_to(ROOT)}")
        return {}
    detail = json.loads(path.read_text(encoding="utf-8"))
    return {**post, **detail}


# ------------------------------------------------------------------ trang bài
def build_posts(posts: list) -> int:
    tpl = read_template("post.html")
    count = 0
    for post in posts:
        full = load_detail(post)
        if not full:
            continue
        cat = BY_ID.get(str(full.get("category")), {"name": "", "slug": ""})
        same_cat = [p for p in posts if str(p.get("category")) == str(full.get("category"))
                    and p["id"] < full["id"]][:3]
        related_ids = {p["id"] for p in same_cat}
        suggested = [p for p in posts if p["id"] < full["id"] and p["id"] not in related_ids][:6]

        doc = tpl
        doc = drop_region_if_empty(doc, "RELATED_BLOCK", bool(same_cat))
        if same_cat:
            doc = render_region(doc, "RELATED", same_cat, post_fields)
        doc = drop_region_if_empty(doc, "SUGGESTED_BLOCK", bool(suggested))
        if suggested:
            doc = render_region(doc, "SUGGESTED_A", suggested[:3], post_fields)
            doc = render_region(doc, "SUGGESTED_B", suggested[3:6], post_fields)

        doc = fill(doc, {
            "TITLE": esc(full.get("title")),
            "DESCRIPTION": esc(full.get("description")),
            "KEYWORDS": esc(full.get("keywords")),
            "IMAGE": esc(full.get("image")),
            "URL": esc(full.get("url")),
            "CREATED_AT": esc(full.get("created_at")),
            "CATEGORY": esc(cat["name"]),
            "CATEGORY_URL": esc(cat["slug"]),
            "CONTENT": full.get("content") or "",   # HTML thật, không escape
        })
        write(OUT / full["url"], doc)
        count += 1
    return count


# --------------------------------------------------------------- trang danh mục
def build_categories(posts: list) -> None:
    tpl = read_template("category.html")
    for cat in CATEGORIES:
        items = [p for p in posts if str(p.get("category")) == cat["id"]]
        doc = render_region(tpl, "TOP4", items[:4], post_fields)

        rest = items[4:]
        groups = [rest[i:i + 12] for i in range(0, len(rest), 12)]
        m = region("GROUP").search(doc)
        group_tpl = m.group(1)
        rendered = []
        for g in groups:
            block = group_tpl
            for name, chunk in (("ITEM_A", g[0:3]), ("ITEM_B", g[3:6]),
                                ("ITEM_C", g[6:9]), ("ITEM_D", g[9:12])):
                block = render_region(block, name, chunk, post_fields)
            rendered.append(block)
        doc = doc[: m.start()] + "".join(rendered) + doc[m.end():]

        doc = fill(doc, {"CATEGORY": esc(cat["name"]), "CATEGORY_URL": esc(cat["slug"])})
        write(OUT / cat["slug"], doc)
        print(f"  · {cat['slug']:<26} {len(items):>3} bài")


# ----------------------------------------------------------------- thư viện ảnh
IMG_TAG = re.compile(r"<img[^>]+>", re.I)
ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def collect_event_images(posts: list) -> list:
    """Gom ảnh trong nội dung các bài thuộc danh mục Sự kiện, mới nhất trước.

    Trả về [{"src": ..., "alt": ...}] theo thứ tự bài mới → cũ, trong 1 bài giữ
    nguyên thứ tự ảnh xuất hiện trong nội dung.
    """
    images, seen = [], set()
    for post in posts:
        if str(post.get("category")) != GALLERY_CATEGORY:
            continue
        full = load_detail(post)
        for tag in IMG_TAG.findall(full.get("content") or ""):
            attrs = dict(ATTR.findall(tag))
            src = attrs.get("src", "").strip()
            if not src or src in seen:
                continue
            seen.add(src)
            images.append({"src": normalize_src(src), "alt": attrs.get("alt") or post.get("title") or "Ảnh Luật Đông Hà Nội"})
    return images


def build_images_page(images: list) -> None:
    tpl = read_template("images.html")
    doc = render_region(tpl, "GALLERY", images,
                        lambda im, i: {"IMAGE": esc(im["src"]), "ALT": esc(im["alt"])})
    write(OUT / "hinh-anh.html", doc)
    print(f"  · hinh-anh.html             {len(images):>3} ảnh")


# ------------------------------------------------------------------- trang chủ
def build_homepage(posts: list, images: list) -> None:
    doc = read_template("homepage.html")
    doc = render_region(doc, "NEW", posts[:4], post_fields_short)

    for cat in CATEGORIES:
        if not cat["home"]:
            continue
        items = [p for p in posts if str(p.get("category")) == cat["id"]]
        regions = cat["home"]
        if len(regions) == 2:
            doc = render_region(doc, regions[0], items[:3], post_fields)
            doc = render_region(doc, regions[1], items[3:6], post_fields)
        else:
            doc = render_region(doc, regions[0], items[:3], post_fields)

    doc = render_region(
        doc, "GALLERY", images[:HOME_GALLERY_LIMIT],
        lambda im, i: {"IMAGE": esc(im["src"]), "ALT": esc(im["alt"]),
                       "ACTIVE": " active" if i == 0 else ""},
    )
    write(OUT / "index.html", doc)

    # Bản sao y hệt, chỉ để Cloudflare phục vụ trang chủ tại "/".
    #
    # Cloudflare LUÔN 301 /index.html về / — luật riêng, không tắt được bằng
    # html_handling. Mà html_handling="none" (bắt buộc, để giữ đuôi .html cho
    # 227 URL đã index) lại khiến / không còn tự trỏ vào index.html. Worker
    # rewrite / → /index.html thì nhận đúng cái 301 đó và thành vòng lặp.
    # Phục vụ / từ một tên file khác là đường thoát duy nhất không đụng tới
    # URL nào đang có. File này không nằm trong sitemap, không được link tới,
    # và mang cùng thẻ canonical trỏ về gốc site nên không tạo trùng nội dung.
    write(OUT / "home.html", doc)
    print(f"  · index.html + home.html    {min(len(images), HOME_GALLERY_LIMIT):>3} ảnh carousel")


# --------------------------------------------------------------------- sitemap
def build_sitemap(posts: list) -> None:
    tpl = read_template("sitemap.xml")
    doc = render_region(tpl, "URLS", posts, lambda p, i: {"URL": esc(p.get("url"))})
    write(OUT / "sitemap.xml", doc)


# ------------------------------------------- index rút gọn cho trang tìm kiếm
def build_public_index(posts: list) -> None:
    """html/data/posts.json — CHỈ metadata, KHÔNG có content.

    Trang tìm kiếm tải file này ở phía trình duyệt; kèm content thì mỗi lượt
    tìm kiếm phải tải vài MB vô ích.
    """
    slim = [{
        "id": p["id"],
        "title": p.get("title", ""),
        "url": p.get("url", ""),
        "description": p.get("description", ""),
        "image": p.get("image", ""),
        "category": str(p.get("category", "")),
        "created_at": p.get("created_at", ""),
    } for p in posts]
    write(OUT / "data" / "posts.json", json.dumps(slim, ensure_ascii=False, indent=1))


# ------------------------------------------------- redirect cho Cloudflare Pages
def build_redirects() -> None:
    """Chuyển danh sách redirect (di sản từ vercel.json) sang định dạng _redirects."""
    src = DATA / "redirects.json"
    if not src.exists():
        return
    rules = json.loads(src.read_text(encoding="utf-8"))
    lines = [f"{r['source']}  {r['destination']}  {r.get('statusCode', 301)}" for r in rules]
    write(OUT / "_redirects", "\n".join(lines) + "\n")
    print(f"  · _redirects                {len(lines):>3} luật")


# ------------------------------------------------- dọn trang của bài đã xoá
MANIFEST = DATA / "generated-pages.json"


def prune_orphans(expected: set) -> None:
    """Xoá những trang build từng sinh ra mà lần này không còn trong dữ liệu.

    Không có bước này thì bài bị xoá vẫn nằm nguyên trên website: build chỉ ghi
    đè file nó dựng, chưa bao giờ dọn file thừa. Trang cũ vẫn truy cập được và
    vẫn nằm trong danh mục cho tới khi ai đó xoá tay.

    Chỉ xoá file có TÊN TRONG MANIFEST của lần build trước — tuyệt đối không suy
    đoán theo kiểu "file nào không nằm trong danh sách mong đợi thì xoá". Ở gốc
    html/ còn 5 trang viết tay (giới thiệu, liên hệ, tìm kiếm, tư vấn, admin);
    đoán mò là xoá nhầm chúng.
    """
    previous = set()
    if MANIFEST.exists():
        previous = set(json.loads(MANIFEST.read_text(encoding="utf-8")))

    for name in sorted(previous - expected):
        path = OUT / name
        if path.exists():
            path.unlink()
            print(f"  · gỡ trang của bài đã xoá: {name}")

    write(MANIFEST, json.dumps(sorted(expected), ensure_ascii=False, indent=1))


# ------------------------------------------------------------------------ main
def main() -> None:
    check_only = "--check" in sys.argv
    posts = load_index()
    print(f"Nạp {len(posts)} bài từ data/posts.json")

    seen = {}
    for p in posts:
        if not p.get("url", "").endswith(".html"):
            raise SystemExit(f"✗ url không hợp lệ ở bài id={p['id']}: {p.get('url')!r}")
        if str(p.get("category")) not in BY_ID:
            raise SystemExit(f"✗ danh mục lạ ở bài id={p['id']}: {p.get('category')!r}")
        if p["url"] in seen:
            raise SystemExit(f"✗ trùng url {p['url']} giữa bài {seen[p['url']]} và {p['id']}")
        seen[p["url"]] = p["id"]
    if check_only:
        print("✓ Dữ liệu hợp lệ (--check: không ghi file nào)")
        return

    n = build_posts(posts)
    print(f"  · {n} trang bài viết")
    build_categories(posts)
    images = collect_event_images(posts)
    build_images_page(images)
    build_homepage(posts, images)
    build_sitemap(posts)
    build_public_index(posts)
    build_redirects()

    prune_orphans({p["url"] for p in posts}
                  | {c["slug"] for c in CATEGORIES}
                  | {"index.html", "home.html", "hinh-anh.html"})
    print("✓ Build xong")


if __name__ == "__main__":
    main()
