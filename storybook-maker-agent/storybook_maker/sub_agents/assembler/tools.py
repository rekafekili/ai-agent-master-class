import base64
from google.adk.tools.tool_context import ToolContext
from google.genai import types


def _build_html(title: str, pages: list, image_data_uris: dict) -> str:
    pages_html = ""
    for page in pages:
        pn = page.get("page_number", 0)
        text = page.get("text", "")
        img_uri = image_data_uris.get(pn, "")

        pages_html += f"""
        <div class="page">
            <div class="page-number">— {pn} —</div>
            <img src="{img_uri}" alt="Page {pn} illustration" />
            <p class="story-text">{text}</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Noto Sans KR', sans-serif;
    background: #fdf6e3;
    color: #3e2723;
  }}
  .cover {{
    text-align: center;
    padding: 60px 20px;
    background: linear-gradient(135deg, #ffe0b2, #fff9c4);
    min-height: 50vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }}
  .cover h1 {{
    font-size: 2.5rem;
    margin-bottom: 10px;
    color: #4e342e;
  }}
  .cover .subtitle {{
    font-size: 1.1rem;
    color: #6d4c41;
  }}
  .page {{
    max-width: 700px;
    margin: 40px auto;
    padding: 30px;
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    text-align: center;
  }}
  .page img {{
    width: 100%;
    max-width: 520px;
    border-radius: 12px;
    margin: 16px 0;
  }}
  .page-number {{
    font-size: 0.9rem;
    color: #a1887f;
    margin-bottom: 8px;
  }}
  .story-text {{
    font-size: 1.25rem;
    line-height: 2;
    margin-top: 16px;
    white-space: pre-line;
  }}
  .ending {{
    text-align: center;
    padding: 60px 20px;
    font-size: 1.5rem;
    color: #6d4c41;
  }}
</style>
</head>
<body>
  <div class="cover">
    <h1>{title}</h1>
    <p class="subtitle">AI 동화책</p>
  </div>
  {pages_html}
  <div class="ending">— 끝 —</div>
</body>
</html>"""


async def assemble_storybook(tool_context: ToolContext) -> str:
    """Assemble the final storybook by combining story text and illustrations into an HTML file.

    Args:
        tool_context: Tool context to access state and artifacts.

    Returns:
        Information about the assembly result.
    """
    story_data = tool_context.state.get("story_writer_output")
    if not story_data:
        return str({"status": "error", "message": "No story data found"})

    title = story_data.get("title", "동화책")
    pages = story_data.get("pages", [])
    pages.sort(key=lambda p: p.get("page_number", 0))

    existing_artifacts = await tool_context.list_artifacts()

    print(f"📚 ASSEMBLER: Combining {len(pages)} pages into storybook")

    image_data_uris = {}
    for page in pages:
        pn = page.get("page_number", 0)
        filename = f"page_{pn}_illustration.png"

        if filename not in existing_artifacts:
            print(f"⚠️ Missing illustration: {filename}")
            continue

        artifact = await tool_context.load_artifact(filename=filename)
        if artifact and artifact.inline_data:
            b64 = base64.b64encode(artifact.inline_data.data).decode("utf-8")
            mime = artifact.inline_data.mime_type or "image/png"
            image_data_uris[pn] = f"data:{mime};base64,{b64}"
            print(f"✅ Loaded illustration for page {pn}")

    html_content = _build_html(title, pages, image_data_uris)

    html_artifact = types.Part(
        inline_data=types.Blob(
            mime_type="text/html",
            data=html_content.encode("utf-8"),
        )
    )

    await tool_context.save_artifact(
        filename="storybook_final.html",
        artifact=html_artifact,
    )

    print(f"✅ Storybook assembled: storybook_final.html")

    return str({
        "status": "success",
        "title": title,
        "pages_assembled": len(pages),
        "illustrations_embedded": len(image_data_uris),
        "output_file": "storybook_final.html",
    })
