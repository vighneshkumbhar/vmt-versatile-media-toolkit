"""
extensions_page.py
Extension Manager UI for VMT.
"""
from __future__ import annotations
import os
import json
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QStackedWidget, QMessageBox,
    QProgressBar, QDialog, QDialogButtonBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QIcon, QColor

from ui.styles import COLORS as C

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
# STUBS for missing backend
# -------------------------------------------------------------------------
class FetchExtensionsThread(QThread):
    result = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            from extensions.client import VMTBackendClient
            client = VMTBackendClient()
            data = client.search()
            result = []
            for ext in data:
                result.append({
                    "id": ext.id,
                    "name": ext.name,
                    "version": ext.version,
                    "description": ext.description,
                    "author": ext.author,
                    "installs": ext.download_count,
                    "verification_status": ext.verification_status,
                    "status": ext.verification_status,
                    "category": ext.category,
                    "permissions": [],
                    "versions": [],
                })
            self.result.emit(result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Backend unavailable: {e}")
            self.result.emit([])


# -------------------------------------------------------------------------
# UI Classes
# -------------------------------------------------------------------------

class VerifiedBadge(QLabel):
    def __init__(self, status: str):
        super().__init__()
        self.set_status(status)
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setContentsMargins(6, 2, 6, 2)
        
    def set_status(self, status: str):
        if status == "verified":
            self.setText("✓ VERIFIED")
            self.setStyleSheet(f"color: {C['success']}; border: 1px solid {C['success']}; border-radius: 4px;")
        elif status == "unverified":
            self.setText("⚠ Unverified")
            self.setStyleSheet(f"color: {C['warning']}; border: 1px solid {C['warning']}; border-radius: 4px;")
        elif status == "rejected":
            self.setText("✕ Rejected")
            self.setStyleSheet(f"color: {C['error']}; border: 1px solid {C['error']}; border-radius: 4px;")
        elif status == "disabled":
            self.setText("⊘ Disabled")
            self.setStyleSheet(f"color: {C['text_dim']}; border: 1px solid {C['text_dim']}; border-radius: 4px;")
        else:
            self.setText(status.upper())
            self.setStyleSheet(f"color: {C['text_muted']}; border: 1px solid {C['text_muted']}; border-radius: 4px;")


class ExtensionCard(QFrame):
    clicked = Signal(dict)
    action_clicked = Signal(str, dict) # action, ext_data

    def __init__(self, data: dict, installed_info: dict = None):
        super().__init__()
        self.data = data
        self.installed_info = installed_info
        self.setProperty("class", "card")
        
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame[class="card"] {{
                background-color: {C['bg_card']};
                border-radius: 12px;
                border: 1px solid {C['border']};
            }}
            QFrame[class="card"]:hover {{
                border: 1px solid {C['accent']};
            }}
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QHBoxLayout()
        name_lbl = QLabel(data.get('name', 'Unknown'))
        name_lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 16px; font-weight: 700; background: transparent;")
        
        badge = VerifiedBadge(data.get('status', 'unverified'))
        
        version_str = f"v{data.get('version', '0.0.0')}"
        if installed_info:
            version_str = f"Installed: v{installed_info.get('version')}"
            
        version_lbl = QLabel(version_str)
        version_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; background: transparent;")
        
        header.addWidget(name_lbl)
        header.addSpacing(8)
        header.addWidget(badge)
        header.addStretch()
        header.addWidget(version_lbl)
        lay.addLayout(header)
        
        # Description
        desc_lbl = QLabel(data.get('description', ''))
        desc_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 13px; background: transparent;")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)
        
        # Footer
        footer = QHBoxLayout()
        meta_lbl = QLabel(f"by {data.get('author', 'Unknown')} · {data.get('installs', 0):,} installs")
        meta_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; background: transparent;")
        footer.addWidget(meta_lbl)
        footer.addStretch()
        
        # Buttons
        if installed_info:
            enabled = installed_info.get("enabled", True)
            if enabled:
                status_lbl = QLabel("Installed")
                status_lbl.setStyleSheet(f"color: {C['success']}; font-size: 12px; font-weight: bold; background: transparent;")
                
                disable_btn = QPushButton("Disable")
                disable_btn.setStyleSheet(f"background: {C['bg_card_alt']}; color: {C['text_primary']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 4px 12px;")
                disable_btn.clicked.connect(self._on_disable)
                
                footer.addWidget(status_lbl)
                footer.addSpacing(10)
                footer.addWidget(disable_btn)
            else:
                status_lbl = QLabel("Disabled")
                status_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; font-weight: bold; background: transparent;")
                
                enable_btn = QPushButton("Enable")
                enable_btn.setStyleSheet(f"background: {C['bg_card_alt']}; color: {C['text_primary']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 4px 12px;")
                enable_btn.clicked.connect(self._on_enable)
                
                footer.addWidget(status_lbl)
                footer.addSpacing(10)
                footer.addWidget(enable_btn)
        else:
            install_btn = QPushButton("Install")
            install_btn.setStyleSheet(f"background: {C['accent']}; color: white; border: none; border-radius: 6px; padding: 4px 16px; font-weight: bold;")
            install_btn.clicked.connect(self._on_install)
            footer.addWidget(install_btn)
            
        lay.addLayout(footer)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(event)

    def _on_install(self):
        self.action_clicked.emit("install", self.data)
        
    def _on_disable(self):
        self.action_clicked.emit("disable", self.data)
        
    def _on_enable(self):
        self.action_clicked.emit("enable", self.data)


class ExtensionDetailView(QWidget):
    back_clicked = Signal()
    install_clicked = Signal(dict, str) # data, version
    
    def __init__(self):
        super().__init__()
        self.data = None
        self._build_ui()
        
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(16)
        
        # Back button
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet(f"background: transparent; color: {C['accent']}; border: none; font-weight: bold; font-size: 14px; text-align: left;")
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(self.back_clicked.emit)
        lay.addWidget(back_btn)
        
        # Container for content
        content = QWidget()
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(20)
        
        # Header
        h_lay = QHBoxLayout()
        self.name_lbl = QLabel()
        self.name_lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 24px; font-weight: 800; background: transparent;")
        self.badge_lbl = VerifiedBadge("unverified")
        h_lay.addWidget(self.name_lbl)
        h_lay.addSpacing(10)
        h_lay.addWidget(self.badge_lbl)
        h_lay.addStretch()
        c_lay.addLayout(h_lay)
        
        self.meta_lbl = QLabel()
        self.meta_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 13px; background: transparent;")
        c_lay.addWidget(self.meta_lbl)
        
        self.desc_lbl = QLabel()
        self.desc_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 14px; background: transparent;")
        self.desc_lbl.setWordWrap(True)
        c_lay.addWidget(self.desc_lbl)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {C['border']}; border: none; max-height: 1px;")
        c_lay.addWidget(sep)
        
        # Lists
        self.cap_group = self._create_group("CAPABILITIES")
        c_lay.addWidget(self.cap_group)
        
        self.compat_group = self._create_group("COMPATIBILITY")
        c_lay.addWidget(self.compat_group)
        
        self.ver_group = self._create_group("VERSIONS")
        c_lay.addWidget(self.ver_group)
        
        self.change_group = self._create_group("CHANGELOG")
        c_lay.addWidget(self.change_group)
        
        # Footer (Install)
        f_lay = QHBoxLayout()
        f_lay.addStretch()
        self.install_btn = QPushButton()
        self.install_btn.setStyleSheet(f"background: {C['accent']}; color: white; border: none; border-radius: 12px; padding: 12px 32px; font-weight: bold; font-size: 14px;")
        self.install_btn.clicked.connect(self._on_install)
        f_lay.addWidget(self.install_btn)
        
        c_lay.addLayout(f_lay)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(content)
        
        lay.addWidget(scroll)

    def _create_group(self, title: str) -> QWidget:
        w = QWidget()
        w_lay = QVBoxLayout(w)
        w_lay.setContentsMargins(0,0,0,0)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; font-weight: bold; letter-spacing: 1px; background: transparent;")
        w_lay.addWidget(title_lbl)
        
        content_lbl = QLabel()
        content_lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 13px; background: transparent;")
        content_lbl.setWordWrap(True)
        w_lay.addWidget(content_lbl)
        
        w.content_lbl = content_lbl
        return w

    def set_data(self, data: dict):
        self.data = data
        self.name_lbl.setText(data.get('name', ''))
        self.badge_lbl.set_status(data.get('status', 'unverified'))
        self.meta_lbl.setText(f"by {data.get('author', '')}  ·  Updated {data.get('updated', '')}")
        self.desc_lbl.setText(data.get('description', ''))
        
        # Capabilities
        caps = data.get('capabilities', [])
        caps_str = "\n".join([f"✓ {CAPABILITY_LABELS.get(c, c)}" for c in caps])
        self.cap_group.content_lbl.setText(caps_str if caps_str else "None")
        
        # Compatibility
        self.compat_group.content_lbl.setText(data.get('compatibility', 'Unknown'))
        
        # Versions
        vers = data.get('versions', [])
        vers_str = ""
        for i, v in enumerate(vers):
            st = v.get('status', '')
            if st == 'verified':
                badge = "✓ Verified"
            elif st == 'unverified':
                badge = "⚠ Unverified"
            elif st == 'rejected':
                badge = "✕ Rejected"
            else:
                badge = st
                
            rec = " ← recommended" if i == 0 else ""
            vers_str += f"{v.get('version', '')}   {badge}{rec}\n"
            
        self.ver_group.content_lbl.setText(vers_str.strip())
        
        # Changelog
        self.change_group.content_lbl.setText(data.get('changelog', ''))
        
        # Install button
        v = data.get('version', '')
        self.install_btn.setText(f"INSTALL v{v}")

    def _on_install(self):
        if self.data:
            self.install_clicked.emit(self.data, self.data.get('version', ''))


class ExtensionsPage(QWidget):
    """Main Extension Manager Page."""
    
    extension_installed = Signal(str)
    extension_uninstalled = Signal(str)
    extension_enabled = Signal(str)
    extension_disabled = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.extensions = []
        self.current_filter = "All"
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background: {C['bg_base']};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        self.stack = QStackedWidget()
        
        # --- BROWSE VIEW ---
        self.browse_view = QWidget()
        b_lay = QVBoxLayout(self.browse_view)
        b_lay.setContentsMargins(16, 16, 16, 16)
        b_lay.setSpacing(16)
        
        # Search & Refresh
        top_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Search extensions...")
        self.search_edit.textChanged.connect(self._filter_list)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        
        top_bar.addWidget(self.search_edit, 1)
        top_bar.addWidget(self.refresh_btn)
        b_lay.addLayout(top_bar)
        
        # Tabs
        tabs_lay = QHBoxLayout()
        self.tab_btns = []
        for t in ["All", "Installed", "Updates", "✓ Verified Only"]:
            btn = QPushButton(t)
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; color: {C['text_muted']}; font-weight: bold; padding: 4px 12px;
                }}
                QPushButton:checked {{
                    color: {C['accent']}; border-bottom: 2px solid {C['accent']};
                }}
            """)
            btn.clicked.connect(lambda checked, tb=t: self._set_tab(tb))
            self.tab_btns.append(btn)
            tabs_lay.addWidget(btn)
        
        self.tab_btns[0].setChecked(True)
        tabs_lay.addStretch()
        b_lay.addLayout(tabs_lay)
        
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
        b_lay.addWidget(self.cards_scroll, 1)
        
        # Warning box
        warn_box = QFrame()
        warn_box.setStyleSheet(f"background: {C['sidebar_bg']}; border: 1px solid {C['border']}; border-radius: 8px;")
        w_lay = QVBoxLayout(warn_box)
        w_lbl = QLabel("⚠ About Extensions\nExtensions run inside VMT and are not isolated from your system. Only install extensions you trust.\n✓ VERIFIED = reviewed by VMT team, not guaranteed safe")
        w_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; background: transparent;")
        w_lay.addWidget(w_lbl)
        b_lay.addWidget(warn_box)
        
        self.stack.addWidget(self.browse_view)
        
        # --- DETAIL VIEW ---
        self.detail_view = ExtensionDetailView()
        self.detail_view.back_clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.detail_view.install_clicked.connect(self._handle_install)
        self.stack.addWidget(self.detail_view)
        
        root.addWidget(self.stack)

    def refresh(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ Loading...")
        
        self.thread = FetchExtensionsThread()
        self.thread.result.connect(self._on_fetch_success)
        self.thread.error.connect(self._on_fetch_error)
        self.thread.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self.thread.finished.connect(lambda: self.refresh_btn.setText("🔄 Refresh"))
        self.thread.start()

    def _on_fetch_success(self, data: list):
        self.extensions = data
        self._filter_list()

    def _on_fetch_error(self, err: str):
        self.extensions = []
        self._filter_list()
        # Could show error message here

    def _set_tab(self, tab: str):
        self.current_filter = tab
        for btn in self.tab_btns:
            btn.setChecked(btn.text() == tab)
        self._filter_list()

    def _filter_list(self):
        # Clear existing
        while self.cards_lay.count() > 1: # Keep the stretch
            item = self.cards_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        query = self.search_edit.text().lower()
        
        try:
            from extensions.registry import ExtensionRegistry
            registry = ExtensionRegistry()
            registry.load_from_disk()
            installed_dict = {r.id: {"version": r.version, "enabled": r.enabled} for r in registry.list_all()}
        except Exception:
            installed_dict = {}
        
        for ext in self.extensions:
            # Apply search
            if query and query not in ext.get('name', '').lower() and query not in ext.get('description', '').lower():
                continue
                
            # Apply tabs
            is_installed = ext['id'] in installed_dict
            
            if self.current_filter == "Installed" and not is_installed:
                continue
            if self.current_filter == "✓ Verified Only" and ext.get('status') != "verified":
                continue
            if self.current_filter == "Updates":
                if not is_installed:
                    continue
                # Simple version check mock
                if installed_dict[ext['id']]['version'] == ext['version']:
                    continue

            inst_info = installed_dict.get(ext['id'])
            card = ExtensionCard(ext, inst_info)
            card.clicked.connect(self._show_detail)
            card.action_clicked.connect(self._handle_action)
            
            self.cards_lay.insertWidget(self.cards_lay.count() - 1, card)

    def _show_detail(self, data: dict):
        self.detail_view.set_data(data)
        self.stack.setCurrentIndex(1)
        
    def _handle_action(self, action: str, data: dict):
        if action == "install":
            self._handle_install(data, data.get('version'))
        elif action == "disable":
            try:
                from extensions.registry import ExtensionRegistry
                from extensions.loader import ExtensionLoader
                from extensions.lifecycle import ExtensionLifecycle
                registry = ExtensionRegistry()
                registry.load_from_disk()
                loader = ExtensionLoader()
                lifecycle = ExtensionLifecycle(registry, loader, self._get_main_window())
                lifecycle.disable(data['id'])
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to disable: {e}")
            self.extension_disabled.emit(data['id'])
            self._filter_list()
        elif action == "enable":
            try:
                from extensions.registry import ExtensionRegistry
                from extensions.loader import ExtensionLoader
                from extensions.lifecycle import ExtensionLifecycle
                registry = ExtensionRegistry()
                registry.load_from_disk()
                loader = ExtensionLoader()
                lifecycle = ExtensionLifecycle(registry, loader, self._get_main_window())
                lifecycle.enable(data['id'])
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to enable: {e}")
            self.extension_enabled.emit(data['id'])
            self._filter_list()

    def _handle_install(self, data: dict, version: str):
        status = data.get('status', 'unverified')
        caps = data.get('capabilities', [])
        
        if status == 'unverified':
            msg = QMessageBox(self)
            msg.setWindowTitle("Install Unverified Extension")
            msg.setIcon(QMessageBox.Warning)
            
            caps_text = "\n".join([f"  · {CAPABILITY_LABELS.get(c, c)}" for c in caps])
            
            msg.setText(f"<b>⚠ UNVERIFIED EXTENSION</b>")
            msg.setInformativeText(
                f'"{data.get("name")}" has not been reviewed by the VMT team.\n'
                f"Extensions run inside VMT and are not isolated from your system.\n"
                f"Only install extensions you trust.\n\n"
                f"This extension requests:\n{caps_text}"
            )
            install_btn = msg.addButton("INSTALL ANYWAY", QMessageBox.ActionRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
            
            msg.exec()
            if msg.clickedButton() != install_btn:
                return
        else:
            # Verified
            msg = QMessageBox(self)
            msg.setWindowTitle("Install Extension")
            caps_text = "\n".join([f"  · {CAPABILITY_LABELS.get(c, c)}" for c in caps])
            msg.setText(f"Install {data.get('name')} v{version}?")
            if caps_text:
                msg.setInformativeText(f"This extension requests:\n{caps_text}")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            if msg.exec() != QMessageBox.Ok:
                return
                
        # Proceed with install
        try:
            self._do_install(data)
            self.extension_installed.emit(data['id'])
        except Exception as e:
            QMessageBox.critical(self, "Installation Failed", str(e))
        self.stack.setCurrentIndex(0)
        self._filter_list()

    def _get_main_window(self):
        """Walk up the parent widget tree to find MainWindow."""
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "register_extension_page"):
                return parent
            parent = parent.parent()
        return None

    def _do_install(self, ext_data: dict) -> None:
        """Download and install an extension."""
        try:
            from extensions.client import VMTBackendClient
            from extensions.paths import get_download_cache_dir
            from extensions.lifecycle import ExtensionLifecycle
            from extensions.registry import ExtensionRegistry
            from extensions.loader import ExtensionLoader
            import tempfile, os
            from pathlib import Path
            
            client = VMTBackendClient()
            ext_id = ext_data["id"]
            
            package_bytes, sha256 = client.download(ext_id)
            
            cache_dir = get_download_cache_dir()
            package_path = cache_dir / f"{ext_id.replace('.', '_')}.vmte"
            package_path.write_bytes(package_bytes)
            
            registry = ExtensionRegistry()
            registry.load_from_disk()
            loader = ExtensionLoader()
            
            main_window = self._get_main_window()
            lifecycle = ExtensionLifecycle(registry, loader, main_window)
            lifecycle.install(package_path, sha256)
            
            try:
                package_path.unlink()
            except Exception:
                pass
                
        except Exception as e:
            raise RuntimeError(f"Installation failed: {e}")
