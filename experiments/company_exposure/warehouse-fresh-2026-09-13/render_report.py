"""Render the reviewed Korean source; no model or provider calls.

Usage: python render_report.py --font-dir FONT_DIR --output report.pdf
Requires reportlab and NanumGothic-Regular.ttf / NanumGothic-Bold.ttf.
"""
import argparse
from html import escape
from pathlib import Path
import re

from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def render(output, font_dir, source=None, display_date='2026.09.13'):
    root = Path(__file__).resolve().parent
    for name, file in [('KR', 'NanumGothic-Regular.ttf'), ('KRB', 'NanumGothic-Bold.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    navy = colors.HexColor('#172E46')
    teal = colors.HexColor('#176F75')
    styles = {
        'p': ParagraphStyle('body', fontName='KR', fontSize=10.5, leading=16.8,
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
        line = line.replace("−", "-")  # NanumGothic lacks U+2212; keep negative signs visible.
        matches = list(re.finditer(r'\[([^\]]+)\]\((https://[^)]+)\)', line))
        result = ''; cursor = 0
        for m in matches:
            result += escape(line[cursor:m.start()])
            result += f'<link href="{escape(m[2], quote=True)}" color="#176F75">{escape(m[1])}</link>'
            cursor = m.end()
        return result + escape(line[cursor:])
    def diagram(kind):
        d = Drawing(511, 180)
        def box(x,y,w,h,label):
            d.add(Rect(x,y,w,h,fillColor=colors.HexColor('#E8F2F2'),strokeColor=teal,rx=4,ry=4))
            d.add(String(x+w/2,y+h/2-4,label,fontName='KR',fontSize=10,textAnchor='middle',fillColor=navy))
        def arrow(x1,y1,x2,y2):
            d.add(Line(x1,y1,x2,y2,strokeColor=teal,strokeWidth=1.3))
            d.add(Polygon([x2,y2,x2-6,y2+3,x2-6,y2-3],fillColor=teal,strokeColor=teal))
        if kind=='!FLOW':
            for x,label in [(5,'입고·확인'),(139,'보관·인출'),(273,'주문별 구성'),(407,'출고')]:
                box(x,40,99,43,label)
            for x in [104,238,372]:arrow(x,61,x+35,61)
            box(139,118,233,38,'주문·재고 정보와 작업 계획')
            for x in [188,322]:
                d.add(Line(x,118,x,84,strokeColor=teal))
            d.add(String(255,12,'상자 이동과 작업 순서를 함께 설계한다',fontName='KR',fontSize=9,textAnchor='middle',fillColor=navy))
        else:
            for row in range(3):
                for col in range(5):
                    d.add(Rect(35+col*38,25+row*30,34,26,fillColor=colors.HexColor('#DCEBEF'),strokeColor=teal))
            box(55,130,145,30,'상부의 이동 로봇')
            box(330,60,155,45,'포트: 입고·집기 작업')
            arrow(227,84,328,84)
            d.add(String(124,8,'격자 안에 쌓인 빈',fontName='KR',fontSize=9,textAnchor='middle',fillColor=navy))
            d.add(String(278,102,'필요한 빈 이동',fontName='KR',fontSize=9,textAnchor='middle',fillColor=navy))
        return d
    pages = (source or root / 'report-source.md').read_text().split('---PAGE---')
    story = []
    for page_index, page in enumerate(pages):
        if page_index: story.append(PageBreak())
        lines = page.strip().splitlines(); i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line: i += 1; continue
            if line in ['!FLOW','!CUBE']:
                story += [diagram(line), Spacer(1,10)]; i += 1; continue
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
        canvas.drawString(42,h-33,'산업 이해 리서치  /  물류창고 자동화')
        canvas.drawRightString(w-42,h-33,display_date)
        canvas.setStrokeColor(colors.HexColor('#DDE4E9')); canvas.line(42,36,w-42,36)
        canvas.setFont('KR',7.5)
        canvas.drawString(42,23,'정보 확인 2026.09.13 · 기술 설명과 기업 경제성 · 가정은 별도 표시')
        canvas.drawRightString(w-42,23,str(doc.page)); canvas.restoreState()
    output.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(output),pagesize=A4,rightMargin=42,leftMargin=42,
                      topMargin=55,bottomMargin=47,title='창고는 어떻게 하나의 기계가 되는가',
                      author='Industry Bottleneck Research').build(story,onFirstPage=frame,onLaterPages=frame)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--font-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--display-date',default='2026.09.13')
    args=parser.parse_args(); render(args.output,args.font_dir,args.source,args.display_date)

