import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import subprocess
import sys

class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("動画ダウンローダー")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        self.downloading = False
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # URL入力エリア
        url_frame = ttk.LabelFrame(self.root, text="URL入力（複数行対応）")
        url_frame.pack(fill="both", expand=True, **pad)

        self.url_text = scrolledtext.ScrolledText(url_frame, height=8, font=("Consolas", 10))
        self.url_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.url_text.insert("1.0", "ここにURLを1行ずつ貼り付けてください\nhttps://youtu.be/xxxx\nhttps://youtu.be/yyyy")
        self.url_text.bind("<FocusIn>", self._clear_placeholder)

        # 設定エリア
        settings_frame = ttk.LabelFrame(self.root, text="ダウンロード設定")
        settings_frame.pack(fill="x", **pad)

        # 画質
        ttk.Label(settings_frame, text="画質:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.quality_var = tk.StringVar(value="1080p")
        quality_cb = ttk.Combobox(settings_frame, textvariable=self.quality_var, width=10, state="readonly")
        quality_cb["values"] = ["最高画質", "1080p", "720p", "480p", "360p", "音声のみ(MP3)"]
        quality_cb.grid(row=0, column=1, padx=5, pady=5)

        # フォーマット
        ttk.Label(settings_frame, text="形式:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.format_var = tk.StringVar(value="MP4")
        format_cb = ttk.Combobox(settings_frame, textvariable=self.format_var, width=8, state="readonly")
        format_cb["values"] = ["MP4", "MKV", "MP3", "M4A", "日産ナビ用(MP4)"]
        format_cb.grid(row=0, column=3, padx=5, pady=5)

        # ファイル名テンプレート
        ttk.Label(settings_frame, text="ファイル名:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.filename_var = tk.StringVar(value="%(title)s.%(ext)s")
        ttk.Entry(settings_frame, textvariable=self.filename_var, width=20).grid(row=0, column=5, padx=5, pady=5)

        # 保存先
        save_frame = ttk.Frame(settings_frame)
        save_frame.grid(row=1, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        ttk.Label(save_frame, text="保存先:").pack(side="left")
        self.save_path_var = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        ttk.Entry(save_frame, textvariable=self.save_path_var, width=45).pack(side="left", padx=5)
        ttk.Button(save_frame, text="📁 参照", command=self._browse_folder).pack(side="left")

        # 進捗エリア
        progress_frame = ttk.LabelFrame(self.root, text="進捗")
        progress_frame.pack(fill="both", expand=True, **pad)

        self.status_label = ttk.Label(progress_frame, text="待機中")
        self.status_label.pack(anchor="w", padx=5)

        self.progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate")
        self.progress_bar.pack(fill="x", padx=5, pady=3)

        self.log_text = scrolledtext.ScrolledText(progress_frame, height=6, font=("Consolas", 9), state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # ボタン
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", **pad)

        self.download_btn = ttk.Button(btn_frame, text="▶ ダウンロード開始", command=self._start_download)
        self.download_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="■ 停止", command=self._stop_download, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="ログをクリア", command=self._clear_log).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="保存先を開く", command=self._open_folder).pack(side="right", padx=5)

    def _clear_placeholder(self, event):
        content = self.url_text.get("1.0", "end").strip()
        if content.startswith("ここにURLを"):
            self.url_text.delete("1.0", "end")

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if folder:
            self.save_path_var.set(folder)

    def _open_folder(self):
        path = self.save_path_var.get()
        if os.path.exists(path):
            os.startfile(path) if sys.platform == "win32" else subprocess.Popen(["xdg-open", path])

    def _get_urls(self):
        content = self.url_text.get("1.0", "end").strip()
        urls = [line.strip() for line in content.splitlines()
                if line.strip() and line.strip().startswith("http")]
        return urls

    def _build_yt_dlp_args(self):
        quality = self.quality_var.get()
        fmt = self.format_var.get()

        if quality == "音声のみ(MP3)" or fmt == "MP3":
            format_arg = "-x --audio-format mp3"
        elif fmt == "日産ナビ用(MP4)":
            # 日産キックス純正ナビ対応: H.264 Baseline Profile, AAC, MP4コンテナ
            format_arg = (
                "-f bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480] "
                "--merge-output-format mp4 "
                "--postprocessor-args \"-vcodec libx264 -profile:v baseline -level 3.0 "
                "-acodec aac -ar 44100 -b:a 128k -movflags +faststart\""
            )
        elif quality == "最高画質":
            format_arg = "-f bestvideo+bestaudio/best --merge-output-format mp4"
        else:
            height = quality.replace("p", "")
            format_arg = f"-f bestvideo[height<={height}]+bestaudio/best[height<={height}] --merge-output-format {fmt.lower()}"

        return format_arg

    def _log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _start_download(self):
        urls = self._get_urls()
        if not urls:
            messagebox.showwarning("URL未入力", "URLを1行ずつ入力してください。")
            return

        save_path = self.save_path_var.get()
        if not os.path.exists(save_path):
            try:
                os.makedirs(save_path)
            except Exception as e:
                messagebox.showerror("エラー", f"保存先の作成に失敗しました:\n{e}")
                return

        self.downloading = True
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.start(10)

        thread = threading.Thread(target=self._download_worker, args=(urls, save_path), daemon=True)
        thread.start()

    def _download_worker(self, urls, save_path):
        self._log(f"ダウンロード開始: {len(urls)}本")
        format_args = self._build_yt_dlp_args()
        filename = self.filename_var.get()

        for i, url in enumerate(urls, 1):
            if not self.downloading:
                self._log("停止しました。")
                break

            self.root.after(0, self.status_label.configure, {"text": f"({i}/{len(urls)}) {url}"})
            self._log(f"\n[{i}/{len(urls)}] {url}")

            cmd = (
                f'python -m yt_dlp {format_args} '
                f'-o "{os.path.join(save_path, filename)}" '
                f'--no-check-certificate '
                f'"{url}"'
            )

            try:
                proc = subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                self.current_proc = proc

                for line in proc.stdout:
                    line = line.rstrip()
                    if line and ("[download]" in line or "[info]" in line or "ERROR" in line):
                        self.root.after(0, self._log, line)

                proc.wait()
                if proc.returncode == 0:
                    self._log("✓ 完了")
                else:
                    self._log("✗ エラーが発生しました")
            except Exception as e:
                self._log(f"✗ 例外: {e}")

        self.root.after(0, self._finish)

    def _finish(self):
        self.downloading = False
        self.progress_bar.stop()
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="完了")
        self._log("\n全て完了しました！")

    def _stop_download(self):
        self.downloading = False
        if hasattr(self, "current_proc"):
            self.current_proc.terminate()
        self.stop_btn.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloader(root)
    root.mainloop()
