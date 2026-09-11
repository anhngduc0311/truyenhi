#!/usr/bin/env bash
# ==============================================================================
# 🚀 NEKOHENTAI MANGA DOWNLOADER PRO - ALL-IN-ONE CRAWLER CHO UBUNTU (TURBO SPEED)
# ==============================================================================
# File tự động hóa 100% dành riêng cho hệ điều hành Ubuntu / Linux VPS:
# - Hỗ trợ cào truyện HentaiVNReal theo chuẩn Zet GUI:
#     • Nguồn: https://hentaivnreal.com (~39.000+ truyện, Mới Nhất ➜ Cũ Nhất)
# - Tự cài đặt Python 3, pip, Virtualenv, CloudScraper, BeautifulSoup4, Boto3
# - Tự động thiết lập bộ nhớ ảo SWAP (4GB/2GB) chống tràn RAM / chống bị kill tiến trình
# - CÁC TỐI ƯU HÓA TĂNG TỐC VƯỢT TRỘI (TURBO SPEED):
#     ⚡ 32 luồng tải & upload song song (Connection Pooling Keep-Alive)
#     ⚡ Nén WebP chất lượng cao (quality=90, method=6) trên đa nhân CPU
#     ⚡ Ghép ảnh Manhwa 5-in-1 tự động khi chapter > 70 ảnh
#     ⚡ Nhận diện & xử lý Oneshot chuẩn xác (chapterNumber = 1.0, title = "Oneshot")
# - Đẩy trực tiếp lên Cloud Storage Bucket (GCS / R2 / S3) & Đồng bộ Web API
# - Bỏ qua chapter đã có trên máy / cloud / web API (Hỗ trợ Resume)
# - Tự động dọn dẹp file tạm cục bộ sau khi đẩy lên Cloud (chống tràn ổ cứng VPS)
# - Hỗ trợ chạy ngầm 24/7 (nohup), tắt SSH máy chủ vẫn tự động tải liên tục
# ==============================================================================

LOG_FILE="mangadex_sync.log"
PID_FILE=".mangadex_sync.pid"
TASK_FILE=".crawler_task"
VENV_DIR=".venv_mangadex"
PYTHON_SCRIPT="mangadex_drive_downloader.py"

PYTHON_BIN="/usr/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(command -v python3 2>/dev/null || which python3 2>/dev/null || echo "python3")"
fi

get_python_runner() {
    if [ -f "$VENV_DIR/bin/python3" ]; then
        echo "$VENV_DIR/bin/python3"
    elif [ -f "$VENV_DIR/bin/python" ]; then
        echo "$VENV_DIR/bin/python"
    elif [ -x "$PYTHON_BIN" ]; then
        echo "$PYTHON_BIN"
    else
        echo "python3"
    fi
}

# Màu sắc hiển thị terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() {
    echo -e "\n${CYAN}================================================================${NC}"
    echo -e "${BOLD}${CYAN}$1${NC}"
    echo -e "${CYAN}================================================================${NC}\n"
}

# Kiểm tra quyền sudo/root
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    fi
fi

# ==============================================================================
# 1. TỰ ĐỘNG CẬP NHẬT / GIẢI NÉN ENGINE PYTHON
# ==============================================================================
extract_python_engine() {
    if [ -f "backend/$PYTHON_SCRIPT" ]; then
        PYTHON_SCRIPT="backend/$PYTHON_SCRIPT"
        return 0
    fi

    log_info "Đang đồng bộ Engine Python '$PYTHON_SCRIPT'..."
    cat << 'EOF' > "$PYTHON_SCRIPT"
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
🚀 NekoHentai Manga Downloader Pro - High Performance Synchronizer (HentaiVNReal)
=============================================================================
Author: NekoHentai Team
Source:
  - HentaiVNReal (https://hentaivnreal.com) - ~39.000+ truyện (Mới Nhất ➜ Cũ Nhất)
Storage:
  - Cloud Storage Bucket: nekohentai (GCS / Cloudflare R2 / AWS S3)
  - Web API: https://nekohentai.lol/api
Features:
  ☑️ Tự động tải lên Cloud Storage Bucket & Đồng bộ Web API: BẬT
  ☑️ Bỏ qua chapter đã có trên máy / Cloud / Web (Hỗ trợ Resume): BẬT
  ☑️ Ghép ảnh Manhwa 5-in-1 khi chapter > 70 ảnh (hoặc tùy chọn): BẬT
  ☑️ Nhận diện Oneshot chuẩn xác (chapterNumber = 1.0, title = "Oneshot"): BẬT
  ☑️ Nén ảnh WebP đa luồng chất lượng cao (quality=90, method=6): BẬT
  ☑️ Tự động dọn dẹp file tạm trên VPS chống tràn ổ cứng: BẬT
  ⚡ ĐỒNG BỘ REALTIME TỪNG CHAPTER: Cứ xong chapter nào là đẩy ngay lên Bucket & Web
=============================================================================
"""

import sys
import os
import re
import time
import json
import shutil
import base64
import hmac
import hashlib
import argparse
import subprocess
import unicodedata
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import cloudscraper
from bs4 import BeautifulSoup
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

# Console encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from rich.console import Console
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def log_info(msg: str):
    if HAS_RICH and console:
        console.print(f"[bold cyan]ℹ️  {msg}[/bold cyan]")
    else:
        print(f"ℹ️  {msg}", flush=True)


def log_success(msg: str):
    if HAS_RICH and console:
        console.print(f"[bold green]✅ {msg}[/bold green]")
    else:
        print(f"✅ {msg}", flush=True)


def log_warning(msg: str):
    if HAS_RICH and console:
        console.print(f"[bold yellow]⚠️  {msg}[/bold yellow]")
    else:
        print(f"⚠️  {msg}", flush=True)


def log_error(msg: str):
    if HAS_RICH and console:
        console.print(f"[bold red]❌ {msg}[/bold red]")
    else:
        print(f"❌ {msg}", flush=True)


def create_reusable_session(pool_size: int = 64) -> requests.Session:
    """Tạo requests.Session dùng chung Connection Pool (HTTP Keep-Alive) để tăng tốc tải & upload tối đa"""
    s = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
    )
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# =============================================================================
# AUTO-LOAD .ENV CONFIGURATION
# =============================================================================
def load_env_file():
    for p in [Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env", Path.cwd().parent / ".env"]:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break

load_env_file()

# =============================================================================
# CẤU HÌNH CLOUD BUCKET & WEB API
# =============================================================================
GCS_ENDPOINT = os.getenv("R2_ENDPOINT", "storage.googleapis.com")
GCS_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "GOOGQHRXVRS7YCR24JBLB33S")
GCS_SECRET_KEY = os.getenv("R2_SECRET_KEY", "3Iamo8whmuUeT2B+CMtRnfW6qdIsmwXVec47tF52")
GCS_BUCKET = os.getenv("R2_BUCKET_NAME", "nekohentai")
CDN_BASE_URL = os.getenv("R2_CDN_BASE_URL", "https://img.nekohentai.lol").rstrip("/")
DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "https://nekohentai.lol/api").rstrip("/")

# ⚙️ CÁC THIẾT LẬP MẶC ĐỊNH KHỚP GIAO DIỆN (ZET GUI):
DEFAULT_UPLOAD_TO_WEB = True          # ☑️ Tự động tải lên Cloud Bucket & Đồng bộ Web API
DEFAULT_SKIP_EXISTING = True          # ☑️ Bỏ qua chapter đã có trên máy / Cloud / Web
DEFAULT_MERGE_SLICES = True           # ☑️ Ghép ảnh Manhwa 5-in-1 khi > 70 ảnh
AUTO_STITCH_THRESHOLD = 70            # Ngưỡng tự động ghép dải ảnh manhwa
STITCH_GROUP_SIZE = 5                 # Ghép 5 lát cắt thành 1 ảnh dài WebP
DEFAULT_MAKE_PDF = False              # ⬜ Tự động xuất PDF: TẮT
DEFAULT_WORKERS = 32                  # ⚡ 32 luồng tải & upload song song (Turbo Speed)

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 4
STATE_FILE_NAME = "crawler_sync_state.json"
TEMP_DOWNLOAD_DIR = "mangadex_temp_cache"


# =============================================================================
# BOTO3 S3 CLIENT CHO CLOUD STORAGE
# =============================================================================
import boto3
from botocore.config import Config

_s3_client = None

def get_s3_client():
    global _s3_client
    if _s3_client is None:
        endpoint = GCS_ENDPOINT
        endpoint_url = f"https://{endpoint}" if endpoint and not endpoint.startswith("http") else endpoint
        _s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=GCS_ACCESS_KEY,
            aws_secret_access_key=GCS_SECRET_KEY,
            region_name="ap-southeast-1",
            config=Config(signature_version="s3v4", max_pool_connections=64)
        )
    return _s3_client


def upload_file_to_cloud(local_path: Path, object_name: str, content_type: str = "image/webp", max_retries: int = 3, session: requests.Session = None) -> str:
    """Tải 1 file ảnh lên Cloud Storage Bucket qua boto3 SigV4 (Fallback sang HMAC-SHA1 nếu lỗi)"""
    object_name = object_name.lstrip("/")
    last_err = None

    # Cách 1: Thử tải qua Boto3 SigV4
    try:
        client = get_s3_client()
        for attempt in range(max_retries):
            try:
                with open(local_path, "rb") as f:
                    client.put_object(
                        Bucket=GCS_BUCKET,
                        Key=object_name,
                        Body=f,
                        ContentType=content_type
                    )
                return f"{CDN_BASE_URL}/{object_name}"
            except Exception as e:
                last_err = str(e)
                time.sleep(0.3 * (attempt + 1))
    except Exception as e:
        last_err = str(e)

    # Cách 2: Fallback sang raw HTTP PUT với HMAC
    try:
        url = f'https://{GCS_ENDPOINT}/{GCS_BUCKET}/{object_name}'
        with open(local_path, "rb") as f:
            data = f.read()

        http_client = session or requests
        for attempt in range(max_retries):
            try:
                date_str = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
                string_to_sign = f'PUT\n\n{content_type}\n{date_str}\n/{GCS_BUCKET}/{object_name}'
                signature = hmac.new(GCS_SECRET_KEY.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha1).digest()
                sig_b64 = base64.b64encode(signature).decode('utf-8')
                auth_header = f'AWS {GCS_ACCESS_KEY}:{sig_b64}'

                headers = {
                    'Date': date_str,
                    'Content-Type': content_type,
                    'Authorization': auth_header
                }

                res = http_client.put(url, data=data, headers=headers, timeout=25)
                if res.status_code in (200, 201, 204):
                    return f"{CDN_BASE_URL}/{object_name}"
                else:
                    last_err = f"HTTP {res.status_code}: {res.text[:100]}"
                    time.sleep(0.3 * (attempt + 1))
            except Exception as ex:
                last_err = str(ex)
                time.sleep(0.3 * (attempt + 1))
    except Exception as ex:
        last_err = str(ex)

    raise Exception(f"Upload bucket failed sau {max_retries} lần thử: {last_err}")


def slugify(text: str) -> str:
    if not text:
        return "comic"
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip("-") or "comic"


def parse_date_to_iso(date_val):
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val.isoformat()
    val_str = str(date_val).strip()
    try:
        clean_str = val_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str).isoformat()
    except Exception:
        pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(val_str, fmt).isoformat()
        except Exception:
            pass
    return val_str


def normalize_chapter_key(val) -> str:
    """Chuẩn hóa số chapter về dạng chuỗi thống nhất (vd: 1 -> '1', 1.0 -> '1', 1.5 -> '1.5')"""
    if val is None:
        return ""
    try:
        f = float(val)
        return f"{int(f)}" if f.is_integer() else f"{f}"
    except (ValueError, TypeError):
        s = str(val).strip()
        if s.endswith(".0"):
            return s[:-2]
        return s


def check_chapter_exists_on_cloud(slug: str, chap_num_str: str, cdn_base_url: str = CDN_BASE_URL, session: requests.Session = None) -> bool:
    try:
        norm_key = normalize_chapter_key(chap_num_str)
        url = f"{cdn_base_url.rstrip('/')}/chapters/{slug}/chap{norm_key}/page_001.webp"
        http_client = session or requests
        res = http_client.head(url, timeout=3)
        return res.status_code == 200
    except Exception:
        return False


def get_existing_chapters_from_web(api_base_url: str, slug: str, session: requests.Session = None) -> set:
    """Truy vấn Web API (NekoHentai) để lấy danh sách chapter đã có trong database"""
    if not api_base_url or not slug:
        return set()
    url = f"{api_base_url.rstrip('/')}/comics/{slug}"
    http_client = session or requests
    try:
        res = http_client.get(url, timeout=6)
        if res.status_code == 200:
            data = res.json()
            chaps = data.get("chapters", [])
            existing = set()
            for c in chaps:
                c_num = c.get("chapterNumber")
                if c_num is not None:
                    existing.add(normalize_chapter_key(c_num))
            return existing
    except Exception:
        pass
    return set()


def sync_chapter_to_web_api(
    api_base_url: str,
    comic_title: str,
    comic_slug: str,
    cover_cdn_url: str,
    chapter_num: float,
    chapter_title: str,
    image_urls: list,
    author: str = None,
    translator_group: str = None,
    other_names: str = None,
    age_limit: str = None,
    views: int = 0,
    published_at: str = None,
    created_at: str = None,
    comic_views: int = None,
    comic_created_at: str = None,
    comic_updated_at: str = None,
    categories: list = None,
    session: requests.Session = None
) -> bool:
    """Đồng bộ chapter lên NekoHentai Web API để hiển thị ngay trên Website"""
    params = {
        "comicTitle": comic_title,
        "comicSlug": comic_slug,
        "coverImage": cover_cdn_url
    }
    if author:
        params["author"] = author
    if translator_group:
        params["translatorGroup"] = translator_group
    if other_names:
        params["otherNames"] = other_names
    if age_limit:
        params["ageLimit"] = age_limit
    if comic_views is not None and comic_views > 0:
        params["comicViews"] = str(comic_views)
    if categories:
        if isinstance(categories, (list, tuple, set)):
            params["categories"] = ",".join(str(c) for c in categories if c)
        else:
            params["categories"] = str(categories)
    if comic_created_at:
        params["comicCreatedAt"] = parse_date_to_iso(comic_created_at)
    if comic_updated_at:
        params["comicUpdatedAt"] = parse_date_to_iso(comic_updated_at)

    query_str = urllib.parse.urlencode(params)
    url = f"{api_base_url.rstrip('/')}/comics/import-scraped?{query_str}"
    payload = {
        "comicId": 0,
        "chapterNumber": chapter_num,
        "title": chapter_title or f"Chương {chapter_num}",
        "isPublic": True,
        "views": views or 0,
        "publishedAt": published_at,
        "createdAt": created_at or published_at,
        "imageUrls": image_urls
    }
    headers = {
        "User-Agent": "NekoHentai-Sync/2.0 (Ubuntu-All-In-One)",
        "Content-Type": "application/json"
    }
    http_client = session or requests
    try:
        res = http_client.post(url, json=payload, headers=headers, timeout=20)
        return res.status_code in (200, 201)
    except Exception:
        return False


# =============================================================================
# QUẢN LÝ TIẾN TRÌNH & CHECKPOINT (RESUME STATE)
# =============================================================================
class SyncStateManager:
    def __init__(self, state_file_path: Path):
        self.state_file_path = state_file_path
        self.data = {
            "version": 3,
            "gcs_bucket": GCS_BUCKET,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "completed_manga": {},
            "synced_chapters": {},
            "failed_manga": {},
            "stats": {"total_comics": 0, "total_chapters": 0, "total_pages": 0}
        }
        self.load()

    def load(self):
        if not self.state_file_path.exists():
            # Kiểm tra file cũ
            legacy = self.state_file_path.parent / "mangadex_sync_state.json"
            if legacy.exists():
                try:
                    with open(legacy, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                    return
                except Exception:
                    pass
            self._try_restore_from_cloud()

        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                log_warning(f"Lỗi đọc file tiến trình: {e}. Tạo mới.")

    def _try_restore_from_cloud(self):
        try:
            for fn in [STATE_FILE_NAME, "mangadex_sync_state.json"]:
                url = f"{CDN_BASE_URL}/metadata/{fn}"
                res = requests.get(url, timeout=5)
                if res.status_code == 200 and len(res.content) > 10:
                    self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.state_file_path, "wb") as f:
                        f.write(res.content)
                    log_success(f"☁️ Đã tự động khôi phục lịch sử tải ({fn}) từ Cloud Bucket!")
                    return
        except Exception:
            pass

    def backup_to_cloud(self, session: requests.Session = None):
        try:
            if self.state_file_path.exists():
                upload_file_to_cloud(
                    self.state_file_path,
                    f"metadata/{STATE_FILE_NAME}",
                    content_type="application/json",
                    session=session
                )
        except Exception:
            pass

    def save(self):
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def is_completed(self, manga_id: str) -> bool:
        return manga_id in self.data.get("completed_manga", {})

    def is_chapter_synced(self, manga_id: str, chap_num_str: str) -> bool:
        chaps = self.data.setdefault("synced_chapters", {}).setdefault(manga_id, [])
        norm_key = normalize_chapter_key(chap_num_str)
        return norm_key in [normalize_chapter_key(x) for x in chaps]

    def mark_chapter_synced(self, manga_id: str, chap_num_str: str):
        chaps = self.data.setdefault("synced_chapters", {}).setdefault(manga_id, [])
        norm_key = normalize_chapter_key(chap_num_str)
        norm_existing = [normalize_chapter_key(x) for x in chaps]
        if norm_key not in norm_existing:
            chaps.append(norm_key)
            self.save()

    def get_completed_info(self, manga_id: str) -> dict:
        return self.data.get("completed_manga", {}).get(manga_id)

    def mark_completed(self, manga_id: str, title: str, slug: str, chapters_count: int, pages_count: int, source: str = "HentaiVNReal"):
        self.data.setdefault("completed_manga", {})[manga_id] = {
            "title": title, "slug": slug, "chapters_count": chapters_count, "pages_count": pages_count,
            "source": source,
            "synced_at": datetime.now(timezone.utc).isoformat()
        }
        if manga_id in self.data.get("failed_manga", {}):
            del self.data["failed_manga"][manga_id]
        stats = self.data.setdefault("stats", {"total_comics": 0, "total_chapters": 0, "total_pages": 0})
        stats["total_comics"] = len(self.data["completed_manga"])
        stats["total_chapters"] += chapters_count
        stats["total_pages"] += pages_count
        self.save()
        if len(self.data["completed_manga"]) % 10 == 0:
            self.backup_to_cloud()

    def mark_failed(self, manga_id: str, title: str, error_msg: str):
        self.data.setdefault("failed_manga", {})[manga_id] = {
            "title": title, "error": str(error_msg), "time": datetime.now(timezone.utc).isoformat()
        }
        self.save()


# =============================================================================
# GHÉP ẢNH MANHWA 5-IN-1 (IMAGE STITCHING) & NÉN WEBP
# =============================================================================
def merge_images_vertical(image_paths: list, output_dir: Path, group_size: int = STITCH_GROUP_SIZE) -> list:
    if not image_paths:
        return []

    groups = []
    for group_idx, i in enumerate(range(0, len(image_paths), group_size), 1):
        groups.append((group_idx, image_paths[i:i + group_size]))

    def process_group(item):
        group_idx, group = item
        loaded_imgs = []
        resized_imgs = []
        combined = None
        try:
            for p in group:
                p_obj = Path(p)
                if not p_obj.exists() or p_obj.stat().st_size < 100:
                    continue
                with Image.open(p_obj) as raw_img:
                    raw_img.load()
                    im = raw_img.convert('RGB') if raw_img.mode != 'RGB' else raw_img.copy()
                    loaded_imgs.append(im)

            if not loaded_imgs:
                return group_idx, None

            max_width = max(im.width for im in loaded_imgs)
            total_height = 0
            for im in loaded_imgs:
                if im.width != max_width:
                    new_h = max(1, int(im.height * (max_width / im.width)))
                    im_resized = im.resize((max_width, new_h), Image.Resampling.LANCZOS)
                    resized_imgs.append(im_resized)
                    total_height += new_h
                else:
                    resized_imgs.append(im)
                    total_height += im.height

            combined = Image.new('RGB', (max_width, total_height), (255, 255, 255))
            curr_y = 0
            for im in resized_imgs:
                combined.paste(im, (0, curr_y))
                curr_y += im.height

            chunk_file = output_dir / f"page_{group_idx:03d}.webp"
            combined.save(chunk_file, 'WEBP', quality=90, method=6)
            return group_idx, chunk_file
        except Exception as e:
            log_warning(f"Lỗi ghép nhóm ảnh {group_idx}: {e}")
            return group_idx, None
        finally:
            to_close = {id(im): im for im in (loaded_imgs + resized_imgs)}
            for im in to_close.values():
                try: im.close()
                except Exception: pass
            if combined:
                try: combined.close()
                except Exception: pass

    results = {}
    with ThreadPoolExecutor(max_workers=min(len(groups), 8)) as stitch_pool:
        futures = [stitch_pool.submit(process_group, g) for g in groups]
        for f in as_completed(futures):
            g_idx, f_path = f.result()
            if f_path:
                results[g_idx] = f_path

    return [results[k] for k in sorted(results.keys())]


def convert_to_webp(src_file: Path, dest_webp_file: Path, quality: int = 90) -> bool:
    try:
        with Image.open(src_file) as im:
            im.load()
            im = im.convert('RGB') if im.mode != 'RGB' else im
            im.save(dest_webp_file, 'WEBP', quality=quality, method=6)
        if src_file != dest_webp_file and src_file.exists():
            src_file.unlink(missing_ok=True)
        return True
    except Exception:
        return False


# =============================================================================
# 1. HENTAIVNREAL CRAWLER ENGINE (Chuẩn Zet GUI)
# =============================================================================
class HentaiVNRealDownloader:
    BASE_URL = "https://hentaivnreal.com"

    def __init__(self, comic_url: str):
        self.comic_url = comic_url.strip()
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.slug = self._extract_slug(self.comic_url)

    def _extract_slug(self, url: str) -> str:
        clean = url.split("?")[0].rstrip("/")
        parts = clean.split("/")
        return parts[-1] if parts else "comic"

    def get_comic_info(self) -> dict:
        res = None
        for attempt in range(MAX_RETRIES):
            try:
                res = self.scraper.get(self.comic_url, timeout=DEFAULT_TIMEOUT)
                if res.status_code == 200:
                    break
            except Exception:
                time.sleep(1.5 * (attempt + 1))

        if not res or res.status_code != 200:
            raise Exception(f"Không thể kết nối đến trang truyện HentaiVNReal: {self.comic_url}")
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, "html.parser")

        # 1. Tên truyện
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else self.slug.replace("-", " ").title()
        title = re.sub(r'\s*\|\s*Hentaivn.*', '', title, flags=re.IGNORECASE).strip()

        # 2. Ảnh bìa
        cover_url = None
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "story-images" in src and "-w575-" in src:
                cover_url = src
                break
        if not cover_url:
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or ""
                if "story-images" in src:
                    cover_url = src
                    break
        if not cover_url:
            ava = soup.select_one(".page-ava img, .box-cover img")
            if ava:
                cover_url = ava.get("src") or ava.get("data-src")

        # 3. Metadata
        author = "Đang cập nhật"
        translator_group = "Đang cập nhật"
        other_names = "Đang cập nhật"
        status = "Đang tiến hành"
        views = 0
        desc = ""
        genres = []

        for p in soup.find_all("p"):
            t = p.get_text(" ", strip=True)
            if t.startswith("Tác giả:"):
                author = t.replace("Tác giả:", "").strip()
            elif t.startswith("Nhóm dịch:"):
                translator_group = t.replace("Nhóm dịch:", "").strip()
            elif t.startswith("Tên Khác:"):
                other_names = t.replace("Tên Khác:", "").strip()
            elif "Tình Trạng:" in t:
                m = re.search(r'Tình Trạng\s*:\s*([^\sL]+)', t)
                if m: status = m.group(1).strip()
            elif "Lượt xem:" in t:
                m = re.search(r'Lượt xem\s*:\s*([\d,.]+)', t)
                if m:
                    try: views = int(m.group(1).replace(",", "").replace(".", ""))
                    except Exception: pass
            elif t.startswith("Nội dung:"):
                next_p = p.find_next_sibling("p")
                if next_p:
                    desc = next_p.get_text(strip=True)

        for a in soup.find_all("a"):
            href = a.get("href", "")
            if "/the-loai/" in href:
                gt = a.get_text(strip=True)
                if gt and gt not in genres and gt.lower() not in ["thể loại", "danh sách", "kết hợp", "full màu", "không che"]:
                    genres.append(gt)

        # 4. Danh sách chapter
        chapters = []
        chuong = soup.find(id="chuong")
        if chuong:
            for tr in chuong.find_all("tr"):
                a = tr.find("a", href=True)
                if a and a["href"] != "#" and not a["href"].startswith("javascript"):
                    c_url = urllib.parse.urljoin(self.BASE_URL, a["href"])
                    c_title = a.get_text(strip=True)
                    m = re.search(r'(?:chap|chương|tập|hoi|hồi|lần)\s*([0-9]+(?:\.[0-9]+)?)', c_title, re.I)
                    if m:
                        c_num = float(m.group(1))
                    elif "oneshot" in c_title.lower() or "1shot" in c_title.lower():
                        c_num = 1.0
                        c_title = re.sub(r'^(?:chương|chap|chapter)\s*[\d\.]*\s*[-:]*\s*', '', c_title, flags=re.I).strip() or "Oneshot"
                    else:
                        c_num = float(len(chapters) + 1)
                    date_td = tr.find_all("td")
                    c_date = date_td[1].get_text(strip=True) if len(date_td) > 1 else ""
                    chapters.append({
                        "number": c_num,
                        "title": c_title,
                        "url": c_url,
                        "date": c_date,
                        "updated_at": parse_date_to_iso(c_date)
                    })

        chapters.reverse()
        if len(chapters) == 1 and ("oneshot" in title.lower() or "one-shot" in title.lower() or any("oneshot" in g.lower() for g in genres)):
            chapters[0]["title"] = "Oneshot"

        seen_numbers = set()
        for idx, chap in enumerate(chapters, 1):
            if chap["number"] in seen_numbers:
                chap["number"] = float(idx)
            seen_numbers.add(chap["number"])

        return {
            "title": title,
            "slug": self.slug,
            "cover_url": cover_url,
            "author": author,
            "translator_group": translator_group,
            "other_names": other_names,
            "status": status,
            "views": views,
            "description": desc,
            "genres": genres,
            "categories": genres,
            "chapters": chapters
        }

    def get_chapter_images(self, chap_url: str) -> list:
        res = None
        for attempt in range(MAX_RETRIES):
            try:
                res = self.scraper.get(chap_url, headers={"Referer": self.comic_url}, timeout=DEFAULT_TIMEOUT)
                if res.status_code == 200:
                    break
            except Exception:
                time.sleep(1.5 * (attempt + 1))

        if not res or res.status_code != 200:
            return []
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, "html.parser")

        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "manga-images" in src and src not in images:
                images.append(src)

        return images

    @staticmethod
    def fetch_all_hentaivn_comics_iter(start_page: int = 1, end_page: int = None, max_comics: int = None):
        """Iterator cào toàn bộ danh sách ~39.000+ truyện từ https://hentaivnreal.com/danh-sach (Mới Nhất ➜ Cũ Nhất)"""
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        current_page = max(1, start_page)
        yielded_count = 0
        total_pages = 982

        while True:
            if end_page and current_page > end_page:
                break
            if current_page > total_pages:
                break
            if max_comics and yielded_count >= max_comics:
                break

            url = f"https://hentaivnreal.com/danh-sach?page={current_page}"
            try:
                res = scraper.get(url, timeout=20)
                if res.status_code != 200:
                    time.sleep(2)
                    continue
                res.encoding = 'utf-8'
                soup = BeautifulSoup(res.text, "html.parser")

                pag = soup.find(class_=lambda c: c and 'pagination' in c)
                if pag:
                    for a in pag.find_all('a'):
                        href = a.get('href', '')
                        if 'page=' in href:
                            try:
                                p_num = int(href.split('page=')[-1].split('&')[0])
                                total_pages = max(total_pages, p_num)
                            except Exception:
                                pass
                        t = a.get_text(strip=True)
                        if t.isdigit():
                            total_pages = max(total_pages, int(t))

                items = soup.select("li.item")
                if not items:
                    break

                for it in items:
                    desc_elem = it.select_one(".box-description")
                    a_tag = desc_elem.find("a", href=True) if desc_elem else it.find("a", href=True)
                    if not a_tag or "/truyen/" not in a_tag.get("href", ""):
                        continue

                    comic_rel_url = a_tag["href"]
                    comic_full_url = urllib.parse.urljoin("https://hentaivnreal.com", comic_rel_url)
                    comic_title = a_tag.get_text(strip=True)
                    slug = comic_rel_url.split("?")[0].rstrip("/").split("/")[-1]

                    img_elem = it.find("img")
                    thumb_url = img_elem.get("src") or img_elem.get("data-src") or "" if img_elem else ""

                    other_names = ""
                    for p in it.find_all("p"):
                        if "Tên Khác:" in p.get_text():
                            other_names = p.get_text().replace("Tên Khác:", "").strip()
                            break

                    tags = [t.get_text(strip=True) for t in it.find_all("a", class_="tag") if t.get_text(strip=True)]

                    views = 0
                    for p in it.find_all("p"):
                        if "Lượt xem:" in p.get_text():
                            m_v = re.search(r'Lượt xem\s*:\s*([\d,.]+)', p.get_text())
                            if m_v:
                                try: views = int(m_v.group(1).replace(",", "").replace(".", ""))
                                except Exception: pass
                            break

                    yielded_count += 1
                    yield {
                        "id": slug,
                        "slug": slug,
                        "title": comic_title,
                        "url": comic_full_url,
                        "cover_thumb": thumb_url,
                        "other_names": other_names,
                        "tags": tags,
                        "views": views,
                        "author": "Đang cập nhật",
                        "page": current_page,
                        "total_pages": total_pages,
                        "total_available": total_pages * 40
                    }

                    if max_comics and yielded_count >= max_comics:
                        return

                current_page += 1
                time.sleep(0.3)

            except Exception as e:
                time.sleep(2)
                continue


# =============================================================================
# 2. ENGINE ĐỒNG BỘ TỔNG HỢP (SYNCHRONIZER PRO)
# =============================================================================
class NekoSynchronizerPro:
    def __init__(
        self,
        temp_dir: str = TEMP_DOWNLOAD_DIR,
        workers: int = DEFAULT_WORKERS,
        upload_to_web: bool = DEFAULT_UPLOAD_TO_WEB,
        skip_existing: bool = DEFAULT_SKIP_EXISTING,
        merge_slices: bool = DEFAULT_MERGE_SLICES,
        make_pdf: bool = DEFAULT_MAKE_PDF,
        delete_local: bool = True,
        api_base_url: str = DEFAULT_API_BASE_URL,
        **kwargs
    ):
        self.temp_root = Path(temp_dir).resolve()
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.state = SyncStateManager(self.temp_root / STATE_FILE_NAME)
        self.workers = workers
        self.upload_to_web = upload_to_web
        self.skip_existing = skip_existing
        self.merge_slices = merge_slices
        self.make_pdf = make_pdf
        self.delete_local = delete_local
        self.api_base_url = api_base_url

        # Connection Pool siêu tốc
        self.download_session = create_reusable_session(pool_size=max(64, self.workers * 2))
        self.download_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })
        self.api_session = create_reusable_session(pool_size=32)

    def _download_single_image(self, url: str, target_path: Path, referer: str = None) -> bool:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        headers = {}
        if referer:
            headers["Referer"] = referer

        for attempt in range(MAX_RETRIES):
            try:
                res = self.download_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
                if res.status_code == 200 and len(res.content) > 300:
                    with open(target_path, "wb") as f:
                        f.write(res.content)
                    return True
                elif res.status_code == 429:
                    time.sleep(1.5 * (attempt + 1))
            except Exception:
                time.sleep(0.5)
        return False

    # =========================================================================
    # A. TẢI TOÀN BỘ HENTAIVNREAL (MỚI NHẤT ➜ CŨ NHẤT)
    # =========================================================================
    def sync_all_hentaivn_comics(self, start_page: int = 1, end_page: int = None, max_comics: int = None):
        log_info(f"🚀 BẮT ĐẦU ĐỒNG BỘ TOÀN BỘ HENTAIVNREAL (MỚI NHẤT ➜ CŨ NHẤT)")
        log_info(f"• Nguồn: https://hentaivnreal.com/danh-sach (Bắt đầu từ Trang #{start_page})")
        log_info(f"• Cloud Storage Bucket: {GCS_BUCKET} ({GCS_ENDPOINT})")
        log_info(f"• Web API: {self.api_base_url}")
        log_info(f"• Số luồng tải: {self.workers} luồng | Ghép Manhwa 5-in-1: {'BẬT' if self.merge_slices else 'TẮT'}\n")

        comic_iter = HentaiVNRealDownloader.fetch_all_hentaivn_comics_iter(
            start_page=start_page,
            end_page=end_page,
            max_comics=max_comics
        )

        count = 0
        for item in comic_iter:
            count += 1
            slug = item["slug"]
            title = item["title"]
            c_url = item["url"]
            c_page = item.get("page", 1)
            tot_pages = item.get("total_pages", "?")

            if self.state.is_completed(slug) and self.skip_existing:
                comp_info = self.state.get_completed_info(slug) or {}
                prev_count = comp_info.get("chapters_count", 0)
                log_info(f"[#{count} | Trang {c_page}/{tot_pages}] ⏭️ Đã hoàn tất ({prev_count} chaps): {title} (Bỏ qua)")
                continue

            log_info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            log_info(f"▶ [#{count} | Trang {c_page}/{tot_pages}] 📖 {title}")
            log_info(f"   🔗 Link: {c_url} | Slug: {slug}")

            try:
                self.sync_single_hentai(c_url)
            except Exception as e:
                log_error(f"Lỗi khi xử lý bộ truyện '{title}': {e}")
                self.state.mark_failed(slug, title, str(e))

            time.sleep(0.3)

        log_success("🎉 ĐÃ HOÀN TẤT TIẾN TRÌNH ĐỒNG BỘ HENTAIVNREAL LÊN BUCKET & WEB!")

    def sync_single_hentai(self, comic_url_or_slug: str) -> bool:
        if not comic_url_or_slug.startswith("http"):
            url = f"https://hentaivnreal.com/truyen/{comic_url_or_slug}"
        else:
            url = comic_url_or_slug

        downloader = HentaiVNRealDownloader(url)
        info = downloader.get_comic_info()
        title = info["title"]
        slug = info["slug"]
        chapters = info["chapters"]

        if not chapters:
            log_warning(f"  ⚠️ Bộ truyện '{title}' chưa có chapter hợp lệ!")
            return False

        local_comic_dir = self.temp_root / "chapters" / slug
        local_covers_dir = self.temp_root / "covers"
        local_comic_dir.mkdir(parents=True, exist_ok=True)
        local_covers_dir.mkdir(parents=True, exist_ok=True)

        # 1. Ảnh bìa
        cover_cdn_url = None
        if info.get("cover_url"):
            raw_cover = local_covers_dir / f"{slug}_raw.jpg"
            target_cover = local_covers_dir / f"{slug}.webp"
            if not target_cover.exists():
                if self._download_single_image(info["cover_url"], raw_cover, referer=url):
                    convert_to_webp(raw_cover, target_cover, quality=90)

            if target_cover.exists() and self.upload_to_web:
                try:
                    cover_cdn_url = upload_file_to_cloud(target_cover, f"covers/{slug}.webp", "image/webp")
                    log_success(f"  📸 Đã đưa Ảnh bìa lên Bucket: {cover_cdn_url}")
                except Exception as err:
                    log_warning(f"  ⚠️ Lỗi upload bìa lên Bucket: {err}")

        # 2. Kiểm tra các chapter đã có
        web_existing = set()
        if self.upload_to_web:
            web_existing = get_existing_chapters_from_web(self.api_base_url, slug, session=self.api_session)
            for wk in web_existing:
                self.state.mark_chapter_synced(slug, wk)

        pending_download = []
        already_synced = []

        for chap in chapters:
            num = chap["number"]
            num_str = normalize_chapter_key(num)
            chap_dir = local_comic_dir / f"chap{num_str}"

            if self.skip_existing:
                if norm_key := num_str:
                    if norm_key in web_existing or self.state.is_chapter_synced(slug, norm_key):
                        already_synced.append(chap)
                        continue
                    if chap_dir.exists() and any(chap_dir.glob("*.webp")):
                        already_synced.append(chap)
                        self.state.mark_chapter_synced(slug, norm_key)
                        continue

            pending_download.append(chap)

        total_chaps = len(chapters)
        if not pending_download and self.skip_existing:
            log_success(f"  ✨ Toàn bộ {total_chaps}/{total_chaps} chapters của '{title}' đã tải/đồng bộ xong trước đó. Bỏ qua!\n")
            self.state.mark_completed(slug, title, slug, total_chaps, 0, source="HentaiVNReal")
            return True

        if already_synced:
            log_info(f"  ⏭️ Đã bỏ qua {len(already_synced)} chapters đã có sẵn trên hệ thống.")

        # 3. Tải các chapter cần thiết
        total_pages_downloaded = 0
        for idx, chap in enumerate(pending_download, 1):
            num = chap["number"]
            num_str = normalize_chapter_key(num)
            raw_t = (chap.get("title") or "").strip()

            # Oneshot check
            is_oneshot = bool(re.search(r'oneshot|one-shot|1shot', raw_t, re.I) or re.search(r'oneshot|one-shot', str(title or ''), re.I))
            if is_oneshot:
                clean_t = re.sub(r'^(?:chương|chap|chapter)\s*[\d\.]*\s*[-:]*\s*', '', raw_t, flags=re.I).strip()
                chap_title = clean_t or "Oneshot"
                api_chap_title = "Oneshot"
            else:
                chap_title = f"Chương {num_str}"
                if raw_t and raw_t != chap_title:
                    chap_title += f" - {raw_t}"
                api_chap_title = raw_t or f"Chương {num_str}"

            chap_dir = local_comic_dir / f"chap{num_str}"
            chap_dir.mkdir(parents=True, exist_ok=True)

            log_info(f"  📥 [{idx}/{len(pending_download)}] Đang tải {chap_title}...")

            img_urls = downloader.get_chapter_images(chap["url"])
            if not img_urls:
                log_warning(f"    ⚠️ Không lấy được link ảnh cho {chap_title}")
                continue

            num_raw = len(img_urls)
            should_stitch = self.merge_slices and (num_raw > AUTO_STITCH_THRESHOLD)
            download_dir = chap_dir / "_temp_slices" if should_stitch else chap_dir
            download_dir.mkdir(parents=True, exist_ok=True)

            raw_paths = []
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                futures = {}
                for p_idx, u in enumerate(img_urls, 1):
                    ext = u.split(".")[-1].split("?")[0].lower()
                    if ext not in ("jpg", "jpeg", "png", "webp"): ext = "jpg"
                    p_file = download_dir / f"raw_{p_idx:04d}.{ext}"
                    raw_paths.append(p_file)
                    futures[pool.submit(self._download_single_image, u, p_file, chap["url"])] = p_file
                for f in as_completed(futures):
                    pass

            downloaded_raw = sorted([p for p in raw_paths if p.exists()])

            # Ghép Manhwa 5-in-1 hoặc nén WebP
            final_paths = []
            if should_stitch:
                final_paths = merge_images_vertical(downloaded_raw, chap_dir, group_size=STITCH_GROUP_SIZE)
                total_pages_downloaded += len(final_paths)
                shutil.rmtree(download_dir, ignore_errors=True)
            else:
                final_paths_dict = {}
                with ThreadPoolExecutor(max_workers=min(self.workers, 16)) as conv_pool:
                    conv_futures = {}
                    for p_idx, p_file in enumerate(downloaded_raw, 1):
                        final_webp = chap_dir / f"page_{p_idx:03d}.webp"
                        conv_futures[conv_pool.submit(convert_to_webp, p_file, final_webp, 90)] = (p_idx, final_webp)
                    for f in as_completed(conv_futures):
                        p_idx, final_webp = conv_futures[f]
                        if f.result() and final_webp.exists():
                            final_paths_dict[p_idx] = final_webp

                final_paths = [final_paths_dict[k] for k in sorted(final_paths_dict.keys())]
                total_pages_downloaded += len(final_paths)

            # Đẩy lên Cloud Storage Bucket & Đồng bộ Web API
            if self.upload_to_web and final_paths:
                uploaded_cdn_urls = [None] * len(final_paths)
                with ThreadPoolExecutor(max_workers=self.workers) as pool:
                    f_to_i = {}
                    for p_i, p_path in enumerate(final_paths):
                        obj_name = f"chapters/{slug}/chap{num_str}/page_{p_i+1:03d}.webp"
                        f = pool.submit(upload_file_to_cloud, p_path, obj_name, "image/webp")
                        f_to_i[f] = p_i
                    for f in as_completed(f_to_i):
                        p_i = f_to_i[f]
                        try: uploaded_cdn_urls[p_i] = f.result()
                        except Exception as e:
                            log_warning(f"    Lỗi upload ảnh {p_i+1} lên bucket: {e}")

                valid_cdn_urls = [u for u in uploaded_cdn_urls if u]
                if valid_cdn_urls:
                    log_success(f"    ☁️ Đã lưu {len(valid_cdn_urls)} ảnh vào Bucket: {GCS_BUCKET}")
                    synced = sync_chapter_to_web_api(
                        api_base_url=self.api_base_url,
                        comic_title=title,
                        comic_slug=slug,
                        cover_cdn_url=cover_cdn_url or valid_cdn_urls[0],
                        chapter_num=num,
                        chapter_title=api_chap_title,
                        image_urls=valid_cdn_urls,
                        author=info["author"],
                        translator_group=info["translator_group"],
                        other_names=info["other_names"],
                        views=chap.get("views", 0),
                        published_at=chap.get("updated_at"),
                        created_at=chap.get("updated_at"),
                        comic_views=info.get("views", 0),
                        categories=info.get("genres", []),
                        session=self.api_session
                    )
                    if synced:
                        log_success(f"    🌐 Đã đồng bộ {chap_title} lên Website NekoHentai thành công!")

            self.state.mark_chapter_synced(slug, num_str)

            # Dọn dẹp bộ nhớ đệm
            if self.delete_local:
                shutil.rmtree(chap_dir, ignore_errors=True)

        self.state.mark_completed(
            manga_id=slug, title=title, slug=slug,
            chapters_count=len(chapters), pages_count=total_pages_downloaded,
            source="HentaiVNReal"
        )
        log_success(f"🎉 Hoàn thành cập nhật trọn bộ '{title}'!\n")
        return True

    # =========================================================================
    # B. TẢI 1 BỘ TRUYỆN THEO LINK HOẶC SLUG (HENTAIVNREAL)
    # =========================================================================
    def sync_single_comic(self, input_val: str) -> bool:
        val = input_val.strip()
        log_info(f"🏷️ Xử lý truyện HentaiVNReal: {val}")
        return self.sync_single_hentai(val)


# Backward compatibility aliases
MangaDexSynchronizer = NekoSynchronizerPro
MangaDexDriveSynchronizer = NekoSynchronizerPro
HentaiVNSynchronizer = NekoSynchronizerPro


# =============================================================================
# MAIN CLI
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="🚀 NekoHentai Crawler Pro (HentaiVNReal) cho Ubuntu / Linux VPS"
    )
    # HentaiVNReal
    parser.add_argument("--all-hentai", "--hentai", action="store_true", help="Tải toàn bộ truyện từ HentaiVNReal (Mới Nhất ➜ Cũ Nhất, Trang 1 ➜ 982+)")
    parser.add_argument("--start-page", "--page", type=int, default=1, help="Trang bắt đầu cào HentaiVNReal (Mặc định: 1)")
    parser.add_argument("--end-page", type=int, default=None, help="Trang kết thúc cào HentaiVNReal (Mặc định: hết)")
    parser.add_argument("--max-manga", type=int, default=None, help="Số lượng truyện tối đa muốn cào (Mặc định: tất cả)")

    # Single comic
    parser.add_argument("--url", "--manga", default=None, help="URL hoặc slug truyện HentaiVNReal")

    # General settings
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"Số luồng tải song song (Mặc định: {DEFAULT_WORKERS})")
    parser.add_argument("--no-merge", action="store_true", help="Tắt tự động ghép ảnh Manhwa 5-in-1")
    parser.add_argument("--no-skip", action="store_true", help="Tắt bỏ qua chapter đã có trên máy / cloud / web")
    parser.add_argument("--no-upload", action="store_true", help="Chỉ tải lưu cục bộ, không đẩy lên Cloud Bucket")
    parser.add_argument("--keep-local", action="store_true", help="Không xóa file tạm sau khi đẩy lên Cloud")
    parser.add_argument("--api", default=DEFAULT_API_BASE_URL, help=f"URL Backend API (Mặc định: {DEFAULT_API_BASE_URL})")

    args = parser.parse_args()

    engine = NekoSynchronizerPro(
        workers=args.workers,
        upload_to_web=not args.no_upload,
        skip_existing=not args.no_skip,
        merge_slices=not args.no_merge,
        delete_local=not args.keep_local,
        api_base_url=args.api
    )

    if args.url:
        engine.sync_single_comic(args.url)
    elif args.all_hentai:
        engine.sync_all_hentaivn_comics(start_page=args.start_page, end_page=args.end_page, max_comics=args.max_manga)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

EOF
    chmod +x "$PYTHON_SCRIPT"
    log_success "Đã cập nhật Engine Python '$PYTHON_SCRIPT' thành công!"
}

# ==============================================================================
# 2. KIỂM TRA VÀ THIẾT LẬP FILE MÔI TRƯỜNG .ENV
# ==============================================================================
setup_env_file() {
    FORCE="${1:-0}"
    if [ -f ".env" ] && [ "$FORCE" != "1" ] && [ "$FORCE" != "--force" ]; then
        return 0
    fi

    log_header "KIỂM TRA VÀ THIẾT LẬP FILE CẤU HÌNH .ENV"

    if [ -f ".env.example" ]; then
        log_info "Đang khởi tạo file .env từ .env.example..."
        cp .env.example .env
        log_success "Đã tạo thành công file .env từ .env.example!"
    elif [ -f "../.env.example" ]; then
        log_info "Đang sao chép file cấu hình từ ../.env.example sang .env..."
        cp ../.env.example .env
        log_success "Đã tạo thành công file .env từ ../.env.example!"
    else
        log_info "Không tìm thấy .env.example. Đang tự động tạo file .env chuẩn..."
        cat << 'EOF' > .env
# ==================================================
# 🚀 NekoHentai Environment Configuration (.env)
# ==================================================

# 1. Primary Cloud Storage (Google Cloud Storage / Cloudflare R2 / AWS S3)
R2_ENDPOINT="storage.googleapis.com"
R2_ACCESS_KEY="GOOGQHRXVRS7YCR24JBLB33S"
R2_SECRET_KEY="3Iamo8whmuUeT2B+CMtRnfW6qdIsmwXVec47tF52"
R2_BUCKET_NAME="nekohentai"
R2_SECURE=true
R2_CDN_BASE_URL="https://img.nekohentai.lol"

# 2. Web App & Backend API
PUBLIC_DOMAIN="https://nekohentai.lol"
API_BASE_URL="https://nekohentai.lol/api"
EOF
        log_success "Đã tạo file .env mặc định thành công!"
    fi

    if [ -f ".env" ]; then
        echo -e "• File cấu hình: ${CYAN}$(pwd)/.env${NC}"
        echo -e "• Cloud Bucket:  ${GREEN}$(grep '^R2_BUCKET_NAME=' .env 2>/dev/null | cut -d'=' -f2 | tr -d '\"' || echo 'nekohentai')${NC}"
        echo -e "• Web API:       ${CYAN}$(grep '^API_BASE_URL=' .env 2>/dev/null | cut -d'=' -f2 | tr -d '\"' || echo 'https://nekohentai.lol/api')${NC}\n"
    fi
}

# ==============================================================================
# 3. KIỂM TRA VÀ THIẾT LẬP BỘ NHỚ ẢO SWAP (CHỐNG TRÀN RAM / OOM KILLER)
# ==============================================================================
setup_swap_memory() {
    log_header "KIỂM TRA BỘ NHỚ ẢO SWAP (CHỐNG TRÀN RAM KHI CHẠY 32 LUỒNG)"

    SWAP_TOTAL=$(free -m 2>/dev/null | awk '/^Swap:/ {print $2}' || echo "0")
    if [ -n "$SWAP_TOTAL" ] && [ "$SWAP_TOTAL" -ge 2000 ]; then
        log_success "Máy chủ đã có sẵn ${SWAP_TOTAL}MB Swap (>= 2GB). An toàn bộ nhớ!"
        return 0
    fi

    log_warning "Máy chủ chưa có Swap hoặc Swap < 2GB (Hiện tại: ${SWAP_TOTAL:-0}MB)."

    if [ "$(id -u)" -ne 0 ] && [ -z "$SUDO" ]; then
        log_warning "Cần quyền sudo hoặc root để tự động tạo Swapfile. Bỏ qua bước này."
        return 0
    fi

    AVAIL_DISK=$(df -m / 2>/dev/null | awk 'NR==2 {print $4}' || echo "0")
    if [ "$AVAIL_DISK" -gt 6000 ]; then
        SWAP_SIZE="4G"
        SWAP_MB=4096
    elif [ "$AVAIL_DISK" -gt 3000 ]; then
        SWAP_SIZE="2G"
        SWAP_MB=2048
    else
        log_warning "Ổ đĩa chỉ còn ${AVAIL_DISK}MB trống, không đủ dung lượng để tạo file Swap lớn."
        return 0
    fi

    log_info "Đang tự động khởi tạo ${SWAP_SIZE} bộ nhớ ảo Swap tại /swapfile..."
    $SUDO swapoff /swapfile 2>/dev/null || true
    $SUDO rm -f /swapfile 2>/dev/null || true

    if ! $SUDO fallocate -l $SWAP_SIZE /swapfile 2>/dev/null; then
        $SUDO dd if=/dev/zero of=/swapfile bs=1M count=$SWAP_MB status=none 2>/dev/null || true
    fi

    if [ -f /swapfile ]; then
        $SUDO chmod 600 /swapfile
        $SUDO mkswap /swapfile >/dev/null 2>&1 || true
        if $SUDO swapon /swapfile 2>/dev/null; then
            if [ -f /etc/fstab ] && ! grep -q "/swapfile" /etc/fstab; then
                echo '/swapfile none swap sw 0 0' | $SUDO tee -a /etc/fstab >/dev/null 2>&1 || true
            fi
            $SUDO sysctl vm.swappiness=10 >/dev/null 2>&1 || true
            if [ -f /etc/sysctl.conf ] && ! grep -q "vm.swappiness=10" /etc/sysctl.conf; then
                echo 'vm.swappiness=10' | $SUDO tee -a /etc/sysctl.conf >/dev/null 2>&1 || true
            fi
            log_success "Đã kích hoạt thành công ${SWAP_SIZE} bộ nhớ ảo Swap tại /swapfile!"
        else
            log_warning "Không thể bật swapon (môi trường ảo hóa OpenVZ / LXC có thể chặn swapon)."
        fi
    fi
}

# ==============================================================================
# 4. KIỂM TRA VÀ CÀI ĐẶT MÔI TRƯỜNG TRÊN UBUNTU
# ==============================================================================
setup_environment() {
    log_header "BƯỚC 1/2: KIỂM TRA VÀ THIẾT LẬP MÔI TRƯỜNG UBUNTU"

    setup_env_file
    setup_swap_memory

    export DEBIAN_FRONTEND=noninteractive
    MISSING_PKGS=()
    if ! command -v python3 >/dev/null 2>&1; then MISSING_PKGS+=("python3"); fi
    if ! command -v pip3 >/dev/null 2>&1; then MISSING_PKGS+=("python3-pip"); fi
    if ! dpkg -s python3-venv >/dev/null 2>&1; then MISSING_PKGS+=("python3-venv"); fi
    if ! dpkg -s python3-virtualenv >/dev/null 2>&1 && ! command -v virtualenv >/dev/null 2>&1; then MISSING_PKGS+=("python3-virtualenv"); fi
    if ! command -v curl >/dev/null 2>&1; then MISSING_PKGS+=("curl"); fi

    if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
        log_info "Đang cài đặt các gói hệ thống: ${MISSING_PKGS[*]}..."
        $SUDO apt-get update -y
        $SUDO apt-get install -y "${MISSING_PKGS[@]}" ca-certificates
    fi

    if [ -x "/usr/bin/python3" ]; then
        PYTHON_BIN="/usr/bin/python3"
    else
        PYTHON_BIN="$(command -v python3 2>/dev/null || which python3 2>/dev/null || echo "python3")"
    fi

    # Khởi tạo virtualenv
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
        log_info "Đang tạo môi trường ảo Python Virtualenv ($VENV_DIR)..."
        rm -rf "$VENV_DIR"

        VENV_CREATED=0
        if "$PYTHON_BIN" -m venv "$VENV_DIR" >/dev/null 2>&1; then
            VENV_CREATED=1
        fi

        if [ "$VENV_CREATED" -eq 0 ]; then
            $SUDO apt-get install -y python3-virtualenv python3-venv >/dev/null 2>&1 || true
            if command -v virtualenv >/dev/null 2>&1 && virtualenv -p "$PYTHON_BIN" "$VENV_DIR" >/dev/null 2>&1; then
                VENV_CREATED=1
            elif "$PYTHON_BIN" -m virtualenv "$VENV_DIR" >/dev/null 2>&1; then
                VENV_CREATED=1
            fi
        fi

        if [ "$VENV_CREATED" -eq 1 ]; then
            log_success "Đã khởi tạo môi trường ảo $VENV_DIR thành công!"
        else
            log_warning "Không thể khởi tạo thư mục venv riêng, chuyển sang dùng Python hệ thống."
        fi
    fi

    # Cài đặt thư viện Python đầy đủ (bao gồm cloudscraper, bs4, boto3)
    log_info "Đang kiểm tra & cập nhật các thư viện Python cần thiết..."
    PIP_PKGS="requests urllib3 pillow rich cloudscraper beautifulsoup4 boto3 brotli"
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck source=/dev/null
        source "$VENV_DIR/bin/activate"
        pip install --upgrade pip >/dev/null 2>&1 || true
        pip install --quiet $PIP_PKGS
    else
        "$PYTHON_BIN" -m pip install --upgrade pip >/dev/null 2>&1 || true
        "$PYTHON_BIN" -m pip install --quiet --break-system-packages $PIP_PKGS 2>/dev/null || \
        "$PYTHON_BIN" -m pip install --quiet $PIP_PKGS
    fi

    log_success "Môi trường máy Ubuntu đã sẵn sàng 100%!"
}

# ==============================================================================
# 5. CÁC HÀM THỰC THI TẢI TRUYỆN (CHUẨN ZET GUI)
# ==============================================================================
prepare_execution() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck source=/dev/null
        source "$VENV_DIR/bin/activate"
    fi
    PY_RUNNER="$(get_python_runner)"
    SCRIPT_EXEC="$PYTHON_SCRIPT"
    if [ -f "backend/$PYTHON_SCRIPT" ]; then
        SCRIPT_EXEC="backend/$PYTHON_SCRIPT"
    fi
}

run_hentaivn_foreground() {
    START_P="${1:-}"
    END_P="${2:-}"
    MAX_M="${3:-}"

    if [ -z "$START_P" ]; then
        echo -e "\n${BOLD}${MAGENTA}--- CẤU HÌNH TẢI TOÀN BỘ HENTAIVNREAL (MỚI NHẤT ➜ CŨ NHẤT) ---${NC}"
        echo -n "🔢 Bắt đầu từ Trang # (Mặc định: 1 - Mới nhất): "
        read -r input_start
        START_P="${input_start:-1}"

        echo -n "🏁 Đến Trang # (Mặc định: 0 = tải đến trang cuối cùng ~982): "
        read -r input_end
        END_P="${input_end:-0}"

        echo -n "📊 Giới hạn số truyện (Mặc định: 0 = tải toàn bộ): "
        read -r input_max
        MAX_M="${input_max:-0}"
    fi

    prepare_execution
    CMD=("$PY_RUNNER" "$SCRIPT_EXEC" "--all-hentai" "--start-page" "$START_P" "--workers" "32")
    if [ "$END_P" -gt 0 ] 2>/dev/null; then
        CMD+=("--end-page" "$END_P")
    fi
    if [ "$MAX_M" -gt 0 ] 2>/dev/null; then
        CMD+=("--max-manga" "$MAX_M")
    fi

    log_header "BẮT ĐẦU TẢI HENTAIVNREAL (Trang $START_P ➔ ${END_P:-Hết} | 32 LUỒNG)"
    "${CMD[@]}"
}

run_hentaivn_background() {
    START_P="${1:-}"
    END_P="${2:-}"
    MAX_M="${3:-}"

    if [ -z "$START_P" ]; then
        echo -e "\n${BOLD}${MAGENTA}--- CẤU HÌNH CHẠY NGẦM HENTAIVNREAL 24/7 (nohup) ---${NC}"
        echo -n "🔢 Bắt đầu từ Trang # (Mặc định: 1): "
        read -r input_start
        START_P="${input_start:-1}"

        echo -n "🏁 Đến Trang # (Mặc định: 0 = tải hết): "
        read -r input_end
        END_P="${input_end:-0}"

        echo -n "📊 Giới hạn số truyện (Mặc định: 0 = tất cả): "
        read -r input_max
        MAX_M="${input_max:-0}"
    fi

    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            log_warning "Tiến trình tải đang chạy ngầm với PID: $OLD_PID!"
            echo -e "Gõ '${BOLD}tail -f $LOG_FILE${NC}' để theo dõi."
            return 0
        fi
    fi

    prepare_execution
    CMD=("$PY_RUNNER" "$SCRIPT_EXEC" "--all-hentai" "--start-page" "$START_P" "--workers" "32")
    if [ "$END_P" -gt 0 ] 2>/dev/null; then
        CMD+=("--end-page" "$END_P")
    fi
    if [ "$MAX_M" -gt 0 ] 2>/dev/null; then
        CMD+=("--max-manga" "$MAX_M")
    fi

    TASK_NAME="HentaiVNReal (Trang $START_P ➔ ${END_P:-982+})"
    log_info "Đang khởi chạy tiến trình tải ngầm 24/7 $TASK_NAME (nohup - 32 luồng)..."
    nohup "${CMD[@]}" >> "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo "$NEW_PID" > "$PID_FILE"
    echo "$TASK_NAME" > "$TASK_FILE"

    log_success "Tiến trình đã được đưa vào chạy ngầm! PID: ${BOLD}$NEW_PID${NC}"
    echo -e "• Nhiệm vụ:     ${MAGENTA}${BOLD}$TASK_NAME${NC}"
    echo -e "• File nhật ký: ${CYAN}$LOG_FILE${NC}"
    echo -e "• Lệnh theo dõi trực tiếp: ${BOLD}tail -f $LOG_FILE${NC}\n"
}

run_single_comic() {
    echo -n "🔗 Nhập URL hoặc slug truyện HentaiVNReal: "
    read -r manga_url
    if [ -z "$manga_url" ]; then
        log_error "Link hoặc slug truyện không được để trống!"
        return 1
    fi

    prepare_execution
    log_header "BẮT ĐẦU TẢI 1 BỘ TRUYỆN HENTAIVNREAL (32 LUỒNG)"
    "$PY_RUNNER" "$SCRIPT_EXEC" --url "$manga_url" --workers 32
}

run_single_comic_cli() {
    prepare_execution
    "$PY_RUNNER" "$SCRIPT_EXEC" --url "$1" --workers 32
}

show_status() {
    log_header "TRẠNG THÁI TIẾN TRÌNH TẢI TRUYỆN"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            TASK_SAVED="Đang tải truyện"
            if [ -f "$TASK_FILE" ]; then
                TASK_SAVED=$(cat "$TASK_FILE" 2>/dev/null)
            fi
            echo -e "Trạng thái: ${GREEN}${BOLD}ĐANG CHẠY NGẦM (Active)${NC} - PID: ${BOLD}$PID${NC}"
            echo -e "Nhiệm vụ:   ${CYAN}${BOLD}$TASK_SAVED${NC}"
        else
            echo -e "Trạng thái: ${YELLOW}ĐÃ DỪNG (Inactive)${NC}"
        fi
    else
        echo -e "Trạng thái: ${YELLOW}CHƯA KHỞI CHẠY TIẾN TRÌNH NGẦM${NC}"
    fi

    if [ -f ".env" ]; then
        echo -e "Cấu hình .env: ${GREEN}${BOLD}ĐÃ KÍCH HOẠT (.env)${NC}"
    else
        echo -e "Cấu hình .env: ${YELLOW}Chưa có .env (Chọn [9] để tạo)${NC}"
    fi

    echo -e "Lưu trữ:    ${GREEN}${BOLD}Cloud Storage Bucket (nekohentai) & Web API${NC}"

    SWAP_INFO=$(free -m 2>/dev/null | awk '/^Swap:/ {print $2}')
    SWAP_USED=$(free -m 2>/dev/null | awk '/^Swap:/ {print $3}')
    if [ -n "$SWAP_INFO" ] && [ "$SWAP_INFO" -gt 0 ]; then
        echo -e "Bộ nhớ ảo:  ${GREEN}${BOLD}${SWAP_INFO}MB Swap${NC} (Đang dùng: ${SWAP_USED}MB)"
    else
        echo -e "Bộ nhớ ảo:  ${YELLOW}Chưa có Swap (Khuyên dùng [8] để tạo Swap chống tràn RAM)${NC}"
    fi

    # Đọc thống kê từ file state JSON
    STATE_FILE="mangadex_temp_cache/crawler_sync_state.json"
    if [ ! -f "$STATE_FILE" ]; then
        STATE_FILE="mangadex_temp_cache/mangadex_sync_state.json"
    fi

    if [ -f "$STATE_FILE" ]; then
        echo -e "\n${BOLD}📊 Thống kê đã đồng bộ lên Cloud Storage Bucket & Web:${NC}"
        PY_RUNNER="$(get_python_runner)"
        "$PY_RUNNER" -c "
import json
try:
    with open('$STATE_FILE', 'r', encoding='utf-8') as f:
        d = json.load(f)
        s = d.get('stats', {})
        print(f'  • Tổng số bộ truyện đã hoàn tất: {s.get(\"total_comics\", 0)} bộ')
        print(f'  • Tổng số chapter đã lưu: {s.get(\"total_chapters\", 0)} chương')
        print(f'  • Tổng số trang ảnh đã lưu: {s.get(\"total_pages\", 0)} trang WebP')
except Exception: pass
" 2>/dev/null || true
    fi

    if [ -f "$LOG_FILE" ]; then
        echo -e "\n${CYAN}--- 15 DÒNG NHẬT KÝ MỚI NHẤT ($LOG_FILE) ---${NC}"
        tail -n 15 "$LOG_FILE"
        echo -e "${CYAN}---------------------------------------------${NC}"
        echo -e "💡 Lệnh xem live liên tục: ${BOLD}tail -f $LOG_FILE${NC}\n"
    fi
}

stop_background_process() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_info "Đang dừng tiến trình PID $PID..."
            kill "$PID" 2>/dev/null || true
            sleep 1
            if ps -p "$PID" > /dev/null 2>&1; then kill -9 "$PID" 2>/dev/null || true; fi
            rm -f "$PID_FILE" "$TASK_FILE"
            log_success "Đã dừng tiến trình tải ngầm thành công!"
            return 0
        fi
    fi
    log_warning "Không có tiến trình tải ngầm nào đang chạy."
    rm -f "$PID_FILE" "$TASK_FILE"
}

# ==============================================================================
# 6. XỬ LÝ DÒNG LỆNH CLI HOẶC MENU TƯƠNG TÁC
# ==============================================================================
extract_python_engine

if [ "$1" = "--setup-env" ] || [ "$1" = "--env" ]; then
    setup_env_file 1
    exit 0
elif [ "$1" = "--setup-swap" ] || [ "$1" = "--swap" ]; then
    setup_swap_memory
    exit 0
elif [ "$1" = "--all-hentai" ] || [ "$1" = "--hentai" ]; then
    setup_environment
    run_hentaivn_foreground "${2:-1}" "${3:-0}" "${4:-0}"
    exit 0
elif [ "$1" = "--bg-hentai" ]; then
    setup_environment
    run_hentaivn_background "${2:-1}" "${3:-0}" "${4:-0}"
    exit 0
elif [ "$1" = "--bg" ] || [ "$1" = "--daemon" ]; then
    setup_environment
    run_hentaivn_background "${2:-1}" "${3:-0}" "${4:-0}"
    exit 0
elif [ "$1" = "--status" ]; then
    show_status
    exit 0
elif [ "$1" = "--stop" ]; then
    stop_background_process
    exit 0
elif [ "$1" = "--url" ] && [ -n "$2" ]; then
    setup_environment
    run_single_comic_cli "$2"
    exit 0
fi

# Chế độ tương tác Menu
setup_environment

while true; do
    SWAP_VAL=$(free -m 2>/dev/null | awk '/^Swap:/ {print $2}')
    if [ -n "$SWAP_VAL" ] && [ "$SWAP_VAL" -gt 0 ]; then
        SWAP_BADGE="${GREEN}🟢 ${SWAP_VAL}MB (Đã kích hoạt)${NC}"
    else
        SWAP_BADGE="${YELLOW}🟡 0MB (Chọn [8] để tạo)${NC}"
    fi

    if [ -f ".env" ]; then
        ENV_BADGE="${GREEN}🟢 Đã có file .env${NC}"
    else
        ENV_BADGE="${YELLOW}🟡 Chưa có (Chọn [9] để tạo)${NC}"
    fi

    echo -e "${CYAN}================================================================${NC}"
    echo -e "${BOLD}${MAGENTA}🚀 NEKOHENTAI MANGA DOWNLOADER PRO (UBUNTU CRAWLER)${NC}"
    echo -e "   File cấu hình: $ENV_BADGE (Đọc từ .env / .env.example)"
    echo -e "   Cloud Bucket:  ${GREEN}nekohentai${NC} (Google Cloud Storage / R2 / S3)"
    echo -e "   Web API:       ${CYAN}https://nekohentai.lol/api${NC}"
    echo -e "   Bộ nhớ ảo:     $SWAP_BADGE (Chống tràn RAM/OOM khi chạy 32 luồng)"
    echo -e "${CYAN}----------------------------------------------------------------${NC}"
    echo -e "⚙️  ${BOLD}CẤU HÌNH & TÍNH NĂNG CHUẨN GIAO DIỆN ZET GUI:${NC}"
    echo -e "   ${GREEN}☑️${NC} Nguồn truyện: HentaiVNReal (~39.000+ bộ, Mới Nhất ➜ Cũ Nhất)"
    echo -e "   ${GREEN}☑️${NC} Tự động tải lên Cloud & Đồng bộ Web API: ${BOLD}${GREEN}BẬT${NC}"
    echo -e "   ${GREEN}☑️${NC} Bỏ qua chapter đã có (Web/Cloud/Máy):   ${BOLD}${GREEN}BẬT (Tránh tải trùng)${NC}"
    echo -e "   ${GREEN}☑️${NC} Ghép ảnh Manhwa 5-in-1 (>70 ảnh):        ${BOLD}${GREEN}BẬT (Đa luồng WebP)${NC}"
    echo -e "   ${GREEN}☑️${NC} Xử lý chuẩn xác chương Oneshot:          ${BOLD}${GREEN}BẬT${NC}"
    echo -e "   ${CYAN}⚡${NC} Luồng tải & Upload song song:            ${BOLD}${GREEN}32 luồng (Turbo Speed)${NC}"
    echo -e "   ${CYAN}⚡${NC} Nén WebP chất lượng cao (quality=90):    ${BOLD}${GREEN}BẬT${NC}"
    echo -e "${CYAN}================================================================${NC}"
    echo -e "  ${BOLD}[1]${NC} ⚡ ${BOLD}Tải TOÀN BỘ HentaiVNReal trực tiếp trên màn hình${NC} (Trang 1 ➜ 982+)"
    echo -e "  ${BOLD}[2]${NC} 🆕 ${BOLD}Tải NGẦM toàn bộ HentaiVNReal 24/7${NC} (nohup - Khuyên dùng)"
    echo -e "  ${BOLD}[3]${NC} 🔗 ${BOLD}Tải 1 bộ truyện theo Link / Slug HentaiVNReal${NC}"
    echo -e "  ${BOLD}[4]${NC} 📊 ${BOLD}Xem trạng thái, thống kê & nhật ký (Live Logs)${NC}"
    echo -e "  ${BOLD}[5]${NC} 🛑 ${BOLD}Dừng tiến trình tải ngầm${NC}"
    echo -e "  ${BOLD}[6]${NC} 🛡️  ${BOLD}Thiết lập / Bật bộ nhớ ảo Swap (4GB / 2GB)${NC}"
    echo -e "  ${BOLD}[7]${NC} 📝 ${BOLD}Tạo / Khôi phục file .env từ .env.example${NC}"
    echo -e "  ${BOLD}[0]${NC} ❌ Thoát"
    echo -e "${CYAN}----------------------------------------------------------------${NC}"
    echo -n "Chọn thao tác [0-7]: "
    read -r choice

    case "$choice" in
        1) run_hentaivn_foreground ;;
        2) run_hentaivn_background ;;
        3) run_single_comic ;;
        4) show_status ;;
        5) stop_background_process ;;
        6) setup_swap_memory ;;
        7)
            if [ -f ".env" ]; then
                echo -n "File .env đã tồn tại. Bạn có muốn ghi đè từ .env.example không? [y/N]: "
                read -r ovr
                if [ "$ovr" = "y" ] || [ "$ovr" = "Y" ]; then
                    setup_env_file 1
                else
                    log_info "Giữ nguyên file .env hiện tại."
                fi
            else
                setup_env_file 1
            fi
            ;;
        0) echo -e "\nTạm biệt!\n"; exit 0 ;;
        *) log_warning "Lựa chọn không hợp lệ." ;;
    esac
    echo ""
done
