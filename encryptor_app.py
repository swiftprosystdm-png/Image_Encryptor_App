"""
encryptor_app.py - High-Speed Standalone Image Encryption Tool (Project 1).

Encrypts image files (.jpg, .jpeg, .png, .bmp, .tiff, .tif, .webp, .gif, .pnm)
into custom .sps files using multi-threaded AES-256-GCM + PBKDF2 cryptography.
Features Pause/Resume, Stop/Cancel controls, Queue status tracking, and 100% responsive UI.
"""

import sys
import os
import time
import queue
import threading
import concurrent.futures
from typing import List, Optional, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QColor, QCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QLineEdit, QProgressBar,
    QTextEdit, QGroupBox, QCheckBox, QMessageBox, QFrame,
    QSplitter, QHeaderView, QTableWidget, QTableWidgetItem, QSizePolicy,
    QComboBox, QSpinBox, QScrollArea, QStackedWidget
)

from collections import deque
from sps_crypto import encrypt_image_data, derive_session_key, DEFAULT_PASSPHRASE
from theme_config import setup_high_dpi, get_app_icon, apply_theme, get_brand_logo_pixmap, get_ui_icon, DARK, LIGHT
from image_compress import compress_to_jp2_lossless, compress_to_jp2, compress_bytes
from updater import check_for_updates_async, download_and_apply_update

SUPPORTED_INPUT_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif", ".pnm", ".jp2", ".j2k"
}
APP_TITLE = "Swift-ProSys Image Encryption Tool"
APP_VERSION = " Alpha"


class BatchEncryptWorker(QThread):
    """
    High-speed multi-threaded worker thread for batch image encryption.
    Uses pre-derived session key for extreme throughput (thousands of images in seconds),
    thread-safe non-blocking event queues, and instant pause/resume/cancel.
    """
    status_changed = pyqtSignal(str)       # "RUNNING", "PAUSED", "STOPPING", "CANCELLED", "COMPLETED"
    log_emitted = pyqtSignal(str)          # Important lifecycle log messages
    finished_all = pyqtSignal(list, bool)  # (output_files, was_cancelled)

    def __init__(
        self,
        file_items: List[Tuple],
        output_dir: Optional[str],
        passphrase: str,
        max_workers: int = 4,
        preserve_structure: bool = True,
        compression_mode: str = "none",
        jp2_target_kb: int = 1024,
    ):
        super().__init__()
        self.file_items = file_items
        self.output_dir = output_dir
        self.passphrase = passphrase
        self.max_workers = max(1, max_workers)
        self.preserve_structure = preserve_structure
        self.compression_mode = compression_mode  # "none" | "jp2" (JPEG 2000, target-size) | "lossless" (PNG optimize / lossless WebP) | "visual" (visually lossless, fixed Q88)
        self.jp2_target_kb = jp2_target_kb  # Target output size (KB) used only when compression_mode == "jp2"
        self.total_original_bytes = 0
        self.total_compressed_bytes = 0
        self._bytes_lock = threading.Lock()

        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_event = threading.Event()
        self._is_paused = False
        self._is_running = False

        # Task queue and thread-safe batch result queue
        self._task_queue = queue.Queue()
        for item in self.file_items:
            self._task_queue.put(item)

        self.pending_results = deque()
        self.results_lock = threading.Lock()
        self.completed_count = 0
        self.total_count = len(file_items)
        self.start_time = 0.0
        self._worker_threads = []
        self._executor = None

    def pause(self):
        """Pause worker threads safely and immediately."""
        if not self._is_paused and not self._stop_event.is_set():
            self._is_paused = True
            self._pause_event.clear()
            self.status_changed.emit("PAUSED")
            self.log_emitted.emit("⏸️ [STATUS] Batch encryption paused by user.")

    def resume(self):
        """Resume paused worker threads immediately."""
        if self._is_paused and not self._stop_event.is_set():
            self._is_paused = False
            self._pause_event.set()
            self.status_changed.emit("RUNNING")
            self.log_emitted.emit("▶️ [STATUS] Batch encryption resumed.")

    def is_paused(self) -> bool:
        return self._is_paused

    def cancel(self):
        """Cancel the ongoing batch operation immediately."""
        self._stop_event.set()
        self._pause_event.set()

        # Clear remaining tasks
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
                self._task_queue.task_done()
            except queue.Empty:
                break

        # Shutdown executor immediately
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)

    def is_cancelled(self) -> bool:
        return self._stop_event.is_set()

    def get_pending_results(self) -> List[Tuple[int, bool, str]]:
        """Pop all pending row status updates for smooth GUI consumption."""
        with self.results_lock:
            if not self.pending_results:
                return []
            items = list(self.pending_results)
            self.pending_results.clear()
            return items

    def run(self):
        total = self.total_count
        if total == 0:
            self.finished_all.emit([], False)
            return

        self._is_running = True
        self.status_changed.emit("RUNNING")
        self.log_emitted.emit("🔒 [Algorithm Concept]: O(1) Session-Level Key Derivation (100k PBKDF2 once) + AES-256-GCM (Hardware AES-NI)")
        self.log_emitted.emit(f"⚡ [Multithreading Concept]: Parallel Worker Pool Active ({self.max_workers} Threads, GIL-Released OpenSSL C-Engine)")
        self.log_emitted.emit(f"🚀 [I/O Optimization]: Single-Syscall Binary Writes & Directory Cache Active. Processing {total} image(s)...")

        # Derive key once for the entire batch session
        session_key, session_salt = derive_session_key(self.passphrase)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        session_cipher = AESGCM(session_key)

        output_files: List[str] = []
        output_lock = threading.Lock()
        self.start_time = time.time()

        def process_item(item):
            """Process a single file encryption task."""
            if self._stop_event.is_set():
                return None, None, None

            if len(item) >= 3:
                row_idx, file_path, rel_subpath = item[0], item[1], item[2]
            else:
                row_idx, file_path = item[0], item[1]
                rel_subpath = None

            base_name = os.path.basename(file_path)
            name_without_ext, _ = os.path.splitext(base_name)

            if not os.path.exists(file_path):
                return row_idx, False, "Not Found"

            try:
                if self.output_dir and self.output_dir.strip():
                    out_base = os.path.abspath(self.output_dir.strip())
                    if self.preserve_structure and rel_subpath:
                        clean_rel = os.path.normpath(rel_subpath)
                        rel_dir = os.path.dirname(clean_rel)
                        dest_dir = os.path.join(out_base, rel_dir) if rel_dir else out_base
                        dest_path = os.path.join(dest_dir, f"{name_without_ext}.sps")
                    else:
                        dest_path = os.path.join(out_base, f"{name_without_ext}.sps")
                else:
                    dest_path = os.path.join(os.path.dirname(file_path), f"{name_without_ext}.sps")

                # Directory creation is handled inside encrypt_image_data()
                # with a thread-safe cache, so no need to call makedirs here too.

                with open(file_path, "rb", buffering=1024 * 1024) as f:
                    raw_bytes = f.read()

                original_ext = os.path.splitext(file_path)[1].lower()
                if self.compression_mode == "jp2":
                    # JPEG 2000 targeting a specific output size (self.jp2_target_kb).
                    # Dimensions/pixels are never resized - only the wavelet
                    # compression ratio is adjusted to hit the target exactly
                    # (min_bpp=0 disables the quality-floor clamp, so the
                    # requested target is always honored as-is).
                    final_bytes, used_ext, orig_size, comp_size, was_clamped, safe_min_kb = compress_to_jp2(
                        raw_bytes, original_ext, target_kb=self.jp2_target_kb, min_bpp=0.0
                    )
                elif self.compression_mode == "lossless":
                    # PNG optimize / lossless WebP - zero quality loss, pixels
                    # untouched, identical even zoomed in. Only the file size
                    # (encoding overhead) shrinks; falls back to original
                    # bytes untouched if the format isn't compressible or the
                    # "compressed" result isn't actually smaller.
                    final_bytes, used_ext, orig_size, comp_size = compress_bytes(
                        raw_bytes, original_ext, mode="lossless"
                    )
                elif self.compression_mode == "visual":
                    # "Visually lossless" high-quality WebP/JPEG re-encode.
                    # Quality fixed at 88 (85-90 range) - not pixel-exact
                    # (unlike jp2/lossless), but no visible difference at
                    # normal viewing. Gives real savings on camera photos,
                    # where the two truly lossless modes above barely help.
                    final_bytes, used_ext, orig_size, comp_size = compress_bytes(
                        raw_bytes, original_ext, mode="visual", quality=88
                    )
                else:
                    final_bytes, used_ext, orig_size, comp_size = raw_bytes, original_ext, len(raw_bytes), len(raw_bytes)
                with self._bytes_lock:
                    self.total_original_bytes += orig_size
                    self.total_compressed_bytes += comp_size

                metadata = {
                    "original_filename": base_name,
                    "extension": used_ext,
                    "file_size": len(final_bytes),
                    "compression_mode": self.compression_mode,
                }

                sps_result = encrypt_image_data(
                    final_bytes,
                    dest_path,
                    passphrase=self.passphrase,
                    metadata=metadata,
                    derived_key=session_key,
                    salt=session_salt,
                    cipher=session_cipher,
                )
                return row_idx, True, sps_result
            except Exception as e:
                return row_idx, False, str(e)

        # Use ThreadPoolExecutor for better thread management
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        futures = []
        
        # Submit all tasks
        while not self._task_queue.empty() and not self._stop_event.is_set():
            try:
                item = self._task_queue.get_nowait()
                future = self._executor.submit(process_item, item)
                futures.append(future)
            except queue.Empty:
                break

        # Process results as they complete
        for future in concurrent.futures.as_completed(futures):
            if self._stop_event.is_set():
                break
                
            result = future.result()
            if result and result[0] is not None:
                row_idx, success, msg = result
                with self.results_lock:
                    self.pending_results.append((row_idx, success, msg))
                    self.completed_count += 1
                
                if success and msg and isinstance(msg, str) and msg.endswith('.sps'):
                    with output_lock:
                        output_files.append(msg)

        # Clean shutdown
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

        was_cancelled = self._stop_event.is_set()
        elapsed = max(0.001, time.time() - self.start_time)
        
        if was_cancelled:
            self.status_changed.emit("CANCELLED")
            self.log_emitted.emit(f"⏹️ [STATUS] Encryption cancelled. {len(output_files)} of {total} files completed in {elapsed:.2f}s.")
        else:
            self.status_changed.emit("COMPLETED")
            avg_speed = len(output_files) / elapsed
            self.log_emitted.emit(
                f"🎉 Finished all {len(output_files)} files in {elapsed:.2f}s ({avg_speed:.1f} files/sec)!"
            )
            if self.compression_mode != "none" and self.total_original_bytes > 0:
                saved_pct = (1 - (self.total_compressed_bytes / self.total_original_bytes)) * 100
                orig_mb = self.total_original_bytes / (1024 * 1024)
                comp_mb = self.total_compressed_bytes / (1024 * 1024)
                self.log_emitted.emit(
                    f"📉 Compression ({self.compression_mode}): {orig_mb:.2f} MB → {comp_mb:.2f} MB "
                    f"({saved_pct:.1f}% smaller, before encryption)"
                )

        self._is_running = False
        self.finished_all.emit(output_files, was_cancelled)


class FolderScanWorker(QThread):
    """
    Scans a folder recursively for supported images on a background thread,
    so selecting a large folder never freezes the UI. Produces the exact
    same (abs_path, rel_path) list that the old synchronous scan produced.
    """
    scan_finished = pyqtSignal(list, str)  # (items, abs_folder)

    def __init__(self, folder: str, parent=None):
        super().__init__(parent)
        self.folder = folder

    def run(self):
        abs_folder = os.path.abspath(self.folder)
        parent_dir = os.path.dirname(abs_folder)
        if parent_dir == abs_folder:
            parent_dir = abs_folder

        items = []
        for root, _, filenames in os.walk(abs_folder):
            for f in sorted(filenames):
                if os.path.splitext(f)[1].lower() in SUPPORTED_INPUT_EXTENSIONS:
                    abs_p = os.path.abspath(os.path.join(root, f))
                    rel_p = os.path.relpath(abs_p, parent_dir)
                    items.append((abs_p, rel_p))

        self.scan_finished.emit(items, abs_folder)


class SPSEncryptorWindow(QMainWindow):
    """Standalone High-Speed Image Encryption Tool Main Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.setWindowIcon(get_app_icon())
        # Safe placeholder until the window actually has a screen assigned
        # (see showEvent) - sizing/centering too early, before the OS has
        # placed the window on a real monitor, can pick the wrong
        # screen/DPI and leave the frame and painted content mismatched.
        self.setMinimumSize(680, 460)
        self.resize(1080, 720)
        self._screen_fit_applied = False

        self.current_theme = LIGHT
        self.max_worker_threads = os.cpu_count() or 4

        self.selected_files: List[str] = []
        self.file_rel_map: dict = {}
        self.worker: Optional[BatchEncryptWorker] = None
        self._folder_scan_worker: Optional[FolderScanWorker] = None
        self._updates_pending = False
        self._last_update_time = 0

        # Smooth UI dispatcher timer
        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(30)  # 30ms for smoother updates
        self.ui_timer.timeout.connect(self._on_ui_tick)

        self._init_ui()

        # Check for updates silently on startup
        check_for_updates_async(self, silent=True, callback=self._on_update_check_finished)

    def _fit_window_to_screen(self, default_w: int, default_h: int, min_w: int, min_h: int):
        """Size and center the window to fit whatever screen it opens on.

        Keeps the app at its normal design size (default_w x default_h) on
        regular/large monitors, but scales down on small laptop/netbook
        screens so the window - and its minimum size - never exceeds the
        available desktop area (accounting for the taskbar). Also checks
        the window's actual content size hint so sections never get
        squeezed/overlapping just because a fixed guess was too small for
        this machine's fonts/DPI.
        """
        screen = self.screen() or QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            self.setMinimumSize(min_w, min_h)
            self.resize(default_w, default_h)
            return

        avail = screen.availableGeometry()
        margin = 40  # breathing room so the window isn't flush with screen edges

        eff_min_w = max(360, min(min_w, avail.width() - margin))
        eff_min_h = max(320, min(min_h, avail.height() - margin))
        self.setMinimumSize(eff_min_w, eff_min_h)

        # Never size the window smaller than what its own content actually
        # wants - otherwise the group boxes get compressed and their
        # spacing collapses, making everything look merged together.
        # IMPORTANT: self.sizeHint() is unreliable here because the body
        # sits inside a QScrollArea, and QScrollArea.sizeHint() does NOT
        # reflect its inner widget's real size - it returns its own small
        # generic guess. So read the true needed size straight from the
        # scrolled content widget (and the header bar) instead.
        body = getattr(self, "_body_container", None)
        if body is not None and body.layout() is not None:
            layout = body.layout()
            min_sz = layout.minimumSize()
            hint_sz = layout.sizeHint()
            content_w = max(min_sz.width(), hint_sz.width())
            content_h = max(min_sz.height(), hint_sz.height())
        else:
            content_w = default_w
            content_h = default_h

        header_h = self.header_bar.sizeHint().height() if hasattr(self, "header_bar") else 0
        frame_allowance = 60  # window title bar / borders added by the OS
        padding_buffer = 16   # a little breathing room so nothing sits flush

        ideal_w = max(default_w, content_w + padding_buffer)
        ideal_h = max(default_h, content_h + header_h + frame_allowance + padding_buffer)

        target_w = max(eff_min_w, min(ideal_w, int(avail.width() * 0.95)))
        target_h = max(eff_min_h, min(ideal_h, int(avail.height() * 0.92)))
        self.resize(target_w, target_h)

        frame_geo = self.frameGeometry()
        frame_geo.moveCenter(avail.center())
        self.move(frame_geo.topLeft())

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Branding Header Bar
        self.header_bar = QFrame()
        self.header_bar.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(10)

        # Left brand icon / pixmap
        corner_logo_pm = get_brand_logo_pixmap(height=28)
        if not corner_logo_pm.isNull():
            self.lbl_corner_logo = QLabel()
            self.lbl_corner_logo.setObjectName("HeaderCornerLogo")
            self.lbl_corner_logo.setPixmap(corner_logo_pm)
            self.lbl_corner_logo.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.lbl_corner_logo.setStyleSheet("background: transparent; padding-right: 4px;")
            self.lbl_corner_logo.setToolTip("Swift-ProSys")
            header_layout.addWidget(self.lbl_corner_logo)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        lbl_brand_title = QLabel("Swift-ProSys Image Encryption Studio")
        lbl_brand_title.setObjectName("BrandTitle")
        title_col.addWidget(lbl_brand_title)
        lbl_brand_sub = QLabel("AES-256-GCM Secure .sps Packaging")
        lbl_brand_sub.setObjectName("BrandSubtitle")
        title_col.addWidget(lbl_brand_sub)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        lbl_sec = QLabel("🔒 AES-256-GCM")
        lbl_sec.setObjectName("SecurityBadge")
        header_layout.addWidget(lbl_sec)

        self.btn_update = QPushButton("Check for Updates")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setFixedHeight(30)
        self._set_update_button_style(is_available=False)
        self.btn_update.clicked.connect(self._on_update_button_clicked)
        header_layout.addWidget(self.btn_update)

        self.btn_theme_toggle = QPushButton("🌙 Dark Mode")
        self.btn_theme_toggle.setProperty("class", "btn-ghost")
        self.btn_theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme_toggle.setToolTip("Switch between Dark and Light theme")
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.btn_theme_toggle)

        main_layout.addWidget(self.header_bar)

        # Main Body Layout
        body_container = QWidget()
        body_container.setObjectName("BodyContainer")
        body_container.setMinimumSize(620, 460)
        self._body_container = body_container
        body_layout = QVBoxLayout(body_container)
        body_layout.setContentsMargins(14, 12, 14, 12)
        body_layout.setSpacing(14)

        # 1. Configuration Card
        top_group = QGroupBox("⚙️ Configuration && Settings")
        top_layout = QVBoxLayout(top_group)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setSpacing(8)

        # Row 1: File Actions + Compression Settings + Engine Pill
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.btn_add_files = QPushButton("➕ Add Files")
        self.btn_add_files.setProperty("class", "btn-primary")
        self.btn_add_files.setFixedHeight(36)
        self.btn_add_files.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_files.clicked.connect(self.select_files)
        row1.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton("📁 Add Folder...")
        self.btn_add_folder.setFixedHeight(36)
        self.btn_add_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_folder.setToolTip("Select an image folder to recursively import all images and subfolders.")
        self.btn_add_folder.clicked.connect(self.select_folder)
        row1.addWidget(self.btn_add_folder)

        self.btn_clear_list = QPushButton("🗑️ Clear")
        self.btn_clear_list.setProperty("class", "btn-danger")
        self.btn_clear_list.setFixedHeight(36)
        self.btn_clear_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_list.clicked.connect(self.clear_files)
        row1.addWidget(self.btn_clear_list)

        # Subtle separator
        sep = QFrame()
        sep.setObjectName("ToolSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        row1.addWidget(sep)

        lbl_compress = QLabel("🗜️ Compression:")
        lbl_compress.setObjectName("BrandSubtitle")
        row1.addWidget(lbl_compress)

        self.cmb_compression = QComboBox()
        self.cmb_compression.addItem("🚫 None (Original Size)", "none")
        self.cmb_compression.addItem("🗜️ JPEG 2000 (Target Size)", "jp2")
        self.cmb_compression.addItem("🗜️ Lossless (PNG/WebP)", "lossless")
        self.cmb_compression.addItem("👁️ Visually Lossless (Q85-90)", "visual")
        self.cmb_compression.setCurrentIndex(0)
        self.cmb_compression.setMinimumWidth(150)
        self.cmb_compression.setFixedHeight(36)
        self.cmb_compression.setToolTip(
            "Dimensions/pixels are never resized.\n"
            "JPEG 2000 (Target Size): converts to .jp2, adjusting the wavelet\n"
            "compression ratio to hit the Target (KB) size you set. If the\n"
            "target is too small to stay above a safe quality floor, it is\n"
            "automatically clamped up (never silently over-compressed).\n\n"
            "Lossless (PNG/WebP): re-encodes PNG with max optimization, or other\n"
            "formats as lossless WebP - zero quality loss, identical even zoomed\n"
            "in. Only the encoding overhead shrinks; pixels are bit-exact.\n\n"
            "Visually Lossless (Q85-90): high-quality JPEG/WebP re-encode, fixed\n"
            "quality 88. Not pixel-exact - a lossy re-encode - but no visible\n"
            "difference at normal viewing. Gives real size savings on camera\n"
            "photos, where the lossless modes above barely help."
        )
        self.cmb_compression.currentIndexChanged.connect(self._on_compression_mode_changed)
        row1.addWidget(self.cmb_compression)

        self.lbl_jp2_target = QLabel("Target:")
        self.spn_jp2_target = QSpinBox()
        self.spn_jp2_target.setRange(16, 102400)
        self.spn_jp2_target.setValue(1024)
        self.spn_jp2_target.setSuffix(" KB")
        self.spn_jp2_target.setFixedHeight(36)
        self.spn_jp2_target.setMinimumWidth(110)
        self.spn_jp2_target.setToolTip(
            "Target output size per image for JPEG 2000. Dimensions are never\n"
            "resized - only compression strength is adjusted. Too small a\n"
            "target is clamped up automatically to protect quality."
        )
        row1.addWidget(self.lbl_jp2_target)
        row1.addWidget(self.spn_jp2_target)
        self.lbl_jp2_target.setVisible(False)
        self.spn_jp2_target.setVisible(False)

        row1.addStretch()

        # Engine pill
        lbl_threads_info = QLabel(f"⚡ {self.max_worker_threads}-Core Engine")
        lbl_threads_info.setObjectName("PillBadge")
        lbl_threads_info.setFixedHeight(36)
        lbl_threads_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_threads_info.setToolTip("All available CPU cores are used automatically for maximum encryption speed.")
        row1.addWidget(lbl_threads_info)

        top_layout.addLayout(row1)

        # Row 2: Destination + Security note
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        lbl_out = QLabel("📂 Output:")
        lbl_out.setObjectName("BrandSubtitle")
        row2.addWidget(lbl_out)

        self.txt_output_dir = QLineEdit()
        self.txt_output_dir.setPlaceholderText("Default: Save alongside original images (Leave blank)")
        self.txt_output_dir.setMinimumWidth(180)
        self.txt_output_dir.setFixedHeight(36)
        row2.addWidget(self.txt_output_dir, stretch=1)

        self.btn_browse_output = QPushButton("📂 Browse...")
        self.btn_browse_output.setFixedHeight(36)
        self.btn_browse_output.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse_output.clicked.connect(self.select_output_dir)
        row2.addWidget(self.btn_browse_output)

        sep2 = QFrame()
        sep2.setObjectName("ToolSeparator")
        sep2.setFrameShape(QFrame.Shape.VLine)
        row2.addWidget(sep2)

        self.chk_preserve_structure = QCheckBox("🗂️ Preserve Subfolders")
        self.chk_preserve_structure.setChecked(True)
        self.chk_preserve_structure.setFixedHeight(36)
        self.chk_preserve_structure.setToolTip("Recreates the root folder and subfolder hierarchy inside the output folder.")
        row2.addWidget(self.chk_preserve_structure)

        row2.addStretch()

        lbl_security_note = QLabel("🔐 AES-256-GCM Accelerated")
        lbl_security_note.setObjectName("BrandSubtitle")
        lbl_security_note.setFixedHeight(36)
        row2.addWidget(lbl_security_note)

        top_layout.addLayout(row2)
        body_layout.addWidget(top_group)

        # File List Table Box (Expands to fill all remaining vertical space)
        file_box = QGroupBox("📋 Image Conversion Queue")
        file_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        file_box.setMinimumHeight(230)
        file_layout = QVBoxLayout(file_box)
        file_layout.setContentsMargins(10, 10, 10, 10)
        file_layout.setSpacing(6)

        # Queue Status Row
        queue_info_row = QHBoxLayout()
        self.lbl_queue_count = QLabel("📊 0 images in queue")
        self.lbl_queue_count.setObjectName("BrandSubtitle")
        queue_info_row.addWidget(self.lbl_queue_count)
        queue_info_row.addStretch()
        lbl_drag_hint = QLabel("💡 Tip: Drag & drop image files or folders anywhere into the window")
        lbl_drag_hint.setObjectName("BrandSubtitle")
        queue_info_row.addWidget(lbl_drag_hint)
        file_layout.addLayout(queue_info_row)

        # File List Stack (Empty Dropzone vs. Active Table)
        self.queue_stack = QStackedWidget()

        # 1. Empty Dropzone Page
        self.empty_dropzone = QFrame()
        self.empty_dropzone.setObjectName("EmptyDropzone")
        self.empty_dropzone.setMinimumHeight(160)
        drop_layout = QVBoxLayout(self.empty_dropzone)
        drop_layout.setContentsMargins(12, 8, 12, 8)
        drop_layout.setSpacing(5)
        drop_layout.addStretch()

        lbl_drop_icon = QLabel("📥")
        lbl_drop_icon.setObjectName("DropzoneIcon")
        lbl_drop_icon.setStyleSheet("font-size: 30px; background: transparent;")
        lbl_drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(lbl_drop_icon)

        lbl_drop_title = QLabel("Drop Images or Folders Here")
        lbl_drop_title.setObjectName("DropzoneTitle")
        lbl_drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(lbl_drop_title)

        lbl_drop_subtitle = QLabel("Supports JPG, PNG, WEBP, BMP, TIFF, GIF & PNM • Preserves Subfolder Structure")
        lbl_drop_subtitle.setObjectName("DropzoneSubtitle")
        lbl_drop_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(lbl_drop_subtitle)

        drop_btn_row = QHBoxLayout()
        drop_btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_btn_row.setSpacing(10)

        btn_drop_add_files = QPushButton("➕ Add Image Files")
        btn_drop_add_files.setProperty("class", "btn-primary")
        btn_drop_add_files.setFixedHeight(30)
        btn_drop_add_files.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_drop_add_files.clicked.connect(self.select_files)
        drop_btn_row.addWidget(btn_drop_add_files)

        btn_drop_add_folder = QPushButton("📁 Add Folder...")
        btn_drop_add_folder.setFixedHeight(30)
        btn_drop_add_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_drop_add_folder.clicked.connect(self.select_folder)
        drop_btn_row.addWidget(btn_drop_add_folder)

        drop_layout.addLayout(drop_btn_row)
        drop_layout.addStretch()

        # 2. Table Page
        self.file_table = QTableWidget(0, 5)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.file_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.file_table.verticalHeader().setDefaultSectionSize(28)
        self.file_table.horizontalHeader().setMinimumHeight(32)
        self.file_table.setShowGrid(True)
        self.file_table.setHorizontalHeaderLabels([
            "📄 Filename", "📁 Subfolder / Relative Path", "🖼️ Format", "⚡ Status", "📍 Source File Path"
        ])
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.queue_stack.addWidget(self.empty_dropzone)
        self.queue_stack.addWidget(self.file_table)
        self.queue_stack.setCurrentIndex(0)

        file_layout.addWidget(self.queue_stack)
        body_layout.addWidget(file_box, stretch=1)

        # 3. Execution Console & Controls Box
        action_box = QGroupBox("🚀 Execution && Controls")
        action_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        action_layout = QVBoxLayout(action_box)
        action_layout.setContentsMargins(10, 8, 10, 8)
        action_layout.setSpacing(4)

        # Consolidated Control & Status Bar
        control_bar = QHBoxLayout()
        control_bar.setSpacing(10)

        # Status & Metrics Cockpit Card
        metrics_card = QFrame()
        metrics_card.setObjectName("MetricsCard")
        metrics_layout = QHBoxLayout(metrics_card)
        metrics_layout.setContentsMargins(8, 3, 10, 3)
        metrics_layout.setSpacing(8)

        self.lbl_status_badge = QLabel("💤 IDLE")
        self.lbl_status_badge.setFixedHeight(24)
        self.lbl_status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        metrics_layout.addWidget(self.lbl_status_badge)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedWidth(95)
        self.progress_bar.setFixedHeight(18)
        metrics_layout.addWidget(self.progress_bar)

        self.lbl_metrics = QLabel("📊 0 / 0  •  ⚡ 0.0 f/s  •  ⏱️ 00:00")
        self.lbl_metrics.setObjectName("MetricsLabel")
        metrics_layout.addWidget(self.lbl_metrics)

        control_bar.addWidget(metrics_card)
        control_bar.addStretch()

        self.btn_pause_resume = QPushButton("⏸️ Pause")
        self.btn_pause_resume.setProperty("class", "btn-warning")
        self.btn_pause_resume.setFixedHeight(34)
        self.btn_pause_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause_resume.setEnabled(False)
        self.btn_pause_resume.clicked.connect(self.toggle_pause_resume)
        control_bar.addWidget(self.btn_pause_resume)

        self.btn_cancel = QPushButton("⏹️ Cancel")
        self.btn_cancel.setProperty("class", "btn-danger")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_encryption)
        control_bar.addWidget(self.btn_cancel)

        self.btn_encrypt = QPushButton("🔒 Start Encryption")
        self.btn_encrypt.setProperty("class", "btn-success")
        self.btn_encrypt.setFixedHeight(34)
        self.btn_encrypt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_encrypt.clicked.connect(self.start_encryption)
        control_bar.addWidget(self.btn_encrypt)

        action_layout.addLayout(control_bar)

        # Log Window (Compact drawer)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.document().setMaximumBlockCount(1000)
        self.txt_log.setObjectName("LogConsole")
        self.txt_log.setFixedHeight(68)
        self.txt_log.append("✨ [SYSTEM] Swift-ProSys Image Encryption Studio vAlpha Ready.")
        self.txt_log.append("💡 [READY] Drag & drop image files or folders anywhere into the window to begin.")

        # Terminal Header Bar
        log_header = QHBoxLayout()
        log_header.setContentsMargins(2, 2, 2, 0)
        lbl_log_title = QLabel("💻 Live Execution Terminal")
        lbl_log_title.setObjectName("BrandSubtitle")
        lbl_log_title.setStyleSheet("font-weight: 600;")
        log_header.addWidget(lbl_log_title)

        log_header.addStretch()

        action_layout.addLayout(log_header)
        action_layout.addWidget(self.txt_log)

        body_layout.addWidget(action_box, stretch=0)

        # Responsive Scroll Area: allows smooth scrolling in all directions on smaller screens / half-screen
        scroll_area = QScrollArea()
        scroll_area.setObjectName("MainScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidget(body_container)

        main_layout.addWidget(scroll_area)

        self._update_status_badge("IDLE")
        self.setAcceptDrops(True)
        self._adjust_table_columns()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._screen_fit_applied:
            self._screen_fit_applied = True
            self._fit_window_to_screen(default_w=1080, default_h=720, min_w=680, min_h=460)
            # Force a full repaint after the late move/resize so no stale
            # pixels (from whatever was behind the window before it was
            # correctly placed) are left showing in the newly exposed area.
            self.update()
        self._adjust_table_columns()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_table_columns()

    def _adjust_table_columns(self):
        """Dynamically and responsively size columns to fit any screen resolution."""
        if not hasattr(self, "file_table") or self.file_table is None:
            return
        total_w = self.file_table.viewport().width()
        if total_w > 400:
            format_w = 95
            status_w = 125
            file_w = max(200, int(total_w * 0.30))
            folder_w = max(180, int(total_w * 0.25))

            self.file_table.setColumnWidth(0, file_w)
            self.file_table.setColumnWidth(1, folder_w)
            self.file_table.setColumnWidth(2, format_w)
            self.file_table.setColumnWidth(3, status_w)
            self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        items_to_add = []
        for url in urls:
            local_path = url.toLocalFile()
            if os.path.isdir(local_path):
                folder = os.path.abspath(local_path)
                parent_dir = os.path.dirname(folder)
                if parent_dir == folder:
                    parent_dir = folder
                for root, _, filenames in os.walk(folder):
                    for f in sorted(filenames):
                        if os.path.splitext(f)[1].lower() in SUPPORTED_INPUT_EXTENSIONS:
                            abs_p = os.path.abspath(os.path.join(root, f))
                            rel_p = os.path.relpath(abs_p, parent_dir)
                            items_to_add.append((abs_p, rel_p))
            elif os.path.isfile(local_path):
                ext = os.path.splitext(local_path)[1].lower()
                if ext in SUPPORTED_INPUT_EXTENSIONS:
                    abs_p = os.path.abspath(local_path)
                    items_to_add.append((abs_p, os.path.basename(abs_p)))

        if items_to_add:
            self._add_files_with_rel(items_to_add)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Image Files to Encrypt",
            "", "Supported Image Files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp *.gif *.pnm *.jp2 *.j2k)"
        )
        if files:
            items = [(os.path.abspath(f), os.path.basename(f)) for f in files]
            self._add_files_with_rel(items)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
        if folder:
            self._start_background_folder_scan(folder)

    def _start_background_folder_scan(self, folder: str):
        """Scan the folder on a background thread so the UI stays responsive."""
        self.btn_add_folder.setEnabled(False)
        self.btn_add_files.setEnabled(False)
        self.txt_log.append(f"🔍 [SCAN] Scanning folder: {folder} ...")

        self._folder_scan_worker = FolderScanWorker(folder)
        self._folder_scan_worker.scan_finished.connect(self._on_folder_scan_finished)
        self._folder_scan_worker.start()

    def _on_folder_scan_finished(self, new_items: List[Tuple[str, str]], abs_folder: str):
        self.btn_add_folder.setEnabled(True)
        self.btn_add_files.setEnabled(True)

        if new_items:
            self._add_files_with_rel(new_items)
            self.txt_log.append(f"📁 [QUEUE] Added folder: {abs_folder} ({len(new_items)} image(s) discovered recursively)")
        else:
            self.txt_log.append(f"⚠️ [WARN] No supported images found in: {abs_folder}")

    def select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory for .sps Files")
        if folder:
            abs_p = os.path.abspath(folder)
            self.txt_output_dir.setText(abs_p)
            self.txt_log.append(f"📂 [CONFIG] Output folder set to: {abs_p}")

    def _add_files_with_rel(self, items: List[Tuple[str, str]]):
        new_items = []
        for abs_p, rel_p in items:
            ext = os.path.splitext(abs_p)[1].lower()
            if ext in SUPPORTED_INPUT_EXTENSIONS and abs_p not in self.selected_files:
                self.selected_files.append(abs_p)
                self.file_rel_map[abs_p] = rel_p
                new_items.append((abs_p, rel_p, ext))

        if new_items:
            self.file_table.setUpdatesEnabled(False)
            start_row = self.file_table.rowCount()
            self.file_table.setRowCount(start_row + len(new_items))

            for idx, (abs_p, rel_p, ext) in enumerate(new_items):
                r = start_row + idx
                self.file_table.setItem(r, 0, QTableWidgetItem(os.path.basename(abs_p)))

                rel_dir = os.path.dirname(rel_p)
                folder_str = f"📁 {rel_dir}/" if rel_dir else "📁 (root)"
                folder_item = QTableWidgetItem(folder_str)
                folder_item.setForeground(QColor("#38bdf8"))
                self.file_table.setItem(r, 1, folder_item)

                self.file_table.setItem(r, 2, QTableWidgetItem(ext.upper().replace(".", "")))

                status_item = QTableWidgetItem("⏳ Queued")
                status_item.setForeground(QColor("#64748b" if self.current_theme == LIGHT else "#94a3b8"))
                self.file_table.setItem(r, 3, status_item)

                self.file_table.setItem(r, 4, QTableWidgetItem(abs_p))

            self.file_table.setUpdatesEnabled(True)
            self.queue_stack.setCurrentIndex(1)
            self._adjust_table_columns()
            self.lbl_queue_count.setText(f"📊 {len(self.selected_files)} images in queue")
            self.txt_log.append(f"📥 [QUEUE] Added {len(new_items)} image(s) to queue. Total: {len(self.selected_files)}")
            self.lbl_metrics.setText(f"📊 0 / {len(self.selected_files)}  •  ⚡ 0.0 f/s  •  ⏱️ 00:00")

    def clear_files(self):
        if self.worker and self.worker.isRunning():
            self._show_popup_message("⚠️ Busy", "Cannot clear queue while encryption is active. Please stop first.", QMessageBox.Icon.Warning)
            return

        self.selected_files.clear()
        self.file_rel_map.clear()
        self.file_table.setRowCount(0)
        self.queue_stack.setCurrentIndex(0)
        self.lbl_queue_count.setText("📊 0 images in queue")
        self.progress_bar.setValue(0)
        self._update_status_badge("IDLE")
        self.lbl_metrics.setText("📊 0 / 0  •  ⚡ 0.0 f/s  •  ⏱️ 00:00")
        self.txt_log.append("🗑️ [QUEUE] Selection cleared.")

    def _on_compression_mode_changed(self, _index: int):
        """Show the Target (KB) spinbox only when JPEG 2000 mode is selected."""
        is_jp2 = self.cmb_compression.currentData() == "jp2"
        self.lbl_jp2_target.setVisible(is_jp2)
        self.spn_jp2_target.setVisible(is_jp2)

    def start_encryption(self):
        if not self.selected_files:
            self._show_popup_message("⚠️ No Files", "Please select at least one image file to encrypt.", QMessageBox.Icon.Warning)
            return

        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(500)

        output_dir = self.txt_output_dir.text().strip() or None
        preserve_structure = self.chk_preserve_structure.isChecked()
        passphrase = DEFAULT_PASSPHRASE
        threads = self.max_worker_threads
        compression_mode = self.cmb_compression.currentData() or "none"
        jp2_target_kb = self.spn_jp2_target.value()

        # Reset all rows to Queued
        self.file_table.setUpdatesEnabled(False)
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, 3)
            if item:
                item.setText("⏳ Queued")
                item.setForeground(QColor("#64748b" if self.current_theme == LIGHT else "#94a3b8"))
        self.file_table.setUpdatesEnabled(True)

        self.progress_bar.setValue(0)
        self.lbl_metrics.setText(f"📊 0 / {len(self.selected_files)}  •  ⚡ 0.0 f/s  •  ⏱️ 00:00")

        # Update UI control states
        self.btn_encrypt.setEnabled(False)
        self.btn_encrypt.setText("⏳ Encrypting...")
        self.btn_add_files.setEnabled(False)
        self.btn_add_folder.setEnabled(False)
        self.btn_clear_list.setEnabled(False)
        self.btn_browse_output.setEnabled(False)
        self.chk_preserve_structure.setEnabled(False)
        self.txt_output_dir.setEnabled(False)
        self.cmb_compression.setEnabled(False)
        self.spn_jp2_target.setEnabled(False)

        self.btn_pause_resume.setEnabled(True)
        self.btn_pause_resume.setText("⏸️ Pause")
        self.btn_pause_resume.setProperty("class", "btn-warning")
        self.btn_pause_resume.style().unpolish(self.btn_pause_resume)
        self.btn_pause_resume.style().polish(self.btn_pause_resume)

        self.btn_cancel.setEnabled(True)
        self._update_status_badge("RUNNING")

        dest_desc = f"Destination: '{output_dir}' (Subfolders: {'Preserved' if preserve_structure else 'Flat'})" if output_dir else "Destination: In-place (Source folders)"
        compress_desc = {
            "none": "Disabled (original size kept)",
            "jp2": f"JPEG 2000 (target {jp2_target_kb} KB per image)",
            "lossless": "Lossless PNG/WebP (identical even zoomed in)",
            "visual": "Visually Lossless (Q88 - no visible difference, not pixel-exact)"
        }.get(compression_mode, "Disabled")
        self.txt_log.append(
            f"\n🚀 Starting Multi-Threaded Batch Encryption ({threads} threads for {len(self.selected_files)} images)..."
            f"\n📂 {dest_desc}"
            f"\n🗜️ Compression: {compress_desc}"
        )

        file_items = [
            (idx, path, self.file_rel_map.get(path, os.path.basename(path)))
            for idx, path in enumerate(self.selected_files)
        ]
        self.worker = BatchEncryptWorker(
            file_items=file_items,
            output_dir=output_dir,
            passphrase=passphrase,
            max_workers=threads,
            preserve_structure=preserve_structure,
            compression_mode=compression_mode,
            jp2_target_kb=jp2_target_kb
        )
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.log_emitted.connect(self._on_worker_log)
        self.worker.finished_all.connect(self._on_worker_finished)

        self.worker.start()
        self.ui_timer.start()

    def _on_ui_tick(self):
        """Called every 30ms to smoothly batch UI table updates."""
        if not self.worker:
            return

        # Process pending results in batches
        pending = self.worker.get_pending_results()
        if pending:
            self.file_table.setUpdatesEnabled(False)
            try:
                for row_idx, success, msg in pending:
                    if row_idx < self.file_table.rowCount():
                        item = self.file_table.item(row_idx, 3)
                        if item:
                            if success:
                                item.setText("✅ Encrypted")
                                item.setForeground(QColor("#16a34a" if self.current_theme == LIGHT else "#34d399"))
                            elif msg == "Cancelled":
                                item.setText("⚠️ Cancelled")
                                item.setForeground(QColor("#d97706" if self.current_theme == LIGHT else "#f59e0b"))
                            else:
                                item.setText(f"❌ Error: {msg}")
                                item.setForeground(QColor("#dc2626" if self.current_theme == LIGHT else "#ef4444"))
            finally:
                self.file_table.setUpdatesEnabled(True)

        # Update progress and speed
        total = self.worker.total_count
        current = self.worker.completed_count
        val = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(val)

        if self.worker.start_time > 0:
            elapsed = max(0.001, time.time() - self.worker.start_time)
            speed = current / elapsed
            mins, secs = divmod(int(elapsed), 60)
            self.lbl_metrics.setText(
                f"📊 {current} / {total}  •  ⚡ {speed:.1f} f/s  •  ⏱️ {mins:02d}:{secs:02d}"
            )

    def toggle_pause_resume(self):
        if not self.worker or not self.worker.isRunning():
            return

        if self.worker.is_paused():
            self.worker.resume()
            self.btn_pause_resume.setText("⏸️ Pause")
            self.btn_pause_resume.setProperty("class", "btn-warning")
        else:
            self.worker.pause()
            self.btn_pause_resume.setText("▶️ Resume")
            self.btn_pause_resume.setProperty("class", "btn-success")

        self.btn_pause_resume.style().unpolish(self.btn_pause_resume)
        self.btn_pause_resume.style().polish(self.btn_pause_resume)

    def cancel_encryption(self):
        """Cancel the ongoing encryption process immediately."""
        if not self.worker:
            return

        self.btn_cancel.setEnabled(False)
        self.btn_pause_resume.setEnabled(False)
        self.btn_pause_resume.setText("⏸️ Pause")
        self._update_status_badge("CANCELLED")

        if self.ui_timer.isActive():
            self.ui_timer.stop()
        self._on_ui_tick()

        worker_ref = self.worker
        worker_ref.cancel()

        # Re-enable Start button
        self.btn_encrypt.setEnabled(True)
        self.btn_encrypt.setText("🔄 Restart Batch Encryption")
        self.btn_encrypt.setProperty("class", "btn-primary")
        self.btn_encrypt.style().unpolish(self.btn_encrypt)
        self.btn_encrypt.style().polish(self.btn_encrypt)

        self.btn_add_files.setEnabled(True)
        self.btn_add_folder.setEnabled(True)
        self.btn_clear_list.setEnabled(True)
        self.btn_browse_output.setEnabled(True)
        self.chk_preserve_structure.setEnabled(True)
        self.txt_output_dir.setEnabled(True)
        self.cmb_compression.setEnabled(True)
        self.spn_jp2_target.setEnabled(True)

        self.txt_log.append("\n⏹️ [STATUS] Process cancelled immediately. Click '🔄 Restart Batch Encryption' to start fresh.")

    def _on_status_changed(self, status: str):
        self._update_status_badge(status)

    def _update_status_badge(self, status: str):
        is_dark = (self.current_theme == DARK)
        if is_dark:
            status_styles = {
                "IDLE": ("💤 IDLE", "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;"),
                "RUNNING": ("⚡ ENCRYPTING", "background-color: #064e3b; color: #34d399; border: 1px solid #059669;"),
                "PAUSED": ("⏸️ PAUSED", "background-color: #78350f; color: #fde68a; border: 1px solid #d97706;"),
                "STOPPING": ("⏳ STOPPING...", "background-color: #831843; color: #fda4af; border: 1px solid #e11d48;"),
                "CANCELLED": ("⏹️ CANCELLED", "background-color: #7f1d1d; color: #fca5a5; border: 1px solid #dc2626;"),
                "COMPLETED": ("🎉 COMPLETED", "background-color: #1e3a8a; color: #93c5fd; border: 1px solid #2563eb;"),
            }
        else:
            status_styles = {
                "IDLE": ("💤 IDLE", "background-color: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;"),
                "RUNNING": ("⚡ ENCRYPTING", "background-color: #ecfdf5; color: #059669; border: 1px solid #a7f3d0;"),
                "PAUSED": ("⏸️ PAUSED", "background-color: #fffbeb; color: #b45309; border: 1px solid #fde68a;"),
                "STOPPING": ("⏳ STOPPING...", "background-color: #fff1f2; color: #be123c; border: 1px solid #fecdd3;"),
                "CANCELLED": ("⏹️ CANCELLED", "background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5;"),
                "COMPLETED": ("🎉 COMPLETED", "background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;"),
            }
        text, style = status_styles.get(status, (f"● {status}", "background-color: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;"))
        self.lbl_status_badge.setText(text)
        self.lbl_status_badge.setStyleSheet(
            f"{style} font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 11px;"
        )

    def _on_worker_log(self, text: str):
        self.txt_log.append(text)

    def _show_popup_message(self, title: str, text: str, icon=QMessageBox.Icon.Information):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setIcon(icon)
        msg.setText(text)
        msg.exec()

    def _on_worker_finished(self, output_files: List[str], was_cancelled: bool):
        self.ui_timer.stop()
        self._on_ui_tick()

        self.btn_encrypt.setEnabled(True)
        self.btn_add_files.setEnabled(True)
        self.btn_add_folder.setEnabled(True)
        self.btn_clear_list.setEnabled(True)
        self.btn_browse_output.setEnabled(True)
        self.chk_preserve_structure.setEnabled(True)
        self.txt_output_dir.setEnabled(True)
        self.cmb_compression.setEnabled(True)
        self.spn_jp2_target.setEnabled(True)

        self.btn_pause_resume.setEnabled(False)
        self.btn_pause_resume.setText("⏸️ Pause")
        self.btn_cancel.setEnabled(False)

        if was_cancelled:
            self.btn_encrypt.setText("🔄 Restart Batch Encryption")
            self.btn_encrypt.setProperty("class", "btn-primary")
            self.btn_encrypt.style().unpolish(self.btn_encrypt)
            self.btn_encrypt.style().polish(self.btn_encrypt)
            self.txt_log.append(f"\n⏹️ Operation cancelled. {len(output_files)} file(s) completed. Ready to restart.")
        else:
            self.btn_encrypt.setText("🔒 Start Batch Encryption")
            self.btn_encrypt.setProperty("class", "btn-success")
            self.btn_encrypt.style().unpolish(self.btn_encrypt)
            self.btn_encrypt.style().polish(self.btn_encrypt)

            self.progress_bar.setValue(100)
            self.txt_log.append(f"\n🎉 === Batch Complete! {len(output_files)} .sps file(s) created. ===\n")

            if output_files:
                out_dir_txt = self.txt_output_dir.text().strip()
                dest_info = f"Destination folder:\n{out_dir_txt}" if out_dir_txt else "Original source folders."
                self._show_popup_message(
                    "🎉 Encryption Complete",
                    f"Successfully encrypted {len(output_files)} file(s) into .sps format!\n\n{dest_info}",
                    QMessageBox.Icon.Information
                )

    def _set_update_button_style(self, is_available: bool = False):
        if is_available:
            self.btn_update.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
                QPushButton:pressed {
                    background-color: #047857;
                }
            """)
        else:
            self.btn_update.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0369a1;
                }
                QPushButton:pressed {
                    background-color: #075985;
                }
            """)

    def _on_update_button_clicked(self):
        if hasattr(self, '_latest_download_url') and self._latest_download_url:
            ver = getattr(self, '_latest_version', 'new version')
            prompt = f"A new version ({ver}) is available!\n\nDo you want to update now?"
            reply = QMessageBox.question(self, "Update Available", prompt,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                download_and_apply_update(self._latest_download_url, getattr(self, '_latest_asset_name', ''), self)
        else:
            check_for_updates_async(self, silent=False, callback=self._on_update_check_finished)

    def _on_update_check_finished(self, success: bool, msg: str, download_url: str, asset_name: str, latest_version: str):
        """Callback when update check completes. Shows button with Update_{version} if an update is found."""
        if success and latest_version:
            self._latest_download_url = download_url
            self._latest_asset_name = asset_name
            self._latest_version = latest_version
            self.btn_update.setText(f"Update_{latest_version}")
            self._set_update_button_style(is_available=True)
            self.btn_update.show()
        else:
            self._latest_download_url = None
            self._latest_asset_name = None
            self._latest_version = None
            self.btn_update.setText("Check for Updates")
            self._set_update_button_style(is_available=False)
            self.btn_update.show()

    def toggle_theme(self):
        """Switch between Dark and Light themes at runtime."""
        app = QApplication.instance()
        if self.current_theme == DARK:
            self.current_theme = LIGHT
            self.btn_theme_toggle.setText("🌙 Dark Mode")
        else:
            self.current_theme = DARK
            self.btn_theme_toggle.setText("☀️ Light Mode")
        apply_theme(app, self.current_theme)
        # Refresh current status badge styling with new theme
        current_text = self.lbl_status_badge.text()
        clean_status = current_text
        for prefix in ["💤 ", "⚡ ", "⏸️ ", "⏳ ", "⏹️ ", "🎉 ", "● "]:
            clean_status = clean_status.replace(prefix, "")
        clean_status = clean_status.strip()
        self._update_status_badge(clean_status)

    def closeEvent(self, event):
        """Ensure clean thread shutdown on window close."""
        if self.worker and self.worker.isRunning():
            msg = QMessageBox(self)
            msg.setWindowTitle("⚠️ Encryption in Progress")
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setText("Batch encryption is currently running. Do you want to cancel and exit?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            reply = msg.exec()

            if reply == QMessageBox.StandardButton.Yes:
                self.ui_timer.stop()
                self.worker.cancel()
                start = time.time()
                while self.worker.isRunning() and (time.time() - start < 2.0):
                    QApplication.processEvents()
                    self.worker.wait(50)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    setup_high_dpi()
    app = QApplication(sys.argv)
    app.setWindowIcon(get_app_icon())
    apply_theme(app, LIGHT)

    window = SPSEncryptorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()