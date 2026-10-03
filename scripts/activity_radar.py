"""Render an "Activity overview" radar (commits / issues / PRs / code review)
for a GitHub user as assets/activity-radar.svg, using the GraphQL API."""
import json
import math
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "niti007")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = os.environ.get("OUT", "assets/activity-radar.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
    }
  }
}"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(body["errors"])
    return body["data"]["user"]["contributionsCollection"]


def render(c):
    # (label, count, angle in degrees; 0 = up, clockwise)
    axes = [
        ("Code review", c["totalPullRequestReviewContributions"], 0),
        ("Issues", c["totalIssueContributions"], 90),
        ("Pull requests", c["totalPullRequestContributions"], 180),
        ("Commits", c["totalCommitContributions"], 270),
    ]
    total = sum(n for _, n, _ in axes) or 1
    pcts = [n / total for _, n, _ in axes]
    top = max(pcts) or 1

    W, H, cx, cy, R = 460, 340, 230, 160, 110
    accent = "#3fb950"

    def pt(angle, frac):
        a = math.radians(angle)
        return cx + R * frac * math.sin(a), cy - R * frac * math.cos(a)

    pts = [pt(a, max(p / top, 0.03)) for (_, _, a), p in zip(axes, pcts)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="14">',
           f'<title>Activity overview for {USER}</title>',
           '<style>.pct{fill:#24292f}.lbl{fill:#57606a}'
           '@media (prefers-color-scheme:dark){.pct{fill:#e6edf3}.lbl{fill:#8b949e}}</style>']
    for _, _, a in axes:
        x, y = pt(a, 1)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{accent}" stroke-width="2" opacity=".8"/>')
    out.append(f'<polygon points="{poly}" fill="{accent}" fill-opacity=".35"/>')
    for x, y in pts:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#fff" stroke="{accent}" stroke-width="2"/>')
    # (x, y of the percentage line, text-anchor) per axis angle; name sits 18px below
    label_pos = {0: (cx, 30), 90: (W - 44, cy - 6), 180: (cx, cy + R + 36), 270: (44, cy - 6)}
    for (name, _, a), p in zip(axes, pcts):
        x, y = label_pos[a]
        out.append(f'<text class="pct" x="{x}" y="{y}" text-anchor="middle">{round(p * 100)}%</text>')
        out.append(f'<text class="lbl" x="{x}" y="{y + 18}" text-anchor="middle">{name}</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(render(fetch()))
    print("wrote", OUT)
