from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from graph import graph

app = FastAPI()


def run_graph(message: str):
    result = graph.invoke(
        {
            "messages": [
                {"role": "user", "content": message},
            ],
        },
    )

    return result["messages"][-1].content


# uvicorn server:app --port 8002 --reload
@app.get("/.well-known/agent-card.json")
def get_agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "An agent that can help students with their philosophy homework.",
        "name": "PhilosophyHelperAgent",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {
                "description": "An agent that can help students with their philosophy homework.",
                "id": "PhilosophyHelperAgent",
                "name": "model",
                "tags": ["llm"],
            },
        ],
        "supportsAuthenticatedExtendedCard": False,
        "url": "http://localhost:8002/messages",
        "version": "0.0.1",
    }


@app.post("/messages")
async def handle_message(req: Request):
    body = await req.json()
    messages = body.get("params").get("message").get("parts")
    messages.reverse()
    message_text = ""
    for message in messages:
        text = message.get("text")
        message_text += f"{text}\n"

    response = run_graph(message_text)

    # https://a2a-protocol.org/latest/sdk/python/api/a2a.types.html#a2a.types.SendMessageSuccessResponse
    return {
        "id": "message_1",
        "jsonrpc": "2.0",
        "result": {
            "kind": "message",
            "message_id": "092834091273904701234",
            "role": "agent",
            "parts": [{"kind": "text", "text": response}],
        },
    }
