import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill, GradientFill
from openpyxl.utils import get_column_letter as gcl
import datetime

wb = openpyxl.Workbook()

# ─── Color palette ──────────────────────────────────────────
NAVY     = "1B3A6B"
NAVY2    = "243F60"
BLUE2    = "2E75B6"
STEEL    = "4472C4"
GOLD     = "B8860B"
LGOLD    = "F5DEB3"
DGOLD    = "996515"
WHITE    = "FFFFFF"
LGRAY    = "F5F5F5"
MGRAY    = "D0D0D0"
SAT_BG   = "D6E4FF"
SUN_BG   = "FFD6D6"
MATCH_BG = "FFFACD"
YOBI_BG  = "E8F5E9"
GREEN    = "155724"
GREEN_BG = "D4EDDA"
RED_C    = "721C24"
AMBER    = "FFF3CD"

# 飯詰チーム (team 2) 網掛け
IIZUME_FG  = "D97706"  # orange foreground
IIZUME_BG  = "FEF3C7"  # amber background

def mk_fill(c):
    return PatternFill(fgColor=c, fill_type="solid")

def mk_mesh(fg=IIZUME_FG, bg=IIZUME_BG):
    """網掛けパターン fill"""
    return PatternFill(patternType="lightTrellis", fgColor=fg, bgColor=bg)

def mk_font(bold=False, sz=10, color="000000", italic=False):
    return Font(bold=bold, size=sz, color=color, name="游ゴシック", italic=italic)

def mk_align(h="center", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def mk_border(l="thin", r="thin", t="thin", b="thin"):
    return Border(left=Side(style=l), right=Side(style=r),
                  top=Side(style=t), bottom=Side(style=b))

THIN = mk_border()
MED  = mk_border("medium","medium","medium","medium")

def sc(ws, row, col, val=None, bold=False, sz=10, color="000000",
       bg=None, h="center", v="center", bdr=None, wrap=False,
       fill=None, italic=False):
    c = ws.cell(row=row, column=col, value=val)
    c.font = mk_font(bold, sz, color, italic)
    c.alignment = mk_align(h, v, wrap)
    if fill: c.fill = fill
    elif bg:  c.fill = mk_fill(bg)
    if bdr:  c.border = bdr
    return c

def get_wd(y, m, d):
    return ["月","火","水","木","金","土","日"][datetime.date(y, m, d).weekday()]

# ─── Schedule Data (PDF通りの番号) ───────────────────────────
# (month, day) → (match_str, ref_str, is_reserve, has_iizume)
IIZUME = 2  # 飯詰チーム番号

raw_games = [
    (5,26, "1 ー 3",   "2・6",   False),
    (5,27, "5 ー 6",   "1・3",   False),
    (5,28, "2 ー 4",   "5・6",   False),
    (6, 2, "1 ー 6",   "2・4",   False),
    (6, 3, "2 ー 3",   "1・6",   False),
    (6, 4, "4 ー 5",   "2・3",   False),
    (6, 9, "1 ー 2",   "4・5",   False),
    (6,10, "3 ー 5",   "1・2",   False),
    (6,11, "4 ー 6",   "3・5",   False),
    (6,16, "予　備　日","",       True ),
    (6,17, "予　備　日","",       True ),
    (6,18, "予　備　日","",       True ),
    (6,23, "2 ー 5",   "4・6",   False),
    (6,24, "1 ー 4",   "2・5",   False),
    (6,25, "3 ー 6",   "1・4",   False),
    (6,30, "1 ー 5",   "3・6",   False),
    (7, 1, "3 ー 4",   "1・5",   False),
    (7, 2, "2 ー 6",   "3・4",   False),
]

# 飯詰が出場する日
IIZUME_DAYS = set()
for m, d, match, ref, reserve in raw_games:
    if not reserve and str(IIZUME) in match.split(" ー "):
        IIZUME_DAYS.add((m, d))

GAMES = {}
for m, d, match, ref, reserve in raw_games:
    GAMES[(m,d)] = (match, ref, reserve)

TEAM_NAMES = {1:"野宮塗装", 2:"飯詰", 3:"バッカス",
              4:"ウエスタン", 5:"富士電機", 6:"日産"}

GAME_LIST = [
    ("5/26(火)", 1, 3), ("5/27(水)", 5, 6), ("5/28(木)", 2, 4),
    ("6/2(火)",  1, 6), ("6/3(水)",  2, 3), ("6/4(木)",  4, 5),
    ("6/9(火)",  1, 2), ("6/10(水)", 3, 5), ("6/11(木)", 4, 6),
    ("6/23(火)", 2, 5), ("6/24(水)", 1, 4), ("6/25(木)", 3, 6),
    ("6/30(火)", 1, 5), ("7/1(水)",  3, 4), ("7/2(木)",  2, 6),
]

# ═══════════════════════════════════════════════════════════
#  SHEET 1: 日程表
# ═══════════════════════════════════════════════════════════
ws1 = wb.active
ws1.title = "日程表"

ws1.page_setup.orientation   = "landscape"
ws1.page_setup.paperSize     = 9
ws1.sheet_properties.pageSetUpPr.fitToPage = True
ws1.page_setup.fitToWidth    = 1
ws1.page_setup.fitToHeight   = 1
ws1.print_area               = "A1:N38"
ws1.page_margins.left = ws1.page_margins.right  = 0.4
ws1.page_margins.top  = ws1.page_margins.bottom = 0.4

# 列幅: A-D(5月) | E(仕切) | F-I(6月) | J(仕切) | K-N(7月)
for col, w in zip(range(1,15),
                  [4.5, 4.5, 20, 15,  1.2,
                   4.5, 4.5, 20, 15,  1.2,
                   4.5, 4.5, 20, 15]):
    ws1.column_dimensions[gcl(col)].width = w

ws1.row_dimensions[1].height = 40
ws1.row_dimensions[2].height = 22
ws1.row_dimensions[3].height = 16
for r in range(4, 39):
    ws1.row_dimensions[r].height = 15

# ── Row 1: タイトル ──
ws1.merge_cells("A1:N1")
c = ws1.cell(1, 1, "令　和　８　年　　朝　野　球　日　程　表")
c.font      = mk_font(True, 22, WHITE)
c.alignment = mk_align()
c.fill      = mk_fill(NAVY)
c.border    = MED

# ── Row 2: 月ヘッダー ──
for s, e, label in [("A","D","５　月"),("F","I","６　月"),("K","N","７　月")]:
    ws1.merge_cells(f"{s}2:{e}2")
    c = ws1[f"{s}2"]
    c.value     = label
    c.font      = mk_font(True, 14, WHITE)
    c.alignment = mk_align()
    c.fill      = mk_fill(STEEL)
    c.border    = THIN

# ── Row 3: サブヘッダー ──
for base in [1, 6, 11]:
    for j, h in enumerate(["日","曜","対　戦　チ　ー　ム","審　判"]):
        sc(ws1, 3, base+j, h, bold=True, sz=9, color=WHITE,
           bg=NAVY, bdr=THIN)

# ── 仕切り列 (E=5, J=10) ──
for r in range(1, 39):
    for col in [5, 10]:
        ws1.cell(r, col).fill   = mk_fill(NAVY)
        ws1.cell(r, col).border = mk_border("medium","medium","thin","thin")

# ── 日程データ ──
MONTH_DAYS = {5:31, 6:30, 7:31}
MONTH_BASE = {5:1,  6:6,  7:11}

for month, num_days in MONTH_DAYS.items():
    base = MONTH_BASE[month]
    for day in range(1, num_days+1):
        row  = day + 3
        wd   = get_wd(2026, month, day)
        game = GAMES.get((month, day))
        is_iizume = (month, day) in IIZUME_DAYS

        # 背景色決定
        if is_iizume:
            cell_fill = mk_mesh()           # 飯詰 → 網掛け
        elif wd == "日":
            cell_fill = mk_fill(SUN_BG)
        elif wd == "土":
            cell_fill = mk_fill(SAT_BG)
        elif game and not game[2]:          # 試合あり
            cell_fill = mk_fill(MATCH_BG)
        elif game and game[2]:              # 予備日
            cell_fill = mk_fill(YOBI_BG)
        else:
            cell_fill = mk_fill(WHITE if day % 2 == 1 else LGRAY)

        # 日番号
        c = ws1.cell(row=row, column=base, value=day)
        c.font      = mk_font(False, 10, NAVY)
        c.alignment = mk_align()
        c.fill      = cell_fill
        c.border    = THIN

        # 曜日
        wd_color = "CC0000" if wd=="日" else ("003399" if wd=="土" else NAVY)
        c = ws1.cell(row=row, column=base+1, value=wd)
        c.font      = mk_font(wd in "土日", 10, wd_color)
        c.alignment = mk_align()
        c.fill      = cell_fill
        c.border    = THIN

        # 対戦チーム
        match_val = game[0] if game else None
        is_res    = game[2] if game else False
        c = ws1.cell(row=row, column=base+2, value=match_val)
        c.font      = mk_font(bool(match_val) and not is_res, 10, NAVY)
        c.alignment = mk_align()
        c.fill      = cell_fill
        c.border    = THIN

        # 審判
        ref_val = game[1] if game else None
        c = ws1.cell(row=row, column=base+3, value=ref_val if ref_val else None)
        c.font      = mk_font(False, 9, "444444")
        c.alignment = mk_align()
        c.fill      = cell_fill
        c.border    = THIN

# ── 凡例行 ──
ws1.row_dimensions[36].height = 13
for s, e, label, bg in [
    ("A","B","■ 飯詰出場",None),
    ("C","D","■ 試合",MATCH_BG),
    ("F","G","■ 予備日",YOBI_BG),
    ("H","I","■ 土曜",SAT_BG),
    ("K","L","■ 日曜",SUN_BG),
]:
    ws1.merge_cells(f"{s}36:{e}36")
    c = ws1[f"{s}36"]
    c.value     = label
    c.font      = mk_font(False, 7, NAVY)
    c.alignment = mk_align("left")
    if bg:
        c.fill = mk_fill(bg)
    else:
        c.fill = mk_mesh()  # 飯詰凡例

# ── 試合規則フッター ──
ws1.row_dimensions[37].height = 14
ws1.merge_cells("A37:N37")
c = ws1.cell(37, 1,
    "◆ メンバー表交換 5:10　◆ 試合時間 5:15～6:45　"
    "◆ 6:40を超えて新しいイニングには入らない　◆ 捕手は防具着用で整列")
c.font      = mk_font(False, 8, WHITE)
c.alignment = mk_align("left")
c.fill      = mk_fill(NAVY)

# ── チーム番号対照表 ──
ws1.column_dimensions["P"].width = 1.5
ws1.column_dimensions["Q"].width = 4.5
ws1.column_dimensions["R"].width = 13

ws1.merge_cells("Q1:R1")
c = ws1.cell(1, 17)
c.value="チーム番号一覧"
c.font=mk_font(True,10,WHITE); c.alignment=mk_align(); c.fill=mk_fill(NAVY); c.border=THIN

ws1.merge_cells("Q2:R2")
c = ws1.cell(2, 17)
c.value="No.  チーム名"
c.font=mk_font(True,9,WHITE); c.alignment=mk_align("left"); c.fill=mk_fill(STEEL); c.border=THIN

for i, name in TEAM_NAMES.items():
    row = i + 2
    is_iizume_team = (i == IIZUME)
    team_fill = mk_mesh() if is_iizume_team else mk_fill(WHITE if i%2==1 else LGRAY)

    c = ws1.cell(row=row, column=17, value=i)
    c.font=mk_font(True, 10, NAVY); c.alignment=mk_align(); c.fill=mk_fill(LGOLD); c.border=THIN

    ws1.merge_cells(f"R{row}:R{row}")
    c = ws1.cell(row=row, column=18, value=("★ " if is_iizume_team else "") + name)
    c.font=mk_font(is_iizume_team, 10, NAVY); c.alignment=mk_align("left")
    c.fill=team_fill; c.border=THIN

# ═══════════════════════════════════════════════════════════
#  SHEET 2: 勝敗表  (構造そのまま・デザイン刷新)
# ═══════════════════════════════════════════════════════════
ws2 = wb.create_sheet("勝敗表")

ws2.page_setup.orientation   = "landscape"
ws2.page_setup.paperSize     = 9
ws2.sheet_properties.pageSetUpPr.fitToPage = True
ws2.page_setup.fitToWidth    = 1
ws2.page_setup.fitToHeight   = 1
ws2.print_area               = "A1:U30"
ws2.page_margins.left = ws2.page_margins.right  = 0.5
ws2.page_margins.top  = ws2.page_margins.bottom = 0.5

# 列幅
for col, w in zip(range(1, 22),
    [4, 16, 1.5, 9, 14, 5.5, 5.5, 14, 5.5, 5.5, 1.5,
     4, 16,  5,  5,  5,  6,   6,   6,   6,   6]):
    ws2.column_dimensions[gcl(col)].width = w

ws2.row_dimensions[1].height = 44
ws2.row_dimensions[2].height = 8   # 細いスペーサー
ws2.row_dimensions[3].height = 22
ws2.row_dimensions[4].height = 16

for r in range(5, 35):
    ws2.row_dimensions[r].height = 19

# ── Row 1: タイトル ──
ws2.merge_cells("A1:U1")
c = ws2.cell(1, 1, "令　和　８　年　　朝　野　球　リ ー グ　勝　敗　表")
c.font      = mk_font(True, 24, WHITE)
c.alignment = mk_align()
c.fill      = mk_fill(NAVY)
c.border    = MED

# ── Row 2: 飾り帯 ──
ws2.merge_cells("A2:U2")
c = ws2.cell(2, 1)
c.fill = mk_fill(GOLD)

# ── Row 3: セクションヘッダー 3列 ──
ws2.merge_cells("A3:B3")
c = ws2.cell(3, 1, "▶  チーム登録")
c.font=mk_font(True,11,WHITE); c.alignment=mk_align("left")
c.fill=mk_fill(STEEL); c.border=THIN

ws2.merge_cells("D3:J3")
c = ws2.cell(3, 4, "▶  試合結果入力（黄色セルに得点を入力）")
c.font=mk_font(True,11,WHITE); c.alignment=mk_align("left")
c.fill=mk_fill(STEEL); c.border=THIN

ws2.merge_cells("L3:U3")
c = ws2.cell(3, 12, "▶  成　績　表　（自動集計）")
c.font=mk_font(True,11,WHITE); c.alignment=mk_align()
c.fill=mk_fill(NAVY); c.border=THIN

# ── Row 4: サブヘッダー ──
# チーム登録
sc(ws2, 4, 1, "No.", bold=True, sz=9, color=WHITE, bg=NAVY2, bdr=THIN)
sc(ws2, 4, 2, "チーム名", bold=True, sz=9, color=WHITE, bg=NAVY2, bdr=THIN)

# 試合結果
for col, h, bg in [
    (4,"日付",NAVY2),(5,"チームA",NAVY2),(6,"得点A",DGOLD),
    (7,"得点B",DGOLD),(8,"チームB",NAVY2),(9,"結果A",NAVY2),(10,"結果B",NAVY2)]:
    sc(ws2, 4, col, h, bold=True, sz=9, color=WHITE, bg=bg, bdr=THIN)

# 成績表ヘッダー
for col, h in zip(range(12,22),
    ["No.","チーム名","勝","分","敗","勝点","得点","失点","残試合","順位"]):
    sc(ws2, 4, col, h, bold=True, sz=9, color=WHITE, bg=NAVY2, bdr=THIN)

# ── Rows 5-10: チーム登録 & 試合結果 & 成績表 ──
team_as_A = {t:[] for t in range(1,7)}
team_as_B = {t:[] for t in range(1,7)}

LOOKUP_LOCAL = "$A$5:$B$10"

for idx, (date_str, ta, tb) in enumerate(GAME_LIST):
    game_row = idx + 5
    team_as_A[ta].append(game_row)
    team_as_B[tb].append(game_row)

for i, name in TEAM_NAMES.items():
    reg_row = i + 4  # rows 5-10
    is_iizume_team = (i == IIZUME)
    stripe = mk_mesh() if is_iizume_team else mk_fill(WHITE if i%2==1 else LGRAY)

    # チーム登録欄
    c = ws2.cell(row=reg_row, column=1, value=i)
    c.font=mk_font(True,13,NAVY); c.alignment=mk_align()
    c.fill=mk_fill(LGOLD); c.border=mk_border("medium","thin","thin","thin")

    c = ws2.cell(row=reg_row, column=2, value=name)
    c.font=mk_font(True,13,NAVY if not is_iizume_team else DGOLD)
    c.alignment=mk_align("left"); c.fill=stripe
    c.border=mk_border("thin","medium","thin","thin")

# ── 試合結果入力 & 成績表 同時に ──
for idx, (date_str, ta, tb) in enumerate(GAME_LIST):
    game_row = idx + 5
    bg_stripe = mk_fill(WHITE if idx%2==0 else LGRAY)

    # 日付
    c = ws2.cell(row=game_row, column=4, value=date_str)
    c.font=mk_font(False,10,NAVY); c.alignment=mk_align(); c.fill=bg_stripe; c.border=THIN

    # チームA名
    c = ws2.cell(row=game_row, column=5,
                 value=f'=IFERROR(VLOOKUP({ta},{LOOKUP_LOCAL},2,0),"{ta}")')
    c.font=mk_font(True,10,NAVY); c.alignment=mk_align(); c.fill=bg_stripe; c.border=THIN

    # 得点A入力セル（黄色）
    c = ws2.cell(row=game_row, column=6)
    c.font=mk_font(True,14,NAVY); c.alignment=mk_align()
    c.fill=mk_fill("FFFACD"); c.border=MED

    # 得点B入力セル（黄色）
    c = ws2.cell(row=game_row, column=7)
    c.font=mk_font(True,14,NAVY); c.alignment=mk_align()
    c.fill=mk_fill("FFFACD"); c.border=MED

    # チームB名
    c = ws2.cell(row=game_row, column=8,
                 value=f'=IFERROR(VLOOKUP({tb},{LOOKUP_LOCAL},2,0),"{tb}")')
    c.font=mk_font(True,10,NAVY); c.alignment=mk_align(); c.fill=bg_stripe; c.border=THIN

    # 結果A
    r = game_row
    c = ws2.cell(r, 9,
        f'=IF(F{r}="","",IF(F{r}>G{r},"○",IF(F{r}=G{r},"△","×")))')
    c.font=mk_font(True,13,NAVY); c.alignment=mk_align(); c.fill=bg_stripe; c.border=THIN

    # 結果B
    c = ws2.cell(r, 10,
        f'=IF(G{r}="","",IF(G{r}>F{r},"○",IF(G{r}=F{r},"△","×")))')
    c.font=mk_font(True,13,NAVY); c.alignment=mk_align(); c.fill=bg_stripe; c.border=THIN

# ── 成績表 (rows 5-10) ──
for t in range(1, 7):
    s_row = t + 4  # rows 5-10
    is_iizume_team = (t == IIZUME)
    bg = mk_mesh() if is_iizume_team else mk_fill(WHITE if t%2==1 else LGRAY)

    # No.
    c = ws2.cell(s_row, 12, t)
    c.font=mk_font(True,11,NAVY); c.alignment=mk_align()
    c.fill=mk_fill(LGOLD); c.border=THIN

    # チーム名
    c = ws2.cell(s_row, 13,
                 f'=IFERROR(VLOOKUP({t},{LOOKUP_LOCAL},2,0),"")')
    c.font=mk_font(True,12,DGOLD if is_iizume_team else NAVY)
    c.alignment=mk_align("left"); c.fill=bg; c.border=THIN

    # 勝/分/敗 計算
    rows_a = team_as_A[t]
    rows_b = team_as_B[t]

    def calc(rows_a, rows_b, ca, cb, sym):
        parts = ([f'IF({gcl(ca)}{r}="{sym}",1,0)' for r in rows_a] +
                 [f'IF({gcl(cb)}{r}="{sym}",1,0)' for r in rows_b])
        return "=" + "+".join(parts) if parts else "=0"

    win_f  = calc(rows_a, rows_b, 9, 10, "○")
    draw_f = calc(rows_a, rows_b, 9, 10, "△")
    loss_f = calc(rows_a, rows_b, 9, 10, "×")

    for col, formula, txt_color in [
        (14, win_f,  GREEN),
        (15, draw_f, NAVY),
        (16, loss_f, RED_C),
    ]:
        c = ws2.cell(s_row, col, formula)
        c.font=mk_font(True,12,txt_color); c.alignment=mk_align()
        c.fill=bg; c.border=THIN

    # 勝点
    c = ws2.cell(s_row, 17, f'={gcl(14)}{s_row}*3+{gcl(15)}{s_row}')
    c.font=mk_font(True,14,NAVY); c.alignment=mk_align(); c.fill=bg; c.border=THIN

    # 得点
    rs = ("=" + "+".join([f'IF(F{r}<>"",F{r},0)' for r in rows_a] +
                         [f'IF(G{r}<>"",G{r},0)' for r in rows_b])
          if rows_a or rows_b else "=0")
    c = ws2.cell(s_row, 18, rs)
    c.font=mk_font(False,11,NAVY); c.alignment=mk_align(); c.fill=bg; c.border=THIN

    # 失点
    ra = ("=" + "+".join([f'IF(G{r}<>"",G{r},0)' for r in rows_a] +
                         [f'IF(F{r}<>"",F{r},0)' for r in rows_b])
          if rows_a or rows_b else "=0")
    c = ws2.cell(s_row, 19, ra)
    c.font=mk_font(False,11,NAVY); c.alignment=mk_align(); c.fill=bg; c.border=THIN

    # 残試合
    c = ws2.cell(s_row, 20,
                 f'=5-{gcl(14)}{s_row}-{gcl(15)}{s_row}-{gcl(16)}{s_row}')
    c.font=mk_font(False,11,NAVY); c.alignment=mk_align(); c.fill=bg; c.border=THIN

    # 順位（勝点基準）
    c = ws2.cell(s_row, 21,
                 f'=IFERROR(RANK(Q{s_row},$Q$5:$Q$10,0),"")')
    c.font=mk_font(True,15,GOLD if not is_iizume_team else DGOLD)
    c.alignment=mk_align(); c.fill=bg; c.border=THIN

# ── 仕切り列 C=3, K=11 ──
for r in range(1, 31):
    for col in [3, 11]:
        ws2.cell(r, col).fill   = mk_fill(GOLD)
        ws2.cell(r, col).border = mk_border("thin","thin","thin","thin")

# ── 空行 rows 11-19 (試合数が15なのでrow5-19まで使うため調整) ──
# 試合は rows 5-19 (15試合), 成績は rows 5-10
# rows 11-19 の col A-B, L-U は空欄でOK
for r in range(11, 20):
    ws2.row_dimensions[r].height = 19
    for col in range(12, 22):
        ws2.cell(r, col).fill   = mk_fill(LGRAY)
        ws2.cell(r, col).border = THIN

# ── フッター ──
ws2.row_dimensions[20].height = 8
ws2.row_dimensions[21].height = 14
ws2.merge_cells("A21:U21")
c = ws2.cell(21, 1,
    "※ 黄色セルに得点を入力 → 勝敗・成績表が自動更新　"
    "◆ 降雨中止は「☂」と入力　◆ チーム名はA列に名前を入力すれば全体に反映")
c.font=mk_font(False,8,WHITE); c.alignment=mk_align("left")
c.fill=mk_fill(NAVY)

# ── 凡例 ──
ws2.row_dimensions[22].height = 16
ws2.merge_cells("A22:B22")
c = ws2.cell(22, 1, "★ 飯　詰　チーム")
c.font=mk_font(True,9,DGOLD); c.alignment=mk_align()
c.fill=mk_mesh(); c.border=THIN

ws2.merge_cells("D22:E22")
c = ws2.cell(22, 4, "■ 勝　点 = 勝×3 + 分×1")
c.font=mk_font(False,8,NAVY); c.alignment=mk_align("left")
c.fill=mk_fill(LGRAY); c.border=THIN

# ─── 保存 ──────────────────────────────────────────────────
output_path = "/home/user/kindle-/schedule_2026_v3.xlsx"
wb.save(output_path)
print(f"Done: {output_path}")
