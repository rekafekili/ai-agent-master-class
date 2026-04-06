from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.a2a.utils.agent_to_a2a import to_a2a


def dummy_tool(hello: str):
    """Dummy Tool. Helps the agent"""  # Agent Card에서 description으로 업데이트 됨.
    return "world"


agent = Agent(
    name="HistoryHelperAgent",
    description="An agent that can help students with their history homework.",
    model=LiteLlm("openai/gpt-4o"),
    tools=[dummy_tool],
    sub_agents=[],
)

app = to_a2a(agent, port=8001)
# user-facing-agent와 다른 포트로 설정
# `uvicorn agent:app --port 8001 --reload`
# http://127.0.0.1:8001/.well-known/agent-card.json로 접속
# 참고 : https://a2a-protocol.org/latest/topics/what-is-a2a/#a2a-request-lifecycle
