from pathlib import Path
import json
P=Path(__file__).parent
v=json.loads((P/'economics.json').read_text())
def table(headers,rows):return '\n'.join('| '+' | '.join(map(str,r))+' |' for r in [headers]+rows)
roi=table(['가정 · 백만 달러','연 순절감','회수 기간','8년 NPV'],[[n,f"{v['customer_example_USD_m'][k]['annual_net_saving']:.0f}",f"{v['customer_example_USD_m'][k]['simple_payback_years']:.1f}년",f"{v['customer_example_USD_m'][k]['NPV_8_year_10pct']:.2f}"] for n,k in [('낮음','low'),('기본','base'),('높음','high')]])
dcf=table(['시나리오','첫 5년 성장 / 5년차 마진','5년차 FCFF · 백만 달러','영업가치 · 십억 달러'],[[name,assumption,f"{v['cases'][key]['years'][4]['FCFF']:,.0f}",f"{v['cases'][key]['EV']/1000:.2f}"] for name,key,assumption in [('지연','delay','10% / 9%'),('기본','base','20% / 14%'),('실행 성공','execution','30% / 19%')]])
s=(P/'report-source.md').read_text().replace('{{ROI}}',roi).replace('{{DCF}}',dcf)
assert '{{' not in s
(P/'report-ko.md').write_text(s)
