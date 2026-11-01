"""
extension_manager_window.py
Dedicated native PySide6 window for VMT Extension Marketplace.
"""
from __future__ import annotations
import os
import json
import logging
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QStackedWidget, QMessageBox,
    QProgressBar, QDialog, QFormLayout, QDialogButtonBox, QComboBox,
    QFileDialog, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QColor

from ui.styles import COLORS as C
import core.settings as settings
from extensions.client import VMTBackendClient, ExtensionSummary, ExtensionDetail
from extensions.registry import ExtensionRegistry
from extensions.loader import ExtensionLoader
from extensions.lifecycle import ExtensionLifecycle
from extensions.paths import get_download_cache_dir, get_extension_dir

logger = logging.getLogger(__name__)

CAPABILITY_LABELS = {
    "media.read":       "Read media files",
    "media.write":      "Write output files",
    "jobs.add":         "Submit processing jobs",
    "jobs.read":        "Read job status",
    "ffmpeg.execute":   "Run FFmpeg",
    "ui.register":      "Add UI pages",
    "settings.read":    "Read settings",
    "settings.write":   "Write settings",
    "filesystem.read":  "Browse files",
    "filesystem.write": "Write files",
}


# -------------------------------------------------------------------------
# Background Worker Threads
# -------------------------------------------------------------------------

class FetchCatalogThread(QThread):
    catalog_ready = Signal(list, bool)  # data, is_online

    def __init__(self, client: VMTBackendClient):
        super().__init__()
        self.client = client

    def run(self):
        data = []
        is_online = False
        try:
            items = self.client.search()
            is_online = True
            for item in items:
                data.append({
                    "id": item.id,
                    "name": item.name,
                    "version": item.version,
                    "description": item.description,
                    "author": item.author,
                    "installs": item.download_count,
                    "verification_status": item.verification_status,
                    "status": item.verification_status,
                    "category": item.category,
                })
        except Exception as e:
            logger.warning(f"Catalog fetch failed: {e}")
            is_online = False

        # Always include First-Party VMT YouTube Downloader extension in catalog
        has_yt = any(d.get("id") == "org.vmt.youtubedownloader" for d in data)
        if not has_yt:
            data.append({
                "id": "org.vmt.youtubedownloader",
                "name": "VMT YouTube Downloader",
                "version": "1.0.1",
                "description": "First-party YouTube video and audio downloader powered by yt-dlp and FFmpeg.",
                "author": "VMT",
                "installs": 1250,
                "verification_status": "verified",
                "status": "verified",
                "category": "utility",
                "permissions": ["media.read", "media.write", "filesystem.write", "ui.register", "ffmpeg.execute"],
                "github_url": "https://github.com/mrunaliwadkar/-yt-dlp-vmt-extention"
            })

        self.catalog_ready.emit(data, is_online)


class FetchDetailThread(QThread):
    detail_ready = Signal(object)  # ExtensionDetail or None

    def __init__(self, client: VMTBackendClient, ext_id: str):
        super().__init__()
        self.client = client
        self.ext_id = ext_id

    def run(self):
        try:
            detail = self.client.get_detail(self.ext_id)
        except Exception:
            detail = None
        self.detail_ready.emit(detail)


class InstallExtensionThread(QThread):
    progress = Signal(str, int)  # status text, percentage
    success = Signal(str, str, str)  # extension id, cached package path, sha256
    failed = Signal(str)

    def __init__(self, client: VMTBackendClient, ext_id: str, version: str, main_window):
        super().__init__()
        self.client = client
        self.ext_id = ext_id
        self.version = version
        self.main_window = main_window

    def run(self):
        try:
            self.progress.emit(f"Downloading {self.ext_id} v{self.version}...", 30)
            package_bytes = None
            sha256 = None

            # Try online backend download first
            try:
                package_bytes, sha256 = self.client.download(self.ext_id, self.version)
            except Exception as net_err:
                logger.info(f"Backend download unavailable ({net_err}), checking local package fallbacks...")

            # Fallback for YouTube Downloader extension
            if not package_bytes and self.ext_id == "org.vmt.youtubedownloader":
                import hashlib
                root = Path(__file__).resolve().parent.parent.parent
                pkg_candidates = [
                    root / "containers" / "youtube_downloader" / "build" / "YouTubeDownloader.vmte",
                    root / "YouTubeDownloader.vmte",
                ]
                found_pkg = None
                for p in pkg_candidates:
                    if p.exists():
                        found_pkg = p
                        break

                if not found_pkg:
                    try:
                        yt_builder_dir = root / "containers" / "youtube_downloader"
                        if yt_builder_dir.exists():
                            if str(yt_builder_dir) not in sys.path:
                                sys.path.insert(0, str(yt_builder_dir))
                            from build_package import build_package
                            built_p, _ = build_package()
                            found_pkg = built_p
                    except Exception as build_err:
                        logger.error(f"Failed to auto-build YouTubeDownloader package: {build_err}")

                if found_pkg and found_pkg.exists():
                    package_bytes = found_pkg.read_bytes()
                    sha256 = hashlib.sha256(package_bytes).hexdigest()

            if not package_bytes:
                raise RuntimeError(f"Could not retrieve extension package for {self.ext_id}")

            self.progress.emit("Verifying package hash...", 60)
            cache_dir = get_download_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)
            package_path = cache_dir / f"{self.ext_id.replace('.', '_')}.vmte"
            package_path.write_bytes(package_bytes)

            # Loading creates QWidget instances, so the actual lifecycle must
            # run on VMT's GUI thread. Return the verified artifact instead.
            self.progress.emit("Ready to install...", 85)
            self.success.emit(self.ext_id, str(package_path), sha256)
        except Exception as e:
            self.failed.emit(str(e))


# -------------------------------------------------------------------------
# UI Elements & Widgets
# -------------------------------------------------------------------------

class VerifiedBadge(QLabel):
    def __init__(self, status: str):
        super().__init__()
        self.set_status(status)
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setContentsMargins(6, 2, 6, 2)

    def set_status(self, status: str):
        st = status.lower()
        if st == "verified":
            self.setText("✓ VERIFIED")
            self.setStyleSheet(f"color: {C['success']}; border: 1px solid {C['success']}; border-radius: 4px; background: rgba(46,204,113,0.1);")
        elif st == "unverified":
            self.setText("⚠ UNVERIFIED")
            self.setStyleSheet(f"color: {C['warning']}; border: 1px solid {C['warning']}; border-radius: 4px; background: rgba(241,196,15,0.1);")
        elif st == "rejected":
            self.setText("✕ REJECTED")
            self.setStyleSheet(f"color: {C['error']}; border: 1px solid {C['error']}; border-radius: 4px; background: rgba(231,76,60,0.1);")
        elif st == "disabled":
            self.setText("⊘ DISABLED")
            self.setStyleSheet(f"color: {C['text_dim']}; border: 1px solid {C['border']}; border-radius: 4px; background: transparent;")
        else:
            self.setText(status.upper())
            self.setStyleSheet(f"color: {C['text_muted']}; border: 1px solid {C['border']}; border-radius: 4px; background: transparent;")


class ExtensionCard(QFrame):
    clicked = Signal(dict)
    action_clicked = Signal(str, dict)  # action ("install", "update", "enable", "disable", "uninstall"), ext_data

    def __init__(self, data: dict, installed_info: dict = None, has_update: bool = False, new_version: str = ""):
        super().__init__()
        self.data = data
        self.installed_info = installed_info
        self.has_update = has_update
        self.new_version = new_version

        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {C['bg_card']};
                border-radius: 12px;
                border: 1px solid {C['border']};
            }}
            QFrame:hover {{
                border: 1px solid {C['accent']};
                background-color: {C['bg_card_alt']};
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(16)

        # Icon box
        icon_box = QLabel("🧩")
        icon_box.setFixedSize(54, 54)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(f"""
            background: {C['bg_dark']};
            border-radius: 10px;
            font-size: 26px;
            border: 1px solid {C['border']};
        """)
        lay.addWidget(icon_box)

        # Center info
        info_lay = QVBoxLayout()
        info_lay.setSpacing(4)

        header_lay = QHBoxLayout()
        header_lay.setSpacing(8)
        
        name_lbl = QLabel(data.get("name", "Unknown Extension"))
        name_lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 16px; font-weight: 700; background: transparent;")
        header_lay.addWidget(name_lbl)

        badge = VerifiedBadge(data.get("status", "unverified"))
        header_lay.addWidget(badge)
        header_lay.addStretch()

        ver_str = f"v{data.get('version', '1.0.0')}"
        if installed_info:
            ver_str = f"Installed: v{installed_info.get('version')}"
        ver_lbl = QLabel(ver_str)
        ver_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; background: transparent;")
        header_lay.addWidget(ver_lbl)

        info_lay.addLayout(header_lay)

        desc_lbl = QLabel(data.get("description", "No description provided."))
        desc_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 13px; background: transparent;")
        desc_lbl.setWordWrap(True)
        info_lay.addWidget(desc_lbl)

        # Sub info
        meta_str = f"by {data.get('author', 'Unknown')}"
        if data.get("installs", 0) > 0:
            meta_str += f" · {data.get('installs', 0):,} installs"
        meta_lbl = QLabel(meta_str)
        meta_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; background: transparent;")
        info_lay.addWidget(meta_lbl)

        lay.addLayout(info_lay, 1)

        # Actions on right
        btn_lay = QVBoxLayout()
        btn_lay.setAlignment(Qt.AlignCenter)
        btn_lay.setSpacing(8)

        if installed_info:
            if has_update:
                update_btn = QPushButton(f"Update to v{new_version}")
                update_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C['accent']}; color: white; border: none;
                        border-radius: 6px; padding: 6px 16px; font-weight: bold; font-size: 12px;
                    }}
                    QPushButton:hover {{ background: {C['accent_dark']}; }}
                """)
                update_btn.clicked.connect(self._on_update)
                btn_lay.addWidget(update_btn)

            enabled = installed_info.get("enabled", True)
            if enabled:
                disable_btn = QPushButton("Disable")
                disable_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C['bg_dark']}; color: {C['text_muted']}; border: 1px solid {C['border']};
                        border-radius: 6px; padding: 6px 14px; font-size: 12px;
                    }}
                    QPushButton:hover {{ color: white; border-color: {C['text_muted']}; }}
                """)
                disable_btn.clicked.connect(self._on_disable)
                btn_lay.addWidget(disable_btn)
            else:
                enable_btn = QPushButton("Enable")
                enable_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C['bg_dark']}; color: {C['success']}; border: 1px solid {C['success']};
                        border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: bold;
                    }}
                    QPushButton:hover {{ background: rgba(46,204,113,0.15); }}
                """)
                enable_btn.clicked.connect(self._on_enable)
                btn_lay.addWidget(enable_btn)

            uninstall_btn = QPushButton("Uninstall")
            uninstall_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C['text_dim']}; border: none;
                    font-size: 11px; text-decoration: underline;
                }}
                QPushButton:hover {{ color: {C['error']}; }}
            """)
            uninstall_btn.clicked.connect(self._on_uninstall)
            btn_lay.addWidget(uninstall_btn)
        else:
            install_btn = QPushButton("Install")
            install_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C['accent']}; color: white; border: none;
                    border-radius: 6px; padding: 8px 20px; font-weight: bold; font-size: 13px;
                }}
                QPushButton:hover {{ background: {C['accent_dark']}; }}
            """)
            install_btn.clicked.connect(self._on_install)
            btn_lay.addWidget(install_btn)

        lay.addLayout(btn_lay)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(event)

    def _on_install(self):
        self.action_clicked.emit("install", self.data)

    def _on_update(self):
        self.action_clicked.emit("update", self.data)

    def _on_disable(self):
        self.action_clicked.emit("disable", self.data)

    def _on_enable(self):
        self.action_clicked.emit("enable", self.data)

    def _on_uninstall(self):
        self.action_clicked.emit("uninstall", self.data)


class ExtensionDetailView(QWidget):
    back_clicked = Signal()
    install_clicked = Signal(dict, str)  # data, version
    uninstall_clicked = Signal(str)
    disable_clicked = Signal(str)
    enable_clicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.data: Optional[dict] = None
        self.detail_info: Optional[ExtensionDetail] = None
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        # Navigation header
        nav_lay = QHBoxLayout()
        back_btn = QPushButton("← Back to Marketplace")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C['accent']}; border: none;
                font-weight: bold; font-size: 14px; text-align: left;
            }}
            QPushButton:hover {{ color: {C['accent_light']}; text-decoration: underline; }}
        """)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_clicked.emit)
        nav_lay.addWidget(back_btn)
        nav_lay.addStretch()
        lay.addLayout(nav_lay)

        # Scroll area for main detail content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content_widget = QWidget()
        c_lay = QVBoxLayout(self.content_widget)
        c_lay.setContentsMargins(10, 10, 10, 10)
        c_lay.setSpacing(20)

        # Top Header Banner
        header_card = QFrame()
        header_card.setStyleSheet(f"background: {C['bg_card']}; border-radius: 12px; border: 1px solid {C['border']};")
        hc_lay = QHBoxLayout(header_card)
        hc_lay.setContentsMargins(20, 20, 20, 20)
        hc_lay.setSpacing(20)

        icon_lbl = QLabel("🧩")
        icon_lbl.setFixedSize(72, 72)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"background: {C['bg_dark']}; border-radius: 12px; font-size: 36px; border: 1px solid {C['border']};")
        hc_lay.addWidget(icon_lbl)

        info_lay = QVBoxLayout()
        info_lay.setSpacing(6)

        title_lay = QHBoxLayout()
        self.name_lbl = QLabel("Extension Name")
        self.name_lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 22px; font-weight: 800; background: transparent;")
        title_lay.addWidget(self.name_lbl)

        self.badge_lbl = VerifiedBadge("unverified")
        title_lay.addWidget(self.badge_lbl)
        title_lay.addStretch()
        info_lay.addLayout(title_lay)

        self.meta_lbl = QLabel("by Author · v1.0.0")
        self.meta_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 13px; background: transparent;")
        info_lay.addWidget(self.meta_lbl)

        hc_lay.addLayout(info_lay, 1)

        self.action_btn = QPushButton("Install")
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['accent']}; color: white; border: none;
                border-radius: 8px; padding: 12px 28px; font-size: 15px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {C['accent_dark']}; }}
        """)
        self.action_btn.clicked.connect(self._on_action_clicked)
        hc_lay.addWidget(self.action_btn)

        c_lay.addWidget(header_card)

        # Unverified Warning Callout Banner
        self.warn_banner = QFrame()
        self.warn_banner.setStyleSheet(f"background: rgba(241,196,15,0.12); border: 1px solid {C['warning']}; border-radius: 10px;")
        wb_lay = QHBoxLayout(self.warn_banner)
        wb_lay.setContentsMargins(16, 14, 16, 14)
        wb_icon = QLabel("⚠")
        wb_icon.setStyleSheet(f"font-size: 24px; color: {C['warning']}; background: transparent;")
        wb_lay.addWidget(wb_icon)

        wb_text = QLabel(
            "<b>UNVERIFIED EXTENSION</b><br>"
            "This extension has not been reviewed by the VMT team.<br>"
            "Extensions run inside VMT and have permissions to interact with your system. Only install extensions from authors you trust."
        )
        wb_text.setStyleSheet(f"color: {C['text_primary']}; font-size: 12px; background: transparent;")
        wb_lay.addWidget(wb_text, 1)
        c_lay.addWidget(self.warn_banner)

        # Description Section
        self.desc_group = self._create_section("DESCRIPTION")
        c_lay.addWidget(self.desc_group)

        # Capabilities / Permissions Section
        self.perm_group = self._create_section("PERMISSIONS & CAPABILITIES REQUESTED")
        c_lay.addWidget(self.perm_group)

        # Compatibility Section
        self.compat_group = self._create_section("COMPATIBILITY")
        c_lay.addWidget(self.compat_group)

        # Versions Section
        self.ver_group = self._create_section("VERSIONS & RELEASES")
        c_lay.addWidget(self.ver_group)

        c_lay.addStretch()
        scroll.setWidget(self.content_widget)
        lay.addWidget(scroll)

    def _create_section(self, title: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"background: {C['bg_card']}; border-radius: 10px; border: 1px solid {C['border']};")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; font-weight: 800; letter-spacing: 1px; background: transparent;")
        v.addWidget(lbl_title)

        lbl_content = QLabel("None")
        lbl_content.setStyleSheet(f"color: {C['text_primary']}; font-size: 13px; background: transparent;")
        lbl_content.setWordWrap(True)
        v.addWidget(lbl_content)

        card.content_lbl = lbl_content
        return card

    def set_data(self, data: dict, detail_info: Optional[ExtensionDetail] = None, installed_info: Optional[dict] = None):
        self.data = data
        self.detail_info = detail_info
        self.installed_info = installed_info

        name = data.get("name", "")
        author = data.get("author", "")
        version = data.get("version", "1.0.0")
        status = data.get("status", "unverified")

        self.name_lbl.setText(name)
        self.badge_lbl.set_status(status)
        self.meta_lbl.setText(f"by {author} · Current version: v{version}")

        # Show warning banner if unverified
        self.warn_banner.setVisible(status.lower() != "verified")

        # Description
        self.desc_group.content_lbl.setText(data.get("description", "No description provided."))

        # Permissions
        perms = []
        if detail_info and detail_info.permissions:
            perms = detail_info.permissions
        elif data.get("permissions"):
            perms = data.get("permissions")

        if perms:
            p_text = "\n".join([f"  • {CAPABILITY_LABELS.get(p, p)} ({p})" for p in perms])
            self.perm_group.content_lbl.setText(p_text)
        else:
            self.perm_group.content_lbl.setText("No special permissions requested.")

        # Compatibility
        min_vmt = "1.0.0"
        if detail_info and detail_info.min_vmt_version:
            min_vmt = detail_info.min_vmt_version
        self.compat_group.content_lbl.setText(f"Requires VMT version {min_vmt} or higher.")

        # Versions
        if detail_info and detail_info.versions:
            v_lines = []
            for v in detail_info.versions:
                st = f"✓ VERIFIED" if v.verification_status == "verified" else "⚠ UNVERIFIED"
                reason = f" ({v.verification_reason})" if v.verification_reason else ""
                v_lines.append(f"<b>v{v.version}</b> — {st}{reason}")
                if v.changelog:
                    v_lines.append(f"   <i>Changelog: {v.changelog}</i>")
            self.ver_group.content_lbl.setText("<br>".join(v_lines))
        else:
            self.ver_group.content_lbl.setText(f"v{version} ({status.upper()})")

        # Action Button
        if installed_info:
            self.action_btn.setText("Uninstall Extension")
            self.action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C['error']}; color: white; border: none;
                    border-radius: 8px; padding: 12px 28px; font-size: 15px; font-weight: bold;
                }}
                QPushButton:hover {{ background: #c0392b; }}
            """)
        else:
            self.action_btn.setText(f"Install v{version}")
            self.action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C['accent']}; color: white; border: none;
                    border-radius: 8px; padding: 12px 28px; font-size: 15px; font-weight: bold;
                }}
                QPushButton:hover {{ background: {C['accent_dark']}; }}
            """)

    def _on_action_clicked(self):
        if not self.data:
            return
        if self.installed_info:
            self.uninstall_clicked.emit(self.data["id"])
        else:
            self.install_clicked.emit(self.data, self.data.get("version", "1.0.0"))


class DeveloperLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Developer Login — VMT Marketplace")
        self.setFixedSize(380, 240)
        self.setStyleSheet(f"background: {C['bg_dark']}; color: {C['text_primary']};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        title = QLabel("Developer Portal Login")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['text_primary']};")
        lay.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Username")
        self.user_edit.setStyleSheet(f"background: {C['bg_base']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 6px; color: white;")
        form.addRow("Username:", self.user_edit)

        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setPlaceholderText("Password")
        self.pass_edit.setStyleSheet(f"background: {C['bg_base']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 6px; color: white;")
        form.addRow("Password:", self.pass_edit)

        lay.addLayout(form)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color: {C['error']}; font-size: 12px;")
        lay.addWidget(self.err_lbl)

        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(cancel_btn)

        login_btn = QPushButton("Log In")
        login_btn.setStyleSheet(f"background: {C['accent']}; color: white; font-weight: bold; border-radius: 6px; padding: 6px 18px;")
        login_btn.clicked.connect(self.accept)
        btn_lay.addWidget(login_btn)

        lay.addLayout(btn_lay)

    def get_credentials(self) -> tuple[str, str]:
        return self.user_edit.text().strip(), self.pass_edit.text().strip()


# -------------------------------------------------------------------------
# Main Window: ExtensionManagerWindow
# -------------------------------------------------------------------------

class ExtensionManagerWindow(QMainWindow):
    extension_changed = Signal(str)  # Emitted when an extension state changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_vmt_window = parent
        self.client = VMTBackendClient()
        self.catalog_data: List[dict] = []
        self.is_online: bool = False
        self.current_nav: str = "discover"

        self.setWindowTitle("VMT Extension Manager")
        self.setMinimumSize(950, 650)
        self.setStyleSheet(f"background-color: {C['bg_base']}; color: {C['text_primary']};")

        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "runner_icon.png"))
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self._restore_geometry()
        self._build_ui()
        self.refresh_catalog()

    def _restore_geometry(self):
        w = settings.get("ext_manager_width", 980)
        h = settings.get("ext_manager_height", 680)
        x = settings.get("ext_manager_x", -1)
        y = settings.get("ext_manager_y", -1)
        is_max = settings.get("ext_manager_maximized", False)

        self.resize(w, h)
        if x >= 0 and y >= 0:
            self.move(x, y)
        elif self.main_vmt_window:
            geo = self.main_vmt_window.geometry()
            cx = geo.x() + (geo.width() - w) // 2
            cy = geo.y() + (geo.height() - h) // 2
            self.move(max(0, cx), max(0, cy))

        if is_max:
            self.showMaximized()

    def closeEvent(self, event):
        if self.isMaximized():
            settings.set("ext_manager_maximized", True)
        else:
            settings.set("ext_manager_maximized", False)
            settings.set("ext_manager_width", self.width())
            settings.set("ext_manager_height", self.height())
            settings.set("ext_manager_x", self.x())
            settings.set("ext_manager_y", self.y())
        settings.save()
        super().closeEvent(event)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Top Header Bar
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"background: {C['bg_dark']}; border-bottom: 1px solid {C['border']};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)
        h_lay.setSpacing(16)

        title_lbl = QLabel("🧩 VMT Marketplace")
        title_lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 18px; font-weight: 800; background: transparent;")
        h_lay.addWidget(title_lbl)

        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Search extensions...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {C['bg_base']}; border: 1px solid {C['border']}; border-radius: 8px;
                padding: 6px 12px; color: white; font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {C['accent']}; }}
        """)
        self.search_edit.textChanged.connect(self._on_search_changed)
        h_lay.addWidget(self.search_edit, 1)

        # Category filter
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["All Categories", "utility", "video", "audio", "effects"])
        self.cat_combo.setStyleSheet(f"""
            QComboBox {{
                background: {C['bg_base']}; border: 1px solid {C['border']}; border-radius: 8px;
                padding: 6px 12px; color: white; font-size: 13px;
            }}
        """)
        self.cat_combo.currentTextChanged.connect(lambda: self._apply_filters())
        h_lay.addWidget(self.cat_combo)

        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_card']}; border: 1px solid {C['border']}; border-radius: 8px;
                padding: 6px 14px; color: white; font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {C['bg_hover']}; }}
        """)
        self.refresh_btn.clicked.connect(self.refresh_catalog)
        h_lay.addWidget(self.refresh_btn)

        # Backend Status pill
        self.status_pill = QLabel("● Online")
        self.status_pill.setStyleSheet(f"color: {C['success']}; font-weight: bold; font-size: 12px; background: transparent;")
        h_lay.addWidget(self.status_pill)

        root_lay.addWidget(header)

        # Main Body Splitter/Layout (Left Nav | Content Stack)
        body = QWidget()
        b_lay = QHBoxLayout(body)
        b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.setSpacing(0)

        # Sidebar Nav
        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet(f"background: {C['sidebar_bg']}; border-right: 1px solid {C['border']};")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(12, 16, 12, 16)
        sb_lay.setSpacing(6)

        nav_items = [
            ("discover",  "🌐  Discover"),
            ("installed", "💾  Installed"),
            ("updates",   "🚀  Updates"),
            ("verified",  "✓  Verified"),
            ("developer", "💻  My Extensions"),
        ]

        self.nav_btns: Dict[str, QPushButton] = {}
        for nid, nlabel in nav_items:
            btn = QPushButton(nlabel)
            btn.setFixedHeight(40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; border-radius: 8px;
                    color: {C['text_muted']}; font-weight: 600; font-size: 13px; text-align: left; padding-left: 12px;
                }}
                QPushButton:hover {{ background: {C['bg_hover']}; color: white; }}
            """)
            btn.clicked.connect(lambda checked, i=nid: self._switch_nav(i))
            self.nav_btns[nid] = btn
            sb_lay.addWidget(btn)

        sb_lay.addStretch()

        b_lay.addWidget(sidebar)

        # Content Stack
        self.stack = QStackedWidget()

        # 0: Catalog Grid View
        self.catalog_view = QWidget()
        cv_lay = QVBoxLayout(self.catalog_view)
        cv_lay.setContentsMargins(20, 20, 20, 20)
        cv_lay.setSpacing(16)

        # Offline Warning Banner
        self.offline_banner = QFrame()
        self.offline_banner.setStyleSheet(f"background: rgba(241,196,15,0.12); border: 1px solid {C['warning']}; border-radius: 8px;")
        ob_lay = QHBoxLayout(self.offline_banner)
        ob_lay.setContentsMargins(14, 10, 14, 10)
        ob_lbl = QLabel("⚠ VMT Extension Service unavailable. You can still view and manage your installed extensions.")
        ob_lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 12px; background: transparent;")
        ob_lay.addWidget(ob_lbl)
        self.offline_banner.hide()
        cv_lay.addWidget(self.offline_banner)

        # Status / Header title in catalog view
        self.catalog_header_lbl = QLabel("Discover Extensions")
        self.catalog_header_lbl.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['text_primary']};")
        cv_lay.addWidget(self.catalog_header_lbl)

        # Scroll area for cards
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_scroll.setStyleSheet("background: transparent;")

        self.cards_container = QWidget()
        self.cards_lay = QVBoxLayout(self.cards_container)
        self.cards_lay.setContentsMargins(0, 0, 0, 0)
        self.cards_lay.setSpacing(12)
        self.cards_lay.addStretch()

        self.cards_scroll.setWidget(self.cards_container)
        cv_lay.addWidget(self.cards_scroll, 1)

        self.stack.addWidget(self.catalog_view)  # idx 0

        # 1: Detail View
        self.detail_view = ExtensionDetailView()
        self.detail_view.back_clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.detail_view.install_clicked.connect(self._handle_install)
        self.detail_view.uninstall_clicked.connect(self._handle_uninstall)
        self.stack.addWidget(self.detail_view)  # idx 1

        # 2: Developer View
        self.dev_view = QWidget()
        self._build_developer_view()
        self.stack.addWidget(self.dev_view)  # idx 2

        b_lay.addWidget(self.stack, 1)
        root_lay.addWidget(body, 1)

        # Progress / Toast Bar at bottom
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {C['accent']}; }}")
        self.progress_bar.hide()
        root_lay.addWidget(self.progress_bar)

        self._switch_nav("discover")

    def _build_developer_view(self):
        lay = QVBoxLayout(self.dev_view)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        title = QLabel("Developer Portal & Extensions")
        title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {C['text_primary']};")
        lay.addWidget(title)

        # Container for dev state
        self.dev_content = QWidget()
        self.dev_content_lay = QVBoxLayout(self.dev_content)
        self.dev_content_lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.dev_content, 1)

    def _update_developer_ui(self):
        # Clear dev_content
        while self.dev_content_lay.count():
            item = self.dev_content_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Display placeholder for My Extensions
        card = QFrame()
        card.setStyleSheet(f"background: {C['bg_card']}; border-radius: 12px; border: 1px solid {C['border']};")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(40, 40, 40, 40)
        c_lay.setSpacing(16)
        c_lay.setAlignment(Qt.AlignCenter)

        icon = QLabel("💻")
        icon.setStyleSheet("font-size: 48px; background: transparent;")
        icon.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(icon)

        h1 = QLabel("My Extensions")
        h1.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {C['text_primary']}; background: transparent;")
        h1.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(h1)

        h2 = QLabel("Developer publishing will be available soon.")
        h2.setStyleSheet(f"font-size: 14px; color: {C['text_muted']}; background: transparent;")
        h2.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(h2)

        self.dev_content_lay.addWidget(card)

    def _show_login_dialog(self):
        pass

    def _developer_logout(self):
        pass

    def _upload_developer_package(self):
        pass

    def _upload_developer_version(self, ext_id: str):
        pass

    # Catalog & Search Handling
    def refresh_catalog(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ Loading...")

        self.fetch_thread = FetchCatalogThread(self.client)
        self.fetch_thread.catalog_ready.connect(self._on_catalog_ready)
        self.fetch_thread.start()

    def _on_catalog_ready(self, data: list, is_online: bool):
        self.catalog_data = data
        self.is_online = is_online
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Refresh")

        if is_online:
            self.status_pill.setText("● Online")
            self.status_pill.setStyleSheet(f"color: {C['success']}; font-weight: bold; font-size: 12px; background: transparent;")
            self.offline_banner.hide()
        else:
            self.status_pill.setText("⚠ Offline Mode")
            self.status_pill.setStyleSheet(f"color: {C['warning']}; font-weight: bold; font-size: 12px; background: transparent;")
            self.offline_banner.show()

        self._apply_filters()

    def _switch_nav(self, nav_id: str):
        self.current_nav = nav_id
        for nid, btn in self.nav_btns.items():
            if nid == nav_id:
                btn.setStyleSheet(f"""
                    background: {C['accent']}; color: white; border-radius: 8px;
                    font-weight: 700; font-size: 13px; text-align: left; padding-left: 12px;
                """)
            else:
                btn.setStyleSheet(f"""
                    background: transparent; border: none; border-radius: 8px;
                    color: {C['text_muted']}; font-weight: 600; font-size: 13px; text-align: left; padding-left: 12px;
                """)

        if nav_id == "developer":
            self._update_developer_ui()
            self.stack.setCurrentIndex(2)
        else:
            self.stack.setCurrentIndex(0)
            self._apply_filters()

    def _on_search_changed(self):
        if self.current_nav == "developer":
            self._switch_nav("discover")
        self._apply_filters()

    @staticmethod
    def _is_dev_test_extension(ext_id: str) -> bool:
        eid = ext_id.lower()
        return eid.startswith("com.audit") or eid.startswith("com.example") or "audittest" in eid or "testextension" in eid

    def _get_installed_dict() -> dict[str, dict]:
        try:
            reg = ExtensionRegistry()
            reg.load_from_disk()
            installed = {}
            for r in reg.list_all():
                if not ExtensionManagerWindow._is_dev_test_extension(r.id):
                    installed[r.id] = {"version": r.version, "enabled": r.enabled, "name": r.name, "manifest": r.manifest}
            return installed
        except Exception:
            return {}

    def _apply_filters(self):
        # Clear existing cards
        while self.cards_lay.count() > 1:
            item = self.cards_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = self.search_edit.text().strip().lower()
        cat_filter = self.cat_combo.currentText()
        installed_dict = ExtensionManagerWindow._get_installed_dict()

        # Update section header
        headers = {
            "discover": "Discover Extensions",
            "installed": f"Installed Extensions ({len(installed_dict)})",
            "updates": "Available Updates",
            "verified": "Verified Extensions Only",
        }
        self.catalog_header_lbl.setText(headers.get(self.current_nav, "Extensions"))

        # Build list to render
        items_to_show = []

        if self.current_nav == "installed":
            # Show all locally installed extensions (excluding dev/test)
            for ext_id, info in installed_dict.items():
                m = info["manifest"]
                remote_match = next((x for x in self.catalog_data if x["id"] == ext_id), None)
                cat = remote_match["category"] if remote_match else m.category
                desc = remote_match["description"] if remote_match else m.description
                author = remote_match["author"] if remote_match else m.author
                status = remote_match["status"] if remote_match else "unverified"
                installs = remote_match["installs"] if remote_match else 0

                items_to_show.append({
                    "data": {
                        "id": ext_id,
                        "name": info["name"],
                        "version": remote_match["version"] if remote_match else info["version"],
                        "description": desc,
                        "author": author,
                        "status": status,
                        "category": cat,
                        "installs": installs,
                    },
                    "installed_info": info,
                    "has_update": remote_match and remote_match["version"] != info["version"] if remote_match else False,
                    "new_version": remote_match["version"] if remote_match else ""
                })

        elif self.current_nav == "updates":
            for ext in self.catalog_data:
                ext_id = ext["id"]
                if self._is_dev_test_extension(ext_id):
                    continue
                if ext_id in installed_dict:
                    inst_v = installed_dict[ext_id]["version"]
                    if ext["version"] != inst_v:
                        items_to_show.append({
                            "data": ext,
                            "installed_info": installed_dict[ext_id],
                            "has_update": True,
                            "new_version": ext["version"]
                        })

        else:
            # Discover or Verified
            for ext in self.catalog_data:
                if self._is_dev_test_extension(ext["id"]):
                    continue
                if self.current_nav == "verified" and ext.get("status") != "verified":
                    continue
                inst_info = installed_dict.get(ext["id"])
                has_up = inst_info and inst_info["version"] != ext["version"]
                items_to_show.append({
                    "data": ext,
                    "installed_info": inst_info,
                    "has_update": has_up,
                    "new_version": ext["version"]
                })

        # Apply search and category filter
        rendered_count = 0
        for entry in items_to_show:
            ext = entry["data"]
            if query and (query not in ext.get("name", "").lower() and query not in ext.get("description", "").lower() and query not in ext.get("id", "").lower()):
                continue
            if cat_filter != "All Categories" and ext.get("category", "").lower() != cat_filter.lower():
                continue

            card = ExtensionCard(
                data=ext,
                installed_info=entry["installed_info"],
                has_update=entry["has_update"],
                new_version=entry["new_version"]
            )
            card.clicked.connect(self._show_detail)
            card.action_clicked.connect(self._handle_action)

            self.cards_lay.insertWidget(self.cards_lay.count() - 1, card)
            rendered_count += 1

        if rendered_count == 0:
            empty_card = QFrame()
            empty_card.setStyleSheet(f"background: {C['bg_card']}; border-radius: 12px; border: 1px dashed {C['border']};")
            el = QVBoxLayout(empty_card)
            el.setContentsMargins(35, 35, 35, 35)
            el.setAlignment(Qt.AlignCenter)
            
            msg_text = "You're up to date." if self.current_nav == "updates" else "No extensions found."
            t = QLabel(msg_text)
            t.setStyleSheet(f"color: {C['text_dim']}; font-size: 15px; font-weight: 600;")
            el.addWidget(t)
            self.cards_lay.insertWidget(self.cards_lay.count() - 1, empty_card)

    def _show_detail(self, data: dict):
        ext_id = data["id"]
        installed_dict = ExtensionManagerWindow._get_installed_dict()
        inst_info = installed_dict.get(ext_id)

        self.detail_thread = FetchDetailThread(self.client, ext_id)
        self.detail_thread.detail_ready.connect(lambda detail: self.detail_view.set_data(data, detail, inst_info))
        self.detail_thread.start()

        self.detail_view.set_data(data, None, inst_info)
        self.stack.setCurrentIndex(1)

    def _handle_action(self, action: str, data: dict):
        ext_id = data["id"]

        if action in ("install", "update"):
            self._handle_install(data, data.get("version", "1.0.0"))
        elif action == "disable":
            try:
                reg = ExtensionRegistry()
                reg.load_from_disk()
                loader = ExtensionLoader()
                lc = ExtensionLifecycle(reg, loader, self.main_vmt_window)
                lc.disable(ext_id)
                self.extension_changed.emit(ext_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to disable: {e}")
            self._apply_filters()
        elif action == "enable":
            try:
                reg = ExtensionRegistry()
                reg.load_from_disk()
                loader = ExtensionLoader()
                lc = ExtensionLifecycle(reg, loader, self.main_vmt_window)
                lc.enable(ext_id)
                self.extension_changed.emit(ext_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to enable: {e}")
            self._apply_filters()
        elif action == "uninstall":
            self._handle_uninstall(ext_id)

    def _handle_install(self, data: dict, version: str):
        status = data.get("status", "unverified")

        if status == "unverified":
            msg = QMessageBox(self)
            msg.setWindowTitle("Install Unverified Extension")
            msg.setIcon(QMessageBox.Warning)
            msg.setText(f"<b>⚠ UNVERIFIED EXTENSION</b>")
            msg.setInformativeText(
                f'"{data.get("name")}" has not been reviewed by the VMT team.\n\n'
                f"Extensions run inside VMT and have access to VMT APIs and system resources.\n"
                f"Only install extensions from authors you trust.\n\n"
                f"Are you sure you want to install {data.get('name')} v{version}?"
            )
            install_btn = msg.addButton("INSTALL ANYWAY", QMessageBox.ActionRole)
            msg.addButton("Cancel", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() != install_btn:
                return

        # Start non-blocking install thread
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.install_thread = InstallExtensionThread(self.client, data["id"], version, self.main_vmt_window)
        self.install_thread.progress.connect(self._on_install_progress)
        self.install_thread.success.connect(self._on_install_success)
        self.install_thread.failed.connect(self._on_install_failed)
        self.install_thread.start()

    def _on_install_progress(self, text: str, val: int):
        self.progress_bar.setValue(val)

    def _on_install_success(self, ext_id: str, package_path: str, sha256: str):
        self.progress_bar.hide()
        try:
            lifecycle = getattr(self.main_vmt_window, "_ext_lifecycle", None)
            if lifecycle is None:
                registry = ExtensionRegistry()
                registry.load_from_disk()
                lifecycle = ExtensionLifecycle(registry, ExtensionLoader(), self.main_vmt_window)
            previous = lifecycle._registry.get(ext_id)
            was_pinned = bool(previous and previous.pinned)
            if previous:
                lifecycle.uninstall(ext_id)
            installed = lifecycle.install(Path(package_path), sha256)
            if was_pinned:
                installed.pinned = True
                lifecycle._registry.save_to_disk()
            QMessageBox.information(self, "Installation Complete", f"Extension '{ext_id}' installed successfully!")
            self.extension_changed.emit(ext_id)
        except Exception as exc:
            QMessageBox.critical(self, "Installation Failed", f"Failed to install extension: {exc}")
        finally:
            try:
                Path(package_path).unlink()
            except OSError:
                pass
        self.stack.setCurrentIndex(0)
        self._apply_filters()
        return
        QMessageBox.information(self, "Installation Complete", f"✓ Extension '{ext_id}' installed successfully!")
        self.extension_changed.emit(ext_id)
        self.stack.setCurrentIndex(0)
        self._apply_filters()

    def _on_install_failed(self, err: str):
        self.progress_bar.hide()
        QMessageBox.critical(self, "Installation Failed", f"Failed to install extension: {err}")

    def _handle_uninstall(self, ext_id: str):
        if QMessageBox.question(self, "Uninstall Extension", f"Are you sure you want to uninstall '{ext_id}'?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                reg = ExtensionRegistry()
                reg.load_from_disk()
                loader = ExtensionLoader()
                lc = ExtensionLifecycle(reg, loader, self.main_vmt_window)
                lc.uninstall(ext_id)
                QMessageBox.information(self, "Uninstalled", f"Extension '{ext_id}' was uninstalled.")
                self.extension_changed.emit(ext_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to uninstall: {e}")
            self.stack.setCurrentIndex(0)
            self._apply_filters()
