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


class OutputGuardrailOutput(BaseModel):
    is_off_topic: bool
    is_off_expert: bool
    is_contain_account_data: bool
    reason: str
