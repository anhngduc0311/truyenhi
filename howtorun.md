# 🚀 Hướng Dẫn Khởi Chạy Dự Án NekoHentai (How to Run)

Tài liệu hướng dẫn chi tiết các bước thiết lập môi trường và khởi chạy toàn bộ hệ thống nền tảng truyện tranh **NekoHentai** (bao gồm: Hạ tầng Docker, Backend .NET API, Frontend Angular, Crawler Engine và Hệ thống Giám sát).

---

## 📋 1. Yêu Cầu Môi Trường (Prerequisites)

Trước khi bắt đầu, hãy đảm bảo máy tính đã cài đặt các công cụ sau:

1. **Docker & Docker Desktop**: Dùng để chạy PostgreSQL, Redis, MinIO, Meilisearch, Prometheus, Grafana.
2. **.NET SDK** (.NET 8, 9 hoặc 10): Dùng để chạy Backend Web API.
3. **Node.js** (Khuyến nghị phiên bản v18+ hoặc v20+ LTS) & **npm**: Dùng để chạy Frontend Angular và Crawler.
4. **Angular CLI** (Tùy chọn, cài đặt toàn cục: `npm install -g @angular/cli`).

---

## 🏗️ 2. Các Bước Khởi Chạy Hệ Thống

### **Bước 1: Khởi động Hạ Tầng & Dịch Vụ Nền (Docker Compose)**

Mở Terminal / PowerShell tại thư mục gốc của dự án:

```bash
docker-compose up -d
```

> **Các dịch vụ container được khởi động:**
> - **PostgreSQL**: Port `5432` (Database `NekoHentaiDb`, user: `postgres`, password: `NekoHentaiDbPassword2026!`)
> - **Redis Cache**: Port `6379` (Caching dữ liệu & Rate Limiting)
> - **MinIO Object Storage**: Port `9000` (S3 API) & Port `9001` (Web Management Console)
> - **Meilisearch**: Port `7700` (Công cụ tìm kiếm Full-text search tốc độ cao)
> - **Prometheus**: Port `9090` (Thu thập metrics hiệu năng)
> - **Grafana**: Port `3000` (Dashboard trực quan hóa metrics)

Kiểm tra trạng thái các container:
```bash
docker-compose ps
```

---

### **Bước 2: Khởi Chạy Backend Web API (.NET)**

Mở một cửa sổ Terminal mới:

```bash
cd backend/MangaFlux.API
dotnet run
```
*(Hoặc chạy với môi trường Production nếu muốn tối ưu: `dotnet run --environment Production`)*

> [!NOTE]
> - Backend API sẽ chạy tại: **`http://localhost:5000`**
> - Cơ chế Auto-Migration của EF Core sẽ **tự động khởi tạo database** và tạo tài khoản Admin mặc định (`admin` / `admin123`) khi khởi động lần đầu.
> - Xem và kiểm thử API qua Swagger UI tại: **`http://localhost:5000/swagger`**
> - Kiểm tra tình trạng dịch vụ (Health Check) tại: **`http://localhost:5000/health`**

---

### **Bước 3: Khởi Chạy Frontend (Angular SPA)**

Mở một cửa sổ Terminal mới:

```bash
cd angular

# 1. Cài đặt dependencies (chỉ cần chạy lần đầu tiên)
npm install

# 2. Khởi động môi trường phát triển (Development)
npm start
# hoặc chạy bản production build nội bộ: npm run start:prod
```

> [!NOTE]
> - Giao diện người dùng sẽ chạy tại: **`http://localhost:4200`**
> - Ứng dụng đã được cấu hình tự động kết nối tới Backend API tại `http://localhost:5000/api`.

---

## 🛠️ 3. Các Tác Vụ Mở Rộng (Optional Features)

### **3.1. Cào Dữ Liệu Truyện Tự Động (Crawler Engine)**

Hệ thống tích hợp sẵn script cào truyện tự động từ các nguồn ngoài, xử lý tối ưu hóa hình ảnh và upload trực tiếp:

```bash
python backend/zet_gui.py
```

---

## 🔑 4. Bảng Cổng Dịch Vụ & Tài Khoản Mặc Định

| Dịch vụ / Ứng dụng | Địa chỉ URL | Tài khoản mặc định | Mật khẩu mặc định |
| :--- | :--- | :--- | :--- |
| **Giao diện Web (Angular)** | [http://localhost:4200](http://localhost:4200) | `admin` | `admin123` |
| **Backend Swagger API** | [http://localhost:5000/swagger](http://localhost:5000/swagger) | - | - |
| **MinIO Console (Storage)** | [http://localhost:9001](http://localhost:9001) | `nekohentai_admin` | `NekoHentaiSecretPassword2026!` |
| **Grafana APM Dashboard** | [http://localhost:3000](http://localhost:3000) | `admin` | `admin` |
| **Prometheus Metrics** | [http://localhost:9090](http://localhost:9090) | - | - |
| **Meilisearch Search Engine** | [http://localhost:7700](http://localhost:7700) | Master Key | `NekoHentaiMeiliMasterKey2026!` |
| **PostgreSQL Database** | `localhost:5432` | `postgres` | `NekoHentaiDbPassword2026!` |

---

## ⚡ 5. Script Chạy Nhanh Toàn Bộ (1-Click Startup Script)

Bạn có thể chạy file `run.bat` tại thư mục gốc để mở đồng thời cả hệ thống bằng 1 click:

```bat
@echo off
echo [1/3] Dang khoi dong Docker Containers...
docker-compose up -d

echo [2/3] Dang khoi dong Backend API...
start "NekoHentai Backend" cmd /k "cd backend\MangaFlux.API && dotnet run"

echo [3/3] Dang khoi dong Frontend Angular...
start "NekoHentai Frontend" cmd /k "cd angular && npm start"

echo.
echo ==============================================
echo  He thong NekoHentai dang khoi dong thanh cong!
echo  Frontend: http://localhost:4200
echo  Backend:  http://localhost:5000/swagger
echo ==============================================
pause
```
