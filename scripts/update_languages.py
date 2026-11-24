import os
import json
import urllib.request

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = os.environ.get("GITHUB_USER", "Romyadhy")

IGNORED_LANGUAGES = {
    "html", "css", "blade", "makefile", "tex", "cmake", "dockerfile",
    "shell", "powershell", "batchfile", "scss", "sass", "less"
}

BAR_LENGTH = 20
TOP_LIMIT = 8

def fetch_languages():
    url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-script"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            repos = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error fetching repos: {e}")
        return {}

    lang_totals = {}
    for repo in repos:
        # Skip forks if any
        if repo.get("fork"):
            continue
        lang_url = repo.get("languages_url")
        if not lang_url:
            continue
        try:
            req_lang = urllib.request.Request(lang_url, headers=headers)
            with urllib.request.urlopen(req_lang) as resp_lang:
                repo_langs = json.loads(resp_lang.read().decode())
                for lang, bytes_count in repo_langs.items():
                    if lang.lower() in IGNORED_LANGUAGES:
                        continue
                    lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count
        except Exception as e:
            print(f"Error fetching languages for {repo.get('name')}: {e}")

    return lang_totals

def generate_block(lang_totals):
    total_bytes = sum(lang_totals.values())
    if total_bytes == 0:
        return "No language statistics found."

    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:TOP_LIMIT]

    max_lang_name_len = max(len(lang) for lang, _ in sorted_langs)
    padding = max(max_lang_name_len + 2, 12)

    lines = ["```text"]
    for lang, bcount in sorted_langs:
        pct = (bcount / total_bytes) * 100
        # Compute filled vs empty blocks
        filled_count = int(round((pct / 100) * BAR_LENGTH))
        # Ensure at least 1 block if pct > 0, unless pct is 0
        if filled_count == 0 and pct > 0.05:
            filled_count = 1
        empty_count = max(BAR_LENGTH - filled_count, 0)

        bar = "█" * filled_count + "░" * empty_count
        lines.append(f"{lang.ljust(padding)}[{bar}] {pct:5.2f}%")
    lines.append("```")
    return "\n".join(lines)

def update_readme(new_stats):
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!-- START_SECTION:languages -->"
    end_marker = "<!-- END_SECTION:languages -->"

    if start_marker in content and end_marker in content:
        start_idx = content.find(start_marker) + len(start_marker)
        end_idx = content.find(end_marker)
        updated = content[:start_idx] + "\n" + new_stats + "\n" + content[end_idx:]
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print("README.md successfully updated.")
    else:
        print("Markers not found in README.md")

if __name__ == "__main__":
    languages = fetch_languages()
    stats_output = generate_block(languages)
    print("Generated output:")
    print(stats_output)
    update_readme(stats_output)
