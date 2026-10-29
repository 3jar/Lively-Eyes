"""Apply project.toml and README.md to the GitHub repository and the Modrinth project.

  python3 -m lively_eyes.sync [--dry-run]

project.toml holds what both sites show besides README.md. A field left out
of it is left alone.

  GitHub    About description   summary
            About website       the Modrinth page (modrinth.type and .slug)
            topics              github.topics
  Modrinth  title, summary      name, summary
            slug, tags          modrinth.slug, .categories, .additional_categories
            links               source: the GitHub repository; modrinth.issues, .wiki, .discord
            icon                icon
            description         README.md with art/ paths swapped for Modrinth image URLs
            gallery             the art/ images README.md shows; only ever added to

Modrinth names every uploaded image by its SHA-1, so each art/ file has a
known address there: in the gallery, or among the images uploaded through the
description editor. Images in neither place are uploaded to the gallery,
titled by their alt text.

Each site needs a token and is skipped without one:
  $MODRINTH_TOKEN   Modrinth PAT with PROJECT_READ and PROJECT_WRITE
  $GH_REPO_TOKEN    GitHub token allowed to edit this repository's settings
                    (fine-grained: Administration, read and write)
--dry-run changes nothing: it lists what would change and writes the Modrinth
description to dist/MODRINTH.md (run with src/ on PYTHONPATH).
"""

import argparse
import hashlib
import json
import mimetypes
import os
import re
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
USER_AGENT = "3jar/Lively-Eyes sync (https://github.com/3jar/Lively-Eyes)"
MODRINTH_API = "https://api.modrinth.com/v2"
GITHUB_API = "https://api.github.com"
CDN = "https://cdn.modrinth.com/data"
GALLERY_LIMIT = 5 * 1024 * 1024  # bytes per gallery image
ICON_LIMIT = 256 * 1024  # bytes
# project.toml [modrinth] key -> Modrinth link field
LINKS = {"issues": "issues_url", "wiki": "wiki_url", "discord": "discord_url"}
# Modrinth fields project.toml can manage; the rest of the project is never touched
MODRINTH_FIELDS = ("title", "description", "slug", "categories", "additional_categories",
                   "source_url", *LINKS.values(), "body")
GITHUB_FIELDS = ("description", "homepage", "topics")
TOPIC = re.compile(r"[a-z0-9][a-z0-9-]{0,49}")

# an art/ path inside ![](...) or src="..."
ART = re.compile(r'(?<=[("])art/[^)"\s]+')


def load():
    return tomllib.loads((PROJECT / "project.toml").read_text())


def _call(method, url, headers=None, data=None, content_type=None):
    request = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": USER_AGENT, **(headers or {})})
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
    except urllib.error.HTTPError as e:
        # Modrinth answers 404 with no body for a draft project the token can't see
        detail = e.read().decode(errors="replace") or "no details; check the token and its permissions"
        raise SystemExit(f"{method} {url} failed with {e.code}: {detail}")
    return json.loads(raw) if raw else None


def _modrinth(method, path, token, data=None, content_type=None):
    return _call(method, MODRINTH_API + path, {"Authorization": token} if token else {}, data, content_type)


def _github(method, path, token, payload=None):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    return _call(method, GITHUB_API + path, headers, data, "application/json" if data else None)


def _on_cdn(url):
    # the CDN answers 200 for a stored image and 400 for anything else
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT}),
                                    timeout=60):
            return True
    except urllib.error.HTTPError:
        return False


def _same(live, wanted):
    if isinstance(wanted, list):
        return sorted(live or []) == sorted(wanted)
    return (live or None) == (wanted or None)  # "" and null both mean empty


def _show(value):
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 100 else f"({len(value)} characters)"


def diff(site, live, wanted, fields):
    """Print each field against what project.toml wants; return the ones to change."""
    changes = {}
    for key in fields:
        if key not in wanted:
            print(f"{site} {key}: not in project.toml, left as {_show(live.get(key))}")
        elif _same(live.get(key), wanted[key]):
            print(f"{site} {key}: up to date")
        else:
            print(f"{site} {key}: {_show(live.get(key))} -> {_show(wanted[key])}")
            changes[key] = wanted[key]
    return changes


def check(config):
    """Stop on anything either site would reject, before changing either."""
    topics = config.get("github", {}).get("topics", [])
    bad = [topic for topic in topics if not TOPIC.fullmatch(topic)]
    if bad or len(topics) > 20:
        raise SystemExit(f"GitHub topics are up to 20 of lowercase letters, digits and hyphens: {bad or topics}")
    modrinth = config.get("modrinth", {})
    tags = modrinth.get("categories", []) + modrinth.get("additional_categories", [])
    if tags:
        known = {tag["name"] for tag in _modrinth("GET", "/tag/category", None)
                 if tag["project_type"] == modrinth.get("type")}
        unknown = sorted(set(tags) - known)
        if unknown:
            raise SystemExit(f"not Modrinth tags for modrinth.type {modrinth.get('type')!r}: {', '.join(unknown)}")
    if "icon" in config:
        size = (PROJECT / config["icon"]).stat().st_size
        if size > ICON_LIMIT:
            raise SystemExit(f"{config['icon']} is {size / 1024:.0f} KiB; Modrinth takes icons up to 256 KiB")


# --- README.md -> Modrinth description

def alt_texts(readme):
    """art/ path -> alt text of the image that shows it."""
    alts = dict((path, alt) for alt, path in re.findall(r"!\[([^\]]*)\]\((art/[^)\s]+)\)", readme))
    for tag in re.findall(r"<img\s[^>]*>", readme):
        src, alt = re.search(r'src="([^"]*)"', tag), re.search(r'alt="([^"]*)"', tag)
        if src and alt:
            alts.setdefault(src.group(1), alt.group(1))
    return alts


def addresses(project_id, path):
    """Where Modrinth keeps this file once uploaded: (gallery, description editor)."""
    file = PROJECT / path
    if not file.is_file():
        raise SystemExit(f"README.md shows {path}, which does not exist")
    name = hashlib.sha1(file.read_bytes()).hexdigest() + file.suffix.lower()
    return f"{CDN}/{project_id}/images/{name}", f"{CDN}/cached_images/{name}"


def plan(project_id, readme):
    """Each art/ image README.md shows -> its Modrinth URL, plus those that still need uploading."""
    urls, uploads = {}, []
    for path in sorted(set(ART.findall(readme))):
        gallery, cached = addresses(project_id, path)
        found = next((url for url in (gallery, cached) if _on_cdn(url)), None)
        urls[path] = found or gallery
        if found is None:
            size = (PROJECT / path).stat().st_size
            if size > GALLERY_LIMIT:
                raise SystemExit(f"{path} is {size / 2**20:.1f} MiB; Modrinth's gallery takes up to 5 MiB")
            uploads.append(path)
    return urls, uploads


def description(readme, urls):
    return ART.sub(lambda m: urls[m.group()], readme)


# --- GitHub

def github_wanted(config):
    modrinth = config.get("modrinth", {})
    wanted = {"description": config.get("summary"), "topics": config.get("github", {}).get("topics")}
    if "type" in modrinth and "slug" in modrinth:
        wanted["homepage"] = f"https://modrinth.com/{modrinth['type']}/{modrinth['slug']}"
    return {key: value for key, value in wanted.items() if value is not None}


def sync_github(config, token, dry_run):
    if not token and not dry_run:
        print("::warning::GH_REPO_TOKEN is not set; GitHub was not updated")
        return
    path = f"/repos/{config['github']['repo']}"
    changes = diff("github", _github("GET", path, token), github_wanted(config), GITHUB_FIELDS)
    if dry_run:
        return
    fields = {key: value for key, value in changes.items() if key != "topics"}
    if fields:
        _github("PATCH", path, token, fields)
    if "topics" in changes:
        _github("PUT", f"{path}/topics", token, {"names": changes["topics"]})


# --- Modrinth

def modrinth_wanted(config, body):
    modrinth = config["modrinth"]
    wanted = {
        "title": config.get("name"),
        "description": config.get("summary"),
        "slug": modrinth.get("slug"),
        "categories": modrinth.get("categories"),
        "additional_categories": modrinth.get("additional_categories"),
        "source_url": f"https://github.com/{config['github']['repo']}",
        **{field: modrinth.get(key) for key, field in LINKS.items()},
        "body": body,
    }
    # "" in project.toml clears a link
    return {key: (value if value != "" else None) for key, value in wanted.items() if value is not None}


def sync_modrinth(config, readme, token, dry_run):
    project_id = config["modrinth"]["id"]
    urls, uploads = plan(project_id, readme)
    if not token:
        print(f"::warning::MODRINTH_TOKEN is not set; Modrinth was not {'read' if dry_run else 'updated'}")
        return
    alts = alt_texts(readme)
    for path in uploads:
        if dry_run:
            print("modrinth gallery: would upload", path)
            continue
        query = urllib.parse.urlencode({"ext": Path(path).suffix[1:].lower(), "featured": "false",
                                        "title": alts.get(path) or Path(path).stem})
        _modrinth("POST", f"/project/{project_id}/gallery?{query}", token, (PROJECT / path).read_bytes(),
                  mimetypes.guess_type(path)[0])
        print("modrinth gallery: uploaded", path)

    project = _modrinth("GET", f"/project/{project_id}", token)
    if config["modrinth"].get("type") not in (None, project["project_type"]):
        raise SystemExit(f"modrinth.type is {config['modrinth']['type']!r}, but the project is a {project['project_type']}")
    if not dry_run:
        filed = {item.get(key) for item in project["gallery"] for key in ("url", "raw_url")}
        lost = [path for path in uploads if urls[path] not in filed]
        if lost:
            raise SystemExit(f"uploaded {', '.join(lost)}, but the gallery lists it under another address; "
                             "nothing else was changed")

    changes = diff("modrinth", project, modrinth_wanted(config, description(readme, urls)), MODRINTH_FIELDS)
    if changes and not dry_run:
        _modrinth("PATCH", f"/project/{project_id}", token, json.dumps(changes).encode(), "application/json")

    if "icon" not in config:
        return
    icon = PROJECT / config["icon"]
    digest = hashlib.sha1(icon.read_bytes()).hexdigest()
    # like gallery images, the icon is filed under the SHA-1 of the uploaded file
    if digest in (project.get("icon_url") or ""):
        print("modrinth icon: up to date")
        return
    print(f"modrinth icon: -> {config['icon']}")
    if dry_run:
        return
    _modrinth("PATCH", f"/project/{project_id}/icon?ext={icon.suffix[1:]}", token, icon.read_bytes(),
              mimetypes.guess_type(icon.name)[0])
    if digest not in (_modrinth("GET", f"/project/{project_id}", token).get("icon_url") or ""):
        print("::warning::Modrinth filed the icon under another name; it will be uploaded again on every run")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="change nothing; list what would change")
    parser.add_argument("--dist", type=Path, default=PROJECT / "dist")
    args = parser.parse_args()
    config = load()
    readme = (PROJECT / "README.md").read_text()
    check(config)
    if args.dry_run:
        args.dist.mkdir(parents=True, exist_ok=True)
        out = args.dist / "MODRINTH.md"
        out.write_text(description(readme, plan(config["modrinth"]["id"], readme)[0]))
        print("wrote", out)
    sync_github(config, os.environ.get("GH_REPO_TOKEN"), args.dry_run)
    sync_modrinth(config, readme, os.environ.get("MODRINTH_TOKEN"), args.dry_run)


if __name__ == "__main__":
    main()
