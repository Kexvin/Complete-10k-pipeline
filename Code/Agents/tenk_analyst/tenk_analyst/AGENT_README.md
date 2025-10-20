tenk_analyst — Agent README

This document explains the `tenk_analyst` agent package: its stages, agents, models, and how the pipeline runs end-to-end. It's intended for developers who will run or extend the agent.

Project structure (key files)
- `run.py` — development runner that composes pipelines (base/qual/quant) and executes them end-to-end.
- `agents/` — agent implementations (ControllerAgent, QualitativeAgent, QuantitativeAgent).
- `models/` — pydantic/dataclass models describing artifacts and results (Chunk, RoutedChunk, QualResult, QuantResult, SummaryReport, ...).
- `stages/` — pipeline stages (FetchStage, ChunkStage, RouteStage, QualStage, QuantStage, SummarizeStage). Each stage transforms artifacts and delegates work to agents.
- `tests/` — unit tests for stages and controller.

How the workflow runs
1. Seed artifact: `RawTextArtifact` (company metadata, empty text). This is seeded in `run.py`.
2. Base pipeline (`FetchStage -> ChunkStage -> RouteStage`) fetches raw filings, produces `ChunksArtifact` and then `RoutedChunksArtifact`.
3. Qual pipeline (`QualStage`) runs the `QualitativeAgent` on routed chunks marked for qualitative analysis; outputs `QualResultsArtifact`.
4. Quant pipeline (`QuantStage`) runs the `QuantitativeAgent` on routed chunks marked for quantitative analysis; outputs `QuantResultsArtifact`.
5. SummarizeStage combines `QualResultsArtifact` + `QuantResultsArtifact` into `SummaryArtifact`.

Stage/Agent contract (short)
- Stages accept an input artifact class and return an output artifact class. See `Code.Assets.Tools.core.stage.Stage` for the generic base.
- Agents expose a `.run(chunks)` method (or similar) returning a list of result models. `QualitativeAgent.run` and `QuantitativeAgent.run` follow this pattern.
- Artifacts and models are under `Knowledge/Schema/Artifacts` and `Code/Agents/tenk_analyst/tenk_analyst/models`.

How to run locally
1. Create and activate a venv (PowerShell):

```powershell
cd C:\Users\kdox1\10-K_Form_Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

2. (Optional) Install heavy optional deps if you need RAG/embedding features:

```powershell
# CPU-only PyTorch (for embeddings)
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
# Pinecone for vector storage
python -m pip install pinecone-client
$env:PINECONE_API_KEY="your-api-key-here"  # Set your Pinecone API key
```

3. Run the dev runner:

```powershell
python -m Code.Agents.tenk_analyst.run
```

4. Run tests:

```powershell
python -m pytest -q Code/Agents/tenk_analyst/tenk_analyst/tests
```

Developer notes and extension points
- To add a new stage: add a Stage subclass in `stages/` and wire it into the runner or pipeline composition. Stages should declare input/output artifact types and be unit-tested.
- To add new artifact schemas: add a dataclass or pydantic model under `Knowledge/Schema/Artifacts` and import it from stages/models.
- Keep heavy external features optional (embedding clients, LLM connectors). Use dependency injection so tests can pass with minimal installs.

Troubleshooting
- If your editor shows "Import could not be resolved": ensure the VS Code interpreter is set to the project's `.venv` (Command Palette -> Python: Select Interpreter). Also `python.analysis.extraPaths` in `.vscode/settings.json` includes `Code` and `Knowledge` to help the language server.
- If pip fails to build `numpy`/`torch` on Windows, either install pre-built wheels (PyTorch CPU wheels) or install Visual Studio Build Tools. See `DEPENDENCIES.md` for details.

Contact
- For questions about the agent design, see `Workflow/10K_Analysis/README.md` for the higher-level pipeline and adapt the patterns here.
