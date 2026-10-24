import os
import sys
import win32com.client

ppt_path = os.path.abspath('Autumn_Coin_IYPT_2026_Full_22Slides.pptx')
ppt_app = win32com.client.Dispatch('PowerPoint.Application')
pres = ppt_app.Presentations.Open(ppt_path, WithWindow=False)

for i, slide in enumerate(pres.Slides):
    slide_num = i + 1
    for s in slide.Shapes:
        top = s.Top / 72.0
        height = s.Height / 72.0
        bottom = top + height
        if top >= 7.0: # footer
            continue
        if bottom > 7.05:
            first_txt = ""
            if s.HasTextFrame and s.TextFrame.HasText:
                first_txt = s.TextFrame.TextRange.Text.replace('\r', ' ').replace('\n', ' ')[:40]
            elif s.HasTable:
                first_txt = "TABLE"
            print(f"Slide {slide_num}: Shape '{s.Name}' (type {s.Type}) bottom={bottom:.2f} > 7.05! Text: {first_txt}")

pres.Close()
ppt_app.Quit()
print("Checked all shapes in PowerPoint runtime.")
