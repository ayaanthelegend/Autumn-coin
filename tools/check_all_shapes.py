import os
import sys
import win32com.client

sys.stdout.reconfigure(encoding='utf-8')

ppt_path = os.path.abspath('Autumn_Coin_IYPT_2026_Full_22Slides.pptx')
ppt_app = win32com.client.Dispatch('PowerPoint.Application')
pres = ppt_app.Presentations.Open(ppt_path, WithWindow=False)

for i, slide in enumerate(pres.Slides):
    slide_num = i + 1
    print(f"=== Slide {slide_num} ===")
    for s in slide.Shapes:
        top = s.Top / 72.0
        height = s.Height / 72.0
        bottom = top + height
        name = s.Name
        txt = ""
        if s.HasTextFrame and s.TextFrame.HasText:
            txt = s.TextFrame.TextRange.Text.replace('\r', ' ').replace('\n', ' ')[:40]
        elif s.HasTable:
            txt = f"TABLE({s.Table.Rows.Count}x{s.Table.Columns.Count})"
            row_h = [round(r.Height / 72.0, 2) for r in s.Table.Rows]
            txt += f" rows={row_h}"
        elif s.Type == 13:
            txt = "PICTURE"
        print(f"  {name:18s} top={top:5.2f} h={height:5.2f} bot={bottom:5.2f} | {txt[:60]}")

pres.Close()
ppt_app.Quit()
