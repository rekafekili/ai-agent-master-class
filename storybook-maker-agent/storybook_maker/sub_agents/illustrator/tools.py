from google.adk.tools.tool_context import ToolContext
from openai import OpenAI
from google.genai import types
import base64

client = OpenAI()


async def generate_image(tool_context: ToolContext, page_number: int):
    """Generate an illustration for a specific page of the storybook.

    Args:
        tool_context: The tool context for accessing state and artifacts.
        page_number: The page number (1-5) to generate an illustration for.
    """
    story_data = tool_context.state.get("story_writer_output")
    if not story_data:
        return {"status": "error", "message": "No story data found in state"}

    pages = story_data.get("pages", [])
    style = story_data.get("style", "children's book illustration")
    title = story_data.get("title", "")

    target_page = None
    for page in pages:
        if page.get("page_number") == page_number:
            target_page = page
            break

    if not target_page:
        return {"status": "error", "message": f"Page {page_number} not found"}

    filename = f"page_{page_number}_illustration.png"

    existing_artifacts = await tool_context.list_artifacts()
    if filename in existing_artifacts:
        return {
            "status": "already_exists",
            "page_number": page_number,
            "filename": filename,
        }

    illustration_desc = target_page.get("illustration_description", "")
    prompt = (
        f"Art style: {style}. "
        f"Children's storybook illustration for '{title}'. "
        f"Scene: {illustration_desc}. "
        f"No text or words in the image."
    )

    image = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size="1024x1024",
        quality="low",
        moderation="low",
        output_format="png",
        background="opaque",
    )

    image_bytes = base64.b64decode(image.data[0].b64_json)
    artifact = types.Part(
        inline_data=types.Blob(
            mime_type="image/png",
            data=image_bytes,
        )
    )

    await tool_context.save_artifact(
        filename=filename,
        artifact=artifact,
    )

    return {
        "status": "success",
        "page_number": page_number,
        "filename": filename,
        "prompt": prompt[:200],
    }
