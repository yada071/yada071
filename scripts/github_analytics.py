"""Generate a self-contained SVG using GitHub's contribution calendar."""
import calendar
import html
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COLORS = ['#1e293b', '#0e5465', '#087e99', '#16a5c5', '#38bdf8']


def query(text, variables):
    token = os.environ.get('GH_TOKEN')
    if not token:
        raise RuntimeError('Execute pelo GitHub Actions ou configure GH_TOKEN localmente.')
    request = Request('https://api.github.com/graphql',
                      data=json.dumps({'query': text, 'variables': variables}).encode(),
                      headers={'Authorization': f'Bearer {token}',
                               'Content-Type': 'application/json',
                               'User-Agent': 'profile-contribution-analytics'})
    with urlopen(request, timeout=60) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError(str(result['errors']))
    return result['data']['user']


def calendar_data(username, start, end):
    result = query('''query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){contributionsCollection(from:$from,to:$to){
        contributionCalendar{totalContributions weeks{contributionDays{
          date contributionCount contributionLevel
        }}}
      }}
    }''', {'login': username, 'from': start.isoformat() + 'T00:00:00Z',
           'to': end.isoformat() + 'T23:59:59Z'})
    return result['contributionsCollection']['contributionCalendar']


def twelve_month_start(today):
    # Same calendar date one year earlier, exclusive, through today inclusive.
    day = min(today.day, calendar.monthrange(today.year - 1, today.month)[1])
    return date(today.year - 1, today.month, day) + timedelta(days=1)


def render(days, lifetime, created, today, username):
    start = twelve_month_start(today)
    days = sorted((d for d in days if start <= date.fromisoformat(d['date']) <= today),
                  key=lambda d: d['date'])
    recent = sum(d['contributionCount'] for d in days)
    first_sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="345" viewBox="0 0 900 345" role="img">',
             '<title>GitHub Analytics</title>',
             f'<desc>{recent} contribuições nos últimos 12 meses; {lifetime} desde a criação da conta.</desc>',
             '<rect width="900" height="345" rx="18" fill="#0f172a"/>',
             '<g font-family="Segoe UI,Arial,sans-serif" fill="#e2e8f0">',
             '<text x="28" y="36" font-size="20" font-weight="700">GitHub Analytics</text>',
             f'<text x="28" y="60" font-size="12" fill="#94a3b8">@{html.escape(username)} · atualizado em {today:%d/%m/%Y} (UTC)</text>',
             f'<text x="28" y="104" font-size="30" fill="#38bdf8" font-weight="700">{recent}</text>',
             '<text x="28" y="127" font-size="13">Contribuições nos últimos 12 meses</text>',
             f'<text x="465" y="104" font-size="30" fill="#38bdf8" font-weight="700">{lifetime}</text>',
             f'<text x="465" y="127" font-size="13">Total desde {created:%d/%m/%Y}</text>',
             f'<text x="28" y="158" font-size="12" fill="#94a3b8">Atividade · {start:%d/%m/%Y} a {today:%d/%m/%Y}</text>']
    levels = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2,
              'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
    labeled = set()
    for day in days:
        current = date.fromisoformat(day['date'])
        col = (current - first_sunday).days // 7
        row = (current.weekday() + 1) % 7
        x, y = 66 + col * 15, 190 + row * 15
        month = (current.year, current.month)
        if month not in labeled:
            parts.append(f'<text x="{x}" y="180" font-size="9" fill="#94a3b8">{current:%m/%y}</text>')
            labeled.add(month)
        color = COLORS[levels[day['contributionLevel']]]
        count = day['contributionCount']
        parts.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{color}"><title>{current:%d/%m/%Y}: {count} contribuições</title></rect>')
    for row, label in [(1, 'Seg'), (3, 'Qua'), (5, 'Sex')]:
        parts.append(f'<text x="28" y="{199 + row * 15}" font-size="10" fill="#94a3b8">{label}</text>')
    parts.append('<text x="28" y="323" font-size="10" fill="#94a3b8">Contribuições reconhecidas pelo GitHub e visíveis à consulta.</text>')
    parts.append('<text x="695" y="323" font-size="10" fill="#94a3b8">Menos</text>')
    for i, color in enumerate(COLORS):
        parts.append(f'<rect x="{735 + i * 15}" y="313" width="11" height="11" rx="2" fill="{color}"/>')
    parts.append('<text x="816" y="323" font-size="10" fill="#94a3b8">Mais</text></g></svg>')
    return '\n'.join(parts)


def main():
    username = os.environ.get('GH_USERNAME', 'yada071')
    today = datetime.now(timezone.utc).date()
    user = query('query($login:String!){user(login:$login){createdAt}}', {'login': username})
    created = date.fromisoformat(user['createdAt'][:10])
    recent_calendar = calendar_data(username, twelve_month_start(today), today)
    lifetime = 0
    for year in range(created.year, today.year + 1):
        annual = calendar_data(username, max(created, date(year, 1, 1)),
                               min(today, date(year, 12, 31)))
        lifetime += annual['totalContributions']
    days = [d for w in recent_calendar['weeks'] for d in w['contributionDays']]
    svg = render(days, lifetime, created, today, username)
    output = ROOT / 'assets' / 'github-analytics.svg'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding='utf-8')
    print(f'Painel atualizado: {sum(d["contributionCount"] for d in days)} recentes; {lifetime} totais.')


if __name__ == '__main__':
    main()
