"""
Kindle Auto Capture — デスクトップGUIアプリ
tkinter製、ブラウザ・サーバー不要
"""

import io
import os
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# ── ライブラリチェック ─────────────────────────────────────────────
def _check_deps():
    missing = []
    for mod in ["PIL", "imagehash", "img2pdf"]:
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


# ═══════════════════════════════════════════════════════════════════
# キャプチャ範囲選択ダイアログ
# ═══════════════════════════════════════════════════════════════════
class CropDialog(tk.Toplevel):
    """
    スクリーンショットプレビュー上でドラッグ・ハンドルリサイズ・
    マウスホイールズームでキャプチャ範囲を選択するダイアログ。
    result: (x1,y1,x2,y2) in image px、None=フルスクリーン
    """
    H = 7  # ハンドル半径 (canvas px)

    def __init__(self, parent: tk.Widget, img_path: str):
        super().__init__(parent)
        self.title("キャプチャ範囲を選択")
        self.resizable(True, True)
        self.grab_set()
        self.result: tuple[int, int, int, int] | None = None

        from PIL import Image
        self._pil = Image.open(img_path)
        self._img_w, self._img_h = self._pil.size

        # キャンバスサイズ (最大 760×900)
        self._cw = 760
        self._ch = min(880, int(self._img_h * 760 / self._img_w))
        self._base_scale = self._cw / self._img_w

        # ビュー状態
        self._zoom  = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0

        # 選択 (image 座標 float)
        self._sel: list[float] = [0.0, 0.0, float(self._img_w), float(self._img_h)]

        # ドラッグ状態
        self._drag_mode: str | None  = None
        self._drag_start_canvas      = (0, 0)
        self._drag_start_sel: list   = []

        self._build()
        self._redraw()

    # ── UI 構築 ─────────────────────────────────────────────────
    def _build(self):
        tk.Label(self,
                 text="ドラッグ: 新規選択   ハンドル(■): リサイズ   "
                      "選択内ドラッグ: 移動   マウスホイール: ズーム",
                 fg="#888", font=("", 8)).pack(pady=4)

        self._canvas = tk.Canvas(self, width=self._cw, height=self._ch,
                                 bg="#111", cursor="crosshair",
                                 bd=0, highlightthickness=0)
        self._canvas.pack(padx=8)

        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",       self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<MouseWheel>",      self._on_wheel)
        self._canvas.bind("<Button-4>",        self._on_wheel)   # Linux scroll up
        self._canvas.bind("<Button-5>",        self._on_wheel)   # Linux scroll down

        self._info = tk.Label(self, text="", font=("Consolas", 9), fg="#aaa")
        self._info.pack(pady=3)

        row = tk.Frame(self)
        row.pack(pady=6)
        tk.Button(row, text="全画面に戻す",  command=self._reset,
                  padx=10, pady=4).pack(side="left", padx=4)
        tk.Button(row, text="✔  確定 (OK)",
                  bg=ACCENT, fg="white", relief="flat",
                  command=self._ok, padx=16, pady=4).pack(side="left", padx=4)
        tk.Button(row, text="キャンセル",   command=self.destroy,
                  padx=10, pady=4).pack(side="left", padx=4)

    # ── 座標変換 ────────────────────────────────────────────────
    def _eff_scale(self) -> float:
        return self._zoom * self._base_scale

    def _to_canvas(self, ix: float, iy: float) -> tuple[float, float]:
        s = self._eff_scale()
        return (ix - self._pan_x) * s, (iy - self._pan_y) * s

    def _to_image(self, cx: float, cy: float) -> tuple[float, float]:
        s = self._eff_scale()
        return cx / s + self._pan_x, cy / s + self._pan_y

    def _clamp_pan(self):
        s = self._eff_scale()
        self._pan_x = max(0.0, min(self._pan_x,
                                   max(0.0, self._img_w - self._cw / s)))
        self._pan_y = max(0.0, min(self._pan_y,
                                   max(0.0, self._img_h - self._ch / s)))

    # ── 描画 ────────────────────────────────────────────────────
    def _redraw(self):
        from PIL import Image, ImageTk
        s = self._eff_scale()
        vis_w = self._cw / s
        vis_h = self._ch / s
        x0, y0 = self._pan_x, self._pan_y
        x1 = min(x0 + vis_w, self._img_w)
        y1 = min(y0 + vis_h, self._img_h)
        crop = self._pil.crop((int(x0), int(y0), int(x1), int(y1)))
        out_w = self._cw
        out_h = min(self._ch, int(crop.height * s))
        if out_w < 1 or out_h < 1:
            return
        resized = crop.resize((out_w, out_h), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(resized)

        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_img)
        self._draw_sel()
        self._update_info()

    def _draw_sel(self):
        x1i, y1i, x2i, y2i = self._sel
        x1c, y1c = self._to_canvas(x1i, y1i)
        x2c, y2c = self._to_canvas(x2i, y2i)
        cw, ch = self._cw, self._ch

        # 選択外を暗くする (4分割)
        for r in [(0,0,cw,y1c),(0,y2c,cw,ch),(0,y1c,x1c,y2c),(x2c,y1c,cw,y2c)]:
            self._canvas.create_rectangle(*r, fill="#000", stipple="gray25", outline="")

        # 選択枠
        self._canvas.create_rectangle(x1c, y1c, x2c, y2c,
                                       outline=ACCENT, width=2)

        # 8 ハンドル
        H = self.H
        mx, my = (x1c+x2c)/2, (y1c+y2c)/2
        for hx, hy in [(x1c,y1c),(mx,y1c),(x2c,y1c),
                       (x1c,my),          (x2c,my),
                       (x1c,y2c),(mx,y2c),(x2c,y2c)]:
            self._canvas.create_rectangle(hx-H, hy-H, hx+H, hy+H,
                                           fill=ACCENT, outline="white", width=1)

    def _update_info(self):
        x1,y1,x2,y2 = [int(v) for v in self._sel]
        w,h = x2-x1, y2-y1
        self._info.configure(
            text=f"範囲: ({x1}, {y1}) 〜 ({x2}, {y2})  |  {w} × {h} px"
                 f"   ズーム: {int(self._zoom*100)}%"
        )

    # ── ヒットテスト ────────────────────────────────────────────
    def _hit_handle(self, cx: float, cy: float) -> str | None:
        x1i,y1i,x2i,y2i = self._sel
        x1c,y1c = self._to_canvas(x1i,y1i)
        x2c,y2c = self._to_canvas(x2i,y2i)
        mx,my = (x1c+x2c)/2, (y1c+y2c)/2
        T = self.H + 5
        for hx,hy,name in [(x1c,y1c,"NW"),(mx,y1c,"N"),(x2c,y1c,"NE"),
                            (x1c,my,"W"),              (x2c,my,"E"),
                            (x1c,y2c,"SW"),(mx,y2c,"S"),(x2c,y2c,"SE")]:
            if abs(cx-hx) <= T and abs(cy-hy) <= T:
                return name
        return None

    def _in_sel(self, cx: float, cy: float) -> bool:
        x1c,y1c = self._to_canvas(self._sel[0],self._sel[1])
        x2c,y2c = self._to_canvas(self._sel[2],self._sel[3])
        return x1c <= cx <= x2c and y1c <= cy <= y2c

    # ── マウスイベント ─────────────────────────────────────────
    def _on_press(self, e):
        self._drag_start_canvas = (e.x, e.y)
        self._drag_start_sel = list(self._sel)
        handle = self._hit_handle(e.x, e.y)
        if handle:
            self._drag_mode = f"handle_{handle}"
        elif self._in_sel(e.x, e.y):
            self._drag_mode = "move"
        else:
            ix, iy = self._to_image(e.x, e.y)
            self._sel = [ix, iy, ix, iy]
            self._drag_start_sel = list(self._sel)
            self._drag_mode = "new"

    def _on_drag(self, e):
        if not self._drag_mode:
            return
        s0 = self._drag_start_sel
        iw, ih = float(self._img_w), float(self._img_h)
        def ci(v,lo,hi): return max(lo, min(hi, v))

        if self._drag_mode == "new":
            ix, iy = self._to_image(e.x, e.y)
            self._sel = [ci(min(s0[0],ix),0,iw), ci(min(s0[1],iy),0,ih),
                         ci(max(s0[0],ix),0,iw), ci(max(s0[1],iy),0,ih)]

        elif self._drag_mode == "move":
            sc = self._eff_scale()
            dxi = (e.x - self._drag_start_canvas[0]) / sc
            dyi = (e.y - self._drag_start_canvas[1]) / sc
            bw, bh = s0[2]-s0[0], s0[3]-s0[1]
            nx1 = ci(s0[0]+dxi, 0, iw-bw)
            ny1 = ci(s0[1]+dyi, 0, ih-bh)
            self._sel = [nx1, ny1, nx1+bw, ny1+bh]

        elif self._drag_mode and self._drag_mode.startswith("handle_"):
            name = self._drag_mode[7:]
            ix, iy = self._to_image(e.x, e.y)
            x1,y1,x2,y2 = s0
            M = 20.0
            if "W" in name: x1 = ci(ix, 0, x2-M)
            if "E" in name: x2 = ci(ix, x1+M, iw)
            if "N" in name: y1 = ci(iy, 0, y2-M)
            if "S" in name: y2 = ci(iy, y1+M, ih)
            self._sel = [x1,y1,x2,y2]

        self._redraw()

    def _on_release(self, e):
        self._drag_mode = None

    def _on_wheel(self, e):
        # Windows/Mac: e.delta  |  Linux: e.num
        if hasattr(e, "delta") and e.delta:
            factor = 1.12 if e.delta > 0 else (1 / 1.12)
        else:
            factor = 1.12 if e.num == 4 else (1 / 1.12)

        ix, iy = self._to_image(e.x, e.y)
        old = self._zoom
        self._zoom = max(1.0, min(10.0, self._zoom * factor))
        if self._zoom != old:
            sc = self._eff_scale()
            self._pan_x = ix - e.x / sc
            self._pan_y = iy - e.y / sc
            self._clamp_pan()
            self._redraw()

    def _reset(self):
        self._sel  = [0.0, 0.0, float(self._img_w), float(self._img_h)]
        self._zoom = 1.0
        self._pan_x = self._pan_y = 0.0
        self._redraw()

    def _ok(self):
        x1,y1,x2,y2 = self._sel
        if int(x1) <= 0 and int(y1) <= 0 and \
           int(x2) >= self._img_w and int(y2) >= self._img_h:
            self.result = None  # フルスクリーン
        else:
            self.result = (int(x1), int(y1), int(x2), int(y2))
        self.destroy()


# ═══════════════════════════════════════════════════════════════════
# メインアプリ
# ═══════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kindle Auto Capture")
        self.geometry("580x760")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(500, 640)

        self._running      = False
        self._thread: threading.Thread | None = None
        self._page_count   = 0
        self._crop_rect: tuple[int,int,int,int] | None = None  # (x1,y1,x2,y2)
        self._preview_path: str | None = None   # 直近プレビュー画像パス

        self._build_ui()
        self._refresh_devices()

    # ──────────────────────────────────────────────────────────────
    # UI 構築
    # ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._style()

        bar = tk.Frame(self, bg=BG, pady=10)
        bar.pack(fill="x", padx=16)
        tk.Label(bar, text="📚 Kindle Auto Capture", bg=BG,
                 fg=TEXT, font=("", 14, "bold")).pack(side="left")

        # ── デバイス ──────────────────────────────────────────
        self._section("Android デバイス (USB + ADB)")
        dev_row = tk.Frame(self._body, bg=PANEL)
        dev_row.pack(fill="x", pady=(0,4))
        self._device_var = tk.StringVar()
        self._device_cb = ttk.Combobox(dev_row, textvariable=self._device_var,
                                       state="readonly", width=30)
        self._device_cb.pack(side="left", padx=(0,6))
        self._btn(dev_row, "更新",      self._refresh_devices).pack(side="left", padx=2)
        self._btn(dev_row, "解像度",    self._show_resolution).pack(side="left", padx=2)
        self._btn(dev_row, "プレビュー", self._preview).pack(side="left", padx=2)

        # ── キャプチャ範囲 ───────────────────────────────────
        self._section("キャプチャ範囲")
        crop_row = tk.Frame(self._body, bg=PANEL)
        crop_row.pack(fill="x", pady=(0,6))
        self._crop_lbl = tk.Label(crop_row, text="全画面 (未選択)",
                                  bg=PANEL, fg=SUBTEXT, font=("", 9))
        self._crop_lbl.pack(side="left", padx=(0,10))
        self._btn(crop_row, "範囲を選択 (ドラッグ/ズーム)", self._open_crop_selector).pack(side="left", padx=2)
        self._btn(crop_row, "全画面に戻す", self._clear_crop).pack(side="left", padx=2)

        # ── 設定 ─────────────────────────────────────────────
        self._section("キャプチャ設定")
        cfg = tk.Frame(self._body, bg=PANEL)
        cfg.pack(fill="x", pady=(0,6))

        self._lbl_entry(cfg, "本のタイトル",      0)
        self._title_var = tk.StringVar(value="無題の本")
        tk.Entry(cfg, textvariable=self._title_var,
                 bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=4).grid(row=0, column=1, sticky="ew", padx=6, pady=3)

        self._lbl_entry(cfg, "ページ数 (0=全自動)", 1)
        self._pages_var = tk.IntVar(value=0)
        tk.Spinbox(cfg, from_=0, to=9999, textvariable=self._pages_var,
                   bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                   relief="flat", bd=4, width=8).grid(row=1, column=1, sticky="w", padx=6, pady=3)

        self._lbl_entry(cfg, "保存フォルダ", 2)
        fr = tk.Frame(cfg, bg=PANEL)
        fr.grid(row=2, column=1, sticky="ew", padx=6, pady=3)
        self._folder_var = tk.StringVar(value=str(Path.home() / "KindleCapture"))
        tk.Entry(fr, textvariable=self._folder_var,
                 bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=4, width=24).pack(side="left")
        self._btn(fr, "…", self._choose_folder).pack(side="left", padx=4)
        cfg.columnconfigure(1, weight=1)

        # ── PDF / OCR オプション ──────────────────────────────
        self._section("出力設定")
        opt = tk.Frame(self._body, bg=PANEL)
        opt.pack(fill="x", pady=(0,4))
        self._auto_pdf = tk.BooleanVar(value=True)
        self._auto_ocr = tk.BooleanVar(value=False)
        self._chk(opt, "PDF を自動生成 (JPEG85% / 11インチ向け圧縮)",
                  self._auto_pdf).pack(side="left", padx=(0,16))

        ocr_row = tk.Frame(self._body, bg=PANEL)
        ocr_row.pack(fill="x", pady=(0,4))
        self._chk(ocr_row, "OCR テキスト認識 (PDF 文字検索対応・要APIキー)",
                  self._auto_ocr).pack(side="left")

        api_row = tk.Frame(self._body, bg=PANEL)
        api_row.pack(fill="x", pady=(0,10))
        tk.Label(api_row, text="Claude API キー (OCR用・省略可)",
                 bg=PANEL, fg=SUBTEXT, font=("", 9)).pack(anchor="w")
        self._api_var = tk.StringVar()
        tk.Entry(api_row, textvariable=self._api_var, show="*",
                 bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=4).pack(fill="x", pady=2)

        # ── コントロール ──────────────────────────────────────
        ctrl = tk.Frame(self._body, bg=PANEL)
        ctrl.pack(fill="x", pady=(0,8))
        self._start_btn = tk.Button(
            ctrl, text="▶  キャプチャ開始", command=self._start,
            bg=ACCENT, fg="white", relief="flat",
            font=("", 11, "bold"), padx=20, pady=8,
            cursor="hand2", activebackground="#3a7de0")
        self._start_btn.pack(side="left", padx=(0,8))
        self._stop_btn = tk.Button(
            ctrl, text="■  停止", command=self._stop,
            bg=RED, fg="white", relief="flat",
            font=("", 11, "bold"), padx=20, pady=8,
            cursor="hand2", state="disabled", activebackground="#cc2e24")
        self._stop_btn.pack(side="left", padx=(0,8))
        self._pdf_btn = tk.Button(
            ctrl, text="PDF のみ生成", command=self._build_pdf_manual,
            bg=ENTRY, fg=TEXT, relief="flat",
            font=("", 10), padx=14, pady=8, cursor="hand2")
        self._pdf_btn.pack(side="left")

        # ── プログレス ────────────────────────────────────────
        pg = tk.Frame(self._body, bg=PANEL)
        pg.pack(fill="x", pady=(0,4))
        self._status_lbl = tk.Label(pg, text="待機中", bg=PANEL,
                                    fg=SUBTEXT, font=("", 9))
        self._status_lbl.pack(side="left")
        self._page_lbl = tk.Label(pg, text="", bg=PANEL,
                                  fg=GREEN, font=("", 9, "bold"))
        self._page_lbl.pack(side="right")
        self._progress = ttk.Progressbar(self._body, mode="indeterminate")
        self._progress.pack(fill="x", pady=(0,6))

        # ── ログ ──────────────────────────────────────────────
        self._section("ログ")
        self._log = scrolledtext.ScrolledText(
            self._body, height=9, bg="#0d1017", fg="#a0aab8",
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
        self._body.pack(fill="both", expand=True, padx=12, pady=(0,12))

    def _section(self, title):
        tk.Label(self._body, text=title, bg=PANEL,
                 fg=SUBTEXT, font=("", 8, "bold")).pack(anchor="w", pady=(6,2))

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
                                    padx=(0,8), pady=3)

    # ──────────────────────────────────────────────────────────────
    # デバイス関連
    # ──────────────────────────────────────────────────────────────
    def _refresh_devices(self):
        try:
            from modules.adb_controller import AdbController
            devices = AdbController().list_devices()
            values = [f"{d['serial']}  {d.get('model','')}" for d in devices]
            self._device_cb["values"] = values or ["(デバイスなし)"]
            self._device_cb.current(0)
            if values:
                self._log_msg(f"デバイス {len(values)} 台を検出")
            else:
                self._log_msg("デバイスが見つかりません。USB・ADB・開発者デバッグONを確認")
        except Exception as e:
            self._device_cb["values"] = ["(ADB未インストール)"]
            self._device_cb.current(0)
            self._log_msg(f"ADB: {e}")

    def _get_serial(self) -> str:
        val = self._device_var.get()
        return val.split()[0] if val and "(" not in val else ""

    def _show_resolution(self):
        try:
            from modules.adb_controller import AdbController
            w, h = AdbController().get_screen_size(self._get_serial())
            messagebox.showinfo("解像度",
                f"{w} × {h} px  ({round(w*h/1e6,1)} MP)\n"
                "PNG ロスレスでキャプチャ、PDF では JPEG85% に変換します。")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def _preview(self):
        import tempfile
        try:
            from modules.adb_controller import AdbController
            tmp = str(Path(tempfile.gettempdir()) / "_kindle_preview.png")
            AdbController().capture(self._get_serial(), tmp)
            self._preview_path = tmp
            self._log_msg("プレビュー取得完了")
            if sys.platform == "win32":
                os.startfile(tmp)
            else:
                import subprocess
                subprocess.run(["xdg-open", tmp])
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    # ──────────────────────────────────────────────────────────────
    # キャプチャ範囲選択
    # ──────────────────────────────────────────────────────────────
    def _open_crop_selector(self):
        import tempfile
        # まずプレビュー取得
        self._log_msg("プレビューを取得してキャプチャ範囲選択を開きます…")
        try:
            from modules.adb_controller import AdbController
            tmp = str(Path(tempfile.gettempdir()) / "_kindle_preview.png")
            AdbController().capture(self._get_serial(), tmp)
            self._preview_path = tmp
        except Exception as e:
            messagebox.showerror("エラー",
                f"プレビュー取得失敗:\n{e}\n\nデバイスを接続・選択してください。")
            return

        dlg = CropDialog(self, tmp)
        self.wait_window(dlg)

        if hasattr(dlg, "result"):
            self._crop_rect = dlg.result
            if self._crop_rect:
                x1,y1,x2,y2 = self._crop_rect
                w,h = x2-x1, y2-y1
                self._crop_lbl.configure(
                    text=f"選択中: ({x1},{y1})〜({x2},{y2})  {w}×{h}px",
                    fg=GREEN)
                self._log_msg(f"キャプチャ範囲を設定: ({x1},{y1})〜({x2},{y2})")
            else:
                self._crop_lbl.configure(text="全画面 (フルスクリーン)", fg=SUBTEXT)
                self._log_msg("キャプチャ範囲: 全画面")

    def _clear_crop(self):
        self._crop_rect = None
        self._crop_lbl.configure(text="全画面 (未選択)", fg=SUBTEXT)
        self._log_msg("キャプチャ範囲を全画面にリセット")

    # ──────────────────────────────────────────────────────────────
    # フォルダ
    # ──────────────────────────────────────────────────────────────
    def _choose_folder(self):
        path = filedialog.askdirectory(title="保存フォルダを選択")
        if path:
            self._folder_var.set(path)

    # ──────────────────────────────────────────────────────────────
    # ログ
    # ──────────────────────────────────────────────────────────────
    def _log_msg(self, msg: str):
        self._log.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self._log.insert("end", f"[{ts}] {msg}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    # ──────────────────────────────────────────────────────────────
    # キャプチャ開始/停止
    # ──────────────────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return
        # OCR が有効だが API キーが未設定の場合は警告
        if self._auto_ocr.get() and not self._api_var.get().strip():
            ok = messagebox.askyesno(
                "OCR の API キーが未設定",
                "OCR が有効ですが Claude API キーが未入力です。\n"
                "このまま続行すると OCR はスキップされます。\n\n"
                "続行しますか？"
            )
            if not ok:
                return
        self._running   = True
        self._page_count = 0
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress.start(12)
        self._status_lbl.configure(text="実行中", fg=GREEN)

        save_dir = (Path(self._folder_var.get()) /
                    self._title_var.get().replace(" ", "_"))
        save_dir.mkdir(parents=True, exist_ok=True)
        self._log_msg(f"開始: 「{self._title_var.get()}」  保存先: {save_dir}")
        if self._crop_rect:
            self._log_msg(f"キャプチャ範囲: {self._crop_rect}")

        self._thread = threading.Thread(
            target=self._capture_loop,
            args=(str(save_dir), self._get_serial(),
                  self._pages_var.get(), self._auto_pdf.get(),
                  self._auto_ocr.get(), self._api_var.get(),
                  self._crop_rect),
            daemon=True,
        )
        self._thread.start()

    def _stop(self):
        self._running = False
        self._log_msg("停止リクエスト送信…")

    # ──────────────────────────────────────────────────────────────
    # キャプチャループ (別スレッド)
    # ──────────────────────────────────────────────────────────────
    def _capture_loop(self, save_dir: str, serial: str,
                      total: int, auto_pdf: bool, auto_ocr: bool,
                      api_key: str, crop_rect):
        try:
            from modules.adb_controller import AdbController
            from modules.page_detector import PageChangeWaiter

            adb = AdbController()
            tmp = str(Path(save_dir) / "_tmp.png")
            waiter = PageChangeWaiter(
                capture_fn=lambda p: adb.capture(serial, p, crop=crop_rect),
                timeout=15.0, poll_interval=0.4,
            )

            # ページ 1
            p1 = str(Path(save_dir) / "page_0001.png")
            adb.capture(serial, p1, crop=crop_rect)
            self._page_count = 1
            self.after(0, self._update_page_label)
            self._log_msg("ページ 1 保存")

            # ループ
            while self._running:
                if total and self._page_count >= total:
                    self._log_msg(f"指定ページ数 ({total}) に到達 — 完了")
                    break
                last = str(Path(save_dir) / f"page_{self._page_count:04d}.png")
                adb.swipe_next_page(serial)
                changed = waiter.wait_for_change(last, tmp)
                if not changed:
                    self._log_msg("ページ変化なし — 最終ページ到達 → 自動停止")
                    break
                nxt = str(Path(save_dir) / f"page_{self._page_count + 1:04d}.png")
                Path(tmp).rename(nxt)
                self._page_count += 1
                self.after(0, self._update_page_label)
                if self._page_count % 10 == 0:
                    self._log_msg(f"{self._page_count} ページ完了")

            # ── OCR (PDF生成の前に実行してテキスト埋め込み) ───────
            ocr_texts: dict[str, str] = {}
            if auto_ocr and self._page_count > 0 and api_key.strip():
                self._log_msg("OCR テキスト認識を開始…")
                import asyncio
                from modules.ocr_engine import OcrEngine
                engine = OcrEngine(api_key)
                png_files = sorted(Path(save_dir).glob("page_*.png"))
                for i, png_path in enumerate(png_files):
                    try:
                        text = asyncio.run(engine.ocr_image(str(png_path)))
                        ocr_texts[png_path.name] = text
                    except Exception as e:
                        self._log_msg(f"  OCR エラー ({png_path.name}): {e}")
                    if (i+1) % 5 == 0 or i+1 == len(png_files):
                        self._log_msg(f"  OCR {i+1}/{len(png_files)} 完了")
                self._log_msg("OCR 完了 — PDF にテキストを埋め込みます")
            elif auto_ocr and self._page_count > 0:
                self._log_msg("OCR スキップ (API キー未設定)")

            # ── PDF 生成 ─────────────────────────────────────────
            if auto_pdf and self._page_count > 0:
                self._log_msg("PDF 生成中 (JPEG85% / 11インチ最適化)…")
                from modules.pdf_builder import build_pdf
                pdf = build_pdf(
                    save_dir,
                    jpeg_quality=85,
                    max_width=1800,
                    ocr_texts=ocr_texts or None,
                )
                self._log_msg(f"PDF 完了 → {pdf}")

            self._log_msg(
                f"✅ すべて完了 — {self._page_count} ページ  保存先: {save_dir}"
            )

        except Exception as e:
            self._log_msg(f"❌ エラー: {e}")
        finally:
            self._running = False
            self.after(0, self._on_done)

    def _update_page_label(self):
        total = self._pages_var.get()
        label = str(self._page_count) + (f" / {total}" if total else "") + " ページ"
        self._page_lbl.configure(text=label)

    def _on_done(self):
        self._progress.stop()
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status_lbl.configure(text="完了", fg=SUBTEXT)

    # ──────────────────────────────────────────────────────────────
    # 手動 PDF 生成
    # ──────────────────────────────────────────────────────────────
    def _build_pdf_manual(self):
        folder = filedialog.askdirectory(title="PNG が入っているフォルダを選択")
        if not folder:
            return
        try:
            from modules.pdf_builder import build_pdf
            self._log_msg("PDF 生成中…")
            pdf = build_pdf(folder, jpeg_quality=85, max_width=1800)
            self._log_msg(f"PDF 完了 → {pdf}")
            if messagebox.askyesno("完了", f"PDF をエクスプローラーで開きますか？\n{pdf}"):
                if sys.platform == "win32":
                    os.startfile(str(Path(pdf).parent))
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
