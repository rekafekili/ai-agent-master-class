from google.adk.agents import ParallelAgent
from .prompt import ASSET_GENERATOR_DESCRIPTION


asset_generator_agent = ParallelAgent(
    name="AssetGeneratorAgent",
    description=ASSET_GENERATOR_DESCRIPTION,
    sub_agents=[],
)
