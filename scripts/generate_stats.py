#!/usr/bin/env python3
import json
import math
import os
import sys
import urllib.request
import urllib.error

GITHUB_API_URL = "https://api.github.com"

def log(tag: str, msg: str):
  print(f"[{tag}] {msg}")

def get_github_token() -> tuple[str, str]:
  """Returns (token, source_description)"""
  token = os.environ.get("PERSONAL_ACCESS_TOKEN")
  if token:
    return token.strip(), "environment variable PERSONAL_ACCESS_TOKEN"

  token = os.environ.get("GITHUB_TOKEN")
  if token:
    return token.strip(), "environment variable GITHUB_TOKEN"

  script_dir = os.path.dirname(os.path.abspath(__file__))
  candidates = [
    os.path.join(os.getcwd(), ".secrets"),
    os.path.join(script_dir, "..", ".secrets"),
    os.path.join(os.getcwd(), ".env"),
    os.path.join(script_dir, "..", ".env"),
  ]

  for path in candidates:
    if os.path.isfile(path):
      try:
        with open(path, "r", encoding="utf-8") as f:
          for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
              continue
            if "=" in line:
              k, v = line.split("=", 1)
              k = k.strip()
              v = v.strip().strip("'\"")
              if k in (
                "PERSONAL_ACCESS_TOKEN",
                "GITHUB_TOKEN",
              ):
                return v, f"{path} (line {line_num})"
            elif line.startswith("ghp_") or line.startswith("github_pat_"):
              return line, f"{path} (line {line_num})"
      except Exception as e:
        log("WARN", f"Could not read file {path}: {e}")
  return "", "None"

def fetch_json(url: str, token: str = None) -> tuple[any, dict]:
  """Returns (parsed_json_or_None, response_headers)"""
  req = urllib.request.Request(url)
  req.add_header("User-Agent", "GitHub-Stats-Card-Generator")
  req.add_header("Accept", "application/vnd.github.v3+json")
  if token:
    req.add_header("Authorization", f"Bearer {token}")

  try:
    with urllib.request.urlopen(req) as resp:
      headers = dict(resp.headers)
      body = json.loads(resp.read().decode("utf-8"))
      return body, headers
  except urllib.error.HTTPError as e:
    error_body = ""
    try:
      error_body = e.read().decode("utf-8")
    except Exception:
      pass
    log("ERROR", f"HTTP {e.code} ({e.reason}) requesting: {url}")
    if error_body:
      log("ERROR", f"Response: {error_body}")
    return None, dict(e.headers) if hasattr(e, "headers") else {}
  except Exception as e:
    log("ERROR", f"Request failed for {url}: {e}")
    return None, {}

# Official GitHub Linguist color palette
LANGUAGE_COLORS = {
  "Kotlin": "#A97BFF",
  "Java": "#b07219",
  "Python": "#3572A5",
  "TypeScript": "#3178c6",
  "JavaScript": "#f1e05a",
  "HTML": "#e34c26",
  "CSS": "#563d7c",
  "Shell": "#89e051",
  "Bash": "#89e051",
  "C": "#555555",
  "C++": "#f34b7d",
  "C#": "#178600",
  "Dart": "#00B4AB",
  "PHP": "#4F5D95",
  "Swift": "#F05138",
  "Go": "#00ADD8",
  "Rust": "#dea584",
  "Ruby": "#701516",
  "Vue": "#41b883",
  "Scala": "#c22d40",
  "R": "#198CE7",
  "Objective-C": "#438eff",
  "Objective-C++": "#6866fb",
  "Lua": "#000080",
  "Dockerfile": "#384d54",
  "Makefile": "#427819",
  "SCSS": "#c6538c",
  "Sass": "#a53b70",
  "Less": "#1d365d",
  "Svelte": "#ff3e00",
  "Zig": "#ec915c",
  "Elixir": "#6e4a7e",
  "Erlang": "#B83998",
  "Clojure": "#db5855",
  "Haskell": "#5e5086",
  "Perl": "#0298c3",
  "Julia": "#a270ba",
  "PowerShell": "#012456",
  "SQL": "#e38c00",
  "PLpgSQL": "#336790",
  "TSQL": "#e38c00",
  "Assembly": "#6E4C13",
  "MATLAB": "#e16737",
  "Jupyter Notebook": "#DA5B0B",
  "Groovy": "#4298b8",
  "CMake": "#DA3434",
  "Vim Script": "#199f4b",
  "Emacs Lisp": "#c065db",
  "Solidity": "#AA6746",
}

def get_language_color(lang_name: str) -> str:
  if lang_name in LANGUAGE_COLORS:
    return LANGUAGE_COLORS[lang_name]
  palette = [
    "#e34c26", "#563d7c", "#f1e05a", "#3572a5", "#b07219",
    "#a97bff", "#00b4ab", "#dea584", "#00add8", "#f34b7d",
    "#178600", "#4F5D95", "#701516", "#41b883"
  ]
  hash_val = sum(ord(c) * (i + 1) for i, c in enumerate(lang_name))
  return palette[hash_val % len(palette)]

def build_svg_card(stats: dict, is_dark: bool = False) -> str:
  # Theme colors
  text_color = "#c9d1d9" if is_dark else "#24292f"
  muted_color = "#8b949e" if is_dark else "#57606a"
  accent_color = "#3fb950" if is_dark else "#2da44e"

  public_repos = stats.get("public_repos", 0)
  private_repos = stats.get("private_repos", 0)
  forks = stats.get("total_forks", 0)
  languages = stats.get("languages", [])

  # Dimensions & Padding (880px wide, centered)
  svg_width = 880
  content_width = 830
  padding_x = (svg_width - content_width) // 2  # 25px
  padding_y = 12

  # Calculate language progress bar with gaps between segments
  total_lang_bytes = sum(item["count"] for item in languages) or 1
  num_langs = len(languages)
  gap = 2.5
  total_gap = (num_langs - 1) * gap if num_langs > 1 else 0
  available_width = max(content_width - total_gap, 10)

  lang_bars_svg = []
  current_x = padding_x

  for lang in languages:
    w = (lang["count"] / total_lang_bytes) * available_width
    w = max(w, 2.0)
    color = get_language_color(lang["name"])
    lang_bars_svg.append(
      f'<rect x="{current_x:.1f}" y="44" width="{w:.1f}" height="8" rx="3" fill="{color}" />'
    )
    current_x += w + gap

  # Multi-row legends (perfectly aligned 4-column grid)
  num_cols = 4
  num_rows = math.ceil(num_langs / num_cols) if num_langs > 0 else 0
  col_w = 200
  grid_w = num_cols * col_w  # 800px total grid width
  grid_start_x = (svg_width - grid_w) // 2  # 40px left offset for exact centering

  lang_legends_svg = []
  for row_idx in range(num_rows):
    chunk = languages[row_idx * num_cols : (row_idx + 1) * num_cols]
    for j, lang in enumerate(chunk):
      pct = (lang["count"] / total_lang_bytes) * 100
      # XML-escape '<' as '&lt;' to ensure valid SVG syntax
      pct_str = "&lt;1%" if pct < 1.0 else f"{pct:.1f}%"
      color = get_language_color(lang["name"])

      item_x = grid_start_x + (j * col_w)
      item_y = 68 + (row_idx * 20)

      lang_legends_svg.append(
        f'''<g transform="translate({item_x}, {item_y})">
        <circle cx="4" cy="5" r="4" fill="{color}" />
        <text x="13" y="8.5" font-size="11.5" fill="{text_color}" font-family="Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif">{lang["name"]} <tspan fill="{muted_color}">({pct_str})</tspan></text>
      </g>'''
      )

  langs_markup = "".join(lang_bars_svg)
  legends_markup = "".join(lang_legends_svg)

  svg_height = 70 + (num_rows * 20) if num_rows > 0 else 70

  # Positions for 3 stats items centered across 880px
  c0 = 95
  c1 = 370
  c2 = 665

  svg = f"""<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .stat-label {{ font: 400 13px 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: {text_color}; }}
    .stat-value {{ font: 600 13px 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: {accent_color}; }}
    .sub-header {{ font: 500 13px 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: {muted_color}; }}
  </style>
  
  <!-- Stats Row: Public Repos, Private Repos, Forks -->
  <g transform="translate({padding_x}, {padding_y})">
    <!-- Public Repos -->
    <g transform="translate({c0}, 0)">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="{muted_color}">
        <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1h-8a1 1 0 00-1 1v6.708A2.486 2.486 0 014.5 9h8V1.5z"/>
      </svg>
      <text x="22" y="13" class="stat-label">Public Repos:</text>
      <text x="108" y="13" class="stat-value">{public_repos}</text>
    </g>
    <!-- Private Repos -->
    <g transform="translate({c1}, 0)">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="{muted_color}">
        <path fill-rule="evenodd" d="M4 4a4 4 0 018 0v2h.25c.966 0 1.75.784 1.75 1.75v5.5A1.75 1.75 0 0112.25 15h-8.5A1.75 1.75 0 012 13.25v-5.5C2 6.784 2.784 6 3.75 6H4V4zm2 2h4V4a2 2 0 10-4 0v2z"/>
      </svg>
      <text x="22" y="13" class="stat-label">Private Repos:</text>
      <text x="110" y="13" class="stat-value">{private_repos}</text>
    </g>
    <!-- Forks -->
    <g transform="translate({c2}, 0)">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="{muted_color}">
        <path d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h4.5A2.25 2.25 0 0012.5 6.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zM12.5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM8 12.75a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM8 10.5a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5z"/>
      </svg>
      <text x="22" y="13" class="stat-label">Forks:</text>
      <text x="64" y="13" class="stat-value">{forks}</text>
    </g>
  </g>

  <!-- Top Languages Progress Bar (segmented) -->
  {langs_markup}

  <!-- Language Legends -->
  {legends_markup}
</svg>
"""
  return svg

def main():
  log("INIT", "Starting GitHub Stats Generator...")
  token, token_source = get_github_token()
  username = (
    os.environ.get("GITHUB_USERNAME")
    or os.environ.get("GITHUB_REPOSITORY_OWNER")
    or "hector6872"
  )

  if token:
    log("AUTH", f"Found token via {token_source}")
  else:
    log("AUTH", "No token found (running unauthenticated; private repos unavailable)")

  log("USER", f"Target user: '{username}'")

  # Check authenticated identity and scopes
  is_authenticated_user = False
  auth_user = None
  if token:
    auth_user, headers = fetch_json(f"{GITHUB_API_URL}/user", token)
    scopes = headers.get("X-OAuth-Scopes", "none/fine-grained")
    log("AUTH", f"Token scopes: [{scopes}]")
    if auth_user:
      auth_login = auth_user.get("login", "")
      log(
        "AUTH",
        f"Authenticated as: '{auth_login}' (private repos: {auth_user.get('total_private_repos', 0)})",
      )
      if auth_login.lower() == username.lower():
        is_authenticated_user = True
        log("AUTH", "Authenticated user matches target username -> Private repo access ENABLED")
      else:
        log("AUTH", f"Token belongs to '{auth_login}', not '{username}' -> Reading target user as public")

  if is_authenticated_user and auth_user:
    user_data = auth_user
  else:
    user_data, _ = fetch_json(f"{GITHUB_API_URL}/users/{username}", token)

  if not user_data:
    log("WARN", f"Could not fetch user profile for '{username}'. Using defaults.")
    user_data = {"login": username, "public_repos": 0, "followers": 0}

  # Fetch repositories with pagination
  log("REPOS", f"Fetching repositories for '{username}'...")
  repos_data = []
  page = 1
  while True:
    if is_authenticated_user:
      url = f"{GITHUB_API_URL}/user/repos?per_page=100&affiliation=owner&sort=updated&page={page}"
    else:
      url = f"{GITHUB_API_URL}/users/{username}/repos?per_page=100&type=owner&sort=updated&page={page}"

    page_data, _ = fetch_json(url, token)
    if not page_data or not isinstance(page_data, list):
      break
    repos_data.extend(page_data)
    log("REPOS", f"  Page {page}: fetched {len(page_data)} repos")
    if len(page_data) < 100:
      break
    page += 1

  public_count = sum(1 for r in repos_data if not r.get("private"))
  private_count = sum(1 for r in repos_data if r.get("private"))
  total_forks = sum(repo.get("forks_count", 0) for repo in repos_data)

  log("REPOS", f"Total fetched repos: {len(repos_data)} (Public: {public_count}, Private: {private_count})")
  log("STATS", f"Total Forks: {total_forks}")

  # Calculate all language usage
  lang_counts = {}
  for repo in repos_data:
    if repo.get("fork"):
      continue
    lang = repo.get("language")
    size = repo.get("size", 1)
    if lang:
      lang_counts[lang] = lang_counts.get(lang, 0) + size

  all_languages = sorted(
    [{"name": k, "count": v} for k, v in lang_counts.items()],
    key=lambda x: x["count"],
    reverse=True,
  )

  total_lang_bytes = sum(item["count"] for item in all_languages) or 1
  lang_summary = ", ".join(
    f"{l['name']}: {(l['count'] / total_lang_bytes) * 100:.1f}% ({l['count']:,} KB)"
    for l in all_languages
  )
  log("LANGS", f"All languages ({len(all_languages)}): [{lang_summary if lang_summary else 'None detected'}]")

  stats = {
    "username": username,
    "name": user_data.get("name") or username,
    "public_repos": public_count,
    "private_repos": private_count,
    "total_forks": total_forks,
    "languages": all_languages,
  }

  out_dir = os.environ.get("OUTPUT_DIR", "dist")
  os.makedirs(out_dir, exist_ok=True)

  light_path = os.path.join(out_dir, "github-stats.svg")
  dark_path = os.path.join(out_dir, "github-stats-dark.svg")

  with open(light_path, "w", encoding="utf-8") as f:
    f.write(build_svg_card(stats, is_dark=False))

  with open(dark_path, "w", encoding="utf-8") as f:
    f.write(build_svg_card(stats, is_dark=True))

  log("OUTPUT", f"Generated: {light_path}")
  log("OUTPUT", f"Generated: {dark_path}")
  log(
    "DONE",
    f"Summary -> Public: {public_count}, Private: {private_count}, Forks: {total_forks}",
  )

if __name__ == "__main__":
  main()
