"""
Kindle Auto Capture — デスクトップGUIアプリ
tkinter製、ブラウザ・サーバー不要
"""

import os
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# ── ライブラリの遅延インポート（エラーを優しく表示） ─────────────────
def _check_deps():
    missing = []
    for mod in ["PIL", "imagehash", "img2pdf", "anthropic"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    return missing


# ── テーマカラー ──────────────────────────────────────────────────
BG      = "#1e2230"
PANEL   = "#252b3b"
ACCENT  = "#4f8ef7"
GREEN   = "#34c759"
RED     = "#ff3b30"
TEXT    = "#e8eaf0"
SUBTEXT = "#8a93a8"
ENTRY   = "#2d3347"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kindle Auto Capture")
        self.geometry("560x700")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(480, 600)

        self._running = False
        self._thread: threading.Thread | None = None
        self._page_count = 0

        self._build_ui()
        self._refresh_devices()

    # ──────────────────────────────────────────────────────────────
    # UI構築
    # ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._style()

        # タイトルバー
        bar = tk.Frame(self, bg=BG, pady=10)
        bar.pack(fill="x", padx=16)
        tk.Label(bar, text="📚 Kindle Auto Capture", bg=BG,
                 fg=TEXT, font=("", 14, "bold")).pack(side="left")

        # デバイス選択
        self._section("Android デバイス (ADB)")
        dev_row = tk.Frame(self._body, bg=PANEL)
        dev_row.pack(fill="x", pady=(0, 6))
        self._device_var = tk.StringVar()
        self._device_cb = ttk.Combobox(dev_row, textvariable=self._device_var,
                                       state="readonly", width=32)
        self._device_cb.pack(side="left", padx=(0, 6))
        self._btn(dev_row, "更新", self._refresh_devices).pack(side="left", padx=2)
        self._btn(dev_row, "解像度確認", self._show_resolution).pack(side="left", padx=2)
        self._btn(dev_row, "プレビュー", self._preview).pack(side="left", padx=2)

        # 設定
        self._section("キャプチャ設定")
        cfg = tk.Frame(self._body, bg=PANEL)
        cfg.pack(fill="x", pady=(0, 6))

        self._lbl_entry(cfg, "本のタイトル", 0)
        self._title_var = tk.StringVar(value="無題の本")
        tk.Entry(cfg, textvariable=self._title_var,
                 bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=4).grid(row=0, column=1, sticky="ew", padx=6, pady=3)

        self._lbl_entry(cfg, "ページ数 (0=全ページ)", 1)
        self._pages_var = tk.IntVar(value=0)
        tk.Spinbox(cfg, from_=0, to=9999, textvariable=self._pages_var,
                   bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                   relief="flat", bd=4, width=8).grid(row=1, column=1, sticky="w", padx=6, pady=3)

        self._lbl_entry(cfg, "保存フォルダ", 2)
        folder_row = tk.Frame(cfg, bg=PANEL)
        folder_row.grid(row=2, column=1, sticky="ew", padx=6, pady=3)
        self._folder_var = tk.StringVar(value=str(Path.home() / "KindleCapture"))
        tk.Entry(folder_row, textvariable=self._folder_var,
                 bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=4, width=24).pack(side="left")
        self._btn(folder_row, "…", self._choose_folder).pack(side="left", padx=4)
        cfg.columnconfigure(1, weight=1)

        # オプション
        self._auto_pdf = tk.BooleanVar(value=True)
        self._auto_ocr = tk.BooleanVar(value=False)
        opt = tk.Frame(self._body, bg=PANEL)
        opt.pack(fill="x", pady=(0, 10))
        self._chk(opt, "完了後にPDFを自動生成", self._auto_pdf).pack(side="left", padx=(0, 16))
        self._chk(opt, "完了後にOCR (要APIキー)", self._auto_ocr).pack(side="left")

        # OCR APIキー
        api_row = tk.Frame(self._body, bg=PANEL)
        api_row.pack(fill="x", pady=(0, 10))
        tk.Label(api_row, text="Claude APIキー (OCR用・省略可)",
                 bg=PANEL, fg=SUBTEXT, font=("", 9)).pack(anchor="w")
        self._api_var = tk.StringVar()
        tk.Entry(api_row, textvariable=self._api_var, show="*",
                 bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=4).pack(fill="x", pady=2)

        # コントロールボタン
        ctrl = tk.Frame(self._body, bg=PANEL)
        ctrl.pack(fill="x", pady=(0, 10))
        self._start_btn = tk.Button(ctrl, text="▶  キャプチャ開始",
                                    command=self._start,
                                    bg=ACCENT, fg="white", relief="flat",
                                    font=("", 11, "bold"), padx=20, pady=8,
                                    cursor="hand2", activebackground="#3a7de0")
        self._start_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = tk.Button(ctrl, text="■  停止",
                                   command=self._stop,
                                   bg=RED, fg="white", relief="flat",
                                   font=("", 11, "bold"), padx=20, pady=8,
                                   cursor="hand2", state="disabled",
                                   activebackground="#cc2e24")
        self._stop_btn.pack(side="left", padx=(0, 8))
        self._pdf_btn = tk.Button(ctrl, text="PDF生成",
                                  command=self._build_pdf_manual,
                                  bg=ENTRY, fg=TEXT, relief="flat",
                                  font=("", 10), padx=14, pady=8,
                                  cursor="hand2")
        self._pdf_btn.pack(side="left")

        # プログレス
        prog_row = tk.Frame(self._body, bg=PANEL)
        prog_row.pack(fill="x", pady=(0, 6))
        self._status_lbl = tk.Label(prog_row, text="待機中", bg=PANEL,
                                    fg=SUBTEXT, font=("", 9))
        self._status_lbl.pack(side="left")
        self._page_lbl = tk.Label(prog_row, text="", bg=PANEL,
                                  fg=GREEN, font=("", 9, "bold"))
        self._page_lbl.pack(side="right")
        self._progress = ttk.Progressbar(self._body, mode="indeterminate")
        self._progress.pack(fill="x", pady=(0, 8))

        # ログ
        self._section("ログ")
        self._log = scrolledtext.ScrolledText(
            self._body, height=10, bg="#0d1017", fg="#a0aab8",
            font=("Consolas", 9), relief="flat", bd=0,
            insertbackground=TEXT, state="disabled")
        self._log.pack(fill="both", expand=True)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=ENTRY, background=ENTRY,
                         foreground=TEXT, selectbackground=ACCENT)
        style.configure("Horizontal.TProgressbar",
                         troughcolor=ENTRY, background=ACCENT)
        self._body = tk.Frame(self, bg=PANEL, padx=16, pady=10)
        self._body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _section(self, title):
        tk.Label(self._body, text=title, bg=PANEL,
                 fg=SUBTEXT, font=("", 8, "bold")).pack(anchor="w", pady=(6, 2))

    def _btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=ENTRY, fg=TEXT, relief="flat",
                         font=("", 9), padx=10, pady=4,
                         cursor="hand2", activebackground="#3d4560")

    def _chk(self, parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var,
                               bg=PANEL, fg=TEXT, selectcolor=ENTRY,
                               activebackground=PANEL, font=("", 9),
                               cursor="hand2")

    def _lbl_entry(self, parent, text, row):
        tk.Label(parent, text=text, bg=PANEL, fg=SUBTEXT,
                 font=("", 9)).grid(row=row, column=0, sticky="w",
                                    padx=(0, 8), pady=3)

    # ──────────────────────────────────────────────────────────────
    # アクション
    # ──────────────────────────────────────────────────────────────
    def _log_msg(self, msg: str):
        self._log.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self._log.insert("end", f"[{ts}] {msg}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _refresh_devices(self):
        try:
            from modules.adb_controller import AdbController
            devices = AdbController().list_devices()
            values = [f"{d['serial']}  {d.get('model','')}" for d in devices]
            self._device_cb["values"] = values or ["(デバイスなし)"]
            if values:
                self._device_cb.current(0)
                self._log_msg(f"デバイス {len(values)} 台を検出")
            else:
                self._device_cb.current(0)
                self._log_msg("デバイスが見つかりません。USB接続・ADB・デバッグONを確認してください")
        except Exception as e:
            self._device_cb["values"] = ["(ADB未インストール)"]
            self._device_cb.current(0)
            self._log_msg(f"ADB: {e}")

    def _get_serial(self) -> str:
        val = self._device_var.get()
        return val.split()[0] if val and "()" not in val else ""

    def _show_resolution(self):
        try:
            from modules.adb_controller import AdbController
            w, h = AdbController().get_screen_size(self._get_serial())
            messagebox.showinfo("解像度", f"{w} × {h} px  ({round(w*h/1e6,1)} MP)\nPNG ロスレスで保存されます")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def _preview(self):
        try:
            from modules.adb_controller import AdbController
            import subprocess, tempfile
            tmp = str(Path(tempfile.gettempdir()) / "_kindle_preview.png")
            AdbController().capture(self._get_serial(), tmp)
            if sys.platform == "win32":
                os.startfile(tmp)
            else:
                subprocess.run(["xdg-open", tmp])
            self._log_msg("プレビュー画像を開きました")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def _choose_folder(self):
        path = filedialog.askdirectory(title="保存フォルダを選択")
        if path:
            self._folder_var.set(path)

    def _start(self):
        if self._running:
            return
        self._running = True
        self._page_count = 0
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress.start(12)
        self._status_lbl.configure(text="実行中", fg=GREEN)
        save_dir = Path(self._folder_var.get()) / self._title_var.get().replace(" ", "_")
        save_dir.mkdir(parents=True, exist_ok=True)
        self._log_msg(f"開始: {self._title_var.get()}  保存先: {save_dir}")
        self._thread = threading.Thread(
            target=self._capture_loop,
            args=(str(save_dir), self._get_serial(),
                  self._pages_var.get(), self._auto_pdf.get(),
                  self._auto_ocr.get(), self._api_var.get()),
            daemon=True,
        )
        self._thread.start()

    def _stop(self):
        self._running = False
        self._log_msg("停止リクエスト送信…")

    def _capture_loop(self, save_dir: str, serial: str,
                      total: int, auto_pdf: bool, auto_ocr: bool, api_key: str):
        try:
            from modules.adb_controller import AdbController
            from modules.page_detector import PageChangeWaiter

            adb = AdbController()
            tmp = str(Path(save_dir) / "_tmp.png")
            waiter = PageChangeWaiter(
                capture_fn=lambda p: adb.capture(serial, p),
                timeout=15.0, poll_interval=0.4,
            )

            # 1ページ目
            p1 = str(Path(save_dir) / "page_0001.png")
            adb.capture(serial, p1)
            self._page_count = 1
            self.after(0, self._update_page_label)
            self._log_msg("ページ 1 保存")

            while self._running:
                if total and self._page_count >= total:
                    self._log_msg(f"指定ページ数 ({total}) に到達")
                    break
                last = str(Path(save_dir) / f"page_{self._page_count:04d}.png")
                adb.swipe_next_page(serial)
                changed = waiter.wait_for_change(last, tmp)
                if not changed:
                    self._log_msg("ページ変化なし — 最終ページに到達")
                    break
                nxt = str(Path(save_dir) / f"page_{self._page_count + 1:04d}.png")
                Path(tmp).rename(nxt)
                self._page_count += 1
                self.after(0, self._update_page_label)
                if self._page_count % 10 == 0:
                    self._log_msg(f"{self._page_count} ページ完了")

            # PDF
            if auto_pdf and self._page_count > 0:
                self._log_msg("PDF 生成中…")
                from modules.pdf_builder import build_pdf
                pdf = build_pdf(save_dir)
                self._log_msg(f"PDF 完了 → {pdf}")

            # OCR
            if auto_ocr and self._page_count > 0:
                self._log_msg("OCR 実行中…")
                import asyncio
                from modules.ocr_engine import OcrEngine
                asyncio.run(OcrEngine(api_key).ocr_directory(
                    save_dir,
                    progress_cb=lambda d, t: self._log_msg(f"OCR {d}/{t}")
                ))
                self._log_msg("OCR 完了")

            self._log_msg(f"✅ 完了 — {self._page_count} ページ  保存先: {save_dir}")

        except Exception as e:
            self._log_msg(f"❌ エラー: {e}")
        finally:
            self._running = False
            self.after(0, self._on_done)

    def _update_page_label(self):
        total = self._pages_var.get()
        label = f"{self._page_count}" + (f" / {total}" if total else "") + " ページ"
        self._page_lbl.configure(text=label)

    def _on_done(self):
        self._progress.stop()
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status_lbl.configure(text="完了" if not self._running else "停止中", fg=SUBTEXT)

    def _build_pdf_manual(self):
        folder = filedialog.askdirectory(title="PNG が入っているフォルダを選択")
        if not folder:
            return
        try:
            from modules.pdf_builder import build_pdf
            self._log_msg("PDF 生成中…")
            pdf = build_pdf(folder)
            self._log_msg(f"PDF 完了 → {pdf}")
            if messagebox.askyesno("完了", f"PDFを開きますか？\n{pdf}"):
                if sys.platform == "win32":
                    os.startfile(pdf)
        except Exception as e:
            messagebox.showerror("エラー", str(e))


# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    missing = _check_deps()
    if missing:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "ライブラリ不足",
            f"以下のライブラリが不足しています:\n{', '.join(missing)}\n\n"
            "build.bat を実行してインストールしてください。"
        )
        sys.exit(1)

    app = App()
    app.mainloop()
