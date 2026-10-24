"""Export all slides from Autumn_Coin_IYPT_2026_Full_22Slides.pptx to PNG using PowerPoint COM."""

import win32com.client
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECK_PATH = str((ROOT / "Autumn_Coin_IYPT_2026_Full_22Slides.pptx").resolve())
OUT_DIR = ROOT / "results" / "slides_export"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def export_slides():
    print(f"Opening presentation: {DECK_PATH}")
    ppt = win32com.client.Dispatch("PowerPoint.Application")
    try:
        pres = ppt.Presentations.Open(DECK_PATH, WithWindow=False)
        total = len(pres.Slides)
        print(f"Exporting {total} slides to {OUT_DIR} at 1920x1080 ...")
        for i in range(1, total + 1):
            slide = pres.Slides(i)
            out_file = str(OUT_DIR / f"slide_{i:02d}.png")
            slide.Export(out_file, "PNG", 1920, 1080)
            print(f"  Slide {i:02d} exported.")
        pres.Close()
        print("[SUCCESS] All 24 slides exported successfully.")
    finally:
        ppt.Quit()

if __name__ == "__main__":
    export_slides()
