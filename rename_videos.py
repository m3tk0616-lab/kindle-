import os
import sys

FOLDER = r"C:\Users\USER\Desktop\TOKAI　RIT\TOKAIRIT2日目"

def main():
    if not os.path.exists(FOLDER):
        print(f"フォルダが見つかりません:\n{FOLDER}")
        input("Enterで終了")
        sys.exit(1)

    files = sorted(
        [f for f in os.listdir(FOLDER)
         if f.lower().endswith((".mp4", ".avi", ".mkv"))
         and not f[0].isdigit()],
        key=lambda f: os.path.getctime(os.path.join(FOLDER, f))
    )

    if not files:
        print("リネーム対象のファイルがありません（すでに番号付きかも）")
        input("Enterで終了")
        return

    print("=== リネーム計画（作成日時順）===\n")
    rename_plan = []
    for i, f in enumerate(files, 1):
        num = f"{i:02d}"
        new_name = f"{num}_{f}"
        rename_plan.append((f, new_name))
        print(f"  {f}")
        print(f"    → {new_name}\n")

    print(f"{len(rename_plan)}件をリネームします。よろしいですか？ (y/n): ", end="")
    ans = input().strip().lower()

    if ans != "y":
        print("キャンセルしました。")
        input("Enterで終了")
        return

    for old, new in rename_plan:
        os.rename(os.path.join(FOLDER, old), os.path.join(FOLDER, new))
        print(f"完了: {new}")

    print("\n全てのリネームが完了しました！")
    input("Enterで終了")

if __name__ == "__main__":
    main()
