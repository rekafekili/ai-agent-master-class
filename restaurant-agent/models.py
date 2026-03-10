from pydantic import BaseModel


class UserAccountContext(BaseModel):
    name: str
    favorites: list[str]
    allergies: list[str]


class InputGuardrailOutput(BaseModel):
    is_off_topic: bool
    reason: str


class HandoffData(BaseModel):
    to_agent_name: str
    issue_type: str
    issue_description: str
    reason: str
