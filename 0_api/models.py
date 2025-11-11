from pydantic       import BaseModel
from typing         import List, Dict, Optional

class ScriptItem(BaseModel):
    id: str
    title: str
    image: str
    cmd: List[str]
    env: Dict[str, str] = {}
    cpu_limit: Optional[str] = None
    mem_limit: Optional[str] = None

class StartRequest(BaseModel):
    script_id: str

class StartResponse(BaseModel):
    container_id: str
    run_id: str

class StopResponse(BaseModel):
    ok: bool
