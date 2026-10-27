"""Comprehensive verification of Autumn_Coin_Research_Paper_final.docx against v3.docx."""

import sys
from pathlib import Path
import docx

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
FINAL_PATH = ROOT / "Autumn_Coin_Research_Paper_final.docx"
V3_PATH = ROOT / "Autumn_Coin_Research_Paper_v3.docx"

doc_final = docx.Document(str(FINAL_PATH))
doc_v3 = docx.Document(str(V3_PATH))

print(f"Final paragraphs: {len(doc_final.paragraphs)} (v3 had {len(doc_v3.paragraphs)})")
print(f"Final tables: {len(doc_final.tables)} (v3 had {len(doc_v3.tables)})")

# 1. Check for any remaining draft/check notes
check_notes = []
for i, p in enumerate(doc_final.paragraphs):
    txt = p.text
    if any(k in txt for k in ["[CHECK", "[Draft note", "[DRAFT NOTE", "CHECK:"]):
        check_notes.append((f"P{i}", txt))

for t_idx, table in enumerate(doc_final.tables):
    for r_idx, row in enumerate(table.rows):
        for c_idx, cell in enumerate(row.cells):
            if any(k in cell.text for k in ["[CHECK", "[Draft note", "[DRAFT NOTE", "CHECK:"]):
                check_notes.append((f"Table {t_idx} [{r_idx},{c_idx}]", cell.text))

if check_notes:
    print(f"ERROR: Found {len(check_notes)} unresolved check/draft notes:")
    for loc, txt in check_notes:
        print(f"  {loc}: {txt[:80]}...")
else:
    print("PASS: Zero unresolved [CHECK] or [Draft note] markers found in document.")

# 2. Check title, author, and intro
p_title = doc_final.paragraphs[0]
p_author = doc_final.paragraphs[1]
p_iypt = doc_final.paragraphs[2]
p_abstract = doc_final.paragraphs[3]

print(f"P0 (Title): {p_title.text}")
print(f"P1 (Author): {p_author.text}")
print(f"P2 (IYPT): {p_iypt.text}")
print(f"P3 (Abstract): {p_abstract.text}")

assert "Ayaan Bilal" in p_author.text, "Author must be Ayaan Bilal"
assert "commit" not in p_author.text.lower(), "Author must not contain commit"
assert "location" not in p_author.text.lower(), "Author must not contain location"
print("PASS: Author line is verified clean ('Ayaan Bilal').")

# 3. Check paragraph styling and line spacing consistency
body_count = 0
spaced_correctly = 0
for i, p in enumerate(doc_final.paragraphs):
    pf = p.paragraph_format
    ls = pf.line_spacing
    sa = pf.space_after.pt if pf.space_after else None
    align = str(p.alignment)
    # Check regular body paragraphs
    if len(p.text) > 100 and not p.text.startswith("Figure ") and not p.text.startswith("Table "):
        body_count += 1
        if ls == 1.1 and sa == 6.0:
            spaced_correctly += 1
        else:
            print(f"  P{i} spacing variance: ls={ls}, sa={sa}, align={align}")

print(f"Body paragraphs with exact 1.1 line spacing & 6.0 pt space-after: {spaced_correctly}/{body_count}")

# 4. Check tables integrity
print("\nTables check:")
for t_idx, table in enumerate(doc_final.tables):
    print(f"  Table {t_idx}: {len(table.rows)} rows, {len(table.columns)} cols | Hdr: {[c.text.strip().replace(chr(10), ' ') for c in table.rows[0].cells[:3]]}...")

# 5. Check images count
img_count = sum(1 for p in doc_final.paragraphs if "graphicData" in p._element.xml)
print(f"Embedded figures in document: {img_count}/12")
assert img_count == 12, f"Expected 12 images, found {img_count}"
print("PASS: All 12 figures verified.")
