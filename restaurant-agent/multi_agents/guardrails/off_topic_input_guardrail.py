from agents import (
    Agent,
    RunContextWrapper,
    GuardrailFunctionOutput,
    Runner,
    input_guardrail,
)
from models import InputGuardrailOutput, UserAccountContext

input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    You are the Domain Filter. Your goal is to ensure the conversation stays within the restaurant's business scope.
    Identify Relevant Topics: Only allow inputs related to menu information, food ingredients, allergies, table reservations, and food ordering.
    Block Irrelevant Topics: If the user asks about politics, religion, coding, sports, or other general knowledge, politely steer them back: "I specialize in our restaurant's services. How can I help you with your meal or reservation today?"
    Handle Ambiguity: If the input is too vague or consists of random characters, ask for clarification instead of guessing the intent.
    """,
    output_type=InputGuardrailOutput,
)


@input_guardrail
async def off_topic_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    input: str,
):
    result = await Runner.run(input_guardrail_agent, input, context=wrapper.context)
    output: InputGuardrailOutput = result.final_output
    return GuardrailFunctionOutput(
        output_info=output,
        tripwire_triggered=output.is_off_topic,
    )
