import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import subprocess
import sys

PATTERNS = [
    {
        "name": "パターン1: H.264 Baseline + AAC-LC (標準)",
        "suffix": "_navi_p1",
        "ext": "mp4",
        "args": (
            "-vf scale=-2:480 "
            "-vcodec libx264 -profile:v baseline -level 3.0 -pix_fmt yuv420p "
            "-acodec aac -strict experimental -ac 2 -ar 44100 -b:a 128k "
            "-movflags +faststart"
        ),
    },
    {
        "name": "パターン2: H.264 Baseline + AAC-LC (低解像度 320x240)",
        "suffix": "_navi_p2",
        "ext": "mp4",
        "args": (
            "-vf scale=320:240 "
            "-vcodec libx264 -profile:v baseline -level 2.1 -pix_fmt yuv420p "
            "-acodec aac -strict experimental -ac 2 -ar 44100 -b:a 96k "
            "-movflags +faststart"
        ),
    },
    {
        "name": "パターン3: MPEG4 + AAC-LC",
        "suffix": "_navi_p3",
        "ext": "mp4",
        "args": (
            "-vf scale=-2:480 "
            "-vcodec mpeg4 -vtag xvid -q:v 5 "
            "-acodec aac -strict experimental -ac 2 -ar 44100 -b:a 128k "
            "-movflags +faststart"
        ),
    },
    {
        "name": "パターン4: DivX (AVI形式)",
        "suffix": "_navi_p4",
        "ext": "avi",
        "args": (
            "-vf scale=-2:480 "
            "-vcodec mpeg4 -vtag DX50 -q:v 5 "
            "-acodec mp3 -ac 2 -ar 44100 -b:a 128k"
        ),
    },
]

class NissanNaviTest:
    def __init__(self, root):
        self.root = root
        self.root.title("日産ナビ 動画変換テスター")
        self.root.geometry("680x550")
        self.converting = False
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # ファイル選択
        file_frame = ttk.LabelFrame(self.root, text="変換する動画ファイル")
        file_frame.pack(fill="x", **pad)

        self.src_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.src_var, width=55).pack(side="left", padx=5, pady=8)
        ttk.Button(file_frame, text="📁 参照", command=self._browse_file).pack(side="left")

        # 保存先
        save_frame = ttk.LabelFrame(self.root, text="変換ファイルの保存先")
        save_frame.pack(fill="x", **pad)

        self.save_var = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        ttk.Entry(save_frame, textvariable=self.save_var, width=55).pack(side="left", padx=5, pady=8)
        ttk.Button(save_frame, text="📁 参照", command=self._browse_save).pack(side="left")

        # パターン選択
        pattern_frame = ttk.LabelFrame(self.root, text="変換パターン（全て変換してナビで試してください）")
        pattern_frame.pack(fill="x", **pad)

        self.pattern_vars = []
        for p in PATTERNS:
            var = tk.BooleanVar(value=True)
            self.pattern_vars.append(var)
            ttk.Checkbutton(pattern_frame, text=p["name"], variable=var).pack(anchor="w", padx=10, pady=2)

        # 進捗
        progress_frame = ttk.LabelFrame(self.root, text="進捗")
        progress_frame.pack(fill="both", expand=True, **pad)

        self.status_label = ttk.Label(progress_frame, text="待機中")
        self.status_label.pack(anchor="w", padx=5, pady=2)

        self.progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate")
        self.progress_bar.pack(fill="x", padx=5, pady=3)

        self.log_text = scrolledtext.ScrolledText(progress_frame, height=7, font=("Consolas", 9), state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # ボタン
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", **pad)

        self.start_btn = ttk.Button(btn_frame, text="▶ 変換開始", command=self._start)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="■ 停止", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="保存先を開く", command=self._open_folder).pack(side="right", padx=5)

        # 説明ラベル
        note = ttk.Label(self.root,
            text="💡 変換後、4つのファイルをSDカードに入れてナビで再生→音が出たパターンが正解です",
            foreground="blue")
        note.pack(pady=5)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("動画ファイル", "*.mp4 *.mkv *.avi *.mov *.flv *.ts"), ("全ファイル", "*.*")]
        )
        if path:
            self.src_var.set(path)
            save_dir = os.path.dirname(path)
            self.save_var.set(save_dir)

    def _browse_save(self):
        folder = filedialog.askdirectory(initialdir=self.save_var.get())
        if folder:
            self.save_var.set(folder)

    def _open_folder(self):
        path = self.save_var.get()
        if os.path.exists(path):
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])

    def _log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _start(self):
        src = self.src_var.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showwarning("ファイル未選択", "変換する動画ファイルを選択してください。")
            return

        selected = [p for p, v in zip(PATTERNS, self.pattern_vars) if v.get()]
        if not selected:
            messagebox.showwarning("パターン未選択", "変換パターンを1つ以上選択してください。")
            return

        self.converting = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.start(10)

        thread = threading.Thread(target=self._worker, args=(src, selected), daemon=True)
        thread.start()

    def _worker(self, src, selected):
        save_dir = self.save_var.get()
        base = os.path.splitext(os.path.basename(src))[0]

        self._log(f"変換開始: {os.path.basename(src)}")
        self._log(f"保存先: {save_dir}\n")

        for i, p in enumerate(selected, 1):
            if not self.converting:
                self._log("停止しました。")
                break

            out_name = f"{base}{p['suffix']}.{p['ext']}"
            out_path = os.path.join(save_dir, out_name)

            self.root.after(0, self.status_label.configure,
                           {"text": f"({i}/{len(selected)}) {p['name']}"})
            self._log(f"[{i}/{len(selected)}] {p['name']}")
            self._log(f"  → {out_name}")

            cmd = f'ffmpeg -y -i "{src}" {p["args"]} "{out_path}"'

            try:
                proc = subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                self.current_proc = proc

                for line in proc.stdout:
                    line = line.rstrip()
                    if "time=" in line or "Error" in line or "error" in line:
                        self.root.after(0, self._log, f"  {line}")

                proc.wait()
                if proc.returncode == 0:
                    size = os.path.getsize(out_path) / (1024 * 1024)
                    self._log(f"  ✓ 完了 ({size:.1f} MB)\n")
                else:
                    self._log(f"  ✗ エラーが発生しました\n")
            except Exception as e:
                self._log(f"  ✗ 例外: {e}\n")

        self.root.after(0, self._finish)

    def _finish(self):
        self.converting = False
        self.progress_bar.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="完了")
        self._log("=" * 40)
        self._log("全パターンの変換が完了しました！")
        self._log("SDカードに入れてナビで再生テストしてください。")

    def _stop(self):
        self.converting = False
        if hasattr(self, "current_proc"):
            self.current_proc.terminate()
        self.stop_btn.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = NissanNaviTest(root)
    root.mainloop()
