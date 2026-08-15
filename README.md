# luatdonghanoi.vn — CMS Google Apps Script + site tĩnh

Thay thế app Flask + pywebview (`main.py`) chạy trên máy cá nhân bằng CMS chạy
trên nền web, không server, không database trả phí.

```
GAS (CMS + đăng nhập OTP + phân quyền + upload ảnh)
   │  Google Sheets = nguồn chân lý nội bộ
   │  Drive = ảnh tạm lúc đang soạn bài
   │  commit qua GitHub Contents API
   ▼
repo:  data/  ──►  GitHub Actions (scripts/build.py)  ──►  html/  ──►  Cloudflare Pages
```

## Cấu trúc thư mục

| Đường dẫn | Ai ghi | Sửa tay được không |
|---|---|---|
| `gas/` | Người (deploy bằng clasp) | Có — **không nằm trong git** |
| `data/posts.json` | GAS khi Lưu/Xoá | **Không** |
| `data/news/<slug>/detail.json` | GAS khi Lưu | **Không** |
| `data/redirects.json` | Người | Có |
| `templates/*.html` | Người | **Có — đây là nơi sửa thiết kế** |
| `scripts/*.py`, `.github/workflows/*.yml` | Người | Có |
| `html/**/*.html` (trang sinh tự động) | CI | **Không** — build sau ghi đè |
| `html/gioi-thieu.html`, `lien-he.html`, `tim-kiem.html`, `tu-van-phap-luat.html` | Người | Có — 4 trang viết tay |
| `html/images/**` | GAS đẩy ảnh | Không cần |

Ảnh ghi **thẳng** vào `html/images/posts/<id>/`, `data/` chỉ giữ đường dẫn —
nếu để cả 2 nơi thì repo phình gấp đôi vô nghĩa.

## Danh mục (set cứng, không quản lý qua CMS)

| id | Tên | Trang |
|---|---|---|
| 1 | Doanh nghiệp | `doanh-nghiep.html` |
| 3 | Dân sự | `dan-su.html` |
| 4 | Hình sự | `hinh-su.html` |
| 2 | Sở hữu trí tuệ | `so-huu-tri-tue.html` |
| 5 | Hỏi đáp pháp luật | `hoi-dap-phap-luat.html` |
| 6 | Văn bản pháp luật | `van-ban-phap-luat.html` |
| 7 | **Tổng hợp án lệ** (mới) | `tong-hop-an-le.html` |
| 0 | Sự kiện | `su-kien.html` |

Đổi danh mục phải sửa **2 chỗ cho khớp nhau**: `CATEGORIES` trong
`scripts/build.py` và `CATEGORIES` trong `gas/Code.js`.

## Liên hệ

Form trên `lien-he.html` vẫn ghi **thẳng vào Firestore** như trước (collection
`contacts`, các field `fullName / email / phone / address / message / timestamp`).
CMS chỉ **đọc**, qua Firestore REST API với service account (JWT RS256 → OAuth2,
token cache 50 phút).

Đánh đổi cần biết: vì trình duyệt ghi thẳng nên không có rate-limit phía server —
chống spam hiện chỉ có honeypot ở client + giới hạn kiểu/độ dài field trong
security rules. Nếu về sau bị spam thật thì mới chuyển đường ghi qua GAS
`doPost`; lúc đó CMS không phải sửa gì vì vẫn đọc từ Firestore.

**"Hình ảnh" không phải danh mục.** `hinh-anh.html` được sinh tự động bằng cách
gom mọi thẻ `<img>` trong nội dung các bài thuộc danh mục **Sự kiện**, mới nhất
trước; 10 ảnh mới nhất trong số đó lên carousel trang chủ. Muốn thêm ảnh vào
trang Hình ảnh thì đăng bài ở danh mục Sự kiện, không có chỗ upload riêng.

## Phân quyền

| Vai trò | Được làm gì |
|---|---|
| `root` | Toàn quyền + quản lý người dùng |
| `editor` | Tạo / sửa / xoá bài viết, xem liên hệ |
| `viewer` | Chỉ xem |

- **Chủ sở hữu script (người deploy) luôn là root**, kể cả khi sheet `Users`
  trống trơn — đây là lan can chống tự khoá mình ra ngoài.
- Giao diện chỉ thêm/sửa/xoá được **editor và viewer**. Muốn thêm root mới phải
  sửa tay trong Google Sheet. Cố ý làm vậy.
- Mọi hàm server đều tự gọi `requireRole_()`. Ẩn nút trên giao diện không phải
  là bảo mật — F12 gọi thẳng hàm vẫn xuyên qua nếu server không tự kiểm tra.

## Cài đặt lần đầu

### 1. Google Sheet + Drive — KHÔNG cần làm gì
Hàm `setup()` tự tạo cả hai và tự ghi `SPREADSHEET_ID` / `DRIVE_FOLDER_ID` vào
Script Properties, rồi in ra URL của chúng. Xem bước 3.

### 2. Repo GitHub
- Tạo repo, push toàn bộ thư mục này lên nhánh `main`.
- Tạo fine-grained PAT với quyền **Contents: Read and write** trên đúng repo đó.

### 3. Apps Script
```bash
cd gas
clasp create --type webapp --title "CMS Luat Dong Ha Noi"
clasp push
```
Script Properties (Project Settings → Script Properties):

Chạy tay hàm **`setup()`** trong editor trước tiên — nó tạo Google Sheet + thư
mục Drive, tự lưu id, và in ra Log danh sách khoá còn thiếu. Sau đó điền nốt:

| Key | setup() tự tạo? | Ghi chú |
|---|---|---|
| `SPREADSHEET_ID` | ✔ tự | |
| `DRIVE_FOLDER_ID` | ✔ tự | |
| `GH_OWNER` / `GH_REPO` | điền tay | |
| `GH_TOKEN` | điền tay | PAT ở bước 2 |
| `FIREBASE_PROJECT_ID` | ✔ | `luatdonghanoi` |
| `FB_SA_EMAIL` | ✔ | email service account đọc Firestore |
| `FB_SA_PRIVATE_KEY` | ✔ | private key trong file JSON service account, dán nguyên chuỗi kèm `\n` |
| `GH_BRANCH` | | mặc định `main` |
| `SITE_URL` | | mặc định `https://luatdonghanoi.vn` |

Thiếu `GH_*` hay `FB_*` vẫn đăng nhập vào CMS được, chỉ mất chức năng tương
ứng (lưu bài / xem liên hệ) — cứ vào xem trước rồi bổ sung dần.

Rồi:
1. Chạy `setup()` lần nữa nếu vừa điền thêm khoá — nó in lại trạng thái.
2. Deploy → New deployment → Web app → Execute as **Me**, Who has access
   **Anyone** → copy URL `/exec` (URL này để mở CMS, bookmark lại).

### 3b. Service account đọc Firestore
Firebase Console → Project settings → Service accounts → Generate new private
key. File JSON tải về có `client_email` (→ `FB_SA_EMAIL`) và `private_key`
(→ `FB_SA_PRIVATE_KEY`). Service account mặc định đã đủ quyền đọc Firestore;
nếu siết quyền thì cấp role **Cloud Datastore Viewer**.

**Siết luật Firestore ngay sau đó.** Service account bỏ qua security rules, nên
có thể khoá đọc công khai hoàn toàn mà CMS vẫn xem được:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /contacts/{doc} {
      allow create: if request.resource.data.keys()
                      .hasOnly(['fullName','email','phone','address','message','timestamp'])
                    && request.resource.data.fullName is string
                    && request.resource.data.fullName.size() < 200
                    && request.resource.data.message is string
                    && request.resource.data.message.size() < 5000;
      allow read, update, delete: if false;   // chỉ CMS (service account) đọc được
    }
  }
}
```

Nếu rules hiện tại đang cho `allow read: if true` thì **bất kỳ ai cũng đọc được
toàn bộ họ tên/email/điện thoại khách hàng** chỉ bằng API key nằm công khai
trong `lien-he.html` — đây là việc nên làm trước tiên, không phải sau.

### 4. Nạp 227 bài cũ
```bash
python3 scripts/migrate_from_flask.py    # đọc ../html/data/posts.json của app Flask
python3 scripts/build.py                 # kiểm tra build ra đúng
git add . && git commit -m "Khởi tạo dữ liệu" && git push
```
Rồi mở CMS bằng tài khoản root, chạy `importFromRepo` (Apps Script editor →
chọn hàm → Run) để nạp vào Sheet. Hàm này **từ chối chạy nếu sheet Posts đã có
dữ liệu**, tránh nạp đè nhầm.

Nạp xong có thể xoá `data/_import/` (2,4 MB) — nó chỉ phục vụ đúng lần nạp này.

### 5. Cloudflare Pages
- Connect repo, **Build command: để trống**, **Output directory: `html`**.
- CI đã commit sẵn `html/` nên Pages chỉ việc phục vụ file tĩnh.
- Trỏ domain `luatdonghanoi.vn` sang Pages project.
- Redirect di sản nằm ở `html/_redirects` (224 luật, chuyển từ `vercel.json` cũ).

## Quy trình làm việc hằng ngày

**Không còn nút Deploy.** Người biên tập bấm Lưu → GAS commit lên repo →
CI build → Cloudflare deploy. Site cập nhật sau 1–2 phút, không ai phải bấm gì thêm.

Đổi thiết kế: sửa `templates/*.html` → commit → CI tự build lại toàn bộ.

Sửa code trong `gas/`: `clasp push`, rồi **Deploy → Manage deployments → Edit →
New version**. Chọn "New deployment" sẽ sinh URL `/exec` MỚI trong khi URL cũ
vẫn chạy code cũ — nhìn thì như deploy hỏng.

## Kiểm tra trước khi báo "xong" một thay đổi

- [ ] Đã test bằng dữ liệu giả (bài có `&`, `"`, dấu tiếng Việt), xem output tận
      mắt, xoá sạch bài giả rồi build lại, `git status` phải sạch.
- [ ] Chạy `python3 scripts/build.py` **2 lần liên tiếp**, lần 2 không sinh diff nào.
- [ ] Hàm server mới có `requireRole_()` chưa (không chỉ ẩn nút)?
- [ ] Đổi tên field/thư mục: đã `grep` toàn repo tìm chỗ tham chiếu cũ chưa?
- [ ] Có sửa file nào trong `gas/`: đã ghi rõ tên từng file đã đổi + nhắc
      `clasp push` + New version chưa? (`gas/` không nằm trong git nên không ai
      tự biết được bằng `git diff`.)

## Những chỗ đã cố ý làm khác app Flask cũ

| Cũ | Mới | Vì sao |
|---|---|---|
| Nút Deploy trong app | Không có; Lưu là publish luôn | Người biên tập không cần biết khái niệm deploy |
| `html/data/posts.json` 3,7 MB kèm content | Bản rút gọn ~60 KB, không content | Trang tìm kiếm tải file này mỗi lượt tìm |
| Firebase Firestore cho form liên hệ | **Giữ nguyên Firestore**; CMS đọc qua service account | Không phải migrate dữ liệu liên hệ cũ, không có giai đoạn 2 nơi cùng nhận |
| Ảnh trong bài: `images/posts/<id>/<n>/<tên gốc>` | `images/posts/<id>/NN.ext`, đánh số bất biến | Ảnh cũ giữ nguyên tên → không mất cache trình duyệt |
| Cắt ảnh bằng Pillow phía server | Cắt bằng canvas phía trình duyệt | Thuật toán y hệt (cắt giữa → 500×333 → WebP q85); GAS không có thư viện ảnh |
| Không có auth | OTP qua email + 3 mức quyền | Nhiều người dùng chung, không còn giới hạn 1 máy |

Ảnh của 227 bài cũ giữ nguyên đường dẫn `images/posts/<id>/<n>/<tên gốc>` — quy
tắc đánh số mới chỉ áp cho ảnh upload từ nay về sau, nên không có file ảnh nào
bị đụng tới khi migrate.
