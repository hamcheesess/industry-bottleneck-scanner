"""Render the reviewed Korean source; no model or provider calls.

Usage: python render_report.py --font-dir FONT_DIR --output report.pdf
Requires reportlab and NanumGothic-Regular.ttf / NanumGothic-Bold.ttf.
"""
import argparse
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def render(output, font_dir, source=None, display_date='2026.09.06'):
    root = Path(__file__).resolve().parent
    for name, file in [('KR', 'NanumGothic-Regular.ttf'), ('KRB', 'NanumGothic-Bold.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    navy = colors.HexColor('#172E46')
    teal = colors.HexColor('#176F75')
    styles = {
        'p': ParagraphStyle('body', fontName='KR', fontSize=10, leading=16.2,
                            textColor=navy, spaceAfter=9, wordWrap='CJK'),
        'h1': ParagraphStyle('title', fontName='KRB', fontSize=21, leading=29,
                             textColor=navy, spaceAfter=16, wordWrap='CJK'),
        'h2': ParagraphStyle('subtitle', fontName='KRB', fontSize=14, leading=21,
                             textColor=teal, spaceAfter=12, wordWrap='CJK'),
        'h3': ParagraphStyle('section', fontName='KRB', fontSize=11.8, leading=18,
                             textColor=teal, spaceBefore=6, spaceAfter=7, wordWrap='CJK'),
        'cell': ParagraphStyle('cell', fontName='KR', fontSize=8.8, leading=13.4,
                               textColor=navy, wordWrap='CJK', alignment=TA_LEFT),
        'link': ParagraphStyle('link', fontName='KR', fontSize=9.1, leading=14.2,
                               textColor=teal, spaceAfter=5, wordWrap='CJK'),
    }
    def inline(line):
        matches = list(re.finditer(r'\[([^\]]+)\]\((https://[^)]+)\)', line))
        result = ''; cursor = 0
        for m in matches:
            result += escape(line[cursor:m.start()])
            result += f'<link href="{escape(m[2], quote=True)}" color="#176F75">{escape(m[1])}</link>'
            cursor = m.end()
        return result + escape(line[cursor:])
    pages = (source or root / 'report-source.md').read_text().split('---PAGE---')
    story = []
    for page_index, page in enumerate(pages):
        if page_index: story.append(PageBreak())
        lines = page.strip().splitlines(); i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line: i += 1; continue
            if line.startswith('|'):
                rows = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                    rows.append([Paragraph(inline(c), styles['cell']) for c in cells]); i += 1
                n = len(rows[0])
                widths = {3:[120,156,235], 4:[127,108,125,151]}.get(n, [511/n]*n)
                table = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
                table.setStyle(TableStyle([
                    ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEBEF')),
                    ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F3F6F8'),colors.white]),
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                    ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                    ('LINEBELOW',(0,0),(-1,0),0.7,teal),
                    ('LINEBELOW',(0,1),(-1,-1),0.3,colors.HexColor('#DDE4E9')),
                ]))
                story += [table, Spacer(1,10)]; continue
            kind = 'p'
            for prefix, key in [('### ', 'h3'), ('## ', 'h2'), ('# ', 'h1')]:
                if line.startswith(prefix): kind = key; line = line[len(prefix):]; break
            if line.startswith('[S') or line.startswith('[M'): kind = 'link'
            story.append(Paragraph(inline(line), styles[kind])); i += 1
    def frame(canvas, doc):
        canvas.saveState(); w,h=A4
        canvas.setFillColor(teal); canvas.rect(0,h-10,w,10,fill=1,stroke=0)
        canvas.setFont('KR',8); canvas.setFillColor(navy)
        canvas.drawString(42,h-33,'산업 병목 리서치  /  AI 네트워크와 광연결')
        canvas.drawRightString(w-42,h-33,display_date)
        canvas.setStrokeColor(colors.HexColor('#DDE4E9')); canvas.line(42,36,w-42,36)
        canvas.setFont('KR',7.5)
        canvas.drawString(42,23,'정보 기준 2025.06.30 · 전망과 가치평가는 분석 가정 포함')
        canvas.drawRightString(w-42,23,str(doc.page)); canvas.restoreState()
    output.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(output),pagesize=A4,rightMargin=42,leftMargin=42,
                      topMargin=55,bottomMargin=47,title='AI 네트워크의 성장은 누구의 현금흐름이 되는가',
                      author='Industry Bottleneck Research').build(story,onFirstPage=frame,onLaterPages=frame)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--font-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--display-date',default='2026.09.06')
    args=parser.parse_args(); render(args.output,args.font_dir,args.source,args.display_date)
