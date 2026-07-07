#!/usr/bin/env python3
import os
import sys
import json
from typing import Dict, List, Any, Optional, Set

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

#
# CONFIGURATION
#

#  Use the same host as the frontend: nginx on localhost:80
# TODO GEAR-567
DOCCANO_URL = os.getenv("DOCCANO_URL", "http://localhost").rstrip("/")

USERNAME = os.getenv("DOCCANO_USERNAME")  # Required
PASSWORD = os.getenv("DOCCANO_PASSWORD")  # Required

# Populated at runtime by login(), then reused for every request.
API_TOKEN: Optional[str] = None

PROJECT_NAME = os.getenv("DOCCANO_PROJECT_NAME")  # Required
PROJECT_TYPE = os.getenv("DOCCANO_PROJECT_TYPE", "SequenceLabeling")  # Required + Default value set
PROJECT_DESCRIPTION = os.getenv("DOCCANO_PROJECT_DESCRIPTION", "")  # Default value set
PROJECT_GUIDELINE = os.getenv("DOCCANO_PROJECT_GUIDELINE", "")  # Default value set
PROJECT_RESOURCETYPE = os.getenv("DOCCANO_PROJECT_RESOURCETYPE", "SequenceLabelingProject")  # Required + Default value set

# Hot folder
ANNOTATIONS_DIR = os.getenv("DOCCANO_ANNOTATIONS_DIR", "annotations")

# Labels file, if we want to put some general labels 
# to use in the event the hot folder file does not have any.
LABELS_FILE = os.getenv("DOCCANO_LABELS_FILE", "labels.json")

# Default
CREATE_PROJECT_IF_MISSING = os.getenv(
    "DOCCANO_CREATE_PROJECT_IF_MISSING", "false"
).lower() in ("1", "true", "yes")

SESSION = requests.Session()
TIMEOUT = (5, 30)  # (connect, read)

retry = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=1,
    status_forcelist=[
        429,
        500,
        502,
        503,
        504,
    ],
    allowed_methods=frozenset(
        ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    ),
    raise_on_status=False,
)

adapter = HTTPAdapter(max_retries=retry)

SESSION.mount("http://", adapter)
SESSION.mount("https://", adapter)


# AUTH: LOG IN ONCE TO EXCHANGE USERNAME/PASSWORD FOR A DRF TOKEN
def login(username: str, password: str) -> str:
    """
    Log into doccano via /v1/auth/login/ using username/password.

    dj_rest_auth's LoginView returns the user's DRF authtoken as
    {"key": "<token>"} (it sets a session cookie, which
    we ignore and every subsequent request authenticates with the
    returned token).
    """
    url = f"{DOCCANO_URL}/v1/auth/login/"
    resp = SESSION.post(
        url,
        json={"username": username, "password": password},
        timeout=TIMEOUT,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        print(f"[ERROR] Login failed: {exc} - {resp.text}", file=sys.stderr)
        raise

    try:
        payload = resp.json()
    except ValueError:
        raise RuntimeError(f"Invalid JSON returned from login: {resp.text}")

    token = payload.get("key")
    if not token:
        raise RuntimeError(f"Login succeeded but no 'key' in response: {resp.text}")

    # Clear session cookies so subsequent requests authenticate via token only,
    # not via the session cookie that dj_rest_auth sets as a side effect.
    SESSION.cookies.clear()

    print("[INFO] Logged in and obtained API token.")
    return token


def get_headers() -> Dict[str, str]:
    """
    Build headers for requests, authenticated via DRF TokenAuthentication.
    """
    if not API_TOKEN:
        raise RuntimeError("API_TOKEN is not set - call login() first.")
    return {
        "Accept": "application/json",
        "Authorization": f"Token {API_TOKEN}",
    }

#
# PROJECT HELPERS
#
def fetch_projects(name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch all projects, optionally filtered server-side by name via `q`,
    paging through results so a project isn't missed if it falls outside
    the first page.
    """
    url = f"{DOCCANO_URL}/v1/projects"
    all_results: List[Dict[str, Any]] = []
    offset = 0
    limit = 100  # page size; adjust as needed

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "q": name or "",
            "ordering": "created_at",
        }
        resp = SESSION.get(url, headers=get_headers(), params=params, timeout=TIMEOUT)
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            print(
                f"[ERROR] GET {resp.url} failed: {exc}\n"
                f"Status: {resp.status_code}\nBody: {resp.text}",
                file=sys.stderr,
            )
            raise

        data = resp.json()
        if isinstance(data, dict) and "results" in data:
            page = data["results"]
            all_results.extend(page)
            if not data.get("next"):
                break
        elif isinstance(data, list):
            # Non-paginated response — assume complete.
            all_results.extend(data)
            break
        else:
            raise RuntimeError(f"Unexpected projects response shape: {type(data)} - {data}")

        offset += limit

    return all_results


def find_project_by_name(projects: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    for proj in projects:
        if proj.get("name") == name:
            return proj
    return None


def create_project() -> Dict[str, Any]:
    """
    Create a new project using PROJECT_* settings.
    """
    if not PROJECT_RESOURCETYPE:
        raise RuntimeError(
            "DOCCANO_PROJECT_RESOURCETYPE is not set, but the backend "
            "requires a 'resourcetype' field to create projects. "
            "Set DOCCANO_PROJECT_RESOURCETYPE to the correct value for this "
            "Doccano deployment (check an existing project's JSON)."
        )

    payload = {
        "name": PROJECT_NAME,
        "project_type": PROJECT_TYPE,
        "description": PROJECT_DESCRIPTION,
        "guideline": PROJECT_GUIDELINE,
        "resourcetype": PROJECT_RESOURCETYPE,
    }

    url = f"{DOCCANO_URL}/v1/projects"
    resp = SESSION.post(
        url,
        json=payload,
        headers=get_headers(),
        timeout=TIMEOUT,
    )
    if resp.status_code not in (200, 201):
        print(
            f"[ERROR] Failed to create project: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )
        resp.raise_for_status()

    project = resp.json()
    print(f"[INFO] Created project '{PROJECT_NAME}' (id={project.get('id')}).")
    return project


def update_project_if_needed(project: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare project description/guideline and update if they differ
    from the configured values.
    """
    project_id = project["id"]
    changed = False

    new_description = project.get("description", "")
    new_guideline = project.get("guideline", "")

    if PROJECT_DESCRIPTION and new_description != PROJECT_DESCRIPTION:
        new_description = PROJECT_DESCRIPTION
        changed = True

    if PROJECT_GUIDELINE and new_guideline != PROJECT_GUIDELINE:
        new_guideline = PROJECT_GUIDELINE
        changed = True

    if not changed:
        print(f"[INFO] Project '{project['name']}' (id={project_id}) is up to date.")
        return project

    # Try to preserve existing resourcetype, or fall back to env if needed
    resourcetype = project.get("resourcetype", PROJECT_RESOURCETYPE)
    if resourcetype is None:
        raise RuntimeError(
            "Project update would drop 'resourcetype', but it is required. "
            "Make sure the project JSON includes 'resourcetype' or set "
            "DOCCANO_PROJECT_RESOURCETYPE when calling cron."
        )

    url = f"{DOCCANO_URL}/v1/projects/{project_id}"
    updated_payload = {
        "name": project.get("name"),
        "project_type": project.get("project_type"),
        "description": new_description,
        "guideline": new_guideline,
        "resourcetype": resourcetype,
    }

    resp = SESSION.put(
        url,
        json=updated_payload,
        headers=get_headers(),
        timeout=TIMEOUT,
    )
    if resp.status_code not in (200, 202):
        print(
            f"[ERROR] Failed to update project {project_id}: "
            f"{resp.status_code} {resp.text}",
            file=sys.stderr,
        )
        resp.raise_for_status()

    updated = resp.json()
    print(f"[INFO] Updated project '{updated['name']}' (id={updated['id']}).")
    return updated


def get_or_create_project() -> Dict[str, Any]:
    """
    Find an existing project by name. If not found and
    CREATE_PROJECT_IF_MISSING is true, create it.

    Otherwise, fail with a clear error so the user can create it via the UI.
    """
    projects = fetch_projects(name=PROJECT_NAME)
    existing = find_project_by_name(projects, PROJECT_NAME)
    if existing:
        print(f"[INFO] Found existing project '{PROJECT_NAME}' (id={existing['id']}).")
        return existing

    if CREATE_PROJECT_IF_MISSING:
        print(
            f"[INFO] Project '{PROJECT_NAME}' not found. "
            "CREATE_PROJECT_IF_MISSING is true – creating it."
        )
        return create_project()

    raise RuntimeError(
        f"Project '{PROJECT_NAME}' not found. "
        "if DOCCANO_CREATE_PROJECT_IF_MISSING is false, "
        " then the project needs to exist."
        "Either create the project via the UI first or set "
        "DOCCANO_CREATE_PROJECT_IF_MISSING=true."
    )


#
# LABEL EXTRACTION FROM ANNOTATIONS
#
def extract_labels_from_annotations_dir(dir_path: str) -> List[Dict[str, Any]]:
    if not os.path.isdir(dir_path):
        print(f"[WARN] Annotations directory '{dir_path}' does not exist.", file=sys.stderr)
        return []

    labels: Set[str] = set()
    # Used only to detect labels that differ only by case.
    normalized_labels: Dict[str, str] = {}
    json_files = [f for f in os.listdir(dir_path) if f.lower().endswith(".json")]

    if not json_files:
        print(f"[WARN] No .json files found in '{dir_path}'.", file=sys.stderr)
        return []

    for fname in sorted(json_files):
        fpath = os.path.join(dir_path, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[WARN] Skipping '{fpath}' (bad JSON): {exc}", file=sys.stderr)
            continue

        if isinstance(data, dict):
            docs = [data]
        elif isinstance(data, list):
            docs = [d for d in data if isinstance(d, dict)]
        else:
            print(
                f"[WARN] Skipping '{fpath}' (unexpected root type {type(data)}).",
                file=sys.stderr,
            )
            continue

        for doc in docs:
            entities = doc.get("entities", [])
            if not isinstance(entities, list):
                continue
            for ent in entities:
                if not isinstance(ent, dict):
                    continue
                label = ent.get("label")
                if not isinstance(label, str):
                    continue

                stripped = label.strip()
                if not stripped:
                    continue

                # Warn if the annotation contains accidental whitespace.
                if stripped != label:
                    print(
                        f"[WARN] Label '{label}' contains leading/trailing whitespace. "
                        f"Using '{stripped}'.",
                        file=sys.stderr,
                    )

                key = stripped.casefold()
                existing = normalized_labels.get(key)
                if existing and existing != stripped:
                    print(
                        f"[WARN] Possible duplicate labels differing only by case: "
                        f"'{existing}' and '{stripped}'",
                        file=sys.stderr,
                    )
                else:
                    normalized_labels[key] = stripped

                labels.add(stripped)

    if not labels:
        print(f"[WARN] No labels found in annotations directory '{dir_path}'.", file=sys.stderr)
        return []

    print(f"[INFO] Extracted {len(labels)} unique labels from '{dir_path}'.")
    return [{"text": lbl} for lbl in sorted(labels)]


def load_label_specs_from_file(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Labels file must contain a list, got {type(data)}")
    return data


#
# LABEL SYNC
#
def fetch_project_labels(project_id: int) -> List[Dict[str, Any]]:
    """
    Fetch label definitions (span types) for a project.

    This calls:
      GET /v1/projects/{project_id}/span-types
    """
    url = f"{DOCCANO_URL}/v1/projects/{project_id}/span-types"  # no trailing slash
    resp = SESSION.get(url, headers=get_headers(), timeout=TIMEOUT)
    resp.raise_for_status()

    data = resp.json()
    
    # Check if the label is a list or dict, not both.
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    elif isinstance(data, list):
        return data
    else:
        raise RuntimeError(
            f"Unexpected label-types response shape: {type(data)} - {data}"
        )


def sync_labels(project_id: int, label_specs: List[Dict[str, Any]]) -> None:
    existing_labels = fetch_project_labels(project_id)
    by_text = {lbl["text"]: lbl for lbl in existing_labels}

    created = 0
    updated = 0

    for spec in label_specs:
        text = spec.get("text")
        if not text:
            print(f"[WARN] Skipping label with no 'text': {spec}", file=sys.stderr)
            continue

        # Make a copy so we don't edit the original
        spec = spec.copy()

        # Specify colors of labels
        spec.setdefault("background_color", "#FFDE64")
        spec.setdefault("text_color", "#000000")

        current = by_text.get(text)

        if current is None:
            # Create new span-type (label)
            url = f"{DOCCANO_URL}/v1/projects/{project_id}/span-types"
            resp = SESSION.post(
                url,
                json=spec,
                headers=get_headers(),
                timeout=TIMEOUT,
            )
            if resp.status_code not in (200, 201):
                print(
                    f"[ERROR] Failed to create label '{text}': "
                    f"{resp.status_code} {resp.text}",
                    file=sys.stderr,
                )
                resp.raise_for_status()
            else:
                created += 1
                print(f"[INFO] Created label '{text}'.")
                by_text[text] = resp.json()
        else:
            # Update existing span-type (label)
            label_id = current["id"]
            payload = current.copy()
            payload.update(spec)

            url = f"{DOCCANO_URL}/v1/projects/{project_id}/span-types/{label_id}"
            resp = SESSION.put(
                url,
                json=payload,
                headers=get_headers(),
                timeout=TIMEOUT,
            )
            if resp.status_code not in (200, 202):
                print(
                    f"[ERROR] Failed to update label '{text}' (id={label_id}): "
                    f"{resp.status_code} {resp.text}",
                    file=sys.stderr,
                )
                resp.raise_for_status()
            else:
                updated += 1
                print(f"[INFO] Updated label '{text}' (id={label_id}).")

    print(f"[INFO] Label sync complete. Created: {created}, Updated: {updated}.")


#
# MAIN
#
def main() -> int:
    global API_TOKEN

    if not USERNAME or not PASSWORD:
        print("[FATAL] DOCCANO_USERNAME and DOCCANO_PASSWORD are required.", file=sys.stderr)
        return 1

    try:
        API_TOKEN = login(USERNAME, PASSWORD)
    except Exception as exc:
        print(f"[FATAL] Could not log in: {exc}", file=sys.stderr)
        return 1

    # Create project if specified
    try:
        project = get_or_create_project()
    except Exception as exc:
        print(f"[FATAL] Could not get or create project: {exc}", file=sys.stderr)
        return 1

    # Update project if needed
    try:
        project = update_project_if_needed(project)
    except Exception as exc:
        print(f"[ERROR] Failed to update project metadata: {exc}", file=sys.stderr)

    # Pull labels from annotations directory
    label_specs: List[Dict[str, Any]] = []
    if ANNOTATIONS_DIR and os.path.isdir(ANNOTATIONS_DIR):
        label_specs = extract_labels_from_annotations_dir(ANNOTATIONS_DIR)

    # Fallback to labels.json if needed
    if not label_specs and LABELS_FILE and os.path.exists(LABELS_FILE):
        try:
            print(
                f"[INFO] No labels from annotations; using labels file '{LABELS_FILE}'."
            )
            label_specs = load_label_specs_from_file(LABELS_FILE)
        except Exception as exc:
            print(
                f"[FATAL] Failed to load labels file '{LABELS_FILE}': {exc}",
                file=sys.stderr,
            )
            return 1

    if not label_specs:
        print(
            "[WARN] No labels to sync (no annotations and no labels file). "
            "Skipping label sync.",
            file=sys.stderr,
        )
        return 0

    try:
        sync_labels(project["id"], label_specs)
    except Exception as exc:
        print(f"[ERROR] Label sync failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
