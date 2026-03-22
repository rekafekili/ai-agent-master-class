from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from .prompt import STORY_WRITER_PROMPT

story_writer_agent = LlmAgent(
    name="StoryWriterAgent",
    description="Writes a 5-page Korean children's storybook with English illustration descriptions",
    instruction=STORY_WRITER_PROMPT,
    model=LiteLlm(model="openai/gpt-4o"),
)
