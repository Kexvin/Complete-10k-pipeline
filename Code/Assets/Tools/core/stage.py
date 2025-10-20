
from typing import Generic, TypeVar, Type
from .artifact import Artifact
I = TypeVar("I", bound=Artifact)
O = TypeVar("O", bound=Artifact)
class Stage(Generic[I, O]):
    name: str
    input_type: Type[I]
    output_type: Type[O]
    def __init__(self, name: str, input_type: Type[I], output_type: Type[O]):
        self.name = name; self.input_type = input_type; self.output_type = output_type
    def run(self, inp: I, **kwargs) -> O:
        raise NotImplementedError