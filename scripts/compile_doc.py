#!/usr/bin/env python3
import base64
import os
import re

def parse_markdown_to_html(md_text: str) -> str:
    # 1. Base64 embed images
    def img_repl(match):
        alt = match.group(1)
        path = match.group(2)
        if os.path.exists(path):
            with open(path, "rb") as img_f:
                b64 = base64.b64encode(img_f.read()).decode("utf-8")
                return f'<div style="text-align: center; margin: 32px 0;"><img src="data:image/jpeg;base64,{b64}" alt="{alt}" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 6px 20px rgba(0,0,0,0.12); border: 1px solid #cbd5e1;" /><br/><em style="color: #64748b; font-size: 10pt; display: block; margin-top: 8px; font-weight: 500;">{alt}</em></div>'
        return match.group(0)

    html = re.sub(r"!\[(.*?)\]\((.*?)\)", img_repl, md_text)

    # 2. Line-by-line parser to handle tables, headers, lists, code, and text robustly
    lines = html.split("\n")
    output_blocks = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped:
            i += 1
            continue
            
        # Check if start of markdown table
        if stripped.startswith("|") and stripped.endswith("|") and i + 1 < len(lines) and lines[i+1].strip().startswith("|") and ("---" in lines[i+1] or "-:" in lines[i+1] or ":-" in lines[i+1]):
            # Table block detected
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
                
            if len(table_lines) >= 2:
                header_cols = [c.strip() for c in table_lines[0].split("|")[1:-1]]
                align_cols = [c.strip() for c in table_lines[1].split("|")[1:-1]]
                
                alignments = []
                for a in align_cols:
                    if a.startswith(":") and a.endswith(":"):
                        alignments.append("center")
                    elif a.endswith(":"):
                        alignments.append("right")
                    else:
                        alignments.append("left")
                while len(alignments) < len(header_cols):
                    alignments.append("left")
                    
                tbl_html = ['<div style="overflow-x: auto; margin: 24px 0;">']
                tbl_html.append('<table style="width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; font-size: 10.5pt; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">')
                
                # Header
                tbl_html.append('  <thead>')
                tbl_html.append('    <tr style="background-color: #f1f5f9;">')
                for idx, h in enumerate(header_cols):
                    align = alignments[idx]
                    h_fmt = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", h)
                    tbl_html.append(f'      <th style="padding: 11px 16px; text-align: {align}; font-weight: 700; color: #0f172a; border-bottom: 2px solid #cbd5e1; border-right: 1px solid #e2e8f0; font-size: 10.5pt;">{h_fmt}</th>')
                tbl_html.append('    </tr>')
                tbl_html.append('  </thead>')
                
                # Body
                tbl_html.append('  <tbody>')
                data_rows = table_lines[2:]
                for r_idx, r in enumerate(data_rows):
                    cols = [c.strip() for c in r.split("|")[1:-1]]
                    bg = "#ffffff" if r_idx % 2 == 0 else "#f8fafc"
                    tbl_html.append(f'    <tr style="background-color: {bg};">')
                    for c_idx, cell in enumerate(cols):
                        align = alignments[c_idx] if c_idx < len(alignments) else "left"
                        c_txt = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", cell)
                        c_txt = re.sub(r"\*(.+?)\*", r"<em>\1</em>", c_txt)
                        c_txt = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" style="color: #1a73e8; text-decoration: none; font-weight: 500;">\1</a>', c_txt)
                        c_txt = re.sub(r"`(.+?)`", r'<code style="background: #e2e8f0; padding: 2px 5px; border-radius: 4px; font-size: 9pt;">\1</code>', c_txt)
                        
                        border_bottom = "border-bottom: 1px solid #e2e8f0;" if r_idx < len(data_rows) - 1 else ""
                        border_right = "border-right: 1px solid #e2e8f0;" if c_idx < len(cols) - 1 else ""
                        tbl_html.append(f'      <td style="padding: 10px 16px; text-align: {align}; color: #334155; {border_bottom} {border_right} vertical-align: middle;">{c_txt}</td>')
                    tbl_html.append('    </tr>')
                tbl_html.append('  </tbody>')
                tbl_html.append('</table>')
                tbl_html.append('</div>')
                output_blocks.append('\n'.join(tbl_html))
            continue

        # Headers
        if stripped.startswith("# "):
            h_text = stripped[2:]
            output_blocks.append(f'<h1 style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; font-size: 24pt; font-weight: 800; color: #1a73e8; margin-top: 28pt; margin-bottom: 10pt; line-height: 1.25; letter-spacing: -0.5px;">{h_text}</h1>')
            i += 1
            continue
        elif stripped.startswith("## "):
            h_text = stripped[3:]
            output_blocks.append(f'<h2 style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; font-size: 16pt; font-weight: 700; color: #0f172a; margin-top: 24pt; margin-bottom: 10pt; border-bottom: 2px solid #e2e8f0; padding-bottom: 6pt; line-height: 1.3;">{h_text}</h2>')
            i += 1
            continue
        elif stripped.startswith("### "):
            h_text = stripped[4:]
            output_blocks.append(f'<h3 style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; font-size: 13pt; font-weight: 700; color: #334155; margin-top: 18pt; margin-bottom: 8pt;">{h_text}</h3>')
            i += 1
            continue

        # Horizontal Rule
        if stripped.startswith("---"):
            output_blocks.append('<hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 32px 0;" />')
            i += 1
            continue

        # List blocks
        if stripped.startswith("- ") or stripped.startswith("* "):
            list_items = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or lines[i].strip().startswith("* ")):
                item_txt = lines[i].strip()[2:]
                item_txt = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item_txt)
                item_txt = re.sub(r"\*(.+?)\*", r"<em>\1</em>", item_txt)
                item_txt = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" style="color: #1a73e8; text-decoration: none; font-weight: 500;">\1</a>', item_txt)
                item_txt = re.sub(r"`(.+?)`", r'<code style="background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-size: 9.5pt;">\1</code>', item_txt)
                list_items.append(f'<li style="margin-bottom: 6px;">{item_txt}</li>')
                i += 1
            output_blocks.append(f'<ul style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; font-size: 11pt; line-height: 1.65; color: #334155; padding-left: 24px; margin: 10px 0;">{"".join(list_items)}</ul>')
            continue

        # Numbered Lists
        if re.match(r"^\d+\.\s+", stripped):
            num_items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                m = re.match(r"^\d+\.\s+(.+)$", lines[i].strip())
                item_txt = m.group(1)
                item_txt = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item_txt)
                item_txt = re.sub(r"\*(.+?)\*", r"<em>\1</em>", item_txt)
                item_txt = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" style="color: #1a73e8; text-decoration: none; font-weight: 500;">\1</a>', item_txt)
                item_txt = re.sub(r"`(.+?)`", r'<code style="background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-size: 9.5pt;">\1</code>', item_txt)
                num_items.append(f'<li style="margin-bottom: 8px;">{item_txt}</li>')
                i += 1
            output_blocks.append(f'<ol style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; font-size: 11pt; line-height: 1.65; color: #334155; padding-left: 24px; margin: 10px 0;">{"".join(num_items)}</ol>')
            continue

        # Images (already converted to div)
        if stripped.startswith("<div style="):
            output_blocks.append(stripped)
            i += 1
            continue

        # Regular Paragraph
        p_txt = stripped
        p_txt = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p_txt)
        p_txt = re.sub(r"\*(.+?)\*", r"<em>\1</em>", p_txt)
        p_txt = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" style="color: #1a73e8; text-decoration: none; font-weight: 500;">\1</a>', p_txt)
        p_txt = re.sub(r"`(.+?)`", r'<code style="background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-size: 9.5pt;">\1</code>', p_txt)
        output_blocks.append(f'<p style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; font-size: 11pt; line-height: 1.7; color: #1e293b; margin: 10pt 0;">{p_txt}</p>')
        i += 1

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Benchmarking Gemini 3.7 Flash on Autonomous Distributed Infrastructure</title>
<style>
@page {{
  size: letter;
  margin: 1in;
}}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  max-width: 880px;
  margin: 40px auto;
  padding: 0 24px;
  color: #0f172a;
  background-color: #ffffff;
  line-height: 1.65;
}}
table tr:hover td {{
  background-color: #f1f5f9 !important;
}}
code {{
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}}
</style>
</head>
<body>
{"".join(output_blocks)}
</body>
</html>"""
    return doc

def main():
    src_md = "/home/ubuntu/code/getcolors/article-gemini-3.7-flash-benchmark.md"
    with open(src_md, "r", encoding="utf-8") as f:
        md_content = f.read()

    doc_html = parse_markdown_to_html(md_content)

    targets = [
        "/home/ubuntu/code/getcolors/article-gemini-3.7-flash-benchmark.html",
        "/home/ubuntu/code/agy/article-gemini-3.7-flash-benchmark.html",
        "/tmp/serve_article/index.html",
        "/tmp/serve_article/article-gemini-3.7-flash-benchmark.html"
    ]
    for t in targets:
        with open(t, "w", encoding="utf-8") as f:
            f.write(doc_html)
        print(f"Updated {t} ({os.path.getsize(t):,} bytes)")

if __name__ == "__main__":
    main()
