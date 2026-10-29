"""Keep the Modrinth project page in step with README.md.

  python3 -m lively_eyes.modrinth [--dry-run]

README.md shows its images from art/, which GitHub resolves but Modrinth
doesn't. Modrinth names every uploaded image by its SHA-1, so each art/ file
has a known address there: in the gallery, or among the images uploaded
through the description editor. Images in neither place are uploaded to the
gallery, titled by their alt text, and the description is set to README.md
with each art/ path swapped for its Modrinth address. The gallery is only
added to; nothing is removed from it.

Needs a Modrinth token with PROJECT_READ and PROJECT_WRITE in $MODRINTH_TOKEN.
--dry-run needs none: it uploads nothing and writes the description that
would be set to dist/MODRINTH.md (run with src/ on PYTHONPATH).
"""

import argparse
import hashlib
import json
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
PROJECT_ID = "fl6UhkVu"
API = f"https://api.modrinth.com/v2/project/{PROJECT_ID}"
CDN = "https://cdn.modrinth.com/data"
USER_AGENT = "3jar/Lively-Eyes (https://github.com/3jar/Lively-Eyes)"
GALLERY_LIMIT = 5 * 1024 * 1024  # bytes per gallery image

# an art/ path inside ![](...) or src="..."
ART = re.compile(r'(?<=[("])art/[^)"\s]+')


def alt_texts(readme):
    """art/ path -> alt text of the image that shows it."""
    alts = dict((path, alt) for alt, path in re.findall(r"!\[([^\]]*)\]\((art/[^)\s]+)\)", readme))
    for tag in re.findall(r"<img\s[^>]*>", readme):
        src, alt = re.search(r'src="([^"]*)"', tag), re.search(r'alt="([^"]*)"', tag)
        if src and alt:
            alts.setdefault(src.group(1), alt.group(1))
    return alts


def addresses(path):
    """Where Modrinth keeps this file once uploaded: (gallery, description editor)."""
    file = PROJECT / path
    if not file.is_file():
        raise SystemExit(f"README.md shows {path}, which does not exist")
    name = hashlib.sha1(file.read_bytes()).hexdigest() + file.suffix.lower()
    return f"{CDN}/{PROJECT_ID}/images/{name}", f"{CDN}/cached_images/{name}"


def _open(request):
    request.add_header("User-Agent", USER_AGENT)
    return urllib.request.urlopen(request, timeout=60)


def _on_cdn(url):
    # the CDN answers 200 for a stored image and 400 for anything else
    try:
        with _open(urllib.request.Request(url, method="HEAD")):
            return True
    except urllib.error.HTTPError:
        return False


def _api(method, query, token, data=None, content_type=None):
    request = urllib.request.Request(API + query, data=data, method=method, headers={"Authorization": token})
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with _open(request) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        # Modrinth answers 404 with no body for a draft project the token can't see
        detail = e.read().decode(errors="replace") or "check MODRINTH_TOKEN and its PROJECT_READ/PROJECT_WRITE scopes"
        raise SystemExit(f"Modrinth: {method} {query or '/'} failed with {e.code}: {detail}")


def plan(readme):
    """Each art/ image README.md shows -> its Modrinth URL, plus those that still need uploading."""
    urls, uploads = {}, []
    for path in sorted(set(ART.findall(readme))):
        gallery, cached = addresses(path)
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


def upload(path, title, token):
    file = PROJECT / path
    query = urllib.parse.urlencode({"ext": file.suffix[1:].lower(), "featured": "false", "title": title})
    _api("POST", f"/gallery?{query}", token, file.read_bytes(), mimetypes.guess_type(file.name)[0])


def sync(readme, token):
    urls, uploads = plan(readme)
    body = description(readme, urls)
    alts = alt_texts(readme)
    for path in uploads:
        upload(path, alts.get(path) or Path(path).stem, token)
        print("uploaded", path)
    project = json.loads(_api("GET", "", token))
    filed = {item.get(key) for item in project["gallery"] for key in ("url", "raw_url")}
    lost = [path for path in uploads if urls[path] not in filed]
    if lost:
        raise SystemExit(f"uploaded {', '.join(lost)}, but the gallery lists it under another address; "
                         "description left unchanged")
    if project["body"] == body:
        print("description already up to date")
    else:
        _api("PATCH", "", token, json.dumps({"body": body}).encode(), "application/json")
        print("updated description")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="upload nothing; write the description to dist/MODRINTH.md")
    parser.add_argument("--dist", type=Path, default=PROJECT / "dist")
    args = parser.parse_args()
    readme = (PROJECT / "README.md").read_text()
    if args.dry_run:
        urls, uploads = plan(readme)
        for path in uploads:
            print("would upload", path)
        args.dist.mkdir(parents=True, exist_ok=True)
        out = args.dist / "MODRINTH.md"
        out.write_text(description(readme, urls))
        print("wrote", out)
        return
    token = os.environ.get("MODRINTH_TOKEN")
    if not token:
        raise SystemExit("set MODRINTH_TOKEN to a Modrinth token with PROJECT_READ and PROJECT_WRITE, or use --dry-run")
    sync(readme, token)


if __name__ == "__main__":
    main()
