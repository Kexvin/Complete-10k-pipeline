"""Check and report missing imports for this project.

Run from the repo root:
    python scripts\check_imports.py
"""
import importlib
import sys

REQUIREMENTS = [
    ("pydantic", "pydantic"),
    ("transformers", "transformers"),
    ("requests", "requests"),
    ("pinecone", "pinecone-client"),
    ("torch", "torch"),
    ("numpy", "numpy"),
]

missing = []
for pkg_name, pip_name in REQUIREMENTS:
    try:
        importlib.import_module(pkg_name)
    except Exception as e:
        missing.append((pkg_name, pip_name, str(e)))

if not missing:
    print("All checked packages import successfully.")
    sys.exit(0)

print("Missing or failing imports detected:\n")
for pkg_name, pip_name, err in missing:
    print(f"- {pkg_name}: import failed with: {err}")
    print(f"  Install: python -m pip install {pip_name}\n")

print("Tip: run inside your virtualenv or use --user if you prefer user installs.")
