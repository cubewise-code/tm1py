import json
import re
import sys
from packaging.version import Version

def parse_version(v):
    """Convert 'v2.1.3' → Version('2.1.3')"""
    return Version(v.lstrip("v"))

def load_versions(path):
    with open(path, "r") as f:
        data = json.load(f)
    return [entry["version"] for entry in data["versions"]]

def group_versions(versions):
    parsed = [parse_version(v) for v in versions]
    parsed.sort(reverse=True)

    # Group by major.minor
    groups = {}
    for v in parsed:
        key = f"{v.major}.{v.minor}"
        groups.setdefault(key, []).append(v)

    return parsed, groups

def select_visible(parsed, groups):
    visible = []

    # 1. Previous major version (e.g., v2.x if current is v3.x)
    current_major = parsed[0].major
    previous_major = current_major - 1

    for v in parsed:
        if v.major == previous_major:
            visible.append(v)
            break  # only latest patch of previous major

    # 2. Last 3 minor versions of current major
    current_minor_groups = [
        g for g in groups.keys()
        if g.startswith(f"{current_major}.")
    ]
    current_minor_groups.sort(reverse=True)
    last_three = current_minor_groups[:3]

    for minor in last_three:
        latest_patch = groups[minor][0]  # sorted desc
        visible.append(latest_patch)

    return visible

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "versions.json"
    versions = load_versions(path)
    
    # In case of first run case as no versions exist yet
    if not versions:
        output = {
            "visible": [],
            "hidden": []
        }
        print(json.dumps(output, indent=2))
        return

    parsed, groups = group_versions(versions)
    visible = select_visible(parsed, groups)
    visible_strings = [f"v{v.public}" for v in visible]
    hidden_strings = [v for v in versions if v not in visible_strings]

    output = {
        "visible": visible_strings,
        "hidden": hidden_strings
    }

    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
