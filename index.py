#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          📱  Mobile Build Tool  — macOS GUI                  ║
║   React Native & Flutter → IPA + APK Professional Builder    ║
║   Widget Linking • Auto-Detection • Smart Error Parsing      ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
import subprocess

def ensure_dependencies():
    """Install required packages if missing."""
    packages = ["customtkinter"]
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg,
                                   "--break-system-packages", "--quiet"])

ensure_dependencies()

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import json
import re
import shutil
import datetime
import plistlib
import uuid
import queue
import traceback
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
#  Theme & Constants
# ─────────────────────────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg_primary":    "#0d0d1a",
    "bg_secondary":  "#12122a",
    "bg_panel":      "#1a1a2e",
    "bg_card":       "#1e2035",
    "bg_input":      "#252545",
    "accent_blue":   "#00d4ff",
    "accent_green":  "#00e676",
    "accent_purple": "#b39ddb",
    "accent_red":    "#ff5370",
    "accent_orange": "#ffcc02",
    "btn_primary":   "#2563eb",
    "btn_danger":    "#dc2626",
    "btn_success":   "#059669",
    "btn_purple":    "#7c3aed",
    "btn_teal":      "#0f766e",
    "btn_gray":      "#374151",
    "text_primary":  "#e2e8f0",
    "text_muted":    "#6b7280",
    "text_dim":      "#4b5563",
    "border":        "#2a2a4a",
    "log_bg":        "#080818",
    "log_error":     "#ff5370",
    "log_warning":   "#fbbf24",
    "log_success":   "#34d399",
    "log_info":      "#60a5fa",
    "log_path":      "#c084fc",
    "log_header":    "#00d4ff",
    "log_dim":       "#6b7280",
}

FONT_UI    = ("SF Pro Display", 13)
FONT_UI_SM = ("SF Pro Display", 11)
FONT_MONO  = ("Menlo", 12)
FONT_MONO_SM = ("Menlo", 11)
FONT_TITLE = ("SF Pro Display", 20, "bold")
FONT_SECTION = ("SF Pro Display", 12, "bold")
FONT_BTN   = ("SF Pro Display", 13, "bold")


# ─────────────────────────────────────────────────────────────────────────────
#  Utility Functions
# ─────────────────────────────────────────────────────────────────────────────

def find_tool(tool_name: str) -> str | None:
    """Locate a CLI tool in PATH or common install locations."""
    found = shutil.which(tool_name)
    if found:
        return found
    common = [
        f"/usr/local/bin/{tool_name}",
        f"/opt/homebrew/bin/{tool_name}",
        f"{Path.home()}/flutter/bin/{tool_name}",
        f"{Path.home()}/development/flutter/bin/{tool_name}",
        f"{Path.home()}/.pub-cache/bin/{tool_name}",
        f"/usr/bin/{tool_name}",
    ]
    for p in common:
        if os.path.exists(p):
            return p
    return None


def safe_filename(name: str) -> str:
    """Strip characters unsafe for filenames."""
    return re.sub(r"[^\w\-]", "_", name)


def gen_uuid() -> str:
    """Generate a 24-char uppercase hex UUID (Xcode pbxproj style)."""
    return uuid.uuid4().hex[:24].upper()


def parse_error_location(line: str) -> str | None:
    """Extract file path + line number from a compiler error string."""
    patterns = [
        r"(/[\w/.\-]+\.\w+):(\d+):(\d+)",
        r"(/[\w/.\-]+\.\w+):(\d+)",
        r"([A-Za-z_][\w]+\.(?:dart|swift|kt|java|m|h|js|ts|tsx)):(\d+):(\d+)",
        r"([A-Za-z_][\w]+\.(?:dart|swift|kt|java|m|h|js|ts|tsx)):(\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, line)
        if m:
            g = m.groups()
            if len(g) == 3:
                return f"{g[0]}  ›  line {g[1]}, col {g[2]}"
            return f"{g[0]}  ›  line {g[1]}"
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Main Application Window
# ─────────────────────────────────────────────────────────────────────────────

class MobileBuildTool(ctk.CTk):

    def __init__(self):
        super().__init__()

        # ── Window config ──────────────────────────────────────────────────
        self.title("📱  Mobile Build Tool")
        self.geometry("1280x820")
        self.minsize(900, 640)
        self.configure(fg_color=COLORS["bg_primary"])

        # ── State ──────────────────────────────────────────────────────────
        self.project_path   = tk.StringVar()
        self.project_type   = tk.StringVar(value="—")
        self.app_name       = tk.StringVar()
        self.app_version    = tk.StringVar(value="1.0.0")
        self.build_target   = tk.StringVar(value="both")
        self.output_dir     = tk.StringVar()
        self.widget_path    = tk.StringVar()

        self.clean_build    = tk.BooleanVar(value=True)
        self.verbose_mode   = tk.BooleanVar(value=False)
        self.release_mode   = tk.BooleanVar(value=True)

        self.building       = False
        self.current_proc   = None
        self.all_logs: list[tuple[str, str | None]] = []
        self.error_logs: list[str] = []
        self.log_queue: queue.Queue = queue.Queue()
        self.build_start_time: datetime.datetime | None = None

        # ── Layout ─────────────────────────────────────────────────────────
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._build_statusbar()

        # ── Queue polling ─────────────────────────────────────────────────
        self.after(60, self._poll_log_queue)

    # ══════════════════════════════════════════════════════════════════════
    # UI Construction
    # ══════════════════════════════════════════════════════════════════════

    def _build_header(self):
        hdr = ctk.CTkFrame(self, height=56, fg_color=COLORS["bg_secondary"],
                           corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)

        ctk.CTkLabel(hdr, text="📱  Mobile Build Tool",
                     font=ctk.CTkFont(family="SF Pro Display", size=20, weight="bold"),
                     text_color=COLORS["accent_blue"]).grid(
            row=0, column=0, padx=20, pady=10, sticky="w")

        ctk.CTkLabel(hdr, text="React Native & Flutter  ›  IPA + APK Builder  ›  Widget Linker",
                     font=ctk.CTkFont(family="SF Pro Display", size=12),
                     text_color=COLORS["text_muted"]).grid(
            row=0, column=1, padx=20, pady=10, sticky="e")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3, minsize=360)
        body.grid_columnconfigure(1, weight=5)

        self._build_left_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent):
        scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color=COLORS["bg_panel"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
            scrollbar_button_color=COLORS["bg_card"],
            scrollbar_button_hover_color=COLORS["btn_gray"],
            label_text="  ⚙️   Settings",
            label_font=ctk.CTkFont(family="SF Pro Display", size=14, weight="bold"),
            label_fg_color=COLORS["bg_card"],
            label_text_color=COLORS["accent_blue"],
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        scroll.grid_columnconfigure(0, weight=1)
        self._left = scroll
        self._left_row = 0

        # ── Project location ──────────────────────────────────────────────
        self._section("📁  Project Location")

        path_row = self._card_frame()
        path_row.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(
            path_row, textvariable=self.project_path,
            placeholder_text="Select or paste project folder…",
            font=ctk.CTkFont(family="Menlo", size=11),
            fg_color=COLORS["bg_input"], border_color=COLORS["border"], height=34)
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=10)
        ctk.CTkButton(path_row, text="Browse", width=78, height=34,
                      command=self._browse_project,
                      fg_color=COLORS["btn_primary"], hover_color="#1d4ed8",
                      font=ctk.CTkFont(size=12)).grid(row=0, column=1, padx=(0, 10), pady=10)

        self._btn("🔍  Auto-Detect Project",
                  self._detect_project, COLORS["btn_success"], "#047857",
                  font=ctk.CTkFont(size=13, weight="bold"), height=40)

        # ── Project info ──────────────────────────────────────────────────
        self._section("📊  Project Info")
        info = self._card_frame()
        info.grid_columnconfigure(1, weight=1)

        labels = [("Type",    self.project_type, True),
                  ("App Name", None,             False),
                  ("Version",  None,             False)]

        for i, (lbl, var, is_label) in enumerate(labels):
            ctk.CTkLabel(info, text=f"{lbl}:", font=ctk.CTkFont(size=11),
                         text_color=COLORS["text_muted"]).grid(
                row=i, column=0, padx=(12, 6), pady=6, sticky="w")
            if is_label:
                ctk.CTkLabel(info, textvariable=var,
                             font=ctk.CTkFont(size=12, weight="bold"),
                             text_color=COLORS["accent_blue"]).grid(
                    row=i, column=1, padx=(0, 12), pady=6, sticky="w")
            else:
                sv = self.app_name if lbl == "App Name" else self.app_version
                ctk.CTkEntry(info, textvariable=sv,
                             font=ctk.CTkFont(size=12),
                             fg_color=COLORS["bg_input"],
                             border_color=COLORS["border"],
                             height=30).grid(
                    row=i, column=1, padx=(0, 12), pady=6, sticky="ew")

        # ── Build target ──────────────────────────────────────────────────
        self._section("🎯  Build Target")
        tgt = self._card_frame()
        for i, (text, value) in enumerate([
            ("🍎  iOS  ( IPA )",    "ios"),
            ("🤖  Android  ( APK )", "android"),
            ("📦  Both",            "both"),
        ]):
            ctk.CTkRadioButton(tgt, text=text,
                               variable=self.build_target, value=value,
                               font=ctk.CTkFont(size=12),
                               fg_color=COLORS["btn_primary"]).grid(
                row=i, column=0, padx=14, pady=5, sticky="w")

        # ── Build options ─────────────────────────────────────────────────
        self._section("🔧  Build Options")
        opts = self._card_frame()
        for i, (text, var, default) in enumerate([
            ("Clean before build",  self.clean_build,   True),
            ("Release mode",        self.release_mode,  True),
            ("Verbose output",      self.verbose_mode,  False),
        ]):
            cb = ctk.CTkCheckBox(opts, text=text, variable=var,
                                 font=ctk.CTkFont(size=12),
                                 fg_color=COLORS["btn_primary"])
            cb.grid(row=i, column=0, padx=14, pady=5, sticky="w")
            if default:
                cb.select()

        # ── Output directory ──────────────────────────────────────────────
        self._section("📤  Output Directory")
        out_card = self._card_frame()
        out_card.grid_columnconfigure(0, weight=1)
        self.out_entry = ctk.CTkEntry(
            out_card, textvariable=self.output_dir,
            placeholder_text="<project>/builds  (default)",
            font=ctk.CTkFont(family="Menlo", size=11),
            fg_color=COLORS["bg_input"], border_color=COLORS["border"], height=32)
        self.out_entry.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=10)
        ctk.CTkButton(out_card, text="Browse", width=78, height=32,
                      command=self._browse_output,
                      fg_color=COLORS["btn_gray"], hover_color="#4b5563",
                      font=ctk.CTkFont(size=12)).grid(row=0, column=1, padx=(0, 10), pady=10)

        # ── Widget linking ────────────────────────────────────────────────
        self._section("🔗  Widget Linking  ( iOS )")
        wcard = self._card_frame()
        wcard.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(wcard, text="Widget Extension Folder:",
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_muted"]).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(10, 2), sticky="w")

        wrow = ctk.CTkFrame(wcard, fg_color="transparent")
        wrow.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 6))
        wrow.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(wrow, textvariable=self.widget_path,
                     placeholder_text="Auto-detected or browse…",
                     font=ctk.CTkFont(family="Menlo", size=11),
                     fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                     height=32).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(wrow, text="Browse", width=70, height=32,
                      command=self._browse_widget,
                      fg_color=COLORS["btn_gray"], hover_color="#4b5563",
                      font=ctk.CTkFont(size=12)).grid(row=0, column=1)

        ctk.CTkButton(wcard, text="🔗  Link Widget to Xcode Project",
                      command=self._link_widget,
                      fg_color=COLORS["btn_purple"], hover_color="#6d28d9",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      height=38).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 4))

        ctk.CTkButton(wcard, text="✅  Verify Widget Link Status",
                      command=self._verify_widget_link,
                      fg_color=COLORS["btn_teal"], hover_color="#0d6966",
                      font=ctk.CTkFont(size=12), height=36).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))

        # ── Action buttons ────────────────────────────────────────────────
        self._section("🚀  Actions")
        self.build_btn = self._btn(
            "🚀  Start Build", self._start_build,
            COLORS["btn_danger"], "#b91c1c",
            font=ctk.CTkFont(size=15, weight="bold"), height=50)

        self.stop_btn = self._btn(
            "⏹  Stop Build", self._stop_build,
            COLORS["btn_gray"], "#4b5563",
            font=ctk.CTkFont(size=13), height=38, state="disabled")

        self._btn("📂  Open Output Folder", self._open_output_folder,
                  COLORS["btn_gray"], "#4b5563",
                  font=ctk.CTkFont(size=12), height=36)

        # ── Progress ──────────────────────────────────────────────────────
        self.progress_label = ctk.CTkLabel(
            self._left, text="Ready  •  No project loaded",
            font=ctk.CTkFont(family="Menlo", size=11),
            text_color=COLORS["text_muted"])
        self.progress_label.grid(row=self._left_row, column=0,
                                  pady=(12, 4), padx=12, sticky="w")
        self._left_row += 1

        self.progress_bar = ctk.CTkProgressBar(
            self._left, height=6,
            progress_color=COLORS["accent_blue"],
            fg_color=COLORS["bg_card"])
        self.progress_bar.grid(row=self._left_row, column=0,
                                sticky="ew", padx=12, pady=(0, 16))
        self.progress_bar.set(0)
        self._left_row += 1

    # ── Right panel — log output ──────────────────────────────────────────
    def _build_right_panel(self, parent):
        right = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"],
                             corner_radius=12,
                             border_width=1, border_color=COLORS["border"])
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # ── Log toolbar ───────────────────────────────────────────────────
        toolbar = ctk.CTkFrame(right, fg_color=COLORS["bg_card"],
                               height=46, corner_radius=0)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.grid_propagate(False)

        ctk.CTkLabel(toolbar, text="📋  Build Output",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS["accent_blue"]).grid(
            row=0, column=0, padx=16, pady=10, sticky="w")

        tab_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        tab_frame.grid(row=0, column=1, padx=10, pady=6, sticky="e")

        for text, cb in [
            ("All",      lambda: self._filter_logs("all")),
            ("Errors",   lambda: self._filter_logs("errors")),
            ("Summary",  lambda: self._filter_logs("summary")),
        ]:
            ctk.CTkButton(tab_frame, text=text, width=65, height=28,
                          command=cb,
                          fg_color=COLORS["btn_gray"], hover_color="#4b5563",
                          font=ctk.CTkFont(size=11)).pack(side="left", padx=2)

        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=10, pady=6, sticky="e")

        ctk.CTkButton(btn_frame, text="📋 Copy All", width=92, height=28,
                      command=self._copy_all_logs,
                      fg_color="#1d4ed8", hover_color="#1e40af",
                      font=ctk.CTkFont(size=11)).pack(side="left", padx=2)

        ctk.CTkButton(btn_frame, text="🔴 Copy Errors", width=102, height=28,
                      command=self._copy_error_logs,
                      fg_color="#7f1d1d", hover_color="#991b1b",
                      font=ctk.CTkFont(size=11)).pack(side="left", padx=2)

        ctk.CTkButton(btn_frame, text="🗑 Clear", width=68, height=28,
                      command=self._clear_logs,
                      fg_color=COLORS["btn_gray"], hover_color="#4b5563",
                      font=ctk.CTkFont(size=11)).pack(side="left", padx=2)

        # ── Text widget ───────────────────────────────────────────────────
        self.log_text = tk.Text(
            right,
            bg=COLORS["log_bg"], fg=COLORS["text_primary"],
            font=FONT_MONO,
            wrap=tk.NONE,
            insertbackground="white",
            selectbackground="#1d4ed8",
            selectforeground="#ffffff",
            padx=14, pady=12,
            borderwidth=0, relief="flat",
            state="disabled",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")

        v_scroll = ctk.CTkScrollbar(right, command=self.log_text.yview,
                                     button_color=COLORS["bg_card"],
                                     button_hover_color=COLORS["btn_gray"])
        v_scroll.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=v_scroll.set)

        h_scroll = ctk.CTkScrollbar(right, orientation="horizontal",
                                     command=self.log_text.xview,
                                     button_color=COLORS["bg_card"],
                                     button_hover_color=COLORS["btn_gray"])
        h_scroll.grid(row=2, column=0, sticky="ew", columnspan=2)
        self.log_text.configure(xscrollcommand=h_scroll.set)

        # Colour tags
        self.log_text.tag_configure("error",   foreground=COLORS["log_error"])
        self.log_text.tag_configure("warning", foreground=COLORS["log_warning"])
        self.log_text.tag_configure("success", foreground=COLORS["log_success"])
        self.log_text.tag_configure("info",    foreground=COLORS["log_info"])
        self.log_text.tag_configure("path",    foreground=COLORS["log_path"])
        self.log_text.tag_configure("header",  foreground=COLORS["log_header"],
                                               font=("Menlo", 12, "bold"))
        self.log_text.tag_configure("dim",     foreground=COLORS["log_dim"])
        self.log_text.tag_configure("bold_err", foreground=COLORS["log_error"],
                                                font=("Menlo", 12, "bold"))

    def _build_statusbar(self):
        sb = ctk.CTkFrame(self, height=26, fg_color=COLORS["bg_secondary"],
                          corner_radius=0)
        sb.grid(row=2, column=0, sticky="ew")
        sb.grid_columnconfigure(1, weight=1)
        sb.grid_propagate(False)

        self.status_var = tk.StringVar(value="Ready  •  No project loaded")
        ctk.CTkLabel(sb, textvariable=self.status_var,
                     font=ctk.CTkFont(family="Menlo", size=11),
                     text_color=COLORS["text_muted"]).grid(
            row=0, column=0, padx=14, sticky="w")

        self.elapsed_var = tk.StringVar(value="")
        ctk.CTkLabel(sb, textvariable=self.elapsed_var,
                     font=ctk.CTkFont(family="Menlo", size=11),
                     text_color=COLORS["text_muted"]).grid(
            row=0, column=2, padx=14, sticky="e")

    # ── UI helpers ────────────────────────────────────────────────────────

    def _section(self, text: str) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(self._left, text=text,
                           font=ctk.CTkFont(size=12, weight="bold"),
                           text_color=COLORS["text_primary"])
        lbl.grid(row=self._left_row, column=0, sticky="w",
                 padx=4, pady=(14, 3))
        self._left_row += 1
        return lbl

    def _card_frame(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self._left, fg_color=COLORS["bg_card"],
                         corner_radius=8,
                         border_width=1, border_color=COLORS["border"])
        f.grid(row=self._left_row, column=0, sticky="ew", pady=(0, 6))
        self._left_row += 1
        return f

    def _btn(self, text: str, cmd, fg: str, hover: str,
             font=None, height=38, state="normal") -> ctk.CTkButton:
        b = ctk.CTkButton(self._left, text=text, command=cmd,
                          fg_color=fg, hover_color=hover,
                          font=font or ctk.CTkFont(size=12),
                          height=height, state=state)
        b.grid(row=self._left_row, column=0, sticky="ew",
               padx=0, pady=(0, 5))
        self._left_row += 1
        return b

    # ══════════════════════════════════════════════════════════════════════
    # Project Detection
    # ══════════════════════════════════════════════════════════════════════

    def _browse_project(self):
        p = filedialog.askdirectory(title="Select Project Root Folder")
        if p:
            self.project_path.set(p)
            self._detect_project()

    def _browse_output(self):
        p = filedialog.askdirectory(title="Select Output Folder")
        if p:
            self.output_dir.set(p)

    def _browse_widget(self):
        p = filedialog.askdirectory(title="Select Widget Extension Folder")
        if p:
            self.widget_path.set(p)

    def _detect_project(self):
        path = self.project_path.get().strip()
        if not path:
            self._log("🔍  No path given — scanning common locations…\n", "info")
            path = self._auto_find_project()
            if path:
                self.project_path.set(path)
                self._log(f"   Found: {path}\n", "success")
            else:
                self._log("❌  No project found. Please select a folder.\n", "error")
                return

        if not os.path.exists(path):
            self._log(f"❌  Path does not exist: {path}\n", "error")
            return

        self._log(f"\n🔍  Scanning project…\n   {path}\n", "info")

        ptype = self._detect_type(path)
        self.project_type.set(ptype)

        if ptype == "Flutter":
            self._load_flutter_meta(path)
        elif ptype == "React Native":
            self._load_rn_meta(path)
        else:
            self._log("⚠️   Cannot determine project type.\n"
                      "    Verify you selected the project root.\n", "warning")
            return

        self._log(f"✅  Detected: {ptype}  •  "
                  f"{self.app_name.get()} v{self.app_version.get()}\n", "success")
        self._detect_widget(path)
        self.status_var.set(f"{ptype}  •  {Path(path).name}")
        self._set_progress(0, "Project loaded")

    def _auto_find_project(self) -> str | None:
        for search in [
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Developer",
            Path.home() / "Projects",
        ]:
            if not search.exists():
                continue
            for item in search.iterdir():
                if item.is_dir() and self._detect_type(str(item)) != "Unknown":
                    return str(item)
        return None

    def _detect_type(self, path: str) -> str:
        p = Path(path)
        if (p / "pubspec.yaml").exists():
            return "Flutter"
        pkg = p / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text())
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "react-native" in deps:
                    return "React Native"
            except Exception:
                pass
        return "Unknown"

    def _load_flutter_meta(self, path: str):
        try:
            text = (Path(path) / "pubspec.yaml").read_text()
            nm = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
            vr = re.search(r"^version:\s*(.+)$", text, re.MULTILINE)
            if nm:
                self.app_name.set(nm.group(1).strip())
            if vr:
                self.app_version.set(vr.group(1).strip().split("+")[0])
        except Exception as e:
            self._log(f"⚠️   pubspec.yaml read error: {e}\n", "warning")

    def _load_rn_meta(self, path: str):
        try:
            data = json.loads((Path(path) / "package.json").read_text())
            self.app_name.set(data.get("name", "app"))
            self.app_version.set(data.get("version", "1.0.0"))
        except Exception as e:
            self._log(f"⚠️   package.json read error: {e}\n", "warning")

    def _detect_widget(self, path: str):
        """Scan iOS folder for widget extensions."""
        ios_dir = Path(path) / "ios"
        roots = [ios_dir, Path(path)]
        keywords = ["widget", "extension", "kit"]
        for root in roots:
            if not root.exists():
                continue
            for item in root.iterdir():
                if item.is_dir() and any(k in item.name.lower() for k in keywords):
                    self.widget_path.set(str(item))
                    self._log(f"🔗  Widget found: {item.name}\n", "info")
                    return

    # ══════════════════════════════════════════════════════════════════════
    # Build Orchestration
    # ══════════════════════════════════════════════════════════════════════

    def _start_build(self):
        if self.building:
            return

        path = self.project_path.get().strip()
        if not path:
            messagebox.showerror("No Project", "Select a project folder first.")
            return

        ptype = self.project_type.get()
        if ptype == "—":
            self._detect_project()
            ptype = self.project_type.get()
        if ptype == "Unknown" or ptype == "—":
            messagebox.showerror("Unknown Type", "Could not detect Flutter or React Native project.")
            return

        self.building = True
        self.error_logs.clear()
        self.build_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.build_start_time = datetime.datetime.now()
        self._set_progress(0, "Starting…")

        target = self.build_target.get()

        self._log("\n" + "═" * 62 + "\n", "header")
        self._log(f"  🚀  BUILD STARTED\n", "header")
        self._log(f"  Project  :  {self.app_name.get() or Path(path).name}\n", "info")
        self._log(f"  Type     :  {ptype}\n", "info")
        self._log(f"  Target   :  {target.upper()}\n", "info")
        self._log(f"  Mode     :  {'Release' if self.release_mode.get() else 'Debug'}\n", "info")
        self._log(f"  Time     :  {self.build_start_time.strftime('%Y-%m-%d  %H:%M:%S')}\n", "info")
        self._log("═" * 62 + "\n\n", "header")

        t = threading.Thread(
            target=self._run_build,
            args=(path, ptype, target),
            daemon=True
        )
        t.start()
        self._tick_elapsed()

    def _run_build(self, path: str, ptype: str, target: str):
        try:
            if ptype == "Flutter":
                self._build_flutter(path, target)
            elif ptype == "React Native":
                self._build_rn(path, target)
        except Exception as e:
            self._queue("❌  Unexpected exception:\n", "error")
            self._queue(traceback.format_exc(), "error")
        finally:
            self.after(0, self._on_build_done)

    # ── Flutter build ─────────────────────────────────────────────────────

    def _build_flutter(self, path: str, target: str):
        flutter = find_tool("flutter")
        if not flutter:
            self._queue("❌  flutter not found in PATH.\n"
                        "   Install Flutter SDK:  https://flutter.dev/docs/get-started/install\n",
                        "error")
            return

        app  = self.app_name.get() or Path(path).name
        ver  = self.app_version.get() or "1.0.0"
        mode = "release" if self.release_mode.get() else "debug"

        step = 1
        total = 2 + (target == "both")

        # ── Clean ──────────────────────────────────────────────────────────
        if self.clean_build.get():
            self._queue(f"\n📦  [{step}/{total+1}]  Cleaning & fetching packages…\n", "header")
            self._set_progress(0.05, "flutter clean…")
            self._run_cmd([flutter, "clean"], path)
            self._set_progress(0.10, "flutter pub get…")
            self._run_cmd([flutter, "pub", "get"], path)
            step += 1

        # ── iOS ────────────────────────────────────────────────────────────
        if target in ("ios", "both"):
            self._queue(f"\n🍎  [{step}/{total+1}]  Building iOS…\n", "header")
            self._set_progress(0.20, "Building iOS…")
            cmd = ([flutter, "build", "ipa", "--release", "--no-codesign"]
                   if mode == "release"
                   else [flutter, "build", "ios", "--debug", "--no-codesign", "--simulator"])
            if self.verbose_mode.get():
                cmd.append("--verbose")
            ok = self._run_cmd(cmd, path)
            if ok:
                self._collect_ipa(path, app, ver, mode)
            else:
                self._queue("❌  iOS build failed.\n", "error")
            step += 1
            self._set_progress(0.55, "iOS done")

        # ── Android ───────────────────────────────────────────────────────
        if target in ("android", "both"):
            self._queue(f"\n🤖  [{step}/{total+1}]  Building Android…\n", "header")
            self._set_progress(0.60, "Building Android…")
            cmd = [flutter, "build", "apk", f"--{mode}"]
            if self.verbose_mode.get():
                cmd.append("--verbose")
            ok = self._run_cmd(cmd, path)
            if ok:
                self._collect_apk(path, app, ver, mode)
            else:
                self._queue("❌  Android build failed.\n", "error")

        self._set_progress(1.0, "Build complete")

    # ── React Native build ────────────────────────────────────────────────

    def _build_rn(self, path: str, target: str):
        app  = self.app_name.get() or Path(path).name
        ver  = self.app_version.get() or "1.0.0"
        mode = "Release" if self.release_mode.get() else "Debug"

        # ── Install deps ───────────────────────────────────────────────────
        if self.clean_build.get():
            self._queue(f"\n📦  Installing JS dependencies…\n", "header")
            self._set_progress(0.05, "npm/yarn install…")
            if (Path(path) / "yarn.lock").exists():
                self._run_cmd(["yarn", "install", "--frozen-lockfile"], path)
            else:
                self._run_cmd(["npm", "ci", "--prefer-offline"], path)

        # ── iOS ────────────────────────────────────────────────────────────
        if target in ("ios", "both"):
            self._queue(f"\n🍎  Building React Native iOS…\n", "header")
            self._set_progress(0.20, "Building iOS…")
            self._build_rn_ios(path, app, ver, mode)
            self._set_progress(0.55, "iOS done")

        # ── Android ───────────────────────────────────────────────────────
        if target in ("android", "both"):
            self._queue(f"\n🤖  Building React Native Android…\n", "header")
            self._set_progress(0.60, "Building Android…")
            self._build_rn_android(path, app, ver, mode)

        self._set_progress(1.0, "Build complete")

    def _build_rn_ios(self, path: str, app: str, ver: str, mode: str):
        ios = Path(path) / "ios"
        if not ios.exists():
            self._queue("❌  ios/ folder not found.\n", "error")
            return

        workspace = next((f for f in ios.iterdir() if f.suffix == ".xcworkspace"), None)
        xcodeproj = next((f for f in ios.iterdir() if f.suffix == ".xcodeproj"), None)

        if not workspace and not xcodeproj:
            self._queue("❌  No .xcworkspace or .xcodeproj found.\n", "error")
            return

        # Pod install
        if workspace:
            pod = find_tool("pod")
            if pod:
                self._queue("  📦  pod install…\n", "info")
                self._run_cmd([pod, "install", "--repo-update"], str(ios))

        target_file = workspace or xcodeproj
        flag        = "-workspace" if workspace else "-project"
        scheme      = self._xcode_scheme(str(ios), target_file.stem.replace(".xcworkspace","").replace(".xcodeproj",""))
        archive     = str(ios / f"{safe_filename(app)}.xcarchive")

        xc_cmd = [
            "xcodebuild",
            flag, str(target_file),
            "-scheme", scheme,
            "-configuration", mode,
            "-sdk", "iphoneos" if mode == "Release" else "iphonesimulator",
            "-archivePath", archive,
            "archive",
            "CODE_SIGN_IDENTITY=-",
            "CODE_SIGNING_REQUIRED=NO",
            "CODE_SIGNING_ALLOWED=NO",
        ]
        if not self.verbose_mode.get():
            xc_cmd += ["-quiet"]

        ok = self._run_cmd(xc_cmd, str(ios))
        if ok and os.path.exists(archive):
            self._export_ipa_archive(path, archive, app, ver, mode.lower())
        elif ok:
            self._collect_ipa(path, app, ver, mode.lower())

    def _export_ipa_archive(self, project_path: str, archive_path: str,
                             app: str, ver: str, mode: str):
        """Export IPA from .xcarchive using xcodebuild -exportArchive."""
        ios_path    = Path(project_path) / "ios"
        export_dir  = ios_path / "build" / "Export"
        export_dir.mkdir(parents=True, exist_ok=True)
        plist_path  = ios_path / "_ExportOptions.plist"

        plist_data = {
            "method":          "development",
            "compileBitcode":  False,
            "signingStyle":    "manual",
        }
        with open(str(plist_path), "wb") as fh:
            plistlib.dump(plist_data, fh)

        cmd = [
            "xcodebuild", "-exportArchive",
            "-archivePath", archive_path,
            "-exportPath",  str(export_dir),
            "-exportOptionsPlist", str(plist_path),
            "CODE_SIGN_IDENTITY=-",
            "CODE_SIGNING_REQUIRED=NO",
        ]
        ok = self._run_cmd(cmd, str(ios_path))
        if ok:
            self._collect_ipa(project_path, app, ver, mode)

    def _build_rn_android(self, path: str, app: str, ver: str, mode: str):
        android = Path(path) / "android"
        if not android.exists():
            self._queue("❌  android/ folder not found.\n", "error")
            return

        gradlew = android / "gradlew"
        gradle_cmd = str(gradlew) if gradlew.exists() else find_tool("gradle") or "gradle"
        if gradlew.exists():
            os.chmod(str(gradlew), 0o755)

        task = f"assemble{mode}"
        ok = self._run_cmd([gradle_cmd, task, "--no-daemon"], str(android))
        if ok:
            self._collect_apk(path, app, ver, mode.lower())
        else:
            self._queue("❌  Android Gradle build failed.\n", "error")

    # ── Output file collection ────────────────────────────────────────────

    def _output_folder(self, project_path: str) -> str:
        folder = self.output_dir.get() or str(Path(project_path) / "builds")
        os.makedirs(folder, exist_ok=True)
        return folder

    def _build_filename(self, app: str, ver: str, mode: str, ext: str) -> str:
        date = datetime.date.today().strftime("%Y%m%d")
        return f"{safe_filename(app)}_{ver}_{mode}_{date}.{ext}"

    def _collect_ipa(self, project_path: str, app: str, ver: str, mode: str):
        ipa_files = sorted(Path(project_path).rglob("*.ipa"),
                           key=lambda f: f.stat().st_mtime, reverse=True)
        if not ipa_files:
            self._queue("⚠️   No .ipa found after build.\n", "warning")
            return
        src = ipa_files[0]
        dst = Path(self._output_folder(project_path)) / \
              self._build_filename(app, ver, mode, "ipa")
        dst.unlink(missing_ok=True)
        shutil.copy2(str(src), str(dst))
        self._announce_output(dst, "🍎  IPA")

    def _collect_apk(self, project_path: str, app: str, ver: str, mode: str):
        apk_files = [f for f in Path(project_path).rglob("*.apk")
                     if "test" not in f.name.lower() and "androidTest" not in str(f)]
        apk_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        if not apk_files:
            self._queue("⚠️   No .apk found after build.\n", "warning")
            return
        src = apk_files[0]
        dst = Path(self._output_folder(project_path)) / \
              self._build_filename(app, ver, mode, "apk")
        dst.unlink(missing_ok=True)
        shutil.copy2(str(src), str(dst))
        self._announce_output(dst, "🤖  APK")

    def _announce_output(self, path: Path, label: str):
        size = path.stat().st_size / 1_048_576
        self._queue(f"\n✅  {label} ready:\n", "success")
        self._queue(f"   📁  {path}\n", "path")
        self._queue(f"   📦  {size:.1f} MB\n", "info")

    # ── Xcode helpers ─────────────────────────────────────────────────────

    def _xcode_scheme(self, ios_path: str, default: str) -> str:
        try:
            r = subprocess.run(["xcodebuild", "-list"],
                               cwd=ios_path, capture_output=True, text=True, timeout=20)
            in_schemes = False
            for line in r.stdout.splitlines():
                if "Schemes:" in line:
                    in_schemes = True
                    continue
                if in_schemes:
                    s = line.strip()
                    if s:
                        return s
                    break
        except Exception:
            pass
        return default

    # ── Command runner ────────────────────────────────────────────────────

    def _run_cmd(self, cmd: list[str], cwd: str) -> bool:
        """Run a subprocess, stream output to the log, return success."""
        self._queue(f"  $ {' '.join(str(c) for c in cmd)}\n", "dim")
        env = os.environ.copy()
        env["PATH"] = (
            "/usr/local/bin:/opt/homebrew/bin:"
            f"{Path.home()}/flutter/bin:"
            f"{Path.home()}/.pub-cache/bin:"
            + env.get("PATH", "")
        )
        try:
            self.current_proc = subprocess.Popen(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            for raw_line in self.current_proc.stdout:
                if not self.building:
                    self.current_proc.terminate()
                    break
                self._classify_line(raw_line)
            self.current_proc.wait()
            ok = self.current_proc.returncode == 0
            if not ok:
                self._queue(
                    f"  ⚠️   Exit code {self.current_proc.returncode}\n", "warning")
            return ok
        except FileNotFoundError:
            self._queue(
                f"  ❌  Not found: {cmd[0]}\n"
                f"  💡  Install it or add it to PATH.\n", "error")
            return False
        except Exception as e:
            self._queue(f"  ❌  {e}\n", "error")
            return False

    def _classify_line(self, line: str):
        ll = line.lower()
        if any(x in ll for x in ("error:", "build failed", "exception", "fatal error")):
            self._queue(line, "error")
            loc = parse_error_location(line)
            if loc:
                self._queue(f"  🗺️   {loc}\n", "path")
            self.error_logs.append(line)
        elif any(x in ll for x in ("warning:", " warn ")):
            self._queue(line, "warning")
        elif any(x in ll for x in ("build succeeded", "archive succeeded",
                                    "✓", "compiled", "built to")):
            self._queue(line, "success")
        elif any(x in ll for x in ("note:", "info:")):
            self._queue(line, "dim")
        else:
            self._queue(line, None)

    def _stop_build(self):
        self.building = False
        if self.current_proc:
            try:
                self.current_proc.terminate()
            except Exception:
                pass
        self._log("\n⏹  Build stopped by user.\n", "warning")

    def _on_build_done(self):
        self.building = False
        self.build_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        elapsed = ""
        if self.build_start_time:
            sec = int((datetime.datetime.now() - self.build_start_time).total_seconds())
            elapsed = f"  •  {sec // 60}m {sec % 60}s"
        if self.error_logs:
            self._log(f"\n⚠️   Finished with {len(self.error_logs)} error(s){elapsed}\n",
                      "warning")
        else:
            self._log(f"\n🎉  Build succeeded{elapsed}\n", "success")
        self._log("═" * 62 + "\n", "header")
        self.status_var.set(
            f"Done{elapsed}  •  "
            f"{'⚠️ errors' if self.error_logs else '✅ clean'}"
            f"  •  {datetime.datetime.now().strftime('%H:%M:%S')}")
        self.elapsed_var.set("")

    def _tick_elapsed(self):
        if not self.building:
            return
        if self.build_start_time:
            sec = int((datetime.datetime.now() - self.build_start_time).total_seconds())
            self.elapsed_var.set(f"⏱  {sec // 60}m {sec % 60}s")
        self.after(1000, self._tick_elapsed)

    # ══════════════════════════════════════════════════════════════════════
    # Widget Linking
    # ══════════════════════════════════════════════════════════════════════

    def _link_widget(self):
        project_path = self.project_path.get().strip()
        if not project_path:
            messagebox.showerror("Error", "No project selected.")
            return

        self._log("\n" + "═" * 62 + "\n", "header")
        self._log("  🔗  WIDGET LINKING\n", "header")
        self._log("═" * 62 + "\n\n", "header")

        t = threading.Thread(
            target=self._widget_link_thread,
            args=(project_path,),
            daemon=True,
        )
        t.start()

    def _widget_link_thread(self, project_path: str):
        ios_dir = Path(project_path) / "ios"
        if not ios_dir.exists():
            self._queue("❌  ios/ not found — widget linking requires an iOS project.\n", "error")
            return

        xcodeproj = next((f for f in ios_dir.iterdir() if f.suffix == ".xcodeproj"), None)
        if not xcodeproj:
            self._queue("❌  No .xcodeproj found inside ios/.\n", "error")
            return

        self._queue(f"📁  Xcode project:  {xcodeproj.name}\n", "info")

        widget_path = self.widget_path.get().strip()
        if not widget_path:
            self._detect_widget(project_path)
            widget_path = self.widget_path.get().strip()

        if not widget_path or not os.path.exists(widget_path):
            self._queue("⚠️   Widget path not set or does not exist.\n", "warning")
            self._queue("   Please set the Widget Extension folder path above.\n", "info")
            self._queue(
                "\n💡  To create a widget in Xcode:\n"
                "   1.  Open the .xcworkspace in Xcode\n"
                "   2.  File ▸ New ▸ Target ▸ Widget Extension\n"
                "   3.  Configure bundle ID & capabilities\n"
                "   4.  Set path here and click Link Widget again\n", "info")
            return

        widget_name = Path(widget_path).name
        pbxproj     = xcodeproj / "project.pbxproj"

        self._queue(f"🔗  Widget:  {widget_name}\n   {widget_path}\n\n", "info")

        if not pbxproj.exists():
            self._queue("❌  project.pbxproj not found.\n", "error")
            return

        try:
            self._do_widget_link(str(pbxproj), str(xcodeproj),
                                  widget_path, widget_name, project_path)
        except Exception as e:
            self._queue(f"❌  Widget linking exception:\n{traceback.format_exc()}\n", "error")

    def _do_widget_link(self, pbxproj_path: str, xcodeproj_path: str,
                         widget_path: str, widget_name: str, project_path: str):
        """Primary linking path: try xcodeproj gem, else manual pbxproj edit."""
        content = Path(pbxproj_path).read_text(encoding="utf-8", errors="replace")

        # ── Already present? ───────────────────────────────────────────────
        if widget_name in content:
            self._queue(f"ℹ️   '{widget_name}' already referenced in project.\n", "info")
            self._check_widget_health(content, widget_name)
            return

        # ── Try xcodeproj ruby gem ─────────────────────────────────────────
        if self._gem_available("xcodeproj"):
            self._queue("  Using xcodeproj gem…\n", "dim")
            script = self._write_ruby_script(xcodeproj_path, widget_path, widget_name, project_path)
            if self._run_ruby(script):
                self._queue("✅  Widget linked via xcodeproj gem.\n", "success")
                new_content = Path(pbxproj_path).read_text(encoding="utf-8", errors="replace")
                self._check_widget_health(new_content, widget_name)
                return
        else:
            self._queue("  ⚠️  xcodeproj gem not found. Attempting install…\n", "warning")
            r = subprocess.run(["gem", "install", "xcodeproj", "--user-install"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                self._queue("  ✅  xcodeproj installed.\n", "success")
                script = self._write_ruby_script(xcodeproj_path, widget_path, widget_name, project_path)
                if self._run_ruby(script):
                    self._queue("✅  Widget linked via xcodeproj gem.\n", "success")
                    new_content = Path(pbxproj_path).read_text(encoding="utf-8", errors="replace")
                    self._check_widget_health(new_content, widget_name)
                    return
            else:
                self._queue("  ⚠️  gem install failed. Falling back to manual method.\n", "warning")

        # ── Manual pbxproj modification ────────────────────────────────────
        self._manual_link(pbxproj_path, content, widget_path, widget_name, project_path)

    def _gem_available(self, gem_name: str) -> bool:
        r = subprocess.run(["gem", "list", gem_name], capture_output=True, text=True)
        return gem_name in r.stdout

    def _write_ruby_script(self, xcodeproj_path: str, widget_path: str,
                            widget_name: str, project_path: str) -> str:
        # Build Ruby script as a plain string to avoid Python f-string / Ruby #{} conflicts.
        # Python variables are injected via .replace() on unique placeholders.
        template = (
            "#!/usr/bin/env ruby\n"
            "# Auto-generated by Mobile Build Tool\n"
            "require 'xcodeproj'\n\n"
            "proj_path   = '__XCODEPROJ__'\n"
            "widget_name = '__WIDGET_NAME__'\n"
            "widget_dir  = '__WIDGET_DIR__'\n\n"
            "proj       = Xcodeproj::Project.open(proj_path)\n"
            "app_target = proj.targets.find { |t| t.product_type == "
            "'com.apple.product-type.application' } || proj.targets.first\n\n"
            "puts \"Opened: #{proj_path}\"\n"
            "puts \"Targets: #{proj.targets.map(&:name).join(', ')}\"\n\n"
            "if proj.targets.any? { |t| t.name == widget_name }\n"
            "  puts \"Target '#{widget_name}' already exists.\"\n"
            "else\n"
            "  widget_target = proj.new_target(:app_extension, widget_name, :ios, '14.0')\n"
            "  puts \"Created target: #{widget_target.name}\"\n\n"
            "  group = proj.main_group.find_subpath(widget_name) ||\n"
            "          proj.main_group.new_group(widget_name, widget_dir)\n\n"
            "  # Swift source files\n"
            "  Dir.glob(File.join(widget_dir, '**', '*.swift')).each do |f|\n"
            "    ref = group.new_file(f) rescue nil\n"
            "    widget_target.source_build_phase.add_file_reference(ref) if ref\n"
            "    puts \"  + #{File.basename(f)}\"\n"
            "  end\n\n"
            "  # Intent definition files\n"
            "  Dir.glob(File.join(widget_dir, '**', '*.intentdefinition')).each do |f|\n"
            "    ref = group.new_file(f) rescue nil\n"
            "    puts \"  + #{File.basename(f)}\" if ref\n"
            "  end\n\n"
            "  # Asset catalogs\n"
            "  Dir.glob(File.join(widget_dir, '**', '*.xcassets')).each do |f|\n"
            "    ref = group.new_file(f) rescue nil\n"
            "    widget_target.resources_build_phase.add_file_reference(ref) if ref\n"
            "    puts \"  + #{File.basename(f)}\"\n"
            "  end\n\n"
            "  # Embed widget in main app target\n"
            "  embed_phase = app_target.build_phases\n"
            "    .find { |p| p.is_a?(Xcodeproj::Project::Object::PBXCopyFilesBuildPhase) &&\n"
            "                p.symbol_dst_subfolder_spec == :plug_ins }\n"
            "  unless embed_phase\n"
            "    embed_phase = proj.new(Xcodeproj::Project::Object::PBXCopyFilesBuildPhase)\n"
            "    embed_phase.name = 'Embed Foundation Extensions'\n"
            "    embed_phase.symbol_dst_subfolder_spec = :plug_ins\n"
            "    app_target.build_phases << embed_phase\n"
            "    puts 'Created embed phase'\n"
            "  end\n\n"
            "  build_file = embed_phase.add_file_reference(widget_target.product_reference)\n"
            "  build_file.settings = { 'ATTRIBUTES' => ['RemoveHeadersOnCopy'] }\n\n"
            "  # Link WidgetKit & SwiftUI\n"
            "  ['WidgetKit.framework', 'SwiftUI.framework'].each do |fw|\n"
            "    widget_target.frameworks_build_phase.add_file_reference(\n"
            "      proj.frameworks_group.new_file(\"/System/Library/Frameworks/#{fw}\")\n"
            "    ) rescue nil\n"
            "    puts \"Linked: #{fw}\"\n"
            "  end\n\n"
            "  puts 'Widget linked successfully.'\n"
            "end\n\n"
            "proj.save\n"
            "puts 'Project saved.'\n"
        )

        script = (template
                  .replace("__XCODEPROJ__",   xcodeproj_path)
                  .replace("__WIDGET_NAME__",  widget_name)
                  .replace("__WIDGET_DIR__",   widget_path))

        p = Path("/tmp/mbt_link_widget.rb")
        p.write_text(script)
        return str(p)

    def _run_ruby(self, script_path: str) -> bool:
        ruby = find_tool("ruby") or "ruby"
        proc = subprocess.Popen([ruby, script_path],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True)
        for line in proc.stdout:
            self._queue(f"  {line}", "dim")
        proc.wait()
        return proc.returncode == 0

    def _manual_link(self, pbxproj_path: str, content: str,
                      widget_path: str, widget_name: str, project_path: str):
        """Backup pbxproj and inject minimal widget target references."""
        backup = pbxproj_path + ".bak_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(pbxproj_path, backup)
        self._queue(f"  💾  Backed up pbxproj → {backup}\n", "dim")

        swift_files = list(Path(widget_path).rglob("*.swift"))
        xcassets    = list(Path(widget_path).rglob("*.xcassets"))
        all_files   = swift_files + xcassets

        self._queue(f"  📄  Found {len(swift_files)} Swift files, "
                    f"{len(xcassets)} asset catalogs.\n", "info")

        widget_group_id  = gen_uuid()
        widget_target_id = gen_uuid()
        embed_phase_id   = gen_uuid()
        product_ref_id   = gen_uuid()
        sources_id       = gen_uuid()
        resources_id     = gen_uuid()
        frameworks_id    = gen_uuid()
        buildcfg_list_id = gen_uuid()
        debug_cfg_id     = gen_uuid()
        release_cfg_id   = gen_uuid()

        # Identify main target (heuristic)
        m = re.search(r"(\w{24})\s*/\*[^*]+\*/\s*=\s*\{[^}]*isa\s*=\s*PBXNativeTarget",
                      content)
        main_target_id = m.group(1) if m else None

        if not main_target_id:
            self._queue("  ❌  Could not locate main app target in pbxproj.\n", "error")
            self._queue("  💡  Open Xcode manually and add the widget extension target.\n", "info")
            return

        self._queue(f"  🎯  Main target ID: {main_target_id}\n", "dim")

        # Build file reference blocks
        file_ref_block = ""
        src_build_block = ""
        res_build_block = ""
        for sf in swift_files:
            fr_id = gen_uuid()
            bf_id = gen_uuid()
            rel   = sf.relative_to(Path(project_path))
            file_ref_block  += (f"\t\t{fr_id} /* {sf.name} */ = {{isa = PBXFileReference; "
                                f"lastKnownFileType = sourcecode.swift; "
                                f"name = {sf.name}; path = {rel}; "
                                f"sourceTree = \"<group>\"; }};\n")
            src_build_block += f"\t\t\t\t{bf_id} /* {sf.name} in Sources */,\n"

        for xa in xcassets:
            fr_id = gen_uuid()
            bf_id = gen_uuid()
            rel   = xa.relative_to(Path(project_path))
            file_ref_block  += (f"\t\t{fr_id} /* {xa.name} */ = {{isa = PBXFileReference; "
                                f"lastKnownFileType = folder.assetcatalog; "
                                f"name = {xa.name}; path = {rel}; "
                                f"sourceTree = \"<group>\"; }};\n")
            res_build_block += f"\t\t\t\t{bf_id} /* {xa.name} in Resources */,\n"

        # Inject file refs before the closing of /* End PBXFileReference section */
        if "/* End PBXFileReference section */" in content:
            content = content.replace(
                "/* End PBXFileReference section */",
                file_ref_block + "/* End PBXFileReference section */"
            )

        # Inject embed build phase into main target's buildPhases
        embed_snippet = (
            f"\n\t\t{embed_phase_id} /* Embed Foundation Extensions */ = {{\n"
            f"\t\t\tisa = PBXCopyFilesBuildPhase;\n"
            f"\t\t\tbuildActionMask = 2147483647;\n"
            f"\t\t\tdstPath = \"\";\n"
            f"\t\t\tdstSubfolderSpec = 13;\n"
            f"\t\t\tfiles = (\n"
            f"\t\t\t);\n"
            f"\t\t\tname = \"Embed Foundation Extensions\";\n"
            f"\t\t\trunOnlyForDeploymentPostprocessing = 0;\n"
            f"\t\t}};\n"
        )

        if "/* End PBXCopyFilesBuildPhase section */" in content:
            content = content.replace(
                "/* End PBXCopyFilesBuildPhase section */",
                embed_snippet + "/* End PBXCopyFilesBuildPhase section */"
            )

        Path(pbxproj_path).write_text(content, encoding="utf-8")
        self._queue("  ✅  pbxproj updated.\n", "success")
        self._queue(
            "  💡  IMPORTANT: Open Xcode to complete linking:\n"
            "      1. Verify widget target appears under Targets\n"
            "      2. Add widget to main app's 'Embed Foundation Extensions'\n"
            "      3. Add App Groups capability to both targets\n"
            "      4. Verify bundle IDs are properly nested\n", "info")

    # ── Widget verification ───────────────────────────────────────────────

    def _verify_widget_link(self):
        project_path = self.project_path.get().strip()
        if not project_path:
            messagebox.showerror("Error", "No project selected.")
            return

        ios_dir = Path(project_path) / "ios"
        if not ios_dir.exists():
            self._log("❌  No ios/ folder found.\n", "error")
            return

        self._log("\n🔍  Verifying widget link…\n", "info")
        xcodeproj = next((f for f in ios_dir.iterdir() if f.suffix == ".xcodeproj"), None)
        if not xcodeproj:
            self._log("❌  No .xcodeproj found.\n", "error")
            return

        pbxproj = xcodeproj / "project.pbxproj"
        content = pbxproj.read_text(encoding="utf-8", errors="replace")
        widget_name = Path(self.widget_path.get()).name if self.widget_path.get() else "Widget"
        self._check_widget_health(content, widget_name)

    def _check_widget_health(self, content: str, widget_name: str):
        checks = [
            ("Widget name referenced",         widget_name in content),
            ("Embed Foundation Extensions",
             "Embed Foundation Extensions" in content or "plug_ins" in content),
            ("WidgetKit framework",             "WidgetKit" in content),
            ("SwiftUI framework",               "SwiftUI" in content),
            ("App Groups entitlement",
             "com.apple.security.application-groups" in content),
            ("Widget bundle identifier",
             bool(re.search(r"PRODUCT_BUNDLE_IDENTIFIER.*widget", content, re.IGNORECASE))),
        ]

        self._queue("\n📊  Widget Health Check:\n", "header")
        issues = 0
        for label, ok in checks:
            sym = "✅" if ok else "❌"
            tag = "success" if ok else "error"
            self._queue(f"  {sym}  {label}\n", tag)
            if not ok:
                issues += 1

        # Bundle ID nesting check
        bundle_ids = re.findall(r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"?([^\s;"]+)"?', content)
        if len(bundle_ids) >= 2:
            main_id   = bundle_ids[0]
            widget_id = bundle_ids[-1]
            nested    = widget_id.startswith(main_id + ".")
            self._queue(f"  {'✅' if nested else '⚠️ '}  Bundle ID nesting  "
                        f"( {main_id}  ›  {widget_id} )\n",
                        "success" if nested else "warning")
            if not nested:
                issues += 1

        if issues == 0:
            self._queue("\n🎉  Widget is correctly linked!\n", "success")
        else:
            self._queue(f"\n⚠️   {issues} issue(s) detected. "
                        "Review and fix in Xcode.\n", "warning")

    # ══════════════════════════════════════════════════════════════════════
    # Logging
    # ══════════════════════════════════════════════════════════════════════

    def _queue(self, text: str, tag: str | None = None):
        """Thread-safe: put a log message on the queue."""
        self.all_logs.append((text, tag))
        self.log_queue.put((text, tag))

    def _log(self, text: str, tag: str | None = None):
        """Main-thread direct log insert."""
        self.all_logs.append((text, tag))
        self._insert_log(text, tag)

    def _insert_log(self, text: str, tag: str | None):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, text, tag or "")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _poll_log_queue(self):
        try:
            while True:
                text, tag = self.log_queue.get_nowait()
                self._insert_log(text, tag)
        except queue.Empty:
            pass
        finally:
            self.after(40, self._poll_log_queue)

    def _filter_logs(self, mode: str):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        if mode == "all":
            for text, tag in self.all_logs:
                self.log_text.insert(tk.END, text, tag or "")
        elif mode == "errors":
            if not self.error_logs:
                self.log_text.insert(tk.END, "✅  No errors recorded.\n", "success")
            else:
                self.log_text.insert(tk.END,
                    f"🔴  {len(self.error_logs)} error(s):\n\n", "bold_err")
                for line in self.error_logs:
                    self.log_text.insert(tk.END, line, "error")
        elif mode == "summary":
            self._write_summary()
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _write_summary(self):
        t = self.log_text
        t.insert(tk.END, "═" * 40 + "\n📊  BUILD SUMMARY\n" + "═" * 40 + "\n", "header")
        t.insert(tk.END, f"Total lines   :  {len(self.all_logs)}\n", "info")
        t.insert(tk.END, f"Errors        :  {len(self.error_logs)}\n",
                  "error" if self.error_logs else "success")
        warns = sum(1 for txt, _ in self.all_logs if "warning" in (txt or "").lower())
        t.insert(tk.END, f"Warnings      :  {warns}\n",
                  "warning" if warns else "success")
        if self.build_start_time:
            elapsed = int((datetime.datetime.now() - self.build_start_time).total_seconds())
            t.insert(tk.END, f"Elapsed       :  {elapsed // 60}m {elapsed % 60}s\n", "info")
        t.insert(tk.END, "\n📦  Output Files:\n", "header")
        found = [(txt, tag) for txt, tag in self.all_logs
                 if txt and (".ipa" in txt or ".apk" in txt) and "📁" in txt]
        if found:
            for txt, _ in found:
                t.insert(tk.END, f"  {txt}", "path")
        else:
            t.insert(tk.END, "  None yet.\n", "dim")

    def _copy_all_logs(self):
        text = "".join(t for t, _ in self.all_logs)
        self.clipboard_clear(); self.clipboard_append(text)
        self._flash_status(f"✅  All logs copied  ({len(self.all_logs)} lines)")

    def _copy_error_logs(self):
        if not self.error_logs:
            self._flash_status("ℹ️  No errors to copy")
            return
        text = "".join(self.error_logs)
        self.clipboard_clear(); self.clipboard_append(text)
        self._flash_status(f"✅  {len(self.error_logs)} error(s) copied")

    def _clear_logs(self):
        self.all_logs.clear()
        self.error_logs.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════════
    # Misc UI helpers
    # ══════════════════════════════════════════════════════════════════════

    def _open_output_folder(self):
        folder = self.output_dir.get() or (
            str(Path(self.project_path.get()) / "builds")
            if self.project_path.get() else str(Path.home())
        )
        if os.path.exists(folder):
            subprocess.run(["open", folder])
        else:
            messagebox.showinfo("Not Found",
                                f"Output folder doesn't exist yet:\n{folder}")

    def _set_progress(self, value: float, label: str):
        self.after(0, lambda: self.progress_bar.set(value))
        self.after(0, lambda: self.progress_label.configure(text=label))

    def _flash_status(self, msg: str, duration: int = 4000):
        old = self.status_var.get()
        self.status_var.set(msg)
        self.after(duration, lambda: self.status_var.set(old))


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = MobileBuildTool()
    app.mainloop()
