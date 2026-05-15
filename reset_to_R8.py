import openpyxl
from openpyxl.cell.cell import MergedCell
import datetime

SRC = "/root/.claude/uploads/5a98ff47-aadd-49b8-9dad-a8d2f564f977/3ab50f35-__7________.xlsx"
DST = "/home/user/kindle-/schedule_R8.xlsx"

wb = openpyxl.load_workbook(SRC)

def safe_set(ws, row, col, value):
    """Set cell value, skipping merged (read-only) cells."""
    cell = ws.cell(row, col)
    if isinstance(cell, MergedCell):
        return False
    cell.value = value
    return True

# ════════════════════════════════════════════
# リーグ勝敗表 — リセット & 令和8年チーム差替
# ════════════════════════════════════════════
ws = wb["リーグ勝敗表"]

# 1) 入力スコアを全クリア (E列〜AK列, 数値のみ — 数式は触らない)
for row in ws.iter_rows(min_row=6, max_row=27, min_col=5, max_col=37):
    for cell in row:
        if isinstance(cell, MergedCell):
            continue
        if isinstance(cell.value, (int, float)):
            cell.value = None

# 2) チームリスト (BA列) を令和8年6チームに差替
new_teams = ["野宮塗装", "飯詰", "バッカス", "ウエスタン", "富士電機", "日産"]
for i, name in enumerate(new_teams):
    safe_set(ws, 6+i, 53, name)  # BA = col 53
# 7番以降はクリア
for r in range(12, 21):
    safe_set(ws, r, 53, None)

# 3) 出場チーム番号 (AW列=49) を 1〜6 に
team_slots = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26]
for i, r in enumerate(team_slots):
    safe_set(ws, r, 49, (i + 1) if i < 6 else None)

# ════════════════════════════════════════════
# 日程表１ — 年度・曜日・対戦表を令和8年に
# ════════════════════════════════════════════
ws1 = wb["日程表１"]
safe_set(ws1, 1, 1, "R8朝野球日程表")
safe_set(ws1, 1, 20, 2026)

# 曜日列を2026年で再計算
WD = ["月","火","水","木","金","土","日"]
weekday_setup = [(2, 5), (8, 6), (14, 7), (20, 8)]  # (列, 月)

for row in range(4, 35):
    day = row - 3
    for col, month in weekday_setup:
        try:
            d = datetime.date(2026, month, day)
            safe_set(ws1, row, col, WD[d.weekday()])
        except ValueError:
            safe_set(ws1, row, col, None)

# 対戦・審判列
match_cols = {
    5: (3, 5, 6),    # 5月: C, E, F
    6: (9, 11, 12),  # 6月: I, K, L
    7: (15, 17, 18), # 7月: O, Q, R
    8: (21, 23, 24), # 8月: U, W, X
}
sep_cols = {5: 4, 6: 10, 7: 16, 8: 22}  # ー separator cols

# 既存の対戦データを全クリア
for month, (ca, cb, cr) in match_cols.items():
    for row in range(4, 35):
        safe_set(ws1, row, ca, None)
        safe_set(ws1, row, cb, None)
        safe_set(ws1, row, cr, None)

# 令和8年 PDF スケジュール
GAMES = {
    (5,26): (1, 3, "2-6"),
    (5,27): (5, 6, "1-3"),
    (5,28): (2, 4, "5-6"),
    (6, 2): (1, 6, "2-4"),
    (6, 3): (2, 3, "1-6"),
    (6, 4): (4, 5, "2-3"),
    (6, 9): (1, 2, "4-5"),
    (6,10): (3, 5, "1-2"),
    (6,11): (4, 6, "3-5"),
    (6,16): "予備日",
    (6,17): "予備日",
    (6,18): "予備日",
    (6,23): (2, 5, "4-6"),
    (6,24): (1, 4, "2-5"),
    (6,25): (3, 6, "1-4"),
    (6,30): (1, 5, "3-6"),
    (7, 1): (3, 4, "1-5"),
    (7, 2): (2, 6, "3-4"),
}

def write_match(ws, row, month, data):
    ca, cb, cr = match_cols[month]
    sc = sep_cols[month]
    if data == "予備日":
        safe_set(ws, row, ca, "予備日")
        safe_set(ws, row, sc, None)
        safe_set(ws, row, cb, None)
        safe_set(ws, row, cr, None)
    else:
        ta, tb, ref = data
        safe_set(ws, row, ca, ta)
        safe_set(ws, row, cb, tb)
        safe_set(ws, row, cr, ref)

for (month, day), data in GAMES.items():
    write_match(ws1, day + 3, month, data)

# ════════════════════════════════════════════
# 日程表２ — 同じスケジュールを反映
# ════════════════════════════════════════════
ws2 = wb["日程表２"]
for month, (ca, cb, cr) in match_cols.items():
    for row in range(4, 35):
        safe_set(ws2, row, ca, None)
        safe_set(ws2, row, cb, None)
        safe_set(ws2, row, cr, None)

for (month, day), data in GAMES.items():
    write_match(ws2, day + 3, month, data)

wb.save(DST)
print(f"Saved: {DST}")
