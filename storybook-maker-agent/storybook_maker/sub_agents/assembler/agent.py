from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from .prompt import ASSEMBLER_PROMPT
from .tools import assemble_storybook

assembler_agent = LlmAgent(
    name="StorybookAssemblerAgent",
    description="Assembles story text and illustrations into a final HTML storybook",
    instruction=ASSEMBLER_PROMPT,
    model=LiteLlm(model="openai/gpt-4o"),
    tools=[assemble_storybook],
    output_key="assembler_output",
)
