from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.models.lite_llm import LiteLlm
from .prompt import get_page_illustrator_prompt
from .tools import generate_image
from ...callbacks import (
    before_illustration,
    after_illustration,
    make_before_page_callback,
    make_after_page_callback,
)

MODEL = LiteLlm(model="openai/gpt-4o")


def create_page_illustrator(page_number: int) -> LlmAgent:
    return LlmAgent(
        name=f"PageIllustrator_{page_number}",
        description=f"Generates illustration for page {page_number}",
        instruction=get_page_illustrator_prompt(page_number),
        model=MODEL,
        tools=[generate_image],
        before_agent_callback=make_before_page_callback(page_number),
        after_agent_callback=make_after_page_callback(page_number),
    )


illustration_agent = ParallelAgent(
    name="IllustrationAgent",
    description="Generates all 5 page illustrations in parallel",
    sub_agents=[create_page_illustrator(i) for i in range(1, 6)],
    before_agent_callback=before_illustration,
    after_agent_callback=after_illustration,
)
