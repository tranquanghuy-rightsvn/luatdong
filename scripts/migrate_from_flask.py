#!/usr/bin/env python3
"""Chuyển 227 bài của CMS Flask cũ sang cấu trúc data/ của pipeline mới.

Đọc (chỉ đọc, không sửa gì bên dự án cũ):
    ../html/data/posts.json     kho bài viết của app Flask
    ../html/vercel.json         danh sách redirect di sản

Ghi:
    data/posts.json             index tổng (metadata, không có content)
    data/news/<slug>/detail.json bản ghi đầy đủ từng bài
    data/redirects.json         redirect, build.py sẽ đổi sang html/_redirects
    data/_import/all-posts.json gói 1 file để GAS nạp vào Google Sheet trong 1 lần gọi

CHẠY MỘT LẦN khi khởi tạo. Sau đó nguồn chân lý là Google Sheet + data/ trong repo.

Dùng: python3 scripts/migrate_from_flask.py [--legacy-root ../]
"""

import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VN_TZ = timezone(timedelta(hours=7))

FIELDS = ["id", "title", "url", "description", "keywords", "category", "image", "created_at"]


def legacy_root() -> Path:
    if "--legacy-root" in sys.argv:
        return Path(sys.argv[sys.argv.index("--legacy-root") + 1]).resolve()
    return ROOT.parent


def main() -> None:
    old = legacy_root()
    src = old / "html" / "data" / "posts.json"
    if not src.exists():
        raise SystemExit(f"✗ Không thấy {src}")

    posts = json.loads(src.read_text(encoding="utf-8"))
    posts.sort(key=lambda p: int(p.get("id", 0)), reverse=True)
    stamp = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")

    index, bundle = [], []
    for p in posts:
        url = p["url"]
        if not url.endswith(".html"):
            raise SystemExit(f"✗ url lạ ở bài {p.get('id')}: {url!r}")
        slug = url[: -len(".html")]

        meta = {k: (int(p["id"]) if k == "id" else str(p.get(k) or "")) for k in FIELDS}
        meta["updated_at"] = stamp          # version cho cache phía client của CMS
        meta["author"] = ""                 # cột mới, dữ liệu cũ để trống
        meta["status"] = "published"
        index.append(meta)

        detail = {**meta, "content": p.get("content") or ""}
        out = DATA / "news" / slug / "detail.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
        bundle.append(detail)

    (DATA / "posts.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    imp = DATA / "_import"
    imp.mkdir(parents=True, exist_ok=True)
    (imp / "all-posts.json").write_text(
        json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    print(f"  ✓ data/posts.json                 {len(index)} bài")
    print(f"  ✓ data/news/<slug>/detail.json    {len(bundle)} file")
    print(f"  ✓ data/_import/all-posts.json     gói nạp vào Sheet")

    # --- redirect di sản: vercel.json → data/redirects.json ---
    vercel = old / "html" / "vercel.json"
    if vercel.exists():
        rules = json.loads(vercel.read_text(encoding="utf-8")).get("redirects", [])
        norm = [{
            "source": r["source"],
            "destination": r["destination"],
            "statusCode": r.get("statusCode", 301),
        } for r in rules]
        (DATA / "redirects.json").write_text(
            json.dumps(norm, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  ✓ data/redirects.json             {len(norm)} luật")

    longest = max(len(b["content"]) for b in bundle)
    print(f"\n  Bài dài nhất: {longest:,} ký tự "
          f"(ô Google Sheets tối đa 50.000 — CMS tự chia cột khi vượt 45.000)")


if __name__ == "__main__":
    main()
