import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter as gcl
import datetime

wb = openpyxl.Workbook()

# ─── Color palette ───────────────────────────────────────────────
NAVY    = "1B3A6B"
BLUE2   = "2E75B6"
GOLD    = "B8860B"
LGOLD   = "F5DEB3"
WHITE   = "FFFFFF"
LGRAY   = "F2F2F2"
MGRAY   = "D0D0D0"
SAT_BG  = "D6E4FF"
SUN_BG  = "FFD6D6"
MATCH_BG= "FFFACD"
YOBI_BG = "E8F5E9"
GREEN   = "006400"
RED     = "990000"
AMBER   = "FFFDE7"

def mk_fill(c): return PatternFill(fgColor=c, fill_type="solid")
def mk_font(bold=False, sz=10, color="000000"):
    return Font(bold=bold, size=sz, color=color, name="游ゴシック")
def mk_align(h="center", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)
def mk_side(s="thin"): return Side(style=s)
def mk_border(l="thin", r="thin", t="thin", b="thin"):
    return Border(left=mk_side(l), right=mk_side(r),
                  top=mk_side(t), bottom=mk_side(b))

THIN   = mk_border()
MED    = mk_border("medium","medium","medium","medium")
MED_R  = mk_border("thin","medium","thin","thin")
MED_L  = mk_border("medium","thin","thin","thin")

def sc(ws, row, col, val=None, bold=False, sz=10, color="000000",
       bg=None, h="center", v="center", bdr=None, wrap=False):
    c = ws.cell(row=row, column=col, value=val)
    c.font = mk_font(bold, sz, color)
    c.alignment = mk_align(h, v, wrap)
    if bg:  c.fill = mk_fill(bg)
    if bdr: c.border = bdr
    return c

def get_wd(y, m, d):
    return ["月","火","水","木","金","土","日"][datetime.date(y, m, d).weekday()]

# ─── Schedule Data ─────────────────────────────────────────────
LOOKUP = "勝敗表!$A$3:$B$8"

def mf(a, b):
    """Match formula: team a vs team b"""
    return (f'=IFERROR(VLOOKUP({a},{LOOKUP},2,0)'
            f'&"  ー  "&VLOOKUP({b},{LOOKUP},2,0),"{a} ー {b}")')

def rf(a, b):
    """Referee formula: team a & team b"""
    return (f'=IFERROR(VLOOKUP({a},{LOOKUP},2,0)'
            f'&"・"&VLOOKUP({b},{LOOKUP},2,0),"{a}・{b}")')

# (month, day) → (match_val, ref_val, is_reserve)
GAMES = {
    (5,26): (mf(1,3), rf(2,6), False),
    (5,27): (mf(5,6), rf(1,3), False),
    (5,28): (mf(2,4), rf(5,6), False),
    (6, 2): (mf(1,6), rf(2,4), False),
    (6, 3): (mf(2,3), rf(1,6), False),
    (6, 4): (mf(4,5), rf(2,3), False),
    (6, 9): (mf(1,2), rf(4,5), False),
    (6,10): (mf(3,5), rf(1,2), False),
    (6,11): (mf(4,6), rf(3,5), False),
    (6,16): ("予  備  日", "", True),
    (6,17): ("予  備  日", "", True),
    (6,18): ("予  備  日", "", True),
    (6,23): (mf(2,5), rf(4,6), False),
    (6,24): (mf(1,4), rf(2,5), False),
    (6,25): (mf(3,6), rf(1,4), False),
    (6,30): (mf(1,5), rf(3,6), False),
    (7, 1): (mf(3,4), rf(1,5), False),
    (7, 2): (mf(2,6), rf(3,4), False),
}

TEAM_NAMES = {1:"野宮塗装", 2:"飯詰", 3:"バッカス",
              4:"ウエスタン", 5:"富士電機", 6:"日産"}

GAME_LIST = [
    ("5/26(火)", 1, 3), ("5/27(水)", 5, 6), ("5/28(木)", 2, 4),
    ("6/2(火)",  1, 6), ("6/3(水)",  2, 3), ("6/4(木)",  4, 5),
    ("6/9(火)",  1, 2), ("6/10(水)", 3, 5), ("6/11(木)", 4, 6),
    ("6/23(火)", 2, 5), ("6/24(水)", 1, 4), ("6/25(木)", 3, 6),
    ("6/30(火)", 1, 5), ("7/1(水)",  3, 4), ("7/2(木)",  2, 6),
]

# ═══════════════════════════════════════════════════════════════
#  SHEET 1: 日程表  (landscape, fit to 1 page)
# ═══════════════════════════════════════════════════════════════
ws1 = wb.active
ws1.title = "日程表"

ws1.page_setup.orientation = "landscape"
ws1.page_setup.paperSize = 9
ws1.sheet_properties.pageSetUpPr.fitToPage = True
ws1.page_setup.fitToWidth  = 1
ws1.page_setup.fitToHeight = 1
ws1.print_area = "A1:N37"
ws1.page_margins.left   = 0.5
ws1.page_margins.right  = 0.5
ws1.page_margins.top    = 0.5
ws1.page_margins.bottom = 0.5

# Col widths: A-D (May) | E spacer | F-I (Jun) | J spacer | K-N (Jul)
for col, w in zip(range(1,15),
                  [4.5, 4.5, 21, 16,  1.5,
                   4.5, 4.5, 21, 16,  1.5,
                   4.5, 4.5, 21, 16]):
    ws1.column_dimensions[gcl(col)].width = w

ws1.row_dimensions[1].height = 38
ws1.row_dimensions[2].height = 24
ws1.row_dimensions[3].height = 17
for r in range(4, 38):
    ws1.row_dimensions[r].height = 15.5

# ── Row 1: Main Title ──
ws1.merge_cells("A1:N1")
c = ws1.cell(1, 1, "令　和　８　年　　朝　野　球　日　程　表")
c.font = mk_font(True, 22, WHITE)
c.alignment = mk_align()
c.fill = mk_fill(NAVY)
c.border = MED

# ── Row 2: Month banners ──
for cols, label, col_fill in [
    ("A2:D2","５　月",BLUE2),
    ("F2:I2","６　月",BLUE2),
    ("K2:N2","７　月",BLUE2),
]:
    ws1.merge_cells(cols)
    c = ws1[cols[:2]]
    c.value = label
    c.font = mk_font(True, 15, WHITE)
    c.alignment = mk_align()
    c.fill = mk_fill(col_fill)
    c.border = THIN

# ── Row 3: Sub-headers ──
for base in [1, 6, 11]:
    for j, h in enumerate(["日","曜","対　戦　チ　ー　ム","審　判"]):
        c = sc(ws1, 3, base+j, h, bold=True, sz=9, color=WHITE,
               bg=NAVY, bdr=THIN)

# ── Spacer columns (E=5, J=10) ──
for r in range(1, 38):
    for col in [5, 10]:
        ws1.cell(r, col).fill = mk_fill(NAVY)
        ws1.cell(r, col).border = mk_border("medium","medium","thin","thin")

# ── Day rows ──
MONTH_DAYS = {5:31, 6:30, 7:31}
MONTH_BASE = {5:1,  6:6,  7:11}

for month, num_days in MONTH_DAYS.items():
    base = MONTH_BASE[month]
    for day in range(1, num_days+1):
        row = day + 3
        wd = get_wd(2026, month, day)
        game = GAMES.get((month, day))

        # Background
        if wd == "日":
            bg = SUN_BG
        elif wd == "土":
            bg = SAT_BG
        elif game:
            bg = YOBI_BG if game[2] else MATCH_BG
        else:
            bg = WHITE if day % 2 == 1 else LGRAY

        # Day number
        sc(ws1, row, base, day, sz=10, color=NAVY, bg=bg, bdr=THIN)

        # Weekday
        wd_color = RED if wd=="日" else ("00008B" if wd=="土" else NAVY)
        sc(ws1, row, base+1, wd, bold=(wd in "土日"), sz=10,
           color=wd_color, bg=bg, bdr=THIN)

        # Match
        match_val = game[0] if game else None
        is_reserve = game[2] if game else False
        c = ws1.cell(row=row, column=base+2,
                     value=match_val if match_val else None)
        c.font = mk_font(bool(match_val) and not is_reserve, 9, NAVY)
        c.alignment = mk_align(wrap=True)
        c.fill = mk_fill(bg)
        c.border = THIN

        # Referee
        ref_val = game[1] if game else None
        c = ws1.cell(row=row, column=base+3,
                     value=ref_val if ref_val else None)
        c.font = mk_font(False, 8, "555555")
        c.alignment = mk_align(wrap=True)
        c.fill = mk_fill(bg)
        c.border = THIN

# ── Row 36: Legend ──
ws1.row_dimensions[36].height = 12
ws1.merge_cells("A36:D36")
c = ws1.cell(36,1,"　試合あり"); c.font=mk_font(False,7,NAVY)
c.fill=mk_fill(MATCH_BG); c.alignment=mk_align("left")
ws1.merge_cells("F36:I36")
c = ws1.cell(36,6,"　予備日"); c.font=mk_font(False,7,NAVY)
c.fill=mk_fill(YOBI_BG); c.alignment=mk_align("left")
ws1.merge_cells("K36:N36")
c = ws1.cell(36,11,"　土曜　　　日曜")
c.font=mk_font(False,7,NAVY); c.alignment=mk_align("left")
ws1.cell(36,11).fill=mk_fill(WHITE)
# color chips inline
for col, bg in [(12,SAT_BG),(13,SUN_BG)]:
    ws1.cell(36,col).fill=mk_fill(bg)

# ── Row 37: Footer ──
ws1.row_dimensions[37].height = 14
ws1.merge_cells("A37:N37")
c = ws1.cell(37,1,
    "◆ メンバー表交換 5:10　◆ 試合時間 5:15～6:45　"
    "◆ 6:40を超えて新しいイニングには入らない　◆ 捕手は防具着用で整列")
c.font = mk_font(False, 8, WHITE)
c.alignment = mk_align("left")
c.fill = mk_fill(NAVY)

# ─── チーム名 reference table in 日程表 (col P-Q, rows 3-9) ───
ws1.column_dimensions["P"].width = 1.5
ws1.column_dimensions["Q"].width = 5
ws1.column_dimensions["R"].width = 14

sc(ws1,2,17,"No.",bold=True,sz=8,color=WHITE,bg=NAVY,bdr=THIN)
sc(ws1,2,18,"チーム名",bold=True,sz=8,color=WHITE,bg=NAVY,bdr=THIN)
ws1.merge_cells("Q2:R2")

for i in range(1,7):
    row = i+2
    sc(ws1,row,17, i, bold=True, sz=9, color=NAVY, bg=LGOLD, bdr=THIN)
    c = ws1.cell(row=row, column=18,
                 value=f'=IFERROR(VLOOKUP({i},{LOOKUP},2,0),"")')
    c.font = mk_font(False, 9, NAVY)
    c.alignment = mk_align("left")
    c.fill = mk_fill(WHITE)
    c.border = THIN
    ws1.merge_cells(f"R{row}:R{row}")  # single (placeholder for wider display)

ws1.column_dimensions["R"].width = 0  # hide, already merged conceptually
# Merge Q and R for each team row for wider display
for i in range(1,7):
    pass  # already handled

# ═══════════════════════════════════════════════════════════════
#  SHEET 2: 勝敗表
# ═══════════════════════════════════════════════════════════════
ws2 = wb.create_sheet("勝敗表")

ws2.page_setup.orientation = "landscape"
ws2.page_setup.paperSize = 9
ws2.sheet_properties.pageSetUpPr.fitToPage = True
ws2.page_setup.fitToWidth  = 1
ws2.page_setup.fitToHeight = 1
ws2.print_area = "A1:U37"
ws2.page_margins.left = ws2.page_margins.right = 0.5
ws2.page_margins.top = ws2.page_margins.bottom = 0.5

# Col widths
#  A=No(4), B=Name(16), C=sp(1.5)
#  D=Date(9), E=TeamA(14), F=ScoreA(5.5), G=ScoreB(5.5), H=TeamB(14),
#  I=ResA(5), J=ResB(5), K=sp(1.5)
#  L=No(4), M=Name(16), N=勝(5), O=分(5), P=敗(5),
#  Q=勝点(6), R=得点(6), S=失点(6), T=残(6), U=順位(6)
for col, w in zip(range(1,22),
    [4, 16, 1.5, 9, 14, 5.5, 5.5, 14, 5, 5, 1.5,
     4, 16,  5,  5,  5,  6,   6,   6,  6,  6]):
    ws2.column_dimensions[gcl(col)].width = w

ws2.row_dimensions[1].height = 40
for r in range(2, 40):
    ws2.row_dimensions[r].height = 18

# ── Row 1: Title ──
ws2.merge_cells("A1:U1")
c = ws2.cell(1,1,"令　和　８　年　　朝　野　球　リーグ　勝　敗　表")
c.font = mk_font(True, 22, WHITE)
c.alignment = mk_align()
c.fill = mk_fill(NAVY)
c.border = MED

# ── Rows 2-8: Team name input ──
ws2.row_dimensions[2].height = 22
ws2.merge_cells("A2:B2")
c = ws2.cell(2,1,"★ チーム登録（ここにチーム名を入力してください）")
c.font = mk_font(True, 11, WHITE)
c.alignment = mk_align("left")
c.fill = mk_fill(BLUE2)
c.border = THIN

ws2.merge_cells("D2:K2")
c = ws2.cell(2,4,
    "◆ 試合結果入力  ／  ◆ 成績表（右）は自動計算")
c.font = mk_font(True, 11, WHITE)
c.alignment = mk_align()
c.fill = mk_fill(GOLD)
c.border = THIN

ws2.merge_cells("L2:U2")
c = ws2.cell(2,12,"★ 成績表")
c.font = mk_font(True, 11, WHITE)
c.alignment = mk_align()
c.fill = mk_fill(NAVY)
c.border = THIN

# Team rows (rows 3-8)
for i, name in TEAM_NAMES.items():
    row = i + 2  # rows 3-8
    ws2.row_dimensions[row].height = 20

    sc(ws2, row, 1, i, bold=True, sz=12, color=NAVY, bg=LGOLD,
       bdr=mk_border("medium","thin","thin","thin"))
    c = ws2.cell(row=row, column=2, value=name)
    c.font = mk_font(True, 13, NAVY)
    c.alignment = mk_align("left")
    c.fill = mk_fill(WHITE)
    c.border = mk_border("thin","medium","thin","thin")

# ── Row 9: Sub-headers for game input ──
ws2.row_dimensions[9].height = 16
for col, h, bg in [
    (4,"日付",NAVY),(5,"チームA",NAVY),(6,"得点A",GOLD),
    (7,"得点B",GOLD),(8,"チームB",NAVY),(9,"結果A",NAVY),(10,"結果B",NAVY)]:
    sc(ws2, 9, col, h, bold=True, sz=9, color=WHITE, bg=bg, bdr=THIN)

# Summary headers (row 9, cols L-U)
for col, h in zip(range(12,22),
    ["No.","チーム名","勝","分","敗","勝点","得点","失点","残試合","順位"]):
    sc(ws2, 9, col, h, bold=True, sz=9, color=WHITE, bg=NAVY, bdr=THIN)

# ── Rows 10-24: Game data ──
team_as_A = {t:[] for t in range(1,7)}
team_as_B = {t:[] for t in range(1,7)}

for idx, (date_str, ta, tb) in enumerate(GAME_LIST):
    row = idx + 10
    ws2.row_dimensions[row].height = 18
    bg = WHITE if idx % 2 == 0 else LGRAY
    team_as_A[ta].append(row)
    team_as_B[tb].append(row)

    # Date
    sc(ws2, row, 4, date_str, sz=9, color=NAVY, bg=bg, bdr=THIN)

    # Team A name (formula)
    c = ws2.cell(row=row, column=5,
                 value=f'=IFERROR(VLOOKUP({ta},$A$3:$B$8,2,0),"{ta}")')
    c.font = mk_font(True, 10, NAVY)
    c.alignment = mk_align()
    c.fill = mk_fill(bg)
    c.border = THIN

    # Score A input (highlighted yellow, medium border)
    c = ws2.cell(row=row, column=6)
    c.font = mk_font(True, 13, NAVY)
    c.alignment = mk_align()
    c.fill = mk_fill(AMBER)
    c.border = MED

    # Score B input
    c = ws2.cell(row=row, column=7)
    c.font = mk_font(True, 13, NAVY)
    c.alignment = mk_align()
    c.fill = mk_fill(AMBER)
    c.border = MED

    # Team B name (formula)
    c = ws2.cell(row=row, column=8,
                 value=f'=IFERROR(VLOOKUP({tb},$A$3:$B$8,2,0),"{tb}")')
    c.font = mk_font(True, 10, NAVY)
    c.alignment = mk_align()
    c.fill = mk_fill(bg)
    c.border = THIN

    # Result A: ○/△/×
    c = ws2.cell(row=row, column=9,
                 value=(f'=IF(F{row}="","",IF(F{row}>G{row},"○",'
                        f'IF(F{row}=G{row},"△","×")))'))
    c.font = mk_font(True, 12, NAVY)
    c.alignment = mk_align()
    c.fill = mk_fill(bg)
    c.border = THIN

    # Result B
    c = ws2.cell(row=row, column=10,
                 value=(f'=IF(G{row}="","",IF(G{row}>F{row},"○",'
                        f'IF(G{row}=F{row},"△","×")))'))
    c.font = mk_font(True, 12, NAVY)
    c.alignment = mk_align()
    c.fill = mk_fill(bg)
    c.border = THIN

# ── Rows 10-24: Summary table ──
for t in range(1, 7):
    row = t + 9  # rows 10-15
    bg = WHITE if t % 2 == 1 else LGRAY

    sc(ws2, row, 12, t, bold=True, sz=10, color=NAVY, bg=LGOLD, bdr=THIN)

    c = ws2.cell(row=row, column=13,
                 value=f'=IFERROR(VLOOKUP({t},$A$3:$B$8,2,0),"")')
    c.font = mk_font(True, 11, NAVY)
    c.alignment = mk_align("left")
    c.fill = mk_fill(bg)
    c.border = THIN

    # Build win/draw/loss formulas from fixed game rows
    rows_a = team_as_A[t]
    rows_b = team_as_B[t]

    def sum_result(rows_a, rows_b, res_col_a, res_col_b, target):
        parts = ([f'IF({gcl(res_col_a)}{r}="{target}",1,0)' for r in rows_a] +
                 [f'IF({gcl(res_col_b)}{r}="{target}",1,0)' for r in rows_b])
        return "=" + "+".join(parts) if parts else "=0"

    win_f  = sum_result(rows_a, rows_b, 9, 10, "○")
    draw_f = sum_result(rows_a, rows_b, 9, 10, "△")
    loss_f = sum_result(rows_a, rows_b, 9, 10, "×")

    c = ws2.cell(row=row, column=14, value=win_f)
    c.font = mk_font(True, 12, GREEN); c.alignment = mk_align()
    c.fill = mk_fill(bg); c.border = THIN

    c = ws2.cell(row=row, column=15, value=draw_f)
    c.font = mk_font(False, 10, NAVY); c.alignment = mk_align()
    c.fill = mk_fill(bg); c.border = THIN

    c = ws2.cell(row=row, column=16, value=loss_f)
    c.font = mk_font(False, 10, RED); c.alignment = mk_align()
    c.fill = mk_fill(bg); c.border = THIN

    # Points
    c = ws2.cell(row=row, column=17,
                 value=f'={gcl(14)}{row}*3+{gcl(15)}{row}')
    c.font = mk_font(True, 13, NAVY); c.alignment = mk_align()
    c.fill = mk_fill(bg); c.border = THIN

    # Runs scored
    rs_parts = ([f'IF(F{r}<>"",F{r},0)' for r in rows_a] +
                [f'IF(G{r}<>"",G{r},0)' for r in rows_b])
    c = ws2.cell(row=row, column=18,
                 value="=" + "+".join(rs_parts) if rs_parts else "=0")
    c.font = mk_font(False, 10, NAVY); c.alignment = mk_align()
    c.fill = mk_fill(bg); c.border = THIN

    # Runs allowed
    ra_parts = ([f'IF(G{r}<>"",G{r},0)' for r in rows_a] +
                [f'IF(F{r}<>"",F{r},0)' for r in rows_b])
    c = ws2.cell(row=row, column=19,
                 value="=" + "+".join(ra_parts) if ra_parts else "=0")
    c.font = mk_font(False, 10, NAVY); c.alignment = mk_align()
    c.fill = mk_fill(bg); c.border = THIN

    # Remaining
    c = ws2.cell(row=row, column=20,
                 value=f'=5-{gcl(14)}{row}-{gcl(15)}{row}-{gcl(16)}{row}')
    c.font = mk_font(False, 10, NAVY); c.alignment = mk_align()
    c.fill = mk_fill(bg); c.border = THIN

    # Rank (by 勝点=col Q=17)
    c = ws2.cell(row=row, column=21,
                 value=f'=IFERROR(RANK(Q{row},$Q$10:$Q$15,0),"")')
    c.font = mk_font(True, 13, GOLD); c.alignment = mk_align()
    c.fill = mk_fill(bg); c.border = THIN

# ── Spacer columns C=3, K=11 ──
for r in range(1, 38):
    for col in [3, 11]:
        ws2.cell(r, col).fill = mk_fill(NAVY)
        ws2.cell(r, col).border = mk_border("medium","medium","thin","thin")

# ── Rows 16-25: remaining game rows below summary (alignment) ──
for row in range(16, 26):
    ws2.row_dimensions[row].height = 18
    for col in range(4, 11):
        ws2.cell(row, col).fill = mk_fill(LGRAY)
        ws2.cell(row, col).border = THIN

# ── Footer note row ──
ws2.merge_cells("A26:U26")
ws2.row_dimensions[26].height = 14
c = ws2.cell(26,1,
    "※ 得点欄（黄色セル）に点数を入力するだけで勝敗・成績表が自動更新されます　"
    "◆ 降雨中止の場合は「☂」と入力")
c.font = mk_font(False, 8, WHITE)
c.alignment = mk_align("left")
c.fill = mk_fill(NAVY)

# ─── Save ────────────────────────────────────────────────────
output_path = "/home/user/kindle-/schedule_2026_v2.xlsx"
wb.save(output_path)
print(f"Done: {output_path}")
