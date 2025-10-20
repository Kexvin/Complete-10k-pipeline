from typing import List
from .artifact import Artifact
from .stage import Stage
class Pipeline:
    def __init__(self, stages: List[Stage]):
        self.stages = stages
    def run(self, art: Artifact, **kwargs) -> Artifact:
        cur = art
        for st in self.stages:
            if not isinstance(cur, st.input_type):
                raise TypeError(f"{st.name} expected {st.input_type.__name__}, got {type(cur).__name__}")
            cur = st.run(cur, **kwargs)  # type: ignore[assignment]
        return cur