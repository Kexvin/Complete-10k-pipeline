# C3AN_Autonomy

C3AN Autonomy layer is split into three main sections - Code, Data and Knowledge. The applications that are built by using these sections are then organized in Workflow folder. The structure of this repo is as follows -

## 📂 Repository Structure

### Root
- **`README.md`** – Overview and usage guide (this file).  
- **`LICENSE`** – Licensing information.  

---

### 🔹 Code
Core logic for agents and shared assets.

- **`Agents/`**  
  Contains autonomous AI agent implementations.  
  - `blog-writer/` – One of the example agents
  - `llm-auditor/` – Another example agent
  - Each agent includes its own `README.md` and configuration (`pyproject.toml`).

- **`Assets/`**  
  Shared resources and tools available to agents. These are the building blocks of an agent  
  - `Resources/` – Models, prompts, and other AI building blocks. These are the atomic building blocks of the platform. Below are two example setups - 
    - `LLMs/` – Configurations and model packages.  
    - `Prompts/` – Predefined prompt templates (JSON).
    - `Protocols/` - These are where the protocols for the agents are defined for specific workflows. can be reused by either tools or specific agents that need them.
  - `Tools/` – Utility libraries that are created by using some resources that works towards solving a specific function and can be reused by multiple agents. Below are two example tools - 
    - `auditing/` – Modules for safety, quality, and relevance evaluation.  
    - `io/` – Utilities for formatting, file system handling, logging, and validation.  

---

### 🔹 Data
Input/output and logs for experiments.

- **`EDS/`** – Emergency Data Sources - These are the emergency files that can be used as a backup for storing the core information needed to restart the system. 
- **`Logs/`** – Execution and audit logs of singular agents as well as the whole workflow.  
- **`Primary/`** – Core datasets (e.g., `requests.jsonl`) uploaded by the user for their workflow specific execution pipelines.  
- **`Secondary/`** – Enriched/derived or external data (e.g., `external_refs.json`) that is added as a supportive feature and doesn't play direct role in the process of the workflows.  
- **`Tertiary/`** – Auxiliary/archival datasets and intermediary generated outputs from agents in the pipeline.  

Each folder contains its own `README.md` describing usage and conventions.

---

### 🔹 Knowledge
Ontology and schema definitions.

- **`KG/`** – Knowledge graph representations.  
- **`Schema/`** – Data schemas, constraints, and interoperability definitions.  

---

### 🔹 Workflow
Pipelines, orchestration scripts, or execution plans that tie **Agents**, **Assets**, **Data**, and **Knowledge** together into autonomous workflows.  

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<your-org>/C3AN_Autonomy.git
cd C3AN_Autonomy
````

### 2. Install dependencies

Each agent and tool has its own `pyproject.toml`. You can install them individually:

#### Install the Blog Writer Agent

```bash
cd Code/Agents/blog-writer
pip install -e .
```

#### Install the LLM Auditor Agent

```bash
cd Code/Agents/llm-auditor
pip install -e .
```

#### Install LLM Resources

```bash
cd Code/Assets/Resources/LLMs
pip install -e .
```

#### Install Shared Tools (Auditing, IO, etc.)

```bash
cd Code/Assets/Tools
pip install -e .
```

### 3. Run an agent

```bash
cd Code/Agents/llm-auditor
python llm-auditor.py
```

---

## 🧩 Key Concepts

* **Agents** – Independent AI-driven actors (writers, auditors, etc.).
* **Assets** – Shared tools, prompts, and models to support agents.
* **Data Layers** – Organized datasets for training, logging, and evaluation.
* **Knowledge Graph** – Schema-driven representation of structured knowledge.
* **Workflows** – Configurable pipelines that compose agents and assets for tasks.

---

## 🛠 Development Notes

* Follow modular principles: keep agents self-contained, but leverage shared assets.
* Use `Data/Logs/` for structured logging to support auditing.
* Extend `Knowledge/Schema/` when introducing new data types.
* Contributions should include tests, documentation, and schema updates.

---

## 📜 License

Distributed under the terms specified in `LICENSE`.
