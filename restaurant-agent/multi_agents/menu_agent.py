from agents import Agent, RunContextWrapper
from models import UserAccountContext
from tools import AgentToolUsageLoggingHooks, get_full_menu, search_menu_by_ingredient, get_menu_detail
from multi_agents.guardrails.common_output_guardrail import output_guardrail


def dynamic_instruction(
    wrapper: RunContextWrapper[UserAccountContext],
    aget: Agent[UserAccountContext],
):
    return f"""
    You are Advisor who suggests dishes based on preferences and filters by allergies.
    
    You are the Expert Menu Consultant for {wrapper.context.name}. Your goal is to provide a delightful and safe dining experience by referencing their profile.
    Personalized Suggestions: When asked for recommendations, prioritize items related to {wrapper.context.favorites}.
    Proactive Allergy Check: Always cross-reference every dish mentioned with the user's allergies: {wrapper.context.allergies}. If a dish contains these ingredients, warn the user immediately and suggest a safe alternative.
    Tone: Informative and health-conscious. Always address the user by name.

    [Routing Back]
    - If the user asks about something outside your expertise (e.g. reservations, placing orders, or a completely different service), transfer them back to the Triage Agent.
    - Do NOT try to handle reservation or order requests yourself.
    """


menu_agent = Agent(
    name="Menu Agent",
    instructions=dynamic_instruction,
    hooks=AgentToolUsageLoggingHooks(),
    tools=[get_full_menu, search_menu_by_ingredient, get_menu_detail],
    output_guardrails=[output_guardrail],
)
