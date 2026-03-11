from agents import (
    Agent,
    RunContextWrapper,
    GuardrailFunctionOutput,
    Runner,
    output_guardrail,
)
from models import OutputGuardrailOutput, UserAccountContext

output_guardrail_agent = Agent(
    name="Output Guardrail Agent",
    instructions="""
    You are the Domain Filter. Your goal is to ensure the conversation stays within the restaurant's business scope.
    Identify Relevant Topics: Only allow inputs related to menu information, food ingredients, allergies, table reservations, and food ordering.
    Block Irrelevant Topics: If the user asks about politics, religion, coding, sports, or other general knowledge, politely steer them back: "I specialize in our restaurant's services. How can I help you with your meal or reservation today?"
    Handle Ambiguity: If the input is too vague or consists of random characters, ask for clarification instead of guessing the intent.
    """,
    output_type=OutputGuardrailOutput,
)


@output_guardrail
async def output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    output: str,
):
    result = await Runner.run(output_guardrail_agent, output, context=wrapper.context)

    validation: OutputGuardrailOutput = result.final_output

    triggered = (
        validation.is_off_topic
        or validation.is_off_expert
        or validation.is_contain_account_data
    )

    return GuardrailFunctionOutput(output_info=validation, tripwire_triggered=triggered)
