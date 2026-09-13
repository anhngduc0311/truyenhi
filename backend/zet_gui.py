#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
🎨 NekoHentai Manga Downloader Pro - Modern GUI Application (CustomTkinter)
=============================================================================
Author: NekoHentai Team
Description: Giao diện đồ họa hiện đại hỗ trợ tải truyện từ ZetTruyen và
             MangaDex (Tiếng Việt), duyệt danh sách MangaDex trực quan,
             tải đa luồng, xuất PDF, ghép ảnh manhwa và đồng bộ Cloud/Web API.
=============================================================================
"""

import sys
import os
import re
import time
import threading
import webbrowser
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import json

# Fix console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import base64
import hmac
import hashlib
import requests
import urllib.parse
from datetime import datetime, timezone

import cloudscraper
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
Image.MAX_IMAGE_PIXELS = None

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Import shared modules from zet_downloader
try:
    from zet_downloader import (
        MangaDexDownloader,
        ZetMangaDownloader,
        HentaiVNRealDownloader,
        slugify,
        upload_file_to_cloud,
        sync_chapter_to_web_api,
        parse_date_to_iso,
        DEFAULT_COMIC_URL,
        DEFAULT_API_BASE_URL,
        MANGADEX_API_BASE,
        MANGADEX_UPLOADS_BASE,
        DEFAULT_LANG,
        AUTO_STITCH_THRESHOLD,
        STITCH_GROUP_SIZE,
    )
except ImportError:
    DEFAULT_COMIC_URL = "https://hentaivnreal.com/truyen/me-ban-la-mau-hinh-ly-tuong-cua-toi"
    DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api")
    MANGADEX_API_BASE = "https://api.mangadex.org"
    MANGADEX_UPLOADS_BASE = "https://uploads.mangadex.org"
    DEFAULT_LANG = "vi"
    AUTO_STITCH_THRESHOLD = 70
    STITCH_GROUP_SIZE = 5

# Set CustomTkinter Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# =============================================================================
# QUẢN LÝ TIẾN TRÌNH TẢI & NHẬN DIỆN TRUYỆN ĐÃ TẢI (CRAWLER SYNC STATE)
# =============================================================================
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


class CrawlerSyncStateManager:
    """Quản lý trạng thái đồng bộ từ crawler_sync_state.json để biết truyện & chapter nào đã tải"""
    def __init__(self, default_file_path: str = None):
        self.file_path = None
        self.data = {
            "version": 3,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "completed_manga": {},
            "synced_chapters": {},
            "failed_manga": {},
            "stats": {"total_comics": 0, "total_chapters": 0, "total_pages": 0}
        }
        # Tự động quét tìm các file tiến trình sẵn có trong thư mục làm việc
        candidates = []
        if default_file_path:
            candidates.append(Path(default_file_path))
        candidates.extend([
            Path("crawler_sync_state.json"),
            Path("mangadex_temp_cache/crawler_sync_state.json"),
            Path("mangadex_temp_cache/mangadex_sync_state.json"),
            Path("downloads/crawler_sync_state.json"),
            Path.home() / "Downloads" / "crawler_sync_state.json",
            Path.home() / "Downloads" / "mangadex_sync_state.json",
            Path("../crawler_sync_state.json"),
            Path("../mangadex_temp_cache/crawler_sync_state.json")
        ])
        for p in candidates:
            if p.exists() and p.is_file():
                if self.load_from_file(p):
                    break

    def load_from_file(self, path: Path or str) -> bool:
        p = Path(path)
        try:
            if p.exists() and p.is_file():
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, dict):
                        self.data = d
                        self.file_path = p.resolve()
                        return True
        except Exception as e:
            print(f"Lỗi khi đọc file sync state ({path}): {e}")
        return False

    def save(self):
        """Lưu toàn bộ tiến trình vào file JSON để ghi nhớ cho các lần tải sau"""
        if not self.file_path:
            self.file_path = Path("crawler_sync_state.json").resolve()
        try:
            self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            # Đồng thời sao lưu một bản vào thư mục dự án nếu file gốc ở nơi khác (vd: thư mục Downloads)
            local_p = Path("crawler_sync_state.json").resolve()
            if self.file_path.resolve() != local_p:
                try:
                    with open(local_p, "w", encoding="utf-8") as f_local:
                        json.dump(self.data, f_local, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            return True
        except Exception as e:
            print(f"Lỗi khi ghi file sync state: {e}")
            return False

    def is_comic_completed(self, slug: str) -> bool:
        if not slug:
            return False
        clean = slug.strip().rstrip("/").split("/")[-1]
        return clean in self.data.get("completed_manga", {})

    def get_completed_info(self, slug: str) -> dict:
        if not slug:
            return None
        clean = slug.strip().rstrip("/").split("/")[-1]
        return self.data.get("completed_manga", {}).get(clean)

    def get_synced_chapters(self, slug: str) -> list:
        if not slug:
            return []
        clean = slug.strip().rstrip("/").split("/")[-1]
        return self.data.get("synced_chapters", {}).get(clean, [])

    def is_chapter_synced(self, slug: str, chap_num_str: str) -> bool:
        synced = self.get_synced_chapters(slug)
        norm_key = normalize_chapter_key(chap_num_str)
        return norm_key in [normalize_chapter_key(x) for x in synced]

    def mark_chapter_synced(self, slug: str, chap_num_str: str):
        clean = slug.strip().rstrip("/").split("/")[-1]
        chaps = self.data.setdefault("synced_chapters", {}).setdefault(clean, [])
        norm_key = normalize_chapter_key(chap_num_str)
        norm_existing = [normalize_chapter_key(x) for x in chaps]
        if norm_key not in norm_existing:
            chaps.append(norm_key)
            self.save()

    def mark_comic_completed(self, slug: str, title: str, chapters_count: int, pages_count: int = 0, source: str = "HentaiVNReal"):
        clean = slug.strip().rstrip("/").split("/")[-1]
        self.data.setdefault("completed_manga", {})[clean] = {
            "title": title,
            "slug": clean,
            "chapters_count": chapters_count,
            "pages_count": pages_count,
            "source": source,
            "synced_at": datetime.now(timezone.utc).isoformat()
        }
        if clean in self.data.get("failed_manga", {}):
            del self.data["failed_manga"][clean]
        stats = self.data.setdefault("stats", {"total_comics": 0, "total_chapters": 0, "total_pages": 0})
        stats["total_comics"] = len(self.data.get("completed_manga", {}))
        stats["total_chapters"] = sum(c.get("chapters_count", 0) for c in self.data.get("completed_manga", {}).values())
        stats["total_pages"] = stats.get("total_pages", 0) + pages_count
        self.save()

    @property
    def completed_count(self) -> int:
        return len(self.data.get("completed_manga", {}))

    @property
    def synced_chapters_count(self) -> int:
        total = 0
        for ch_list in self.data.get("synced_chapters", {}).values():
            total += len(ch_list)
        return total


class HentaiVNBatchConfigDialog(ctk.CTkToplevel):
    """Cửa sổ cấu hình tải hàng loạt toàn bộ truyện từ https://hentaivnreal.com/danh-sach theo thứ tự Mới Nhất ➜ Cũ Nhất"""
    def __init__(self, parent, default_save_dir: str, default_api_url: str, on_start_callback, sync_state: CrawlerSyncStateManager = None):
        super().__init__(parent)
        self.title("⚡ Tải Toàn Bộ Truyện HentaiVNReal (Mới Nhất ➜ Cũ Nhất)")
        self.geometry("660x740")
        self.minsize(580, 660)
        self.resizable(False, False)
        self.default_save_dir = default_save_dir
        self.default_api_url = default_api_url
        self.on_start_callback = on_start_callback
        self.sync_state = sync_state

        self.transient(parent)
        self.grab_set()

        self._setup_dialog_ui()

    def _setup_dialog_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Frame
        hdr = ctk.CTkFrame(self, fg_color="#131722", corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        
        t_lbl = ctk.CTkLabel(
            hdr, 
            text="📥 Tải Hàng Loạt Toàn Bộ HentaiVNReal", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ec4899"
        )
        t_lbl.pack(anchor="w", padx=20, pady=(15, 2))

        sub_lbl = ctk.CTkLabel(
            hdr,
            text="Tự động cào toàn bộ danh sách ~39.000+ truyện từ https://hentaivnreal.com/danh-sach\ntheo thứ tự từ MỚI NHẤT đến CŨ NHẤT (bắt đầu từ Trang 1 ➜ Trang 982+).\nHỗ trợ đa luồng, chuyển đổi WebP, ghép ảnh manhwa, tạo PDF và tự động đồng bộ Web / Cloud.",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
            justify="left"
        )
        sub_lbl.pack(anchor="w", padx=20, pady=(0, 15))

        # Body Scrollable Frame
        body = ctk.CTkScrollableFrame(self, fg_color="#18202f", corner_radius=10)
        body.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        body.grid_columnconfigure(1, weight=1)

        # 1. Thứ tự tải (Luôn là Mới nhất -> Cũ nhất)
        ctk.CTkLabel(body, text="🎯 Thứ tự tải:", font=ctk.CTkFont(weight="bold"), text_color="#38bdf8").grid(row=0, column=0, padx=10, pady=(10, 4), sticky="w")
        order_box = ctk.CTkFrame(body, fg_color="transparent")
        order_box.grid(row=0, column=1, padx=10, pady=(10, 4), sticky="w")
        ctk.CTkLabel(order_box, text="⚡ Từ Mới Nhất ➜ Cũ Nhất (Trang 1 ➜ Trang 982+)", font=ctk.CTkFont(weight="bold"), text_color="#10b981").pack(anchor="w")

        # 2. Trang bắt đầu & Trang kết thúc
        ctk.CTkLabel(body, text="🔢 Bắt đầu từ Trang #:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=6, sticky="w")
        start_p_box = ctk.CTkFrame(body, fg_color="transparent")
        start_p_box.grid(row=1, column=1, padx=10, pady=6, sticky="w")
        self.start_page_entry = ctk.CTkEntry(start_p_box, width=90, placeholder_text="1")
        self.start_page_entry.insert(0, "1")
        self.start_page_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(start_p_box, text="(Trang 1 = Mới nhất)", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left")

        ctk.CTkLabel(body, text="🏁 Đến Trang #:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=10, pady=6, sticky="w")
        end_p_box = ctk.CTkFrame(body, fg_color="transparent")
        end_p_box.grid(row=2, column=1, padx=10, pady=6, sticky="w")
        self.end_page_entry = ctk.CTkEntry(end_p_box, width=90, placeholder_text="0")
        self.end_page_entry.insert(0, "0")
        self.end_page_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(end_p_box, text="(0 = Tải hết đến trang cuối cùng ~982)", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left")

        # 3. Giới hạn số truyện
        ctk.CTkLabel(body, text="📊 Giới hạn số truyện:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=10, pady=6, sticky="w")
        max_box = ctk.CTkFrame(body, fg_color="transparent")
        max_box.grid(row=3, column=1, padx=10, pady=6, sticky="w")
        self.max_manga_entry = ctk.CTkEntry(max_box, width=90, placeholder_text="0")
        self.max_manga_entry.insert(0, "0")
        self.max_manga_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(max_box, text="(0 = Tải TẤT CẢ ~39.000+ bộ)", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left")

        # 4. Thư mục lưu
        ctk.CTkLabel(body, text="📂 Thư mục lưu máy:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=10, pady=6, sticky="w")
        save_box = ctk.CTkFrame(body, fg_color="transparent")
        save_box.grid(row=4, column=1, padx=10, pady=6, sticky="ew")
        save_box.grid_columnconfigure(0, weight=1)

        self.save_dir_entry = ctk.CTkEntry(save_box)
        self.save_dir_entry.insert(0, self.default_save_dir)
        self.save_dir_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        ctk.CTkButton(save_box, text="Chọn", width=60, command=self._browse_save_folder, fg_color="#334155").grid(row=0, column=1)

        # 5. Tùy chọn xử lý & Tải lên
        ctk.CTkLabel(body, text="⚙️ Tùy chọn xử lý:", font=ctk.CTkFont(weight="bold"), text_color="#38bdf8").grid(row=5, column=0, padx=10, pady=(12, 4), sticky="w")

        opts_frame = ctk.CTkFrame(body, fg_color="#0f172a", corner_radius=6)
        opts_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=4, sticky="ew")

        self.cb_upload_web = ctk.CTkCheckBox(opts_frame, text="🌐 Tự động tải lên Cloud Storage & Đồng bộ Web API", fg_color="#0284c7")
        self.cb_upload_web.select()
        self.cb_upload_web.pack(anchor="w", padx=12, pady=(10, 4))

        self.cb_skip_existing = ctk.CTkCheckBox(opts_frame, text="⏭️ Bỏ qua chapter đã có trên máy (Tránh tải trùng / Hỗ trợ Resume)", fg_color="#0284c7")
        self.cb_skip_existing.select()
        self.cb_skip_existing.pack(anchor="w", padx=12, pady=4)

        if self.sync_state and self.sync_state.completed_count > 0:
            c_cnt = self.sync_state.completed_count
            self.cb_skip_sync_state = ctk.CTkCheckBox(
                opts_frame, 
                text=f"⚡ Bỏ qua {c_cnt:,} bộ truyện đã ghi nhận trong crawler_sync_state.json", 
                fg_color="#10b981"
            )
            self.cb_skip_sync_state.select()
            self.cb_skip_sync_state.pack(anchor="w", padx=12, pady=4)
        else:
            self.cb_skip_sync_state = None

        self.cb_merge = ctk.CTkCheckBox(opts_frame, text="🧩 Ghép ảnh Manhwa 5-in-1 (Tự động khi chapter > 70 ảnh)", fg_color="#0284c7")
        self.cb_merge.pack(anchor="w", padx=12, pady=4)

        self.cb_pdf = ctk.CTkCheckBox(opts_frame, text="📄 Tự động xuất mỗi chapter thành file PDF", fg_color="#0284c7")
        self.cb_pdf.pack(anchor="w", padx=12, pady=(4, 10))

        # 6. Luồng tải
        ctk.CTkLabel(body, text="⚡ Luồng tải song song:", font=ctk.CTkFont(weight="bold")).grid(row=7, column=0, padx=10, pady=(10, 4), sticky="w")
        thread_box = ctk.CTkFrame(body, fg_color="transparent")
        thread_box.grid(row=7, column=1, padx=10, pady=(10, 4), sticky="ew")
        thread_box.grid_columnconfigure(0, weight=1)

        self.lbl_threads_dialog = ctk.CTkLabel(thread_box, text="16 luồng")
        self.slider_threads_dialog = ctk.CTkSlider(
            thread_box, from_=4, to=32, number_of_steps=7,
            command=lambda v: self.lbl_threads_dialog.configure(text=f"{int(v)} luồng")
        )
        self.slider_threads_dialog.set(16)
        self.slider_threads_dialog.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.lbl_threads_dialog.grid(row=0, column=1)

        # Bottom Buttons
        btn_bar = ctk.CTkFrame(self, fg_color="#131722", corner_radius=0)
        btn_bar.grid(row=2, column=0, sticky="ew", padx=0, pady=0)

        ctk.CTkButton(
            btn_bar,
            text="❌ Hủy / Đóng",
            command=self.destroy,
            fg_color="#334155",
            hover_color="#475569",
            width=120,
            height=36
        ).pack(side="right", padx=(5, 20), pady=12)

        ctk.CTkButton(
            btn_bar,
            text="🚀 Bắt Đầu Tải Hàng Loạt (Mới ➜ Cũ)",
            command=self._on_start_clicked,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=270,
            height=36
        ).pack(side="right", padx=5, pady=12)

    def _browse_save_folder(self):
        f = filedialog.askdirectory(initialdir=self.save_dir_entry.get())
        if f:
            self.save_dir_entry.delete(0, "end")
            self.save_dir_entry.insert(0, f)

    def _on_start_clicked(self):
        try:
            start_p = max(1, int(self.start_page_entry.get() or 1))
        except ValueError:
            start_p = 1

        try:
            end_p = int(self.end_page_entry.get() or 0)
            if end_p <= 0:
                end_p = None
        except ValueError:
            end_p = None

        try:
            max_manga = int(self.max_manga_entry.get() or 0)
            if max_manga <= 0:
                max_manga = None
        except ValueError:
            max_manga = None

        config = {
            "start_page": start_p,
            "end_page": end_p,
            "max_manga": max_manga,
            "save_dir": self.save_dir_entry.get().strip(),
            "upload_to_web": self.cb_upload_web.get() == 1,
            "skip_existing": self.cb_skip_existing.get() == 1,
            "skip_sync_state": self.cb_skip_sync_state.get() == 1 if self.cb_skip_sync_state else True,
            "merge_slices": self.cb_merge.get() == 1,
            "make_pdf": self.cb_pdf.get() == 1,
            "workers": int(self.slider_threads_dialog.get())
        }
        self.destroy()
        self.on_start_callback(config)


# Alias để tương thích
MangaDexBatchConfigDialog = HentaiVNBatchConfigDialog


class MangaDownloaderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("⚡ NekoHentai Manga Downloader Pro (HentaiVNReal & MangaDex)")
        self.geometry("1100x840")
        self.minsize(950, 700)

        # App state
        self.downloader_instance = None
        self.comic_info = None
        self.is_downloading = False
        self.cancel_requested = False
        self.current_hentai_page = 1
        self.total_hentai_pages = 982
        self.is_fetching_hentai_list = False
        self.last_hentai_items = []

        # Quản lý tiến trình tải crawler_sync_state.json
        self.sync_state = CrawlerSyncStateManager()

        self._setup_ui()
        self._update_sync_state_ui()

    def _update_sync_state_ui(self):
        """Cập nhật nhãn trạng thái của crawler_sync_state.json trên Header"""
        if not hasattr(self, 'lbl_sync_state_badge'):
            return
        c_cnt = self.sync_state.completed_count
        ch_cnt = self.sync_state.synced_chapters_count
        if c_cnt > 0:
            fn = Path(self.sync_state.file_path).name if self.sync_state.file_path else "crawler_sync_state.json"
            self.lbl_sync_state_badge.configure(
                text=f"🟢 Đã nạp: {c_cnt:,} bộ ({ch_cnt:,} chaps) • {fn}",
                text_color="#10b981"
            )
        else:
            self.lbl_sync_state_badge.configure(
                text="⚪ Chưa nạp crawler_sync_state.json",
                text_color="#94a3b8"
            )

    def import_sync_state_file(self):
        """Mở hộp thoại chọn file crawler_sync_state.json hoặc mangadex_sync_state.json để nạp"""
        initial_dir = str(Path.cwd())
        file_path = filedialog.askopenfilename(
            title="Chọn file crawler_sync_state.json hoặc mangadex_sync_state.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir=initial_dir
        )
        if file_path:
            ok = self.sync_state.load_from_file(file_path)
            if ok:
                c_count = self.sync_state.completed_count
                ch_count = self.sync_state.synced_chapters_count
                self._update_sync_state_ui()
                self.log(f"\n📂 ĐÃ NẠP FILE TIẾN TRÌNH: {file_path}")
                self.log(f"   • Số bộ truyện đã hoàn tất: {c_count:,} bộ")
                self.log(f"   • Số chapter đã đồng bộ: {ch_count:,} chương")
                messagebox.showinfo(
                    "Thành công",
                    f"Đã nạp file tiến trình thành công!\n\n"
                    f"📂 File: {Path(file_path).name}\n"
                    f"• {c_count:,} bộ truyện đã hoàn tất\n"
                    f"• {ch_count:,} chapter đã đồng bộ\n\n"
                    f"Các truyện đã tải sẽ được đánh dấu viền xanh và huy hiệu '✅ ĐÃ TẢI XONG' trong danh sách."
                )
                if hasattr(self, 'last_hentai_items') and self.last_hentai_items:
                    self._render_hentai_results(self.last_hentai_items)
            else:
                messagebox.showerror("Lỗi", f"Không thể đọc file {file_path} hoặc dữ liệu JSON không đúng cấu trúc!")

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---------------- 1. TOP HEADER ----------------
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#131722")
        header_frame.grid(row=0, column=0, padx=15, pady=(12, 6), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="🚀 NekoHentai Manga Downloader Pro",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ec4899"
        )
        title_lbl.pack(anchor="w", pady=(0, 2))

        sub_lbl = ctk.CTkLabel(
            title_box,
            text="Tải truyện siêu tốc từ HentaiVNReal (https://hentaivnreal.com) & MangaDex • Đa luồng • Xuất PDF • Ghép ảnh Manhwa • Đồng bộ Cloud & Website",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        sub_lbl.pack(anchor="w")

        # Quick Batch Download Button & Sync State in Header
        hdr_right_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        hdr_right_box.pack(side="right", padx=15, pady=8)

        self.btn_header_batch = ctk.CTkButton(
            hdr_right_box,
            text="⚡ Tải Toàn Bộ HentaiVN (Mới ➜ Cũ)",
            command=self.open_hentaivn_batch_dialog,
            fg_color="#db2777",
            hover_color="#be185d",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=34,
            width=270
        )
        self.btn_header_batch.pack(side="top", anchor="e", pady=(0, 4))

        state_bar = ctk.CTkFrame(hdr_right_box, fg_color="transparent")
        state_bar.pack(side="top", anchor="e")

        self.lbl_sync_state_badge = ctk.CTkLabel(
            state_bar,
            text="⚪ Chưa nạp crawler_sync_state.json",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_sync_state_badge.pack(side="left", padx=(0, 10))

        self.btn_import_state = ctk.CTkButton(
            state_bar,
            text="📁 Nạp File JSON",
            command=self.import_sync_state_file,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=26,
            width=115
        )
        self.btn_import_state.pack(side="left")

        # ---------------- 2. TAB VIEW (DOWNLOADER / HENTAIVN BROWSER) ----------------
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="nsew")

        self.tab_download = self.tabview.add("⚡ Tải Theo Link / ID")
        self.tab_hentai = self.tabview.add("📚 Danh Sách HentaiVNReal (Mới Nhất ➜ Cũ Nhất)")

        self._setup_tab_download()
        self._setup_tab_hentaivn()

    # =========================================================================
    # TAB 1: DOWNLOAD BY DIRECT LINK / ID
    # =========================================================================
    def _setup_tab_download(self):
        tab = self.tab_download
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Top Controls: URL & Directory
        input_card = ctk.CTkFrame(tab, corner_radius=8, fg_color="#18202f")
        input_card.grid(row=0, column=0, padx=5, pady=(5, 8), sticky="ew")
        input_card.grid_columnconfigure(1, weight=1)

        # Row 0: URL
        ctk.CTkLabel(input_card, text="🔗 URL / ID Truyện:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")
        
        self.url_entry = ctk.CTkEntry(
            input_card, 
            placeholder_text="Nhập URL truyện (HentaiVN, ZetTruyen, MangaDex, hoặc MangaDex UUID)"
        )
        self.url_entry.insert(0, DEFAULT_COMIC_URL)
        self.url_entry.grid(row=0, column=1, padx=(0, 8), pady=(10, 4), sticky="ew")
        self.url_entry.bind("<KeyRelease>", self._on_url_changed)

        self.btn_fetch = ctk.CTkButton(
            input_card,
            text="🔍 Lấy Thông Tin",
            command=self.fetch_comic_info_thread,
            fg_color="#0284c7",
            hover_color="#0369a1",
            width=130,
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_fetch.grid(row=0, column=2, padx=(0, 12), pady=(10, 4))

        # Row 1: Source detection & Save path
        ctk.CTkLabel(input_card, text="📂 Lưu vào:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=12, pady=4, sticky="w")
        
        default_save_path = str((Path.cwd() / "downloads").resolve())
        self.save_entry = ctk.CTkEntry(input_card)
        self.save_entry.insert(0, default_save_path)
        self.save_entry.grid(row=1, column=1, padx=(0, 8), pady=4, sticky="ew")

        self.btn_browse = ctk.CTkButton(
            input_card,
            text="📁 Chọn Thư Mục",
            command=self.browse_folder,
            fg_color="#334155",
            hover_color="#475569",
            width=130
        )
        self.btn_browse.grid(row=1, column=2, padx=(0, 12), pady=4)

        # Row 2: Options bar (Source tag, Language, Data Saver)
        opt_bar = ctk.CTkFrame(input_card, fg_color="transparent")
        opt_bar.grid(row=2, column=0, columnspan=3, padx=12, pady=(4, 10), sticky="ew")

        self.lbl_source_detected = ctk.CTkLabel(
            opt_bar, 
            text="🏷️ Nguồn: Tự động nhận diện (ZetTruyen)", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_source_detected.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(opt_bar, text="Ngôn ngữ dịch:").pack(side="left", padx=(0, 4))
        self.lang_menu = ctk.CTkOptionMenu(
            opt_bar, 
            values=["vi (Tiếng Việt)", "en (English)", "ja (Japanese)", "all (Tất cả)"],
            width=130,
            fg_color="#1e293b"
        )
        self.lang_menu.set("vi (Tiếng Việt)")
        self.lang_menu.pack(side="left", padx=(0, 15))

        self.cb_data_saver = ctk.CTkCheckBox(opt_bar, text="⚡ MangaDex Data-Saver (Ảnh nén nhẹ)", fg_color="#0284c7")
        self.cb_data_saver.pack(side="left", padx=5)

        # Main Layout: Left panel (Options) + Right panel (Logs)
        main_split = ctk.CTkFrame(tab, fg_color="transparent")
        main_split.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        main_split.grid_columnconfigure(0, weight=4)
        main_split.grid_columnconfigure(1, weight=5)
        main_split.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL: Comic details & Options ---
        left_card = ctk.CTkScrollableFrame(main_split, corner_radius=8, fg_color="#18202f")
        left_card.grid(row=0, column=0, padx=(0, 6), pady=0, sticky="nsew")
        left_card.grid_columnconfigure(1, weight=1)

        # Comic Metadata Preview
        self.lbl_comic_title = ctk.CTkLabel(left_card, text="📖 Tên truyện: (Chưa tải dữ liệu)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8", wraplength=340, justify="left")
        self.lbl_comic_title.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 3), sticky="w")

        self.lbl_comic_stats = ctk.CTkLabel(left_card, text="📚 Tổng số chương: 0 chương", font=ctk.CTkFont(size=12), text_color="#cbd5e1", wraplength=340, justify="left")
        self.lbl_comic_stats.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")

        # Range Options
        ctk.CTkLabel(left_card, text="🎯 Chế độ tải:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=12, pady=4, sticky="w")
        
        self.mode_var = ctk.StringVar(value="all")
        self.radio_all = ctk.CTkRadioButton(left_card, text="Tất cả các chương", variable=self.mode_var, value="all", command=self._toggle_mode)
        self.radio_all.grid(row=2, column=1, padx=8, pady=4, sticky="w")

        self.radio_range = ctk.CTkRadioButton(left_card, text="Theo khoảng chương", variable=self.mode_var, value="range", command=self._toggle_mode)
        self.radio_range.grid(row=3, column=1, padx=8, pady=4, sticky="w")

        # Range inputs
        range_frame = ctk.CTkFrame(left_card, fg_color="transparent")
        range_frame.grid(row=4, column=0, columnspan=2, padx=12, pady=4, sticky="w")

        ctk.CTkLabel(range_frame, text="Từ chương:").pack(side="left", padx=(0, 4))
        self.start_chap_entry = ctk.CTkEntry(range_frame, width=65, placeholder_text="1")
        self.start_chap_entry.pack(side="left", padx=4)

        ctk.CTkLabel(range_frame, text="Đến chương:").pack(side="left", padx=(8, 4))
        self.end_chap_entry = ctk.CTkEntry(range_frame, width=65, placeholder_text="10")
        self.end_chap_entry.pack(side="left", padx=4)

        # Advanced Checkboxes
        ctk.CTkLabel(left_card, text="⚙️ Tùy chọn nâng cao:", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w")

        self.cb_pdf = ctk.CTkCheckBox(left_card, text="📄 Tự động xuất mỗi chương thành file PDF", fg_color="#0284c7")
        self.cb_pdf.grid(row=6, column=0, columnspan=2, padx=12, pady=3, sticky="w")

        self.cb_merge = ctk.CTkCheckBox(left_card, text="🧩 Ghép ảnh Manhwa (5-in-1, tự động khi > 70 ảnh)", fg_color="#0284c7")
        self.cb_merge.grid(row=7, column=0, columnspan=2, padx=12, pady=3, sticky="w")

        self.cb_upload_web = ctk.CTkCheckBox(left_card, text="🌐 Tự động đồng bộ lên Website & Cloud Storage", fg_color="#0284c7")
        self.cb_upload_web.select()
        self.cb_upload_web.grid(row=8, column=0, columnspan=2, padx=12, pady=3, sticky="w")

        # Threads slider
        thread_frame = ctk.CTkFrame(left_card, fg_color="transparent")
        thread_frame.grid(row=9, column=0, columnspan=2, padx=12, pady=8, sticky="ew")
        
        self.lbl_threads = ctk.CTkLabel(thread_frame, text="⚡ Luồng tải song song: 16 luồng")
        self.lbl_threads.pack(anchor="w")

        self.slider_threads = ctk.CTkSlider(thread_frame, from_=4, to=32, number_of_steps=7, command=self._update_threads_label)
        self.slider_threads.set(16)
        self.slider_threads.pack(fill="x", pady=4)

        # Cover Preview Frame
        self.cover_label = ctk.CTkLabel(left_card, text="[ Chưa có ảnh bìa ]", width=120, height=160, fg_color="#0f172a", corner_radius=6)
        self.cover_label.grid(row=10, column=0, columnspan=2, padx=12, pady=(5, 10))

        # --- RIGHT PANEL: Logs ---
        right_card = ctk.CTkFrame(main_split, corner_radius=8, fg_color="#18202f")
        right_card.grid(row=0, column=1, padx=(6, 0), pady=0, sticky="nsew")
        right_card.grid_rowconfigure(1, weight=1)
        right_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_card, text="📋 Nhật Ký Tải Truyện (Live Logs):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=12, pady=(8, 4), sticky="w")

        self.log_box = ctk.CTkTextbox(right_card, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#090d16", text_color="#38bdf8")
        self.log_box.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")

        # Bottom Progress & Action Bar
        bottom_frame = ctk.CTkFrame(tab, corner_radius=8, fg_color="#18202f")
        bottom_frame.grid(row=2, column=0, padx=5, pady=(8, 5), sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(bottom_frame, height=12, fg_color="#0f172a", progress_color="#38bdf8")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, columnspan=3, padx=15, pady=(10, 4), sticky="ew")

        self.lbl_status = ctk.CTkLabel(bottom_frame, text="Sẵn sàng...", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        self.lbl_status.grid(row=1, column=0, padx=15, pady=(0, 8), sticky="w")

        btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=2, padx=15, pady=(0, 8), sticky="e")

        self.btn_open_folder = ctk.CTkButton(
            btn_frame,
            text="📂 Mở Thư Mục",
            command=self.open_output_folder,
            fg_color="#334155",
            hover_color="#475569",
            width=115
        )
        self.btn_open_folder.pack(side="left", padx=4)

        self.btn_start = ctk.CTkButton(
            btn_frame,
            text="🚀 Bắt Đầu Tải",
            command=self.start_download_thread,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=135
        )
        self.btn_start.pack(side="left", padx=4)

        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text="⛔ Dừng Lại",
            command=self.cancel_download,
            fg_color="#ef4444",
            hover_color="#dc2626",
            width=90,
            state="disabled"
        )
        self.btn_cancel.pack(side="left", padx=4)

        self._toggle_mode()
        self.log("🚀 NekoHentai Manga Downloader sẵn sàng!\nHỗ trợ tải từ ZetTruyen và MangaDex (Tiếng Việt).")

    # =========================================================================
    # TAB 2: HENTAIVNREAL BROWSER & LIST (MỚI NHẤT ➜ CŨ NHẤT)
    # =========================================================================
    def _setup_tab_hentaivn(self):
        tab = self.tab_hentai
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Nav & Search Bar Card
        search_card = ctk.CTkFrame(tab, corner_radius=8, fg_color="#18202f")
        search_card.grid(row=0, column=0, padx=5, pady=(5, 8), sticky="ew")
        search_card.grid_columnconfigure(0, weight=1)

        nav_row = ctk.CTkFrame(search_card, fg_color="transparent")
        nav_row.pack(fill="x", padx=10, pady=8)

        self.lbl_hentai_status = ctk.CTkLabel(
            nav_row,
            text="Danh sách truyện trên hentaivnreal.com/danh-sach (Mới nhất ➜ Cũ nhất)",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.lbl_hentai_status.pack(side="left", padx=5)

        self.cb_hide_downloaded = ctk.CTkCheckBox(
            nav_row,
            text="Ẩn truyện đã tải",
            command=self._on_toggle_hide_downloaded,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10b981"
        )
        self.cb_hide_downloaded.pack(side="left", padx=15)

        # Right Action Buttons
        btn_action_box = ctk.CTkFrame(nav_row, fg_color="transparent")
        btn_action_box.pack(side="right")

        self.btn_prev_page = ctk.CTkButton(
            btn_action_box,
            text="◀ Trang Trước",
            command=self.prev_hentai_page,
            width=95,
            fg_color="#1e293b"
        )
        self.btn_prev_page.pack(side="left", padx=3)

        ctk.CTkLabel(btn_action_box, text="Trang", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(6, 3))

        self.hentai_page_entry = ctk.CTkEntry(
            btn_action_box,
            width=50,
            height=28,
            justify="center",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.hentai_page_entry.insert(0, "1")
        self.hentai_page_entry.pack(side="left", padx=2)
        self.hentai_page_entry.bind("<Return>", self.goto_hentai_page)

        self.lbl_hentai_total_pages = ctk.CTkLabel(
            btn_action_box,
            text="/ 982",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_hentai_total_pages.pack(side="left", padx=(2, 4))

        self.btn_goto_page = ctk.CTkButton(
            btn_action_box,
            text="Đi ↵",
            command=self.goto_hentai_page,
            width=42,
            height=28,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_goto_page.pack(side="left", padx=(0, 4))

        self.btn_next_page = ctk.CTkButton(
            btn_action_box,
            text="Trang Sau ▶",
            command=self.next_hentai_page,
            width=95,
            fg_color="#1e293b"
        )
        self.btn_next_page.pack(side="left", padx=3)

        self.btn_hentai_refresh = ctk.CTkButton(
            btn_action_box,
            text="🔄 Làm Mới",
            command=self.refresh_hentai_list,
            fg_color="#334155",
            hover_color="#475569",
            width=85
        )
        self.btn_hentai_refresh.pack(side="left", padx=4)

        self.btn_hentai_download_all = ctk.CTkButton(
            btn_action_box,
            text="⚡ Tải Toàn Bộ (Mới ➜ Cũ)",
            command=self.open_hentaivn_batch_dialog,
            fg_color="#db2777",
            hover_color="#be185d",
            font=ctk.CTkFont(weight="bold"),
            width=210
        )
        self.btn_hentai_download_all.pack(side="left", padx=(6, 0))

        # Scrollable Comic Cards Container
        self.hentai_scroll_frame = ctk.CTkScrollableFrame(tab, corner_radius=8, fg_color="#131722")
        self.hentai_scroll_frame.grid(row=1, column=0, padx=5, pady=0, sticky="nsew")
        self.hentai_scroll_frame.grid_columnconfigure(0, weight=1)

        # Trigger first HentaiVN load
        self.after(500, self.refresh_hentai_list)

    # =========================================================================
    # EVENT HANDLERS & HELPERS
    # =========================================================================
    def _update_threads_label(self, val):
        self.lbl_threads.configure(text=f"⚡ Luồng tải song song: {int(val)} luồng")

    def _toggle_mode(self):
        is_range = (self.mode_var.get() == "range")
        if is_range:
            self.start_chap_entry.configure(state="normal")
            self.end_chap_entry.configure(state="normal")
        else:
            self.start_chap_entry.configure(state="disabled")
            self.end_chap_entry.configure(state="disabled")

    def _on_url_changed(self, event=None):
        url = self.url_entry.get().strip()
        is_hentai = "hentaivnreal.com" in url or "/truyen/" in url
        is_mangadex = "mangadex.org" in url or re.match(r'^[0-9a-fA-F-]{36}$', url)
        if is_hentai:
            self.lbl_source_detected.configure(text="🏷️ Nguồn: HentaiVNReal (https://hentaivnreal.com)", text_color="#ec4899")
        elif is_mangadex:
            self.lbl_source_detected.configure(text="🏷️ Nguồn: MangaDex (Tiếng Việt)", text_color="#10b981")
        elif "zettruyen" in url:
            self.lbl_source_detected.configure(text="🏷️ Nguồn: ZetTruyen", text_color="#38bdf8")
        else:
            self.lbl_source_detected.configure(text="🏷️ Nguồn: Tự động nhận diện", text_color="#94a3b8")

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_entry.get())
        if folder:
            self.save_entry.delete(0, "end")
            self.save_entry.insert(0, folder)

    def open_output_folder(self):
        folder = self.save_entry.get()
        if os.path.exists(folder):
            if sys.platform == 'win32':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        else:
            messagebox.showwarning("Thông báo", "Thư mục lưu chưa tồn tại!")

    def log(self, text: str):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    # =========================================================================
    # HENTAIVNREAL BROWSER LOGIC
    # =========================================================================
    def _on_toggle_hide_downloaded(self):
        if hasattr(self, 'last_hentai_items') and self.last_hentai_items:
            self._render_hentai_results(self.last_hentai_items)

    def refresh_hentai_list(self):
        self.fetch_hentai_list_thread()

    def prev_hentai_page(self):
        if self.current_hentai_page > 1:
            self.current_hentai_page -= 1
            self.fetch_hentai_list_thread()

    def next_hentai_page(self):
        if self.current_hentai_page < self.total_hentai_pages:
            self.current_hentai_page += 1
            self.fetch_hentai_list_thread()

    def goto_hentai_page(self, event=None):
        try:
            page = int(self.hentai_page_entry.get().strip())
            if 1 <= page <= self.total_hentai_pages:
                self.current_hentai_page = page
                self.fetch_hentai_list_thread()
            else:
                messagebox.showwarning("Cảnh báo", f"Vui lòng nhập trang từ 1 đến {self.total_hentai_pages}")
        except ValueError:
            pass

    # Aliases
    refresh_mangadex_latest = refresh_hentai_list
    prev_mangadex_page = prev_hentai_page
    next_mangadex_page = next_hentai_page
    goto_mangadex_page = goto_hentai_page

    def fetch_hentai_list_thread(self):
        if self.is_fetching_hentai_list:
            return
        self.is_fetching_hentai_list = True
        self.lbl_hentai_status.configure(text=f"Đang tải danh sách truyện trang {self.current_hentai_page} từ hentaivnreal.com...")
        self.btn_goto_page.configure(state="disabled")
        self.btn_hentai_refresh.configure(state="disabled")
        self.btn_prev_page.configure(state="disabled")
        self.btn_next_page.configure(state="disabled")
        self.hentai_page_entry.delete(0, "end")
        self.hentai_page_entry.insert(0, str(self.current_hentai_page))

        for widget in self.hentai_scroll_frame.winfo_children():
            widget.destroy()

        loading_lbl = ctk.CTkLabel(
            self.hentai_scroll_frame, 
            text=f"⏳ Đang kết nối hentaivnreal.com (Trang {self.current_hentai_page})...", 
            font=ctk.CTkFont(size=14)
        )
        loading_lbl.pack(pady=30)

        threading.Thread(target=self._fetch_hentai_list_worker, daemon=True).start()

    def _fetch_hentai_list_worker(self):
        try:
            scraper = cloudscraper.create_scraper()
            url = f"https://hentaivnreal.com/danh-sach?page={self.current_hentai_page}"
            res = scraper.get(url, timeout=20)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, "html.parser")

            pag = soup.find(class_=lambda c: c and 'pagination' in c)
            if pag:
                for a in pag.find_all('a'):
                    href = a.get('href', '')
                    if 'page=' in href:
                        try:
                            p_num = int(href.split('page=')[-1].split('&')[0])
                            self.total_hentai_pages = max(self.total_hentai_pages, p_num)
                        except Exception:
                            pass
                    t = a.get_text(strip=True)
                    if t.isdigit():
                        self.total_hentai_pages = max(self.total_hentai_pages, int(t))

            items = []
            for it in soup.select("li.item"):
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

                items.append({
                    "id": slug,
                    "slug": slug,
                    "title": comic_title,
                    "url": comic_full_url,
                    "cover_thumb": thumb_url,
                    "other_names": other_names,
                    "tags": tags,
                    "views": views
                })

            self.after(0, lambda: self._render_hentai_results(items))
        except Exception as e:
            self.after(0, lambda err=str(e): self._render_hentai_error(err))
        finally:
            self.is_fetching_hentai_list = False
            self.after(0, lambda: (
                self.btn_hentai_refresh.configure(state="normal"),
                self.btn_goto_page.configure(state="normal"),
                self.btn_prev_page.configure(state="normal" if self.current_hentai_page > 1 else "disabled"),
                self.btn_next_page.configure(state="normal" if self.current_hentai_page < self.total_hentai_pages else "disabled")
            ))

    def _render_hentai_results(self, items):
        self.last_hentai_items = items
        for widget in self.hentai_scroll_frame.winfo_children():
            widget.destroy()

        self.lbl_hentai_total_pages.configure(text=f"/ {self.total_hentai_pages}")
        self.btn_prev_page.configure(state="normal" if self.current_hentai_page > 1 else "disabled")
        self.btn_next_page.configure(state="normal" if self.current_hentai_page < self.total_hentai_pages else "disabled")
        self.btn_goto_page.configure(state="normal")
        self.hentai_page_entry.delete(0, "end")
        self.hentai_page_entry.insert(0, str(self.current_hentai_page))

        hide_downloaded = hasattr(self, 'cb_hide_downloaded') and (self.cb_hide_downloaded.get() == 1)
        hidden_count = 0

        # Lọc danh sách nếu người dùng bật ẩn truyện đã tải
        visible_items = []
        for item in items:
            slug = item.get("slug") or item["url"].split("?")[0].rstrip("/").split("/")[-1]
            if hide_downloaded and self.sync_state.is_comic_completed(slug):
                hidden_count += 1
                continue
            visible_items.append(item)

        status_text = f"Trang {self.current_hentai_page}/{self.total_hentai_pages} • Hiển thị {len(visible_items)} bộ truyện"
        if hidden_count > 0:
            status_text += f" (Đã ẩn {hidden_count} bộ đã tải)"
        self.lbl_hentai_status.configure(text=status_text)

        if not visible_items:
            msg = "❌ Không có truyện nào trên trang này!"
            if hidden_count > 0:
                msg = f"✅ Tất cả {hidden_count} bộ truyện trên trang này đã được tải xong!\n(Bỏ chọn 'Ẩn truyện đã tải' ở góc trên để xem lại)"
            empty_lbl = ctk.CTkLabel(
                self.hentai_scroll_frame, 
                text=msg,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#10b981" if hidden_count > 0 else "#ef4444"
            )
            empty_lbl.pack(pady=40)
            return

        for item in visible_items:
            slug = item.get("slug") or item["url"].split("?")[0].rstrip("/").split("/")[-1]
            is_completed = self.sync_state.is_comic_completed(slug)
            synced_chaps = self.sync_state.get_synced_chapters(slug)

            if is_completed:
                card_bg = "#0c281e"
                card_border = "#10b981"
                border_w = 2
            elif synced_chaps:
                card_bg = "#1f2430"
                card_border = "#f59e0b"
                border_w = 1
            else:
                card_bg = "#18202f"
                card_border = "#334155"
                border_w = 0

            card_kwargs = {
                "corner_radius": 8,
                "fg_color": card_bg,
                "border_width": border_w
            }
            if border_w > 0:
                card_kwargs["border_color"] = card_border

            card = ctk.CTkFrame(self.hentai_scroll_frame, **card_kwargs)
            card.pack(fill="x", padx=5, pady=5)
            card.grid_columnconfigure(1, weight=1)

            # Cover Label Placeholder
            cover_lbl = ctk.CTkLabel(card, text="[Ảnh bìa]", width=65, height=90, fg_color="#0f172a", corner_radius=4)
            cover_lbl.grid(row=0, column=0, rowspan=3, padx=10, pady=10)

            # Details
            title_txt = item["title"]
            if is_completed:
                comp = self.sync_state.get_completed_info(slug) or {}
                chap_c = comp.get("chapters_count", len(synced_chaps))
                disp_title = f"✅ [ĐÃ TẢI XONG - {chap_c} CHAP]  {title_txt}"
                title_color = "#6ee7b7"
            elif synced_chaps:
                disp_title = f"⚡ [ĐÃ TẢI {len(synced_chaps)} CHAP]  {title_txt}"
                title_color = "#fbbf24"
            else:
                disp_title = title_txt
                title_color = "#38bdf8"

            t_lbl = ctk.CTkLabel(
                card, 
                text=disp_title, 
                font=ctk.CTkFont(size=14, weight="bold"), 
                text_color=title_color,
                anchor="w",
                justify="left",
                wraplength=550
            )
            t_lbl.grid(row=0, column=1, padx=5, pady=(8, 2), sticky="w")

            genres_txt = ", ".join(item["tags"][:5]) if item.get("tags") else "Manga"
            meta_txt = f"🏷️ Thể loại: {genres_txt}"
            if item.get("other_names"):
                meta_txt += f"  •  Tên khác: {item['other_names'][:40]}"
            if item.get("views"):
                meta_txt += f"  •  👁️ {item['views']:,} lượt xem"

            m_lbl = ctk.CTkLabel(
                card, 
                text=meta_txt, 
                font=ctk.CTkFont(size=11), 
                text_color="#94a3b8",
                anchor="w",
                justify="left",
                wraplength=550
            )
            m_lbl.grid(row=1, column=1, padx=5, pady=0, sticky="w")

            url_lbl = ctk.CTkLabel(
                card, 
                text=item["url"], 
                font=ctk.CTkFont(family="Consolas", size=10), 
                text_color="#64748b"
            )
            url_lbl.grid(row=2, column=1, padx=5, pady=(0, 6), sticky="w")

            # Buttons
            btn_box = ctk.CTkFrame(card, fg_color="transparent")
            btn_box.grid(row=0, column=2, rowspan=3, padx=10, pady=10)

            if is_completed:
                btn_dl_text = "✅ Đã Tải (Tải Lại)"
                btn_dl_color = "#059669"
                btn_dl_hover = "#047857"
            elif synced_chaps:
                btn_dl_text = "⚡ Tải Tiếp"
                btn_dl_color = "#d97706"
                btn_dl_hover = "#b45309"
            else:
                btn_dl_text = "📥 Chọn Tải Truyện"
                btn_dl_color = "#10b981"
                btn_dl_hover = "#059669"

            btn_select = ctk.CTkButton(
                btn_box,
                text=btn_dl_text,
                fg_color=btn_dl_color,
                hover_color=btn_dl_hover,
                width=145,
                font=ctk.CTkFont(weight="bold"),
                command=lambda u=item['url']: self.select_comic_for_download(u)
            )
            btn_select.pack(pady=3)

            btn_open_web = ctk.CTkButton(
                btn_box,
                text="🌐 Mở Web",
                fg_color="#334155",
                hover_color="#475569",
                width=145,
                command=lambda u=item['url']: webbrowser.open(u)
            )
            btn_open_web.pack(pady=3)

            # Load thumbnail async
            if item.get("cover_thumb"):
                threading.Thread(
                    target=self._load_async_thumb, 
                    args=(item["cover_thumb"], cover_lbl), 
                    daemon=True
                ).start()

    def _render_hentai_error(self, err_msg):
        for widget in self.hentai_scroll_frame.winfo_children():
            widget.destroy()
        err_lbl = ctk.CTkLabel(
            self.hentai_scroll_frame,
            text=f"❌ Lỗi kết nối hentaivnreal.com:\n{err_msg}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ef4444"
        )
        err_lbl.pack(pady=30)

    def select_comic_for_download(self, comic_url):
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, comic_url)
        self._on_url_changed()
        self.tabview.set("⚡ Tải Theo Link / ID")
        self.fetch_comic_info_thread()

    def select_mangadex_comic(self, manga_id, manga_title):
        self.select_comic_for_download(f"https://mangadex.org/title/{manga_id}")

    def _load_async_thumb(self, img_url, label_widget):
        try:
            r = requests.get(img_url, headers={"User-Agent": "NekoHentai-Downloader/1.0", "Referer": "https://hentaivnreal.com/"}, timeout=10)
            if r.status_code == 200:
                pil_im = Image.open(BytesIO(r.content))
                pil_im.thumbnail((65, 90))
                ctk_im = ctk.CTkImage(light_image=pil_im, dark_image=pil_im, size=pil_im.size)
                self.after(0, lambda: label_widget.configure(image=ctk_im, text=""))
        except Exception:
            pass

    # =========================================================================
    # METADATA FETCH ENGINE (HENTAIVNREAL, ZETTRUYEN & MANGADEX)
    # =========================================================================
    def fetch_comic_info_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Lỗi", "Vui lòng nhập đường dẫn hoặc ID truyện!")
            return

        self.btn_fetch.configure(state="disabled", text="Đang lấy...")
        self.lbl_status.configure(text="Đang phân tích dữ liệu truyện...")

        threading.Thread(target=self._fetch_comic_info_worker, args=(url,), daemon=True).start()

    def _fetch_comic_info_worker(self, url):
        try:
            self.log(f"\n🔍 Đang phân tích thông tin từ: {url}")
            is_hentai = "hentaivnreal.com" in url or "/truyen/" in url
            is_mangadex = "mangadex.org" in url or re.match(r'^[0-9a-fA-F-]{36}$', url)

            # Get selected lang
            lang_choice = self.lang_menu.get().split(" ")[0].strip()
            data_saver = self.cb_data_saver.get() == 1

            if is_hentai:
                downloader = HentaiVNRealDownloader(
                    comic_url=url,
                    output_dir=self.save_entry.get(),
                    merge_slices=self.cb_merge.get() == 1,
                    make_pdf=self.cb_pdf.get() == 1,
                    upload_to_web=self.cb_upload_web.get() == 1,
                    api_base_url=DEFAULT_API_BASE_URL
                )
            elif is_mangadex:
                downloader = MangaDexDownloader(
                    manga_id_or_url=url,
                    output_dir=self.save_entry.get(),
                    merge_slices=self.cb_merge.get() == 1,
                    make_pdf=self.cb_pdf.get() == 1,
                    upload_to_web=self.cb_upload_web.get() == 1,
                    api_base_url=DEFAULT_API_BASE_URL,
                    lang=lang_choice if lang_choice != "all" else DEFAULT_LANG,
                    data_saver=data_saver
                )
            else:
                downloader = ZetMangaDownloader(
                    comic_url=url,
                    output_dir=self.save_entry.get(),
                    merge_slices=self.cb_merge.get() == 1,
                    make_pdf=self.cb_pdf.get() == 1,
                    upload_to_web=self.cb_upload_web.get() == 1,
                    api_base_url=DEFAULT_API_BASE_URL
                )

            info = downloader.get_comic_info()
            self.downloader_instance = downloader
            self.comic_info = info

            self.after(0, self._on_fetch_success)

        except Exception as e:
            self.after(0, lambda err=str(e): self._on_fetch_error(err))

    def _on_fetch_success(self):
        info = self.comic_info
        self.btn_fetch.configure(state="normal", text="🔍 Lấy Thông Tin")

        slug = info.get("slug", "")
        src_name = getattr(self.downloader_instance, 'source_name', 'NekoHentai')
        chapters_count = len(info.get('chapters', []))
        views_txt = f"{info.get('views', 0):,} lượt xem" if info.get('views') else "0 lượt xem"
        genres_txt = ", ".join(info.get('genres', [])[:4]) if info.get('genres') else "Manga"

        is_completed = self.sync_state.is_comic_completed(slug)
        synced_ch = self.sync_state.get_synced_chapters(slug)

        if is_completed:
            comp_info = self.sync_state.get_completed_info(slug) or {}
            c_cnt = comp_info.get("chapters_count", len(synced_ch))
            self.lbl_comic_title.configure(text=f"✅ [ĐÃ TẢI XONG - {c_cnt} CHƯƠNG] {info['title']}", text_color="#10b981")
            self.log(f"✅ Bộ truyện '{info['title']}' ĐÃ ĐƯỢC TẢI XONG theo crawler_sync_state.json ({c_cnt} chapters)!")
        elif synced_ch:
            self.lbl_comic_title.configure(text=f"⚡ [ĐÃ TẢI {len(synced_ch)} CHƯƠNG] {info['title']}", text_color="#f59e0b")
            self.log(f"⚡ Truyện '{info['title']}' đã có {len(synced_ch)} chương trong sync state: {', '.join(synced_ch[:8])}...")
        else:
            self.lbl_comic_title.configure(text=f"📖 {info['title']}", text_color="#38bdf8")

        self.lbl_comic_stats.configure(
            text=f"🏷️ Nguồn: {src_name}  •  📚 {chapters_count} chương\n✍️ Tác giả: {info.get('author', 'Đang cập nhật')}  •  Nhóm dịch: {info.get('translator_group', 'Đang cập nhật')}\n🏷️ Thể loại: {genres_txt}"
        )
        
        if info.get('chapters'):
            self.start_chap_entry.delete(0, "end")
            first_num = info['chapters'][0]['number']
            self.start_chap_entry.insert(0, str(int(first_num) if isinstance(first_num, float) and first_num.is_integer() else first_num))
            
            self.end_chap_entry.delete(0, "end")
            last_num = info['chapters'][-1]['number']
            self.end_chap_entry.insert(0, str(int(last_num) if isinstance(last_num, float) and last_num.is_integer() else last_num))

        self.lbl_status.configure(text=f"Đã lấy thông tin: {info['title']} ({chapters_count} chương)")
        self.log(f"✓ Đã tìm thấy {chapters_count} chương của '{info['title']}' từ {src_name}.")

        # Load cover preview
        if info.get("cover_url"):
            threading.Thread(target=self._load_cover_thumbnail, args=(info["cover_url"],), daemon=True).start()

    def _load_cover_thumbnail(self, cover_url):
        try:
            r = requests.get(cover_url, headers={"User-Agent": "NekoHentai-Downloader/1.0"}, timeout=10)
            if r.status_code == 200:
                img_data = BytesIO(r.content)
                pil_img = Image.open(img_data)
                pil_img.thumbnail((120, 160))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                self.after(0, lambda: self.cover_label.configure(image=ctk_img, text=""))
        except Exception:
            pass

    def _on_fetch_error(self, err_msg):
        self.btn_fetch.configure(state="normal", text="🔍 Lấy Thông Tin")
        self.lbl_status.configure(text="Lỗi lấy dữ liệu!")
        self.log(f"❌ Lỗi: {err_msg}")
        messagebox.showerror("Lỗi", f"Không thể lấy thông tin truyện:\n{err_msg}")

    # =========================================================================
    # DOWNLOAD EXECUTION WORKER
    # =========================================================================
    def start_download_thread(self):
        if not self.comic_info or not self.comic_info.get("chapters"):
            messagebox.showwarning("Cảnh báo", "Vui lòng bấm 'Lấy Thông Tin' trước khi tải!")
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.btn_start.configure(state="disabled")
        self.btn_fetch.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.progress_bar.set(0)

        threading.Thread(target=self._download_worker, daemon=True).start()

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.lbl_status.configure(text="Đang hủy tiến trình...")
            self.log("⚠️ Người dùng yêu cầu dừng tải...")

    def _download_worker(self):
        info = self.comic_info
        title = info["title"]
        slug = info["slug"]
        all_chaps = info["chapters"]
        out_root = Path(self.save_entry.get())

        # Cấu trúc lưu chuẩn theo bucket: covers/{slug}.webp & chapters/{slug}/chap{num}/page_{idx:03d}.webp
        covers_dir = out_root / "covers"
        covers_dir.mkdir(parents=True, exist_ok=True)
        chapters_root_dir = out_root / "chapters" / slug
        chapters_root_dir.mkdir(parents=True, exist_ok=True)

        # Filter target chapters
        if self.mode_var.get() == "range":
            try:
                start_c = float(self.start_chap_entry.get() or 1)
                end_c = float(self.end_chap_entry.get() or 9999)
                target_chaps = [c for c in all_chaps if start_c <= c["number"] <= end_c]
            except Exception:
                target_chaps = all_chaps
        else:
            target_chaps = all_chaps

        if not target_chaps:
            self.after(0, lambda: self.log("❌ Không có chapter nào được chọn!"))
            self.after(0, self._on_download_finished)
            return

        workers = int(self.slider_threads.get())
        make_pdf = self.cb_pdf.get() == 1
        merge_slices = self.cb_merge.get() == 1
        upload_to_web = self.cb_upload_web.get() == 1
        downloader = self.downloader_instance

        self.after(0, lambda: self.log(f"\n=========================================="))
        self.after(0, lambda: self.log(f"🚀 Bắt đầu tải {len(target_chaps)} chương ({workers} luồng song song)..."))
        self.after(0, lambda: self.log(f"📂 Thư mục máy: {chapters_root_dir}"))
        self.after(0, lambda: self.log(f"📁 Cấu trúc lưu chuẩn: covers/{slug}.webp & chapters/{slug}/chap<num>/page_001.webp"))
        self.after(0, lambda: self.log(f"🖼 Định dạng ảnh: WebP (Chất lượng 90)"))
        if upload_to_web:
            self.after(0, lambda: self.log(f"🌐 Chế độ: Tự động đưa lên Website & Cloud Storage sau khi tải"))

        # Download and upload cover (covers/{slug}.webp)
        cover_cdn_url = None
        if info.get("cover_url"):
            raw_cover_path = covers_dir / f"{slug}_raw.jpg"
            cover_path = covers_dir / f"{slug}.webp"
            downloader._download_single_image(info["cover_url"], raw_cover_path)
            if raw_cover_path.exists():
                try:
                    with Image.open(raw_cover_path) as im:
                        if im.mode != 'RGB':
                            im = im.convert('RGB')
                        im.save(cover_path, 'WEBP', quality=90, method=6)
                    raw_cover_path.unlink(missing_ok=True)
                except Exception:
                    cover_path = raw_cover_path

            if upload_to_web and cover_path.exists():
                try:
                    cover_cdn_url = upload_file_to_cloud(cover_path, f"covers/{slug}.webp", "image/webp")
                    self.after(0, lambda u=cover_cdn_url: self.log(f"📸 Đã lưu & đưa Ảnh bìa lên Cloud: {u}"))
                except Exception as e:
                    self.after(0, lambda err=e: self.log(f"⚠️ Lỗi upload ảnh bìa: {err}"))

        total_images_all = 0
        start_time = time.time()

        for idx, chap in enumerate(target_chaps, 1):
            if self.cancel_requested:
                self.after(0, lambda: self.log("⛔ Đã hủy quá trình tải!"))
                break

            num = chap["number"]
            num_str = f"{int(num)}" if isinstance(num, (int, float)) and float(num).is_integer() else f"{num}"
            raw_t = (chap.get("title") or "").strip()
            is_oneshot = bool(re.search(r'oneshot|one-shot|1shot', raw_t, re.I) or re.search(r'oneshot|one-shot', str(title or ''), re.I))
            if is_oneshot:
                clean_t = re.sub(r'^(?:chương|chap|chapter)\s*[\d\.]*\s*[-:]*\s*', '', raw_t, flags=re.I).strip()
                chap_title = clean_t or "Oneshot"
                api_chap_title = "Oneshot"
            else:
                clean_t = re.sub(r'^(?:chương|chap|chapter|tập|ep|episode)\s*[\d\.]*\s*[-:–—.]*\s*', '', raw_t, flags=re.I).strip()
                clean_t = re.sub(rf'^0*{re.escape(num_str)}\s*[-:–—.]+\s*', '', clean_t, flags=re.I).strip()
                if clean_t == num_str or clean_t == f"0{num_str}":
                    clean_t = ""
                clean_t = clean_t.lstrip('-:–—. ').rstrip('-:–—. ')

                chap_title = f"Chương {num_str}"
                if clean_t:
                    chap_title += f" - {clean_t}"
                api_chap_title = clean_t if clean_t else f"Chapter {num_str}"

            chap_dir = chapters_root_dir / f"chap{num_str}"
            chap_dir.mkdir(parents=True, exist_ok=True)

            self.after(0, lambda t=chap_title, i=idx, tot=len(target_chaps): (
                self.lbl_status.configure(text=f"Đang xử lý [{i}/{tot}] {t}..."),
                self.log(f"\n▶ [{i}/{tot}] Đang tải {t}...")
            ))

            images = downloader.get_chapter_images(chap)
            if not images:
                self.after(0, lambda t=chap_title: self.log(f"  ⚠️ Không tìm thấy ảnh cho {t}"))
                continue

            num_raw = len(images)
            should_merge = merge_slices or (num_raw > AUTO_STITCH_THRESHOLD)

            if should_merge:
                temp_dir = chap_dir / "_temp_slices"
                temp_dir.mkdir(parents=True, exist_ok=True)
                download_dir = temp_dir
            else:
                download_dir = chap_dir

            downloaded = []
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {}
                for i, img_url in enumerate(images):
                    if self.cancel_requested:
                        break
                    ext = img_url.split(".")[-1].split("?")[0].lower()
                    if ext not in ("jpg", "jpeg", "png", "webp"):
                        ext = "jpg"
                    save_p = download_dir / f"page_raw_{i+1:04d}.{ext}" if should_merge else download_dir / f"page_{i+1:03d}.{ext}"
                    downloaded.append(save_p)
                    f = executor.submit(downloader._download_single_image, img_url, save_p, chap.get("url"))
                    futures[f] = save_p

                done_count = 0
                for f in as_completed(futures):
                    if self.cancel_requested:
                        break
                    f.result()
                    done_count += 1
                    prog = (idx - 1 + (done_count / len(images))) / len(target_chaps)
                    self.after(0, lambda p=prog, dc=done_count, tc=len(images), ct=chap_title: (
                        self.progress_bar.set(p),
                        self.lbl_status.configure(text=f"{ct}: {dc}/{tc} ảnh ({int(p*100)}%)")
                    ))

            valid_paths = [p for p in downloaded if p.exists()]
            num_downloaded = len(valid_paths)

            final_paths = []
            if should_merge:
                reason = f"Chapter có {num_downloaded} lát cắt (> {AUTO_STITCH_THRESHOLD})" if num_downloaded > AUTO_STITCH_THRESHOLD else "Tùy chọn ghép ảnh được bật"
                self.after(0, lambda r=reason: self.log(f"  🧩 {r} ➜ Đang ghép trực tiếp {STITCH_GROUP_SIZE} in 1 (WebP)..."))
                
                final_paths = downloader._merge_images_vertical(valid_paths, chap_dir, STITCH_GROUP_SIZE)
                
                for p in valid_paths:
                    try:
                        p.unlink(missing_ok=True)
                    except Exception:
                        pass
                try:
                    temp_dir.rmdir()
                except Exception:
                    pass

                self.after(0, lambda cnt=len(final_paths), n=num_downloaded, cname=f"chap{num_str}": self.log(
                    f"  ✓ Đã xuất {cnt} trang ảnh WebP hoàn chỉnh vào chapters/{slug}/{cname}/ (đã dọn {n} lát cắt thô)"
                ))
            else:
                final_paths = []
                for idx_p, p in enumerate(valid_paths, 1):
                    webp_path = chap_dir / f"page_{idx_p:03d}.webp"
                    try:
                        with Image.open(p) as raw_im:
                            raw_im.load()
                            if raw_im.mode != 'RGB':
                                im = raw_im.convert('RGB')
                            else:
                                im = raw_im
                            im.save(webp_path, 'WEBP', quality=90, method=6)
                        final_paths.append(webp_path)
                        if p != webp_path and p.exists():
                            p.unlink(missing_ok=True)
                    except Exception:
                        final_paths.append(p)
                self.after(0, lambda t=chap_title, c=len(final_paths): self.log(f"  ✓ Đã tải xong {c} trang ảnh WebP."))

            total_images_all += len(final_paths)

            if make_pdf:
                self.after(0, lambda: self.log("  📄 Đang tạo file PDF..."))
                pdf_f = chap_dir / f"chap{num_str}.pdf"
                downloader._export_pdf(final_paths, pdf_f)

            # Upload to Cloud Storage & Web API
            if upload_to_web and final_paths:
                self.after(0, lambda t=chap_title: self.log(f"  ☁️ Đang đưa {t} (WebP) lên Cloud Storage & Website..."))
                uploaded_cdn_urls = [None] * len(final_paths)
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    fut_map = {}
                    for p_idx, p in enumerate(final_paths):
                        obj_name = f"chapters/{slug}/chap{num_str}/page_{p_idx+1:03d}.webp"
                        fut = executor.submit(upload_file_to_cloud, p, obj_name, "image/webp")
                        fut_map[fut] = p_idx
                    for fut in as_completed(fut_map):
                        p_idx = fut_map[fut]
                        try:
                            uploaded_cdn_urls[p_idx] = fut.result()
                        except Exception:
                            pass

                valid_cdn_urls = [u for u in uploaded_cdn_urls if u]
                if valid_cdn_urls:
                    synced = sync_chapter_to_web_api(
                        api_base_url=DEFAULT_API_BASE_URL,
                        comic_title=title,
                        comic_slug=slug,
                        cover_cdn_url=cover_cdn_url or valid_cdn_urls[0],
                        chapter_num=num,
                        chapter_title=api_chap_title,
                        image_urls=valid_cdn_urls,
                        author=info.get("author"),
                        translator_group=chap.get("scanlation_group") or info.get("translator_group"),
                        other_names=info.get("other_names"),
                        age_limit=info.get("age_limit"),
                        views=chap.get("views", 0),
                        published_at=chap.get("updated_at"),
                        created_at=chap.get("updated_at"),
                        comic_views=info.get("views", 0),
                        comic_created_at=info.get("created_at_iso") or info.get("created_date_str"),
                        comic_updated_at=info.get("updated_at_iso") or info.get("updated_date_str"),
                        categories=info.get("genres", [])
                    )
                    if synced:
                        self.after(0, lambda t=chap_title, cnt=len(valid_cdn_urls): self.log(
                            f"  🌐 Đã đưa {t} lên Website thành công ({cnt} trang ảnh)!"
                        ))
                    else:
                        self.after(0, lambda t=chap_title, cnt=len(valid_cdn_urls): self.log(
                            f"  ⚠️ Đã upload Cloud {t} ({cnt} ảnh) - Chưa kết nối được Web API ({DEFAULT_API_BASE_URL})"
                        ))

            # Ghi nhận chapter đã đồng bộ vào crawler_sync_state
            self.sync_state.mark_chapter_synced(slug, num_str)

        # Ghi nhận hoàn tất bộ truyện vào crawler_sync_state
        if not self.cancel_requested:
            self.sync_state.mark_comic_completed(
                slug=slug,
                title=title,
                chapters_count=len(target_chaps),
                pages_count=total_images_all,
                source=getattr(downloader, 'source_name', 'NekoHentai')
            )
            self.after(0, self._update_sync_state_ui)
            st_name = Path(self.sync_state.file_path).name if self.sync_state.file_path else "crawler_sync_state.json"
            self.after(0, lambda fn=st_name: self.log(f"💾 Đã lưu tiến trình bộ truyện vào '{fn}' để ghi nhớ cho lần tải tiếp theo!"))

        elapsed = time.time() - start_time
        public_domain = os.getenv("PUBLIC_DOMAIN", "https://nekohentai.lol").rstrip("/")
        web_link = f"{public_domain}/comic/{slug}"
        self.after(0, lambda: self.progress_bar.set(1.0))
        self.after(0, lambda: self.log(f"\n=========================================="))
        self.after(0, lambda: self.log(f"🎉 HOÀN TẤT! Đã tải {total_images_all} ảnh trong {elapsed:.1f}s."))
        if upload_to_web:
            self.after(0, lambda: self.log(f"🌐 Link đọc truyện trên Web: {web_link}"))
        self.after(0, lambda: self.lbl_status.configure(text=f"Hoàn tất! {total_images_all} ảnh ({elapsed:.1f}s)"))

        self.after(0, self._on_download_finished)

    # =========================================================================
    # HENTAIVNREAL BATCH DOWNLOAD (ALL COMICS FROM NEWEST TO OLDEST)
    # =========================================================================
    def open_hentaivn_batch_dialog(self):
        if self.is_downloading:
            messagebox.showwarning("Cảnh báo", "Đang có tiến trình tải hoạt động! Vui lòng dừng lại trước khi bắt đầu tải hàng loạt.")
            return
        HentaiVNBatchConfigDialog(
            self,
            default_save_dir=self.save_entry.get(),
            default_api_url=DEFAULT_API_BASE_URL,
            on_start_callback=self.start_batch_hentaivn_download,
            sync_state=self.sync_state
        )

    # Alias
    open_mangadex_batch_dialog = open_hentaivn_batch_dialog

    def start_batch_hentaivn_download(self, config: dict):
        if self.is_downloading:
            return
        self.is_downloading = True
        self.cancel_requested = False
        self.btn_start.configure(state="disabled")
        self.btn_fetch.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        if hasattr(self, 'btn_header_batch'):
            self.btn_header_batch.configure(state="disabled")
        if hasattr(self, 'btn_hentai_download_all'):
            self.btn_hentai_download_all.configure(state="disabled")
        if hasattr(self, 'btn_dex_download_all'):
            self.btn_dex_download_all.configure(state="disabled")

        # Chuyển sang tab 1 để xem live progress và log chi tiết
        self.tabview.set("⚡ Tải Theo Link / ID")
        self.progress_bar.set(0)

        threading.Thread(target=self._batch_download_hentaivn_worker, args=(config,), daemon=True).start()

    # Alias
    start_batch_mangadex_download = start_batch_hentaivn_download

    def _batch_download_hentaivn_worker(self, config: dict):
        start_page = config.get("start_page", 1)
        end_page = config.get("end_page")
        max_manga = config.get("max_manga")
        out_root = Path(config.get("save_dir", self.save_entry.get()))
        upload_to_web = config.get("upload_to_web", True)
        skip_existing = config.get("skip_existing", True)
        skip_sync_state = config.get("skip_sync_state", True)
        merge_slices = config.get("merge_slices", False)
        make_pdf = config.get("make_pdf", False)
        workers = config.get("workers", 16)

        self.after(0, lambda: self.log("\n" + "=" * 70))
        self.after(0, lambda: self.log("🚀 BẮT ĐẦU TIẾN TRÌNH TẢI TOÀN BỘ HENTAIVNREAL (MỚI NHẤT ➜ CŨ NHẤT)"))
        self.after(0, lambda: self.log(f"📋 Nguồn: https://hentaivnreal.com/danh-sach | Bắt đầu từ Trang #{start_page}"))
        self.after(0, lambda: self.log(f"📂 Thư mục lưu: {out_root.resolve()}"))
        self.after(0, lambda: self.log(f"⚡ Luồng tải song song: {workers} luồng"))
        self.after(0, lambda: self.log(f"🌐 Đồng bộ Web & Cloud: {'BẬT' if upload_to_web else 'TẮT'} | ⏭️ Bỏ qua chapter đã có: {'BẬT' if skip_existing else 'TẮT'}"))
        if self.sync_state.completed_count > 0:
            self.after(0, lambda cc=self.sync_state.completed_count, sc=self.sync_state.synced_chapters_count: (
                self.log(f"📦 Đã nạp crawler_sync_state.json: {cc:,} bộ truyện đã hoàn tất ({sc:,} chapters)."),
                self.log(f"⏭️ Bỏ qua truyện đã tải trong file state: {'BẬT' if skip_sync_state else 'TẮT'}")
            ))
        self.after(0, lambda: self.log("=" * 70 + "\n"))

        self.after(0, lambda: self.lbl_status.configure(text="Đang kết nối lấy danh sách truyện từ hentaivnreal.com/danh-sach..."))

        try:
            comic_iter = HentaiVNRealDownloader.fetch_all_hentaivn_comics_iter(
                start_page=start_page,
                end_page=end_page,
                max_comics=max_manga
            )
        except Exception as e:
            self.after(0, lambda err=str(e): self.log(f"❌ Lỗi kết nối lấy danh sách HentaiVNReal: {err}"))
            self.after(0, self._on_download_finished)
            return

        total_processed_comics = 0
        total_downloaded_images = 0
        total_chapters_all = 0
        start_time = time.time()

        for item in comic_iter:
            if self.cancel_requested:
                self.after(0, lambda: self.log("\n⛔ Đã hủy tiến trình tải hàng loạt theo yêu cầu của người dùng!"))
                break

            total_processed_comics += 1
            c_title = item["title"]
            c_url = item["url"]
            c_page = item.get("page", 1)
            tot_pages = item.get("total_pages", "?")
            c_slug = item["slug"]
            remote_chaps = item.get("chapters_count")

            # 1. Kiểm tra xem truyện đã tải hoàn tất trong crawler_sync_state.json chưa
            if skip_sync_state and self.sync_state.is_comic_completed(c_slug):
                comp_info = self.sync_state.get_completed_info(c_slug) or {}
                prev_count = comp_info.get("chapters_count", 0)
                synced_list = self.sync_state.get_synced_chapters(c_slug)
                local_count = max(prev_count, len(synced_list))

                if remote_chaps is not None and remote_chaps > local_count:
                    diff = remote_chaps - local_count
                    self.after(0, lambda t=c_title, d=diff, lc=local_count, rc=remote_chaps, n=total_processed_comics, p=c_page, tp=tot_pages: (
                        self.lbl_status.configure(text=f"[#{n} | Trang {p}/{tp}] 🔄 Cập nhật chapter mới: {t}..."),
                        self.log(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"),
                        self.log(f"▶ [#{n} | Trang {p}/{tp}] 📖 {t}"),
                        self.log(f"   🔄 Phát hiện truyện ra {d} chapter mới! (Hiện có: {lc} ➜ Web: {rc} chaps). Bắt đầu tải...")
                    ))
                else:
                    self.after(0, lambda t=c_title, lc=local_count, rc=remote_chaps, n=total_processed_comics, p=c_page, tp=tot_pages: (
                        self.log(f"[#{n} | Trang {p}/{tp}] ⏭️ [crawler_sync_state.json] Đã hoàn tất ({lc}{f'/{rc}' if rc else ''} chaps): '{t}' ➜ Bỏ qua.")
                    ))
                    continue

            self.after(0, lambda n=total_processed_comics, p=c_page, tp=tot_pages, t=c_title, u=c_url: (
                self.lbl_status.configure(text=f"[#{n} | Trang {p}/{tp}] Đang xử lý: {t}..."),
                self.log(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"),
                self.log(f"▶ [#{n} | Trang {p}/{tp}] 📖 {t}"),
                self.log(f"   🔗 Link: {u} | Slug: {c_slug}")
            ))

            try:
                downloader = HentaiVNRealDownloader(
                    comic_url=c_url,
                    output_dir=str(out_root),
                    merge_slices=merge_slices,
                    make_pdf=make_pdf,
                    upload_to_web=upload_to_web,
                    api_base_url=DEFAULT_API_BASE_URL
                )

                info = downloader.get_comic_info()
                chapters = info.get("chapters", [])
                if not chapters:
                    self.after(0, lambda: self.log("   ⚠️ Truyện chưa có chapter hợp lệ ➜ Bỏ qua."))
                    continue

                slug = info["slug"]
                covers_dir = out_root / "covers"
                covers_dir.mkdir(parents=True, exist_ok=True)
                chapters_root_dir = out_root / "chapters" / slug
                chapters_root_dir.mkdir(parents=True, exist_ok=True)

                # Cover: covers/{slug}.webp
                cover_cdn_url = None
                if info.get("cover_url"):
                    raw_cover_path = covers_dir / f"{slug}_raw.jpg"
                    cover_path = covers_dir / f"{slug}.webp"
                    if not cover_path.exists():
                        downloader._download_single_image(info["cover_url"], raw_cover_path)
                        if raw_cover_path.exists():
                            try:
                                with Image.open(raw_cover_path) as im:
                                    if im.mode != 'RGB':
                                        im = im.convert('RGB')
                                    im.save(cover_path, 'WEBP', quality=90, method=6)
                                raw_cover_path.unlink(missing_ok=True)
                            except Exception:
                                cover_path = raw_cover_path

                    if upload_to_web and cover_path.exists():
                        try:
                            cover_cdn_url = upload_file_to_cloud(cover_path, f"covers/{slug}.webp", "image/webp")
                            self.after(0, lambda u=cover_cdn_url: self.log(f"   📸 Đã đưa Ảnh bìa lên Cloud: {u}"))
                        except Exception as err:
                            self.after(0, lambda e=err: self.log(f"   ⚠️ Lỗi upload ảnh bìa: {e}"))

                self.after(0, lambda cnt=len(chapters): self.log(f"   📚 Có {cnt} chương. Bắt đầu tải..."))

                comic_img_count = 0
                for c_idx, chap in enumerate(chapters, 1):
                    if self.cancel_requested:
                        break

                    num = chap["number"]
                    num_str = f"{int(num)}" if isinstance(num, (int, float)) and float(num).is_integer() else f"{num}"
                    raw_t = (chap.get("title") or "").strip()
                    is_oneshot = bool(re.search(r'oneshot|one-shot|1shot', raw_t, re.I) or re.search(r'oneshot|one-shot', str(info.get("title") or ''), re.I))
                    if is_oneshot:
                        clean_t = re.sub(r'^(?:chương|chap|chapter)\s*[\d\.]*\s*[-:]*\s*', '', raw_t, flags=re.I).strip()
                        chap_title = clean_t or "Oneshot"
                        api_chap_title = "Oneshot"
                    else:
                        clean_t = re.sub(r'^(?:chương|chap|chapter|tập|ep|episode)\s*[\d\.]*\s*[-:–—.]*\s*', '', raw_t, flags=re.I).strip()
                        clean_t = re.sub(rf'^0*{re.escape(num_str)}\s*[-:–—.]+\s*', '', clean_t, flags=re.I).strip()
                        if clean_t == num_str or clean_t == f"0{num_str}":
                            clean_t = ""
                        clean_t = clean_t.lstrip('-:–—. ').rstrip('-:–—. ')

                        chap_title = f"Chương {num_str}"
                        if clean_t:
                            chap_title += f" - {clean_t}"
                        api_chap_title = clean_t if clean_t else f"Chapter {num_str}"

                    chap_dir = chapters_root_dir / f"chap{num_str}"

                    # Skip if existing in sync state or on disk
                    if skip_sync_state and self.sync_state.is_chapter_synced(slug, num_str):
                        self.after(0, lambda t=chap_title: self.log(f"   ⏭️ [crawler_sync_state.json] {t} đã ghi nhận hoàn tất ➜ Bỏ qua."))
                        continue

                    if skip_existing and chap_dir.exists():
                        existing_webp = list(chap_dir.glob("page_*.webp")) or list(chap_dir.glob("*.webp"))
                        if len(existing_webp) >= 1:
                            self.sync_state.mark_chapter_synced(slug, num_str)
                            self.after(0, lambda t=chap_title, c=len(existing_webp): self.log(f"   ⏭️ {t} đã có trên máy ({c} ảnh WebP) ➜ Bỏ qua."))
                            continue

                    chap_dir.mkdir(parents=True, exist_ok=True)
                    self.after(0, lambda t=chap_title, ci=c_idx, ct=len(chapters), cn=total_processed_comics: (
                        self.lbl_status.configure(text=f"[#{cn}] [{ci}/{ct}] Đang tải {t}..."),
                        self.log(f"   ▶ [{ci}/{ct}] Đang tải {t}...")
                    ))

                    images = downloader.get_chapter_images(chap)
                    if not images:
                        self.after(0, lambda t=chap_title: self.log(f"     ⚠️ Không tìm thấy ảnh cho {t}"))
                        continue

                    num_raw = len(images)
                    should_merge = merge_slices or (num_raw > AUTO_STITCH_THRESHOLD)

                    if should_merge:
                        temp_dir = chap_dir / "_temp_slices"
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        download_dir = temp_dir
                    else:
                        download_dir = chap_dir

                    downloaded = []
                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        futures = {}
                        for i, img_url in enumerate(images):
                            if self.cancel_requested:
                                break
                            ext = img_url.split(".")[-1].split("?")[0].lower()
                            if ext not in ("jpg", "jpeg", "png", "webp"):
                                ext = "jpg"
                            save_p = download_dir / f"page_raw_{i+1:04d}.{ext}" if should_merge else download_dir / f"page_{i+1:03d}.{ext}"
                            downloaded.append(save_p)
                            f = executor.submit(downloader._download_single_image, img_url, save_p, chap.get("url"))
                            futures[f] = save_p

                        done_count = 0
                        for f in as_completed(futures):
                            if self.cancel_requested:
                                break
                            f.result()
                            done_count += 1
                            prog = (c_idx - 1 + (done_count / len(images))) / len(chapters)
                            self.after(0, lambda p=prog, dc=done_count, tc=len(images), ct=chap_title: (
                                self.progress_bar.set(p),
                                self.lbl_status.configure(text=f"{ct}: {dc}/{tc} ảnh ({int(p*100)}%)")
                            ))

                    valid_paths = [p for p in downloaded if p.exists()]
                    final_paths = []
                    if should_merge:
                        final_paths = downloader._merge_images_vertical(valid_paths, chap_dir, STITCH_GROUP_SIZE)
                        for p in valid_paths:
                            try: p.unlink(missing_ok=True)
                            except Exception: pass
                        try: temp_dir.rmdir()
                        except Exception: pass
                        self.after(0, lambda cnt=len(final_paths): self.log(f"     🧩 Đã ghép {cnt} ảnh WebP hoàn chỉnh (5-in-1)"))
                    else:
                        for idx_p, p in enumerate(valid_paths, 1):
                            webp_path = chap_dir / f"page_{idx_p:03d}.webp"
                            try:
                                with Image.open(p) as raw_im:
                                    raw_im.load()
                                    if raw_im.mode != 'RGB':
                                        im = raw_im.convert('RGB')
                                    else:
                                        im = raw_im
                                    im.save(webp_path, 'WEBP', quality=90, method=6)
                                final_paths.append(webp_path)
                                if p != webp_path and p.exists():
                                    p.unlink(missing_ok=True)
                            except Exception:
                                final_paths.append(p)
                        self.after(0, lambda cnt=len(final_paths): self.log(f"     ✓ Đã tải {cnt} trang ảnh WebP."))

                    comic_img_count += len(final_paths)
                    total_downloaded_images += len(final_paths)
                    total_chapters_all += 1

                    if make_pdf:
                        pdf_f = chap_dir / f"chap{num_str}.pdf"
                        downloader._export_pdf(final_paths, pdf_f)

                    # Upload to Cloud Storage & Web API
                    if upload_to_web and final_paths:
                        uploaded_cdn_urls = [None] * len(final_paths)
                        with ThreadPoolExecutor(max_workers=workers) as executor:
                            fut_map = {}
                            for p_idx, p in enumerate(final_paths):
                                obj_name = f"chapters/{slug}/chap{num_str}/page_{p_idx+1:03d}.webp"
                                fut = executor.submit(upload_file_to_cloud, p, obj_name, "image/webp")
                                fut_map[fut] = p_idx
                            for fut in as_completed(fut_map):
                                p_idx = fut_map[fut]
                                try:
                                    uploaded_cdn_urls[p_idx] = fut.result()
                                except Exception:
                                    pass

                        valid_cdn_urls = [u for u in uploaded_cdn_urls if u]
                        if valid_cdn_urls:
                            synced = sync_chapter_to_web_api(
                                api_base_url=DEFAULT_API_BASE_URL,
                                comic_title=info["title"],
                                comic_slug=slug,
                                cover_cdn_url=cover_cdn_url or valid_cdn_urls[0],
                                chapter_num=num,
                                chapter_title=api_chap_title,
                                image_urls=valid_cdn_urls,
                                author=info.get("author"),
                                translator_group=info.get("translator_group"),
                                other_names=info.get("other_names"),
                                views=chap.get("views", 0),
                                published_at=chap.get("updated_at"),
                                created_at=chap.get("updated_at"),
                                comic_views=info.get("views", 0),
                                categories=info.get("genres", [])
                            )
                            if synced:
                                self.after(0, lambda t=chap_title: self.log(f"     🌐 Đã đồng bộ {t} lên Website!"))
                            else:
                                self.after(0, lambda t=chap_title: self.log(f"     ⚠️ Đã upload Cloud {t} - Chưa đồng bộ Web API"))

                    # Ghi nhận chapter vào sync state
                    self.sync_state.mark_chapter_synced(slug, num_str)

                # Ghi nhận hoàn tất bộ truyện vào sync state
                if not self.cancel_requested:
                    self.sync_state.mark_comic_completed(
                        slug=slug,
                        title=info["title"],
                        chapters_count=len(chapters),
                        pages_count=comic_img_count,
                        source="HentaiVNReal"
                    )
                    self.after(0, self._update_sync_state_ui)
                    st_name = Path(self.sync_state.file_path).name if self.sync_state.file_path else "crawler_sync_state.json"
                    self.after(0, lambda t=info["title"], fn=st_name: self.log(f"   💾 [Sync State] Đã lưu '{t}' vào '{fn}' để ghi nhớ cho lần sau."))

                self.after(0, lambda t=c_title, img_c=comic_img_count, n=total_processed_comics: self.log(f"   🎉 [#{n}] Hoàn tất bộ '{t}' ({img_c} ảnh)!"))

            except Exception as ex:
                self.after(0, lambda t=c_title, err=str(ex): self.log(f"   ❌ Lỗi khi xử lý bộ truyện '{t}': {err}"))
                continue

        elapsed = time.time() - start_time
        self.after(0, lambda: self.progress_bar.set(1.0))
        self.after(0, lambda: self.log("\n" + "=" * 70))
        self.after(0, lambda: self.log(f"🎉 HOÀN TẤT TIẾN TRÌNH TẢI HÀNG LOẠT!"))
        self.after(0, lambda: self.log(f"• Tổng số bộ truyện đã xử lý: {total_processed_comics} bộ"))
        self.after(0, lambda: self.log(f"• Tổng số chapter đã tải: {total_chapters_all} chapter"))
        self.after(0, lambda: self.log(f"• Tổng số trang ảnh đã tải: {total_downloaded_images} ảnh"))
        self.after(0, lambda: self.log(f"• Thời gian chạy: {elapsed:.1f}s ({elapsed/60:.1f} phút)"))
        self.after(0, lambda: self.log("=" * 70 + "\n"))
        self.after(0, lambda: self.lbl_status.configure(text=f"Hoàn tất tải hàng loạt: {total_processed_comics} bộ ({total_downloaded_images} ảnh)"))

        self.after(0, self._on_download_finished)

    # Alias
    _batch_download_mangadex_worker = _batch_download_hentaivn_worker

    def _on_download_finished(self):
        self.is_downloading = False
        self.btn_start.configure(state="normal")
        self.btn_fetch.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        if hasattr(self, 'btn_header_batch'):
            self.btn_header_batch.configure(state="normal")
        if hasattr(self, 'btn_hentai_download_all'):
            self.btn_hentai_download_all.configure(state="normal")
        if hasattr(self, 'btn_dex_download_all'):
            self.btn_dex_download_all.configure(state="normal")


def main():
    app = MangaDownloaderGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
