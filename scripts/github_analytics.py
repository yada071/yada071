"""Generate bilingual, self-contained contribution KPI cards from public GitHub data."""
import calendar
import html
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def query(text, variables):
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("Execute pelo GitHub Actions ou configure GH_TOKEN localmente.")
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": text, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-contribution-kpis"},
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                result = json.load(response)
            break
        except (HTTPError, URLError) as error:
            if isinstance(error, HTTPError) and error.code < 500:
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    if result.get("errors"):
        raise RuntimeError(str(result["errors"]))
    return result["data"]


def twelve_month_start(today):
    day = min(today.day, calendar.monthrange(today.year - 1, today.month)[1])
    return date(today.year - 1, today.month, day) + timedelta(days=1)


def contributions(username, start, end, field, selection):
    """Paginate contributions; GitHub supplies the contribution-date filtering."""
    after = None
    while True:
        document = """
        query($login:String!,$from:DateTime!,$to:DateTime!,$after:String){
          user(login:$login){
            contributionsCollection(from:$from,to:$to){
              FIELD(first:100,after:$after){
                nodes{SELECTION}
                pageInfo{hasNextPage endCursor}
              }
            }
          }
        }""".replace("FIELD", field).replace("SELECTION", selection)
        data = query(document, {"login": username, "from": start.isoformat()+"T00:00:00Z",
                               "to": end.isoformat()+"T23:59:59Z", "after": after})
        if data["user"] is None:
            raise RuntimeError("Perfil GitHub não encontrado.")
        connection = data["user"]["contributionsCollection"][field]
        yield from connection["nodes"]
        if not connection["pageInfo"]["hasNextPage"]:
            break
        cursor = connection["pageInfo"]["endCursor"]
        if not cursor or cursor == after:
            raise RuntimeError("Paginação sem progresso; imagem anterior preservada.")
        after = cursor


def fetch_metrics(username, today):
    if not re.fullmatch(r"[A-Za-z0-9-]+", username):
        raise ValueError("Username GitHub inválido.")
    start = twelve_month_start(today)
    # Public merged PRs authored by the profile, filtered by merge date.
    search = (f"is:pr is:public author:{username} is:merged "
              f"merged:{start.isoformat()}..{today.isoformat()}")
    merged = query(
        "query($q:String!){search(query:$q,type:ISSUE,first:1){issueCount}}",
        {"q": search},
    )["search"]["issueCount"]
    repositories = set()
    reviewed = set()
    for field, node in [
        ("issueContributions", "issue"),
        ("pullRequestContributions", "pullRequest"),
        ("pullRequestReviewContributions", "pullRequest"),
    ]:
        selection = f"{node}{{id repository{{nameWithOwner isPrivate}}}}"
        for contribution in contributions(username, start, today, field, selection):
            resource = contribution[node]
            if resource is None:
                continue
            repository = resource["repository"]
            if repository["isPrivate"]:
                continue
            repositories.add(repository["nameWithOwner"])
            if field == "pullRequestReviewContributions":
                reviewed.add(resource["id"])
    data = query("""
        query($login:String!,$from:DateTime!,$to:DateTime!){
          user(login:$login){contributionsCollection(from:$from,to:$to){
            commitContributionsByRepository(maxRepositories:100){
              repository{nameWithOwner isPrivate}
            }
          }}
        }""", {"login": username, "from": start.isoformat()+"T00:00:00Z",
               "to": today.isoformat()+"T23:59:59Z"})
    commit_repositories = data["user"]["contributionsCollection"]["commitContributionsByRepository"]
    if len(commit_repositories) >= 100:
        raise RuntimeError("Limite de 100 repositórios atingido; total não será publicado como completo.")
    repositories.update(item["repository"]["nameWithOwner"] for item in commit_repositories
                        if not item["repository"]["isPrivate"])
    return {"merged": merged, "reviewed": len(reviewed), "repositories": len(repositories)}


ICONS = [
    '<circle cx="5" cy="5" r="3"/><circle cx="5" cy="23" r="3"/><circle cx="23" cy="23" r="3"/><path d="M5 8v12M12 5c11 0 11 8 11 15M12 5l4-4M12 5l4 4"/>',
    '<path d="M4 4h24v18H16l-7 6v-6H4z"/><path d="m10 12 4 4 8-8"/>',
    '<path d="M2 8h11l3 4h14v15H2z"/><path d="m12 16-4 4 4 4m8-8 4 4-4 4"/>',
]


def render(metrics, today, username, language="pt"):
    en = language == "en"
    labels = (["Merged pull requests", "Pull requests reviewed", "Repositories contributed to"] if en else
              ["Pull requests mesclados", "Pull requests revisados", "Repositórios com contribuições"])
    captions = (["Authored by me", "Distinct PRs reviewed", "Commits, issues, PRs and reviews"] if en else
                ["De minha autoria", "PRs distintos revisados", "Commits, issues, PRs e revisões"])
    waiting = metrics is None
    start = twelve_month_start(today)
    period = f"{start:%d/%m/%Y} — {today:%d/%m/%Y}"
    footer = ("Public activity · Last 12 months" if en else "Atividade pública · Últimos 12 meses")
    updated = (("Awaiting first sync" if en else "Aguardando primeira atualização") if waiting else
               (f"Updated {today:%d/%m/%Y} · UTC" if en else f"Atualizado em {today:%d/%m/%Y} · UTC"))
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="256" viewBox="0 0 1200 256" role="img" aria-labelledby="title desc">',
        '<title id="title">GitHub Activity</title>',
        f'<desc id="desc">{html.escape(footer)}. {html.escape(updated)}.</desc>',
        '''<style>
          .edge-light { stroke-dasharray: 75 1085; animation: edge-travel 22s linear infinite; }
          .facet { animation: facet-glow 10s ease-in-out infinite; }
          .metric { animation: metric-enter 1.1s ease-out both; }
          .icon-light { animation: icon-glow 8s ease-in-out infinite; }
          @keyframes edge-travel { to { stroke-dashoffset: -1160; } }
          @keyframes facet-glow { 0%,100% { opacity: .025; } 50% { opacity: .085; } }
          @keyframes metric-enter { from { opacity: .15; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
          @keyframes icon-glow { 0%,100% { opacity: .65; } 50% { opacity: 1; } }
          @media (prefers-reduced-motion: reduce) {
            .edge-light,.facet,.metric,.icon-light { animation: none; }
          }
        </style>''',
        '<defs><linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101d16"/><stop offset="1" stop-color="#09110d"/></linearGradient>',
        '<linearGradient id="edge"><stop stop-color="#72cca0"/><stop offset="1" stop-color="#244b37"/></linearGradient></defs>',
        '<g font-family="Segoe UI,Helvetica,Arial,sans-serif">',
    ]
    for index, (key, label, caption, icon) in enumerate(zip(
            ("merged", "reviewed", "repositories"), labels, captions, ICONS)):
        x = index * 408
        value = "—" if waiting else f"{metrics[key]:,}".replace(",", "." if not en else ",")
        parts.extend([
            f'<g transform="translate({x},0)">',
            '<rect x="1" y="1" width="382" height="198" rx="16" fill="url(#card)" stroke="#294534"/>',
            f'<rect class="edge-light" x="2" y="2" width="380" height="196" rx="15" fill="none" stroke="#88d4ac" stroke-width="1.2" opacity=".55" style="animation-delay:-{index * 7}s"/>',
            '<path d="M23 1h116" stroke="url(#edge)" stroke-width="2"/>',
            f'<text x="25" y="35" fill="#729983" font-family="Consolas,monospace" font-size="10" letter-spacing="2">0{index+1} / GITHUB</text>',
            f'<path class="facet" d="M297 0 383 86v-46L343 0z" fill="#76d3a0" opacity=".025" style="animation-delay:-{index * 3}s"/>',
            f'<g class="icon-light" style="animation-delay:-{index * 2}s"><g transform="translate(320,27) scale(.8)" fill="none" stroke="#8bc5a4" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{icon}</g></g>',
            f'<text class="metric" style="animation-delay:{index * .18:.2f}s" x="25" y="103" fill="#eaf5ee" font-size="51" font-weight="600" letter-spacing="-1">{value}</text>',
            f'<text x="26" y="141" fill="#c0d8ca" font-size="18" font-weight="600">{html.escape(label)}</text>',
            f'<text x="26" y="171" fill="#819f8d" font-size="13">{html.escape(caption)}</text>',
            '</g>',
        ])
    parts.extend([
        f'<text x="2" y="225" fill="#8fae9c" font-size="12">{footer} · {period}</text>',
        f'<text x="1198" y="225" text-anchor="end" fill="#8fae9c" font-size="12">{updated}</text>',
        f'<text x="2" y="248" fill="#75917f" font-size="11">@{html.escape(username)}</text>',
        '</g></svg>',
    ])
    return "\n".join(parts)


def main():
    username = os.environ.get("GH_USERNAME", "yada071")
    today = datetime.now(timezone.utc).date()
    metrics = None if "--placeholder" in sys.argv else fetch_metrics(username, today)
    # Complete both renderings before replacing either output.
    images = [(ROOT / "assets" / filename, render(metrics, today, username, language))
              for filename, language in [("github-analytics.svg", "pt"),
                                          ("github-analytics.en.svg", "en")]]
    for path, image in images:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(image, encoding="utf-8")
    print("Cards gerados (aguardando sincronização)." if metrics is None else json.dumps(metrics))


if __name__ == "__main__":
    main()
