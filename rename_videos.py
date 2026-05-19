import os
import sys
import subprocess

FOLDER = r"C:\Users\USER\Desktop\TOKAI　RIT\TOKAIRIT2日目"

# 正しい順番のURL一覧
VIDEOS = [
    ("01", "導入1(TOKAI式サーチ)day2",    "https://youtu.be/tMiNts3eaxI"),
    ("02", "導入2(TOKAI式サーチ)day2",    "https://youtu.be/sj7pHP8Ybs8"),
    ("03", "導入3(デンバー)day2",          "https://youtu.be/lmgpZ3z0Krg"),
    ("04", "アップバーピーday2",           "https://youtu.be/vzOR3-MGLes"),
    ("05", "VEISデンバー1day2",            "https://youtu.be/9WsxXNLb92U"),
    ("06", "ベイルアウト1day2",            "https://youtu.be/ZwNw8DXZQYQ"),
    ("07", "ベイルアウト2day2",            "https://youtu.be/dPPa1NbLcyY"),
    ("08", "サーチ1day2",                  "https://youtu.be/64elf63maPY"),
    ("09", "サーチ2day2",                  "https://youtu.be/6c-QHhll3mY"),
    ("10", "FFS3階～2階ベイルアウト1day2", "https://youtu.be/q0ebHGBe37k"),
    ("11", "セブンティーンday2",           "https://youtu.be/B9dqPXc0IOY"),
    ("12", "ベイルアウト3day2",            "https://youtu.be/A8Em8mRsQJ0"),
    ("13", "サーチ3day2",                  "https://youtu.be/6RQUAo6-B44"),
    ("14", "FFS3階～ベイルアウト2day2",    "https://youtu.be/1XpFGHvZb3o"),
    ("15", "サーチ4day2",                  "https://youtu.be/jTeCEgo7Tfo"),
    ("16", "FFS3階～2階ベイルアウト4day2", "https://youtu.be/eE_jBdMslfE"),
    ("17", "Heavy Rescue Japan機材デモ1day2", "https://youtu.be/S_XDSLKjQQs"),
    ("18", "Heavy Rescue Japan機材デモ2day2", "https://youtu.be/pMzlJstN1p4"),
    ("19", "Heavy Rescue Japan機材デモ3day2", "https://youtu.be/18pW1mNdIyE"),
    ("20", "ラージエリア説明day2",         "https://youtu.be/usrjxepjIo4"),
    ("21", "ラージエリア1day2",            "https://youtu.be/Is6eTg5wcCI"),
    ("22", "ラージエリア2day2",            "https://youtu.be/MygcjFdlauU"),
    ("23", "想定1-1",                      "https://youtu.be/gsCusW_6_hg"),
    ("24", "想定1-2",                      "https://youtu.be/PdxDOSQSyQM"),
    ("25", "想定2-1",                      "https://youtu.be/rGBxIfDEN-s"),
    ("26", "想定2-2",                      "https://youtu.be/t6Z9rqtDSec"),
    ("27", "想定2-3",                      "https://youtu.be/zDOwKm_XpPs"),
    ("28", "想定2-4",                      "https://youtu.be/De1YWre99iM"),
    ("29", "まとめ",                       "https://youtu.be/LZKKQy-iWPY"),
]

def get_video_id(url):
    return url.split("/")[-1].split("?")[0]

def get_title_from_yt_dlp(url):
    try:
        result = subprocess.run(
            ["python", "-m", "yt_dlp", "--get-title", "--no-playlist", url],
            capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        title = result.stdout.strip().splitlines()[0] if result.stdout.strip() else None
        return title
    except Exception:
        return None

def find_file_by_title(files, title):
    if not title:
        return None
    title_lower = title.lower()
    for f in files:
        name = os.path.splitext(f)[0].lower()
        if name == title_lower:
            return f
        # 部分一致（タイトルの先頭20文字で照合）
        if title_lower[:20] in name or name[:20] in title_lower:
            return f
    return None

def main():
    if not os.path.exists(FOLDER):
        print(f"フォルダが見つかりません:\n{FOLDER}")
        input("Enterで終了")
        sys.exit(1)

    files = [f for f in os.listdir(FOLDER)
             if f.lower().endswith((".mp4", ".avi", ".mkv"))
             and not f[0].isdigit()]  # すでに番号付きはスキップ

    if not files:
        print("リネーム対象のファイルがありません（すでに番号付きかも）")
        input("Enterで終了")
        return

    print(f"フォルダ内のファイル数: {len(files)}")
    print("YouTubeからタイトルを取得してファイルを照合します...\n")

    rename_plan = []
    unmatched_nums = []

    for num, label, url in VIDEOS:
        print(f"[{num}] {label} ... ", end="", flush=True)
        title = get_title_from_yt_dlp(url)

        if title:
            matched = find_file_by_title(files, title)
        else:
            matched = None

        if matched:
            ext = os.path.splitext(matched)[1]
            new_name = f"{num}_{label}{ext}"
            rename_plan.append((matched, new_name))
            files.remove(matched)
            print(f"✓ {matched}")
        else:
            unmatched_nums.append((num, label, title))
            print(f"✗ 見つからず (取得タイトル: {title})")

    print("\n=== リネーム計画 ===")
    for old, new in rename_plan:
        print(f"  {old}\n    → {new}")

    if unmatched_nums:
        print("\n=== 未一致 ===")
        for num, label, title in unmatched_nums:
            print(f"  [{num}] {label}  (YouTube取得タイトル: {title})")

    if files:
        print("\n=== 照合できなかったファイル ===")
        for f in files:
            print(f"  {f}")

    if not rename_plan:
        print("\nリネームするファイルがありませんでした。")
        input("Enterで終了")
        return

    print(f"\n{len(rename_plan)}件をリネームします。よろしいですか？ (y/n): ", end="")
    ans = input().strip().lower()

    if ans != "y":
        print("キャンセルしました。")
        input("Enterで終了")
        return

    for old, new in rename_plan:
        src = os.path.join(FOLDER, old)
        dst = os.path.join(FOLDER, new)
        os.rename(src, dst)
        print(f"完了: {new}")

    print("\n全てのリネームが完了しました！")
    input("Enterで終了")

if __name__ == "__main__":
    main()
