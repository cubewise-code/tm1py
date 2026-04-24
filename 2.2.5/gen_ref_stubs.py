from pathlib import Path
import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

base_dir = Path("TM1py")

categories = {
    "Services": base_dir / "Services",
    "Objects": base_dir / "Objects",
    "Utils": base_dir / "Utils",
    "Exceptions": base_dir / "Exceptions",
}

api_map = {}
for category, path in categories.items():
    api_map[category] = {}
    for file in path.glob("*.py"):
        if file.name == "__init__.py":
            continue
        module_name = file.stem
        import_path = f"TM1py.{category}.{module_name}"
        api_map[category][module_name] = import_path


for category, entries in api_map.items():
    for name, import_path in sorted(entries.items()):
        filename = Path("reference") / category.lower() / f"{name.lower()}.md"
        with mkdocs_gen_files.open(filename, "w") as f:
            f.write(f"<!-- {name}-->\n\n")
            f.write(f"::: {import_path}\n")

        rel_filename = Path(*filename.parts[1:])
        nav[category, name] = rel_filename


with mkdocs_gen_files.open("reference/summary.md", "w") as nav_file:
    nav_file.write("# API Reference\n")
    nav_file.writelines(nav.build_literate_nav())
