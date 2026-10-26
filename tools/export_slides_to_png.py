"""Export all PowerPoint slides to PNG images via win32com."""

from pathlib import Path
import sys

def main():
    root = Path(__file__).resolve().parent.parent
    deck_path = root / "Autumn_Coin_IYPT_2026.pptx"
    out_dir = root / "docs" / "slides_export"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not deck_path.exists():
        print(f"Error: {deck_path} does not exist!")
        sys.exit(1)

    import win32com.client
    print(f"[PowerPoint Export] Opening {deck_path.name}...")
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    try:
        presentation = ppt_app.Presentations.Open(str(deck_path.resolve()), WithWindow=False)
        # Format 18 is ppSaveAsPNG
        print(f"[PowerPoint Export] Exporting 24 slides to {out_dir}...")
        presentation.SaveAs(str(out_dir.resolve()), 18)
        presentation.Close()
        print("[PowerPoint Export] Export completed successfully.")
    finally:
        ppt_app.Quit()

if __name__ == "__main__":
    main()
