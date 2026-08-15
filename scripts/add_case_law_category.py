#!/usr/bin/env python3
"""Thêm danh mục mới "Tổng hợp án lệ" vào menu + footer + trang chủ.

CHẠY MỘT LẦN khi khởi tạo dự án. Vị trí: ngay sau "Văn bản pháp luật",
trước "Hình ảnh" trên thanh menu.

Chạm vào:
  templates/*.html   — nguồn thiết kế sống của trang sinh tự động
  html/*.html        — 4 trang tĩnh viết tay (giới thiệu, liên hệ, tìm kiếm, tư vấn)

Sau khi chạy, script này không cần chạy lại — menu đã nằm trong thiết kế.
Dùng: python3 scripts/add_case_law_category.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NAV_ANCHOR = """          <li class="nav-item">
            <a class="nav-link" href="./van-ban-phap-luat.html">Văn bản pháp luật</a>
          </li>
"""
NAV_NEW = """          <li class="nav-item">
            <a class="nav-link" href="./tong-hop-an-le.html">Tổng hợp án lệ</a>
          </li>
"""

FOOTER_ANCHOR = '<a href="./van-ban-phap-luat.html">VĂN BẢN PHÁP LUẬT</a>'
FOOTER_NEW = '<a href="./tong-hop-an-le.html">TỔNG HỢP ÁN LỆ</a>'

# Khối trang chủ cho danh mục mới — dựng theo đúng layout khối "Văn bản pháp
# luật" đã có (hàng 3 box), đặt ngay trước khối "Đối tác".
HOME_ANCHOR = """  <div class="container">
    <h2 class="text-uppercase mt-30 section-title news">Đối tác</h2>"""

HOME_NEW = """  <div class="category-news">
    <div class="container">
      <div class="row">
        <div class="col-12">
          <a class="category-title" href="./tong-hop-an-le.html">
            <h2 class="text-uppercase mt-30 section-title news">Tổng hợp án lệ</h2>
          </a>
          <div class="row">
            <!--@CAT7-->
              <div class="col-12 col-lg-4 mb-4">
                <div class="box-article">
                  <div class="article-img">
                    <a href="{{URL}}">
                      <img src="{{IMAGE}}" class="img-fluid mr-3 mb-md-2" alt="{{TITLE}}" loading="lazy">
                    </a>
                  </div>
                  <p class="article-title">
                    <a href="{{URL}}">{{TITLE}}</a>
                  </p>
                </div>
              </div>
            <!--/@CAT7-->
          </div>
        </div>
      </div>
    </div>
  </div>
"""

TARGETS = [
    ROOT / "templates" / "post.html",
    ROOT / "templates" / "category.html",
    ROOT / "templates" / "homepage.html",
    ROOT / "templates" / "images.html",
    ROOT / "html" / "gioi-thieu.html",
    ROOT / "html" / "lien-he.html",
    ROOT / "html" / "tim-kiem.html",
    ROOT / "html" / "tu-van-phap-luat.html",
]


def main() -> None:
    for path in TARGETS:
        src = path.read_text(encoding="utf-8")
        if "tong-hop-an-le.html" in src:
            print(f"  ⏭  {path.name} đã có sẵn danh mục mới")
            continue
        if NAV_ANCHOR not in src:
            raise SystemExit(f"  ✗ {path.name}: không tìm thấy mốc neo menu")
        src = src.replace(NAV_ANCHOR, NAV_ANCHOR + NAV_NEW, 1)
        if FOOTER_ANCHOR in src:
            src = src.replace(FOOTER_ANCHOR, FOOTER_ANCHOR + "\n          " + FOOTER_NEW, 1)
        path.write_text(src, encoding="utf-8")
        print(f"  ✓ {path.name}")

    home = ROOT / "templates" / "homepage.html"
    src = home.read_text(encoding="utf-8")
    if "<!--@CAT7-->" in src:
        print("  ⏭  homepage.html đã có khối Tổng hợp án lệ")
        return
    if HOME_ANCHOR not in src:
        raise SystemExit("  ✗ homepage.html: không tìm thấy mốc neo khối Đối tác")
    home.write_text(src.replace(HOME_ANCHOR, HOME_NEW + HOME_ANCHOR, 1), encoding="utf-8")
    print("  ✓ homepage.html: thêm khối Tổng hợp án lệ")


if __name__ == "__main__":
    main()
