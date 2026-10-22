import os
import win32com.client

ppt_path = os.path.abspath('Autumn_Coin_IYPT_2026_Full_22Slides.pptx')
ppt_app = win32com.client.Dispatch('PowerPoint.Application')
pres = ppt_app.Presentations.Open(ppt_path, WithWindow=False)

for i, slide in enumerate(pres.Slides):
    slide_num = i + 1
    shapes_info = []
    for s in slide.Shapes:
        left = s.Left / 72.0
        top = s.Top / 72.0
        width = s.Width / 72.0
        height = s.Height / 72.0
        right = left + width
        bottom = top + height
        name = s.Name
        txt = ""
        if s.HasTextFrame and s.TextFrame.HasText:
            txt = s.TextFrame.TextRange.Text.replace('\r', ' ').replace('\n', ' ')[:30]
        elif s.HasTable:
            txt = f"TABLE({s.Table.Rows.Count}x{s.Table.Columns.Count})"
        elif s.Type == 13:
            txt = "PICTURE"
        shapes_info.append({
            'name': name, 'type': s.Type, 'left': left, 'top': top,
            'right': right, 'bottom': bottom, 'width': width, 'height': height, 'txt': txt
        })

    # Check boundaries
    for s in shapes_info:
        if s['top'] < 7.0 and s['bottom'] > 7.05:
            print(f"Slide {slide_num}: Shape '{s['name']}' ({s['txt']}) bottom={s['bottom']:.2f} > 7.05")
        if s['right'] > 13.25:
            print(f"Slide {slide_num}: Shape '{s['name']}' ({s['txt']}) right={s['right']:.2f} > 13.25")

    # Check overlaps between non-footer, non-header shapes
    content_shapes = [s for s in shapes_info if s['top'] > 1.1 and s['bottom'] <= 7.08]
    for j in range(len(content_shapes)):
        for k in range(j + 1, len(content_shapes)):
            s1 = content_shapes[j]
            s2 = content_shapes[k]
            # Check bounding box overlap
            x_overlap = max(0, min(s1['right'], s2['right']) - max(s1['left'], s2['left']))
            y_overlap = max(0, min(s1['bottom'], s2['bottom']) - max(s1['top'], s2['top']))
            if x_overlap > 0.05 and y_overlap > 0.05:
                print(f"Slide {slide_num}: OVERLAP between '{s1['name']}' ({s1['txt']}) and '{s2['name']}' ({s2['txt']}): x_ov={x_overlap:.2f}, y_ov={y_overlap:.2f}")

pres.Close()
ppt_app.Quit()
