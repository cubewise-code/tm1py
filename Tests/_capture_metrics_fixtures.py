"""One-off, read-only discovery: capture real }Stats* schemas + payloads.

Run against the configured servers to record fixtures for the pure record
shaper tests. Does NOT mutate server state. Writes JSON under
Tests/resources/metrics/.
"""

import configparser
import json
from pathlib import Path

from TM1py import TM1Service

HERE = Path(__file__).parent
OUT = HERE / "resources" / "metrics"
OUT.mkdir(parents=True, exist_ok=True)

STATS_CUBES = [
    "}StatsByCube",
    "}StatsForServer",
    "}StatsByRule",
    "}StatsByClient",
    "}StatsByCubeByClient",
    "}StatsByChore",
    "}StatsByProcess",
]


def dump(name, obj):
    path = OUT / name
    path.write_text(json.dumps(obj, indent=2, default=str))
    print(f"  wrote {path.relative_to(HERE)} ({path.stat().st_size} bytes)")


def capture_raw_cellset(tm1, mdx, name):
    cid = tm1.cells.create_cellset(mdx=mdx)
    try:
        raw = tm1.cells.extract_cellset_raw_response(cid, member_properties=["Name", "UniqueName"]).json()
    finally:
        tm1.cells.delete_cellset(cid)
    dump(name, raw)
    return raw


def capture_v11(tm1: TM1Service):
    print(f"v11 version: {tm1.version}")
    schemas = {}
    members = {}
    for cube in STATS_CUBES:
        if not tm1.cubes.exists(cube):
            print(f"  {cube}: MISSING")
            continue
        dims = tm1.cubes.get_dimension_names(cube)
        schemas[cube] = dims
        print(f"  {cube}: dims={dims}")
        for dim in dims:
            key = f"{cube}::{dim}"
            try:
                elems = tm1.elements.get_element_names(dim, dim)
                members[key] = elems if len(elems) <= 200 else elems[:200] + ["...(truncated)"]
            except Exception as e:
                members[key] = f"ERROR: {e}"
    dump("v11_stats_cube_dimensions.json", schemas)
    dump("v11_stats_members.json", members)

    # Real raw cellsets via the EXACT MDX the builder (Module B) produces.
    from TM1py.Metrics.mdx import build_v11_mdx

    builds = {
        "v11_by_cube_cellset_raw.json": build_v11_mdx("by_cube"),
        "v11_by_cube_include_control_cellset_raw.json": build_v11_mdx("by_cube", include_control=True),
        "v11_by_server_cellset_raw.json": build_v11_mdx("by_server"),
    }
    for name, mdx in builds.items():
        print(f"  MDX [{name}]:\n    {mdx}")
        try:
            capture_raw_cellset(tm1, mdx, name)
        except Exception as e:
            print(f"  {name} FAILED: {str(e)[:200]}")

    # by_rule (only if populated); structurally identical across versions.
    by_rule_mdx = (
        "SELECT NON EMPTY {[}RuleStats].Members} ON 0,"
        "NON EMPTY {[}Cubes].Members * [}LineNumber].Members} ON 1 "
        "FROM [}StatsByRule]"
    )
    try:
        capture_raw_cellset(tm1, by_rule_mdx, "v11_by_rule_cellset_raw.json")
    except Exception as e:
        print(f"  by_rule cellset failed: {str(e)[:200]}")


def capture_v12(tm1: TM1Service):
    print(f"v12 version: {tm1.version}")
    # raw, unshaped Metrics() payload (drives the v12 shaper tests)
    from TM1py.Metrics.odata_filter import build_metrics_url

    raw = tm1._tm1_rest.GET(build_metrics_url()).json().get("value", [])
    dump("v12_metrics_raw.json", raw)
    print(f"  Metrics(): {len(raw)} rows")


def main():
    config = configparser.ConfigParser()
    config.read(HERE / "config.ini")

    for label, fn in (("tm1srv01", capture_v11), ("tm1srv02", capture_v12)):
        print(f"=== {label} ===")
        try:
            with TM1Service(**config[label]) as tm1:
                fn(tm1)
        except Exception as e:
            print(f"  CONNECT/CAPTURE FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
