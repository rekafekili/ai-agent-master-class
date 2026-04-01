from typing import Annotated
from operator import add

from typing_extensions import TypedDict


class PaperState(TypedDict):
    file_path: str
    paper_id: str
    paper_title: str
    sections: list[dict]
    vocabulary: Annotated[list[dict], add]
