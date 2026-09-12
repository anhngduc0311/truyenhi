# 🚀 Hướng Dẫn: Tải Truyện HentaiVNReal Lưu Vào Cloud Storage Bucket & Web API Trên Ubuntu

Tài liệu này hướng dẫn chi tiết cách chạy file **`tai_mangadex_ubuntu.sh`** trên máy tính hoặc máy chủ **Ubuntu / Debian** để cào toàn bộ hơn **39.000+ bộ truyện HentaiVNReal**, tự động lưu trực tiếp vào Cloud Storage Bucket & Web API NekoHentai:
👉 **Nguồn hỗ trợ**: 
- **HentaiVNReal** (`https://hentaivnreal.com/danh-sach` ~39.000+ truyện từ Mới Nhất ➜ Cũ Nhất)
👉 **Cloud Storage Bucket**: `nekohentai` (Google Cloud Storage / R2 S3 API)  
👉 **CDN Base URL**: `https://img.nekohentai.lol`  
👉 **Web API**: `https://nekohentai.lol/api`  
👉 **Bộ nhớ ảo Swap**: Tự động tạo 4GB / 2GB Swap chống tràn RAM khi chạy đa luồng  
👉 *(Đã tích hợp nén WebP đa luồng, tự động nhận diện Oneshot, ghép Manhwa 5-in-1, chống trùng lặp và dọn dẹp file tạm tức thì)*

---

## ⚙️ Thiết Lập Mặc Định (Đồng bộ chuẩn Zet GUI)

File script đã được cấu hình mặc định sẵn các tùy chọn xử lý chính xác như sau:
* ☑️ **Tự động tải lên Cloud Storage Bucket & Đồng bộ Web API**: `BẬT` (Lưu trực tiếp vào bucket `nekohentai` & đồng bộ website)
* ☑️ **Tự động tạo bộ nhớ ảo Swap (4GB/2GB)**: `BẬT` (Ngăn chặn tràn RAM / OOM Killer khi chạy đa luồng)
* ☑️ **Bỏ qua chapter đã có trên máy / Cloud / Web (Tránh tải trùng / Resume)**: `BẬT` (Kiểm tra và bỏ qua chapter đã tải)
* ☑️ **Tự động nhận diện Oneshot**: `BẬT` (Gán `chapterNumber = 1.0`, `title = "Oneshot"`)
* ☑️ **Ghép ảnh Manhwa 5-in-1 (Tự động khi chapter > 70 ảnh)**: `BẬT` (Tự động ghép 5 lát cắt thành 1 ảnh dài WebP)
* ☑️ **Tự động dọn dẹp file tạm trên VPS**: `BẬT` (Chống đầy dung lượng ổ cứng VPS)
* ⚡ **Luồng tải & upload song song**: `32 luồng` (Tối ưu Turbo Speed)

---

## 🌟 Điểm Vượt Trội Của File Script (Tối Ưu Turbo Speed)

1. **Tự động tạo bộ nhớ ảo Swap (Chống tràn RAM / Out-of-Memory)**:
   - Tự động kiểm tra bộ nhớ RAM và tạo Swapfile 4GB (hoặc 2GB nếu ổ cứng nhỏ) tại `/swapfile`.
   - Giúp các VPS gói thấp (1GB - 2GB RAM) có thể chạy mượt mà 32 luồng tải song song mà không bao giờ bị hệ thống Linux kill tiến trình (`Killed`).
2. **Tăng tốc độ tải & upload vượt trội (gấp 5 - 10 lần)**:
   - **Tái sử dụng kết nối HTTP Keep-Alive (Connection Pooling)**: Không phải tạo lại kết nối SSL/TLS cho từng ảnh, tiết kiệm hàng chục giây cho mỗi chapter.
   - **Nén WebP đa luồng song song**: Nén WebP cùng lúc trên đa nhân CPU với thuật toán tối ưu `method=6`, xử lý xong cả chapter trong tích tắc.
   - **Ghép dải Manhwa song song**: Các nhóm lát cắt Manhwa được xử lý đồng thời.
   - **Tải & upload 32 luồng song song**: Tận dụng tối đa băng thông mạng VPS / máy chủ.
3. **Chỉ cần đúng 1 file duy nhất (`tai_mangadex_ubuntu.sh`)**:
   - Tự động kiểm tra và cài đặt Python 3, pip, Virtualenv và các thư viện cần thiết.
   - Script tự trích xuất mã nguồn engine nếu chưa có trên máy.
4. **Cơ chế chống tràn ổ cứng VPS (Zero-Disk Buildup)**:
   - Tải và xử lý xong chapter nào ➡️ Tự động đẩy ngay lên Cloud Storage Bucket & Web API ➡️ Xóa sạch file đệm trên máy chủ.
   - Dù máy chủ Ubuntu chỉ có ổ cứng 20GB - 40GB vẫn tải được hàng trăm GB truyện mà không bao giờ lo đầy ổ cứng.
5. **Tự động lưu tiến trình (Resume Checkpoint)**:
   - File `crawler_sync_state.json` ghi nhận danh sách truyện và chapter đã tải.
   - Nếu bị đứt mạng, khởi động lại VPS hoặc tắt máy, lần chạy tiếp theo sẽ tự động bỏ qua các truyện/chapter đã có, tiếp tục tải ngay lập tức.
6. **Hỗ trợ chạy ngầm 24/7 (Background Nohup)**:
   - Bạn có thể ngắt kết nối SSH, tắt máy tính cá nhân, máy chủ Ubuntu vẫn tự động tải xuyên ngày đêm.

---

## 📥 Bước 1: Đưa File Lên Máy Chủ Ubuntu

Bạn có thể đưa file `tai_mangadex_ubuntu.sh` lên máy Ubuntu theo một trong các cách sau:

### Cách 1: Sao chép qua lệnh `scp` (từ Windows)
Mở PowerShell trên máy Windows của bạn:
```powershell
scp d:\Project\truyenhi\tai_mangadex_ubuntu.sh user@dia_chi_ip_ubuntu:~/
```

### Cách 2: Nếu máy Ubuntu đã clone Git của dự án
Tại thư mục dự án trên Ubuntu:
```bash
git pull
chmod +x tai_mangadex_ubuntu.sh
```

### Cách 3: Tạo trực tiếp trên máy Ubuntu bằng `nano`
```bash
nano tai_mangadex_ubuntu.sh
# Dán toàn bộ nội dung file tai_mangadex_ubuntu.sh vào, bấm Ctrl+O -> Enter -> Ctrl+X để lưu
chmod +x tai_mangadex_ubuntu.sh
```

---

## ⚡ Bước 2: Khởi Chạy Script Trên Ubuntu

Tại terminal của máy Ubuntu, gõ lệnh:

```bash
bash tai_mangadex_ubuntu.sh
```

Lần đầu tiên khởi chạy:
- Script sẽ tự động tạo bộ nhớ ảo Swap (4GB / 2GB) và cài đặt `python3`, `python3-venv`, `pillow`, `requests`, `cloudscraper`, `beautifulsoup4`, `boto3`.
- Màn hình Menu tương tác sẽ hiển thị:

```text
================================================================
🚀 NEKOHENTAI MANGA DOWNLOADER PRO (UBUNTU CRAWLER)
   File cấu hình: 🟢 Đã có file .env (Đọc từ .env / .env.example)
   Cloud Bucket:  nekohentai (Google Cloud Storage / R2 / S3)
   Web API:       https://nekohentai.lol/api
   Bộ nhớ ảo:     🟢 4096MB (Đã kích hoạt)
----------------------------------------------------------------
⚙️  CẤU HÌNH & TÍNH NĂNG CHUẨN GIAO DIỆN ZET GUI:
   ☑️ Nguồn truyện: HentaiVNReal (~39.000+ bộ, Mới Nhất ➜ Cũ Nhất)
   ☑️ Tự động tải lên Cloud & Đồng bộ Web API: BẬT
   ☑️ Bỏ qua chapter đã có (Web/Cloud/Máy):   BẬT (Tránh tải trùng)
   ☑️ Ghép ảnh Manhwa 5-in-1 (>70 ảnh):        BẬT (Đa luồng WebP)
   ☑️ Xử lý chuẩn xác chương Oneshot:          BẬT
   ⚡ Luồng tải & Upload song song:            32 luồng (Turbo Speed)
   ⚡ Nén WebP chất lượng cao (quality=90):    BẬT
================================================================
  [1] 🔄 Kiểm tra & Tải TRUYỆN MỚI CẬP NHẬT trực tiếp (Quét 5-10 trang đầu)
  [2] 🤖 Tự động kiểm tra & Tải truyện mới NGẦM 24/7 (Auto-Updater định kỳ)
  [3] ⚡ Tải TOÀN BỘ HentaiVNReal trực tiếp trên màn hình (Trang 1 ➜ 982+)
  [4] 🆕 Tải NGẦM toàn bộ HentaiVNReal 24/7 (nohup - Khuyên dùng)
  [5] 🔗 Tải 1 bộ truyện theo Link / Slug HentaiVNReal
  [6] 📊 Xem trạng thái, thống kê & nhật ký (Live Logs)
  [7] 🛑 Dừng tiến trình tải ngầm
  [8] 🛡️  Thiết lập / Bật bộ nhớ ảo Swap (4GB / 2GB)
  [9] 📝 Tạo / Khôi phục file .env từ .env.example
  [0] ❌ Thoát
----------------------------------------------------------------
Chọn thao tác [0-9]:
```

---

## 🚀 Bước 3: Bắt Đầu Tải & Tự Động Cập Nhật Truyện

### Tùy chọn A: Tự động kiểm tra & Tải truyện mới ra chapter NGẦM 24/7 (Auto-Updater)
- Chọn phím **`2`** trên menu (hoặc gõ: `./tai_mangadex_ubuntu.sh --bg-updates 10 30`).
- Tính năng này sẽ quét các trang đầu tiên trên HentaiVNReal (mặc định 10 trang = ~400 bộ truyện mới nhất).
- Nếu phát hiện truyện đã có nhưng **vừa ra thêm chapter mới**, script sẽ **chỉ tải các chapter mới** rồi đẩy lên Cloud S3 & Web API.
- Cứ sau mỗi 30 phút (tùy chỉnh được), tiến trình tự động quét lại vòng lặp mới hoàn toàn tự động 24/7.

### Tùy chọn B: Kiểm tra cập nhật ngay trên màn hình (Foreground)
- Chọn phím **`1`** trên menu (hoặc gõ: `./tai_mangadex_ubuntu.sh --check-updates 10`).
- Script sẽ quét nhanh 10 trang mới nhất, tải ngay các chapter mới hoặc truyện mới toanh chưa có trong hệ thống và hiển thị kết quả trực tiếp.

### Tùy chọn C: Cào toàn bộ kho truyện 24/7 (Chạy ngầm nohup)
- Chọn phím **`4`** trên menu (hoặc chạy lệnh: `./tai_mangadex_ubuntu.sh --bg-hentai`).
- Script sẽ kích hoạt tiến trình tải lần lượt toàn bộ ~39.000+ bộ truyện từ mới nhất đến cũ nhất.

### Tùy chọn D: Xem tiến độ & nhật ký thời gian thực
- Chọn phím **`6`** trên menu để xem thống kê số truyện, số chương, số ảnh đã hoàn thành và dung lượng RAM/Swap đang sử dụng.
- Hoặc gõ lệnh xem nhật ký live:
  ```bash
  tail -f mangadex_sync.log
  ```

### Tùy chọn E: Tải 1 bộ truyện cụ thể để kiểm tra
- Chọn phím **`5`** trên menu (hoặc gõ: `./tai_mangadex_ubuntu.sh --url https://hentaivnreal.com/truyen/slug-truyen`).
- Script sẽ tải đầy đủ các chương của bộ truyện đó và đẩy ngay lên Cloud Storage Bucket & Web.

---

## 📁 Cấu Trúc File Lưu Trữ Trên Cloud Storage Bucket

Trong Cloud Bucket **`nekohentai`**, dữ liệu ảnh WebP sẽ được lưu theo cấu trúc chuẩn:

```text
nekohentai (Bucket)/
├── covers/
│   ├── ten-truyen-1.webp
│   ├── ten-truyen-2.webp
│   └── ...
└── chapters/
    ├── ten-truyen-1/
    │   ├── chap1/
    │   │   ├── page_001.webp
    │   │   ├── page_002.webp
    │   │   └── ...
    │   └── chap2/
    │       └── ...
    └── ten-truyen-2/
        └── ...
```

---

## 🛠️ Các Lệnh Thao Tác Nhanh (CLI Shortcut)

Nếu bạn muốn tạo cronjob hoặc tự động hóa trong bash script khác:

```bash
# Thiết lập bộ nhớ ảo Swap:
./tai_mangadex_ubuntu.sh --setup-swap

# Thiết lập / cập nhật cấu hình .env:
./tai_mangadex_ubuntu.sh --setup-env

# 1. TỰ ĐỘNG KIỂM TRA & TẢI TRUYỆN MỚI CẬP NHẬT (CHƯƠNG MỚI RA):
# Quét 10 trang đầu trực tiếp trên màn hình:
./tai_mangadex_ubuntu.sh --check-updates 10

# Chạy ngầm 24/7 kiểm tra cập nhật định kỳ (Quét 10 trang, lặp lại mỗi 30 phút):
./tai_mangadex_ubuntu.sh --bg-updates 10 30

# 2. TẢI HENTAIVNREAL TOÀN BỘ (~39.000+ TRUYỆN MỚI ➜ CŨ):
# Tải toàn bộ HentaiVNReal trực tiếp trên màn hình:
./tai_mangadex_ubuntu.sh --all-hentai

# Tải ngầm toàn bộ HentaiVNReal 24/7 (nohup background):
./tai_mangadex_ubuntu.sh --bg-hentai

# Tùy chỉnh trang bắt đầu / trang kết thúc:
./tai_mangadex_ubuntu.sh --all-hentai --start-page 1 --end-page 50

# 3. TẢI 1 TRUYỆN DUY NHẤT (Theo Link hoặc Slug):
./tai_mangadex_ubuntu.sh --url "https://hentaivnreal.com/truyen/slug-truyen"
./tai_mangadex_ubuntu.sh --url "slug-truyen"

# 4. QUẢN LÝ TIẾN TRÌNH:
# Xem trạng thái tiến trình, thống kê và theo dõi live logs:
./tai_mangadex_ubuntu.sh --status

# Dừng tiến trình chạy ngầm:
./tai_mangadex_ubuntu.sh --stop
```
