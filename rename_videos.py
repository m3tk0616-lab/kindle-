import os
import sys

# 正しい順番リスト（キーワードで照合）
ORDER = [
    ("01", "導入1"),
    ("02", "導入2"),
    ("03", "導入3"),
    ("04", "アップバーピー"),
    ("05", "VEIS"),
    ("06", "ベイルアウト1"),
    ("07", "ベイルアウト2"),
    ("08", "サーチ1"),
    ("09", "サーチ2"),
    ("10", "FFS3階～2階ベイルアウト1"),
    ("11", "セブンティーン"),
    ("12", "ベイルアウト3"),
    ("13", "サーチ3"),
    ("14", "FFS3階～ベイルアウト2"),
    ("15", "サーチ4"),
    ("16", "FFS3階～2階ベイルアウト4"),
    ("17", "機材デモ1"),
    ("18", "機材デモ2"),
    ("19", "機材デモ3"),
    ("20", "ラージエリア説明"),
    ("21", "ラージエリア1"),
    ("22", "ラージエリア2"),
    ("23", "想定1-1"),
    ("24", "想定1-2"),
    ("25", "想定2-1"),
    ("26", "想定2-2"),
    ("27", "想定2-3"),
    ("28", "想定2-4"),
    ("29", "まとめ"),
]

def find_match(filename, keyword):
    return keyword in filename

def main():
    folder = r"C:\Users\USER\Desktop\TOKAI　RIT\TOKAIRIT2日目"

    if not os.path.exists(folder):
        print(f"フォルダが見つかりません: {folder}")
        input("Enterで終了")
        sys.exit(1)

    files = [f for f in os.listdir(folder) if f.endswith(".mp4") or f.endswith(".avi")]

    print(f"ファイル数: {len(files)}\n")
    print("=== リネーム計画 ===")

    rename_plan = []
    unmatched = list(files)

    for num, keyword in ORDER:
        matched = None
        for f in unmatched:
            if find_match(f, keyword):
                matched = f
                break
        if matched:
            new_name = f"{num}_{matched}"
            rename_plan.append((matched, new_name))
            unmatched.remove(matched)
            print(f"  {matched}")
            print(f"    → {new_name}")
        else:
            print(f"  [{num}] ★未一致: '{keyword}' に対応するファイルが見つかりません")

    if unmatched:
        print(f"\n=== 未一致ファイル（そのまま） ===")
        for f in unmatched:
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
        src = os.path.join(folder, old)
        dst = os.path.join(folder, new)
        os.rename(src, dst)
        print(f"完了: {new}")

    print("\n全てのリネームが完了しました！")
    input("Enterで終了")

if __name__ == "__main__":
    main()
