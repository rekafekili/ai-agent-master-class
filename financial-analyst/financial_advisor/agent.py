from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

MODEL = LiteLlm("openai/gpt-4o")


def get_weather(city: str):
    return f"The weather in {city} in 30 degrees."


def convert_units(degrees: int):
    return f"That is 40 farenheit."


geo_agent = Agent(
    name="GeoAgent",
    instruction="You help with geo questions",
    model=MODEL,
    description="Transfer to this agent when you have a geo related question.",
)

weather_agent = Agent(
    name="WeatherAgent",
    instruction="You help the user with weather related questions.",
    model=MODEL,
    tools=[get_weather, convert_units],
    sub_agents=[geo_agent],
)

# `root_agent` is Required!!
root_agent = weather_agent

# uv run adk web -> Web에서 에이전트 테스트 가능
# uv run adk api_server -> /docs를 통해 스웨거 조회 가능
