# Code/Agents/tenk_analyst/tenk_analyst/agent_registry.py

from __future__ import annotations
from typing import Any, Dict, Optional
import importlib
import json
import os

# tool deps
from Code.Assets.Tools.nlp.finbert import FinBert
from Code.Assets.Tools.rag.pinecone_client import RAG
from Code.Assets.Tools.llm.openai_client import LLMClient

# agent classes
from Code.Agents.tenk_analyst.tenk_analyst.agents.qualitative import QualitativeAgent
from Code.Agents.tenk_analyst.tenk_analyst.agents.quantitative import QuantitativeAgent
from Code.Agents.tenk_analyst.tenk_analyst.agents.summarizer import SummarizerAgent


class AgentRegistry:
    """
      - load an agents.json file (optional)
      - build known agents with runtime parameters (csv path, pinecone collection, model)
      - return concrete instances to the stages
    """

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

    def get(
        self,
        name: str,
        *,
        kaggle_csv_path: Optional[str] = None,
        pinecone_collection: str = "knowledgepinecone",
        openai_model: str = "gpt-3.5-turbo",
    ) -> Any:
        """
        Return a concrete agent instance by name.
        Known agents:
          - 'qual'
          - 'quant'
          - 'summarizer'
        """
        if name in self._config:
            # not doing generic dynamic build right now since we know 3 agents exactly
            pass

        if name == "qual":
            # build FinBert + RAG, then agent
            finbert = FinBert(heavy=True)
            rag = RAG(collection=pinecone_collection)
            return QualitativeAgent(finbert, rag)

        if name == "quant":
            # if caller passes csv path, use it; else fall back to your default
            csv_path = kaggle_csv_path or "Data/Primary/kaggle_facts/companyfacts.csv"
            # note: QuantitativeAgent itself creates KaggleFinancialData
            return QuantitativeAgent(kaggle_csv_path=csv_path)

        if name == "summarizer":
            llm = LLMClient(model=openai_model)
            rag = RAG(collection=pinecone_collection)
            return SummarizerAgent(rag=rag, llm=llm, pinecone_collection=pinecone_collection)

        raise KeyError(f"Unknown agent name: {name}")


agent_registry = AgentRegistry()
