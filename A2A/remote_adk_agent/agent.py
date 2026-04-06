from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.a2a.utils.agent_to_a2a import to_a2a

agent = Agent(
    name="HistoryHelperAgent",
    description="An agent that can help students with their history homework.",
    model=LiteLlm("openai/gpt-4o"),
    sub_agents=[],
)

app = to_a2a(agent, port=8001)
# user-facing-agent와 다른 포트로 설정
# http://127.0.0.1:8001/.well-known/agent-card.json로 접속
