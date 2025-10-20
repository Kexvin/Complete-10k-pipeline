tenk_analyst

This package expects a Python environment with the project's dependencies installed.

If your editor (e.g. VS Code) shows "Import could not be resolved" for packages like `pydantic`, it's usually because the editor is using a different Python interpreter than the one where the packages are installed. To fix it:

- Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r ../../../requirements.txt
```

- In VS Code, open the Command Palette (Ctrl+Shift+P) -> Python: Select Interpreter -> choose the `.venv` interpreter you created.

After selecting the correct interpreter, the language server should resolve imports like `pydantic` and `transformers`.
