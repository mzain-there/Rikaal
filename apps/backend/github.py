import httpx

from .config import GITHUB_TOKEN


GITHUB_API_URL = "https://api.github.com"

MAX_FILE_SIZE = 100 * 1024

def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return headers

def get_repo_tree(repo: str, branch: str) -> list[dict]:
    """Return all files in a GitHub repository branch."""
    url = f"{GITHUB_API_URL}/repos/{repo}/git/trees/{branch}"

    response = httpx.get(
        url,
        headers=_headers(),
        params={"recursive": "1"},
        timeout=20.0,
    )

    if response.status_code == 404:
        raise ValueError("Repository/branch was not found or Repo is Private.")

    if response.status_code == 403:
        raise ValueError("Repository is not public or GitHub rate limit was reached.")

    response.raise_for_status()

    data = response.json()

    return data.get("tree", [])


def get_file_content(repo: str, path: str, branch: str) -> str:
    """Fetch the text content of a file from a GitHub repository."""
    url = f"{GITHUB_API_URL}/repos/{repo}/contents/{path}"

    response = httpx.get(
        url,
        headers=_headers(),
        params={"ref": branch},
        timeout=20.0,
    )

    if response.status_code == 404:
        raise ValueError(f"File not found: {path}")

    if response.status_code == 403:
        raise ValueError("Repository is not public or GitHub rate limit was reached.")

    response.raise_for_status()

    data = response.json()

    if data.get("type") != "file":
        raise ValueError(f"{path} is not a file.")

    download_url = data.get("download_url")

    if not download_url:
        raise ValueError(f"Could not get download URL for {path}")

    file_response = httpx.get(
        download_url,
        headers=_headers(),
        timeout=20.0,
    )

    file_response.raise_for_status()

    return file_response.text


def select_markdown_files(tree: list[dict]) -> list[dict]:
    """Select README.md and Markdown files under docs/."""
    selected = []

    for item in tree:
        if item.get("type") != "blob":
            continue

        path = item.get("path", "")
        size = item.get("size", 0)

        if path == "README.md":
            selected.append({"path": path, "size": size})
        elif path.startswith("docs/") and path.endswith(".md"):
            selected.append({"path": path, "size": size})

    return selected

def is_file_too_large(size: int) -> bool:
    """Return True when a file is larger than the ingestion limit."""
    return size > MAX_FILE_SIZE