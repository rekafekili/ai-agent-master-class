from pydantic import BaseModel


class UserAccountContext(BaseModel):
    customer_id: int
    name: str
    email: str
    tier: str = "basic"  # premium, enterprise ...


class InputGuardrailOutput(BaseModel):
    is_off_topic: bool
    reason: str


class TechnicalOutputGuardrailOutput(BaseModel):
    contains_off_topic: bool
    contains_billing_data: bool
    contains_account_data: bool
    reason: str


class HandoffData(BaseModel):
    to_agent_name: str
    issue_type: str
    issue_description: str
    reason: str
