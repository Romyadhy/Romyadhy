import json
import math
import os
import urllib.error
import urllib.request

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = os.environ.get("GITHUB_USER", "Romyadhy")

IGNORED_LANGUAGES = {
    "html", "css", "blade", "makefile", "tex", "cmake", "dockerfile",
    "shell", "powershell", "batchfile", "scss", "sass", "less"
}

BAR_LENGTH = 20
TOP_LIMIT = 8
PER_PAGE = 100


def fetch_json(url: str, headers: dict):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_repos(headers: dict) -> list[dict]:
    all_repos = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{USERNAME}/repos"
            f"?per_page={PER_PAGE}&page={page}&type=owner"
        )
        repos = fetch_json(url, headers)
        if not isinstance(repos, list) or not repos:
            break
        all_repos.extend(repos)
        if len(repos) < PER_PAGE:
            break
        page += 1

    return all_repos


def fetch_languages() -> dict[str, int] | None:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "readme-language-stats-script"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        repos = fetch_all_repos(headers)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"Error fetching repos: {e}")
        return None

    lang_totals: dict[str, int] = {}
    for repo in repos:
        if repo.get("fork"):
            continue

        lang_url = repo.get("languages_url")
        if not lang_url:
            continue

        try:
            repo_langs = fetch_json(lang_url, headers)
            for lang, bytes_count in repo_langs.items():
                if lang.lower() in IGNORED_LANGUAGES:
                    continue
                if isinstance(bytes_count, int) and bytes_count > 0:
                    lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"Warning: skipped languages for {repo.get('name')}: {e}")

    return lang_totals


def generate_block(lang_totals: dict[str, int]) -> str | None:
    total_bytes = sum(lang_totals.values())
    if total_bytes <= 0:
        return None

    sorted_langs = sorted(
        lang_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )[:TOP_LIMIT]

    max_lang_name_len = max(len(lang) for lang, _ in sorted_langs)
    padding = max(max_lang_name_len + 2, 12)

    lines = ["```text"]
    for lang, bcount in sorted_langs:
        pct = (bcount / total_bytes) * 100
        exact_blocks = (pct / 100) * BAR_LENGTH

        if pct > 0:
            # Minimal 1 blok jika persentase > 0%, selain itu pembulatan standar
            filled_count = max(1, int(math.floor(exact_blocks + 0.5)))
            filled_count = min(filled_count, BAR_LENGTH)
        else:
            filled_count = 0

        empty_count = BAR_LENGTH - filled_count
        bar = "█" * filled_count + "░" * empty_count
        lines.append(f"{lang.ljust(padding)}[{bar}] {pct:5.2f}%")

    lines.append("```")
    return "\n".join(lines)


def update_readme(new_stats: str, readme_path: str = "README.md") -> bool:
    if not os.path.exists(readme_path):
        print(f"{readme_path} not found.")
        return False

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!-- START_SECTION:languages -->"
    end_marker = "<!-- END_SECTION:languages -->"

    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)

    if start_pos == -1 or end_pos == -1 or end_pos < start_pos:
        print("Markers not found or invalid order in README.md")
        return False

    start_idx = start_pos + len(start_marker)
    updated = (
        content[:start_idx]
        + "\n"
        + new_stats
        + "\n"
        + content[end_idx:]
    )

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated)

    print("README.md successfully updated.")
    return True


if __name__ == "__main__":
    languages = fetch_languages()
    if languages is None:
        print("Aborting README update due to API fetch error.")
        raise SystemExit(1)

    stats_output = generate_block(languages)
    if not stats_output:
        print("No language statistics found; leaving README.md untouched.")
        raise SystemExit(0)

    print("Generated output:")
    print(stats_output)
    update_readme(stats_output)
