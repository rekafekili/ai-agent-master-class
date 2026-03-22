from google.adk.agents import SequentialAgent
from .sub_agents.story_writer.agent import story_writer_agent
from .sub_agents.illustrator.agent import illustration_agent
from .sub_agents.assembler.agent import assembler_agent
from .callbacks import (
    before_story_writer,
    after_story_writer_model,
    before_assembler,
    after_assembler,
)

story_writer_agent.before_agent_callback = before_story_writer
story_writer_agent.after_model_callback = after_story_writer_model
assembler_agent.before_agent_callback = before_assembler
assembler_agent.after_agent_callback = after_assembler

root_agent = SequentialAgent(
    name="StorybookMakerAgent",
    description="Creates a complete 5-page illustrated children's storybook from a theme",
    sub_agents=[story_writer_agent, illustration_agent, assembler_agent],
)
