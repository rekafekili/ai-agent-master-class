import json
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from google.genai import types


# ── StoryWriter callbacks ──

async def before_story_writer(callback_context: CallbackContext):
    print("📖 스토리 작성 중...")
    return None


async def after_story_writer_model(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Parse story JSON, store in state, return clean summary instead of raw JSON."""
    try:
        text = llm_response.content.parts[0].text
        data = json.loads(text)
        callback_context.state["story_writer_output"] = data

        title = data.get("title", "")
        style = data.get("style", "")
        pages = data.get("pages", [])
        page_previews = "\n".join(
            f"  {p.get('page_number', '?')}. {p.get('text', '')[:40]}..."
            for p in pages
        )

        summary = (
            f"📖 스토리 작성 완료!\n\n"
            f"📕 제목: {title}\n"
            f"🎨 화풍: {style}\n"
            f"📄 페이지 수: {len(pages)}\n\n"
            f"{page_previews}"
        )

        return LlmResponse(
            content=types.Content(
                parts=[types.Part(text=summary)],
                role="model",
            )
        )
    except Exception:
        return llm_response


# ── Illustration callbacks ──

async def before_illustration(callback_context: CallbackContext):
    print("🎨 삽화 생성 시작!")
    return None


async def after_illustration(callback_context: CallbackContext):
    return types.Content(
        parts=[types.Part(text="✅ 모든 삽화 생성 완료!")],
        role="model",
    )


def make_before_page_callback(n: int):
    async def _cb(callback_context: CallbackContext):
        print(f"🖼️ 이미지 {n}/5 생성 중...")
        return None
    return _cb


def make_after_page_callback(n: int):
    async def _cb(callback_context: CallbackContext):
        return types.Content(
            parts=[types.Part(text=f"🖼️ 이미지 {n}/5 완료!")],
            role="model",
        )
    return _cb


# ── Assembler callbacks ──

async def before_assembler(callback_context: CallbackContext):
    print("📚 동화책 조립 중...")
    return None


async def after_assembler(callback_context: CallbackContext):
    return types.Content(
        parts=[types.Part(text="✅ 동화책이 완성되었습니다! storybook_final.html 아티팩트를 확인하세요.")],
        role="model",
    )
