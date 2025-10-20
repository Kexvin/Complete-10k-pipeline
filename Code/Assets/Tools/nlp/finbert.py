from __future__ import annotations

class FinBert:
    """
    Minimal FinBERT wrapper.
    - By default returns "neutral" to keep tests deterministic.
    - Later you can enable heavy mode with transformers/torch.
    """

    def __init__(self, heavy: bool = False, model_name: str = "ProsusAI/finbert"):
        self.heavy = heavy
        self.model_name = model_name
        self._pipe = None
        if heavy:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
                tok = AutoTokenizer.from_pretrained(model_name)
                mdl = AutoModelForSequenceClassification.from_pretrained(model_name)
                self._pipe = pipeline("sentiment-analysis", model=mdl, tokenizer=tok, truncation=True)
            except Exception:
                # fallback to neutral
                self.heavy = False
                self._pipe = None

    def predict_tone(self, text: str) -> str:
        if not self.heavy or self._pipe is None:
            return "neutral"
        out = self._pipe(text[:4096])[0]["label"].lower()
        # Map to three-way tone
        if "positive" in out:
            return "positive"
        if "negative" in out:
            return "negative"
        return "neutral"
