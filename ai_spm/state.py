from typing import Optional, Literal, Dict
from pydantic import BaseModel

class UniverseState(BaseModel):
    work_item: str
    artifact: Optional[str] = None
    evidence: Optional[Dict] = None
    decision: Optional[Literal["approve", "reject"]] = None
    version_pin: Optional[str] = None
