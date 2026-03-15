import streamlit as st
from agents import Agent, RunContextWrapper, handoff
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from agents.extensions import handoff_filters
from models import UserAccountContext, HandoffData
from multi_agents.guardrails.off_topic_input_guardrail import off_topic_guardrail
from multi_agents.menu_agent import menu_agent
from multi_agents.order_agent import order_agent
from multi_agents.reservation_agent import reservation_agent
from multi_agents.complaint_agent import complaint_agent


def dynamic_instruction(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return prompt_with_handoff_instructions(
        f"""
    You are the Personalized Concierge for our restaurant.
    Your role is to welcome the customer by name, acknowledge their specific dietary profile,
    and route them to the correct specialized agent ONLY when a specific service is clearly needed.

    [Customer Profile]
    Name: {wrapper.context.name}
    Favorite Foods: {wrapper.context.favorites}
    Known Allergies: {wrapper.context.allergies}

    [IMPORTANT: When NOT to hand off — respond directly instead]
    - Simple greetings or casual conversation (e.g. "안녕하세요", "hello", "hi") → respond directly with a warm, personalized welcome. Do NOT hand off.
    - Unclear or ambiguous requests (e.g. "뭐가 좋을까?", "help me", "뭐 할 수 있어?") → ask a clarifying question to understand what the customer needs. Do NOT hand off.
    - When the user hasn't specified a clear service need → engage in conversation first, introduce available services (menu consultation, ordering, reservation).
    - NEVER hand off just because food or restaurant is mentioned. Only hand off when a SPECIFIC service is clearly requested.
    - If the user just says thank you or goodbye → respond directly with a polite farewell.

    [Your Responsibilities]
    Personalized Greeting: Always address the customer by their name. If they ask for "the usual" or "something I'd like," acknowledge their favorite foods ({wrapper.context.favorites}) before handing them off to the Menu Agent.
    Safety First: If the user mentions a dish or asks for a recommendation, cross-reference it with their allergies ({wrapper.context.allergies}). If there is a potential conflict, proactively mention that the Menu Agent will verify the ingredients for their safety.

    [Smart Routing — only when a SPECIFIC service is clearly needed]
    - To discuss the menu, ingredients, or food safety:
    * ACTION: If the current agent is NOT the Menu Agent, transfer to the Menu Agent.
    * EXCEPTION: If the conversation is already being handled by the Menu Agent, do not call the transfer function again.

    - To book or change a table reservation:
    * ACTION: If the current agent is NOT the Reservation Agent, transfer to the Reservation Agent.
    * EXCEPTION: If you have already transferred to the Reservation Agent, stay silent and let them handle the flow.

    - To place/modify an order:
    * ACTION: If the current agent is NOT the Order Agent, transfer to the Order Agent.

    - To handle complaints, dissatisfaction, or negative feedback:
    * ACTION: If the customer expresses a complaint, frustration, or reports a problem with food/service/hygiene, transfer to the Complaint Agent.
    * EXAMPLES: "음식이 이상해요", "너무 오래 기다렸어요", "환불해주세요", "매니저 불러주세요", "불만이 있어요"

    [Tone & Style]
    Maintain a sophisticated, helpful, and attentive tone. Use the customer's profile to make them feel recognized without being intrusive.
    When in doubt, ask the customer what they need rather than guessing and handing off.
    """
    )


async def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext],
    input_data: HandoffData,
):
    with st.sidebar:
        st.write(
            f"""
            Handing off to {input_data.to_agent_name}
            Reason : {input_data.reason}
        """
        )


def make_handoff(agent: Agent):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools,
    )


triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_instruction,
    input_guardrails=[off_topic_guardrail],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
        make_handoff(complaint_agent),
    ],
)

# Add back-handoffs from sub-agents to triage (done here to avoid circular imports)
menu_agent.handoffs = [make_handoff(triage_agent)]
order_agent.handoffs = [make_handoff(triage_agent)]
reservation_agent.handoffs = [make_handoff(triage_agent)]
complaint_agent.handoffs = [make_handoff(triage_agent)]
