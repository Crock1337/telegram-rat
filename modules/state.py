from dataclasses import dataclass, field
from typing import List, Any

@dataclass
class State:
    keylog_buffer: List[str] = field(default_factory=list)
    keylog_active: bool = False
    clip_active: bool = False
    listener: Any = None
    last_clip: str = ""

state = State()
