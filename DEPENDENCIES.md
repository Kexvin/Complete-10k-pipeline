# Dependencies and how to install

This project uses several third-party Python packages. To install the typical set used during development, run:

```powershell
python -m pip install -r requirements.txt
```

If you prefer a virtual environment:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install -r requirements.txt
```

If an import error appears in your editor, run `scripts/check_imports.py` to get direct pip commands for missing packages.

Notes for Windows / heavy packages
---------------------------------
- Some packages (notably `numpy` and `torch`) include compiled components. On Windows you may need either pre-built wheels or a C build toolchain (Visual Studio Build Tools) to compile from source.

- Recommended approach on Windows:

	1. Install the minimal dependencies first:

```powershell
python -m pip install -r requirements.txt
```

	2. Install PyTorch (CPU-only) using the official index if needed:

```powershell
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
```

	3. Set up Pinecone for vector storage:

```powershell
python -m pip install pinecone-client
$env:PINECONE_API_KEY="your-api-key-here"  # Replace with your actual API key
```

If a package fails to build (error about compilers or meson), either install the Visual Studio Build Tools or install a binary wheel for that package that matches your Python version.

For Pinecone setup instructions, visit: https://docs.pinecone.io/docs/quickstart
