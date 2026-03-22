from google.adk.tools.tool_context import ToolContext
from openai import OpenAI
from google import genai
import base64, io
from google.genai import types

client = OpenAI()
# client = genai.Client()


async def generate_images(tool_context: ToolContext):
    prompt_builder_output = tool_context.state.get("prompt_builder_output")
    optimized_prompts = prompt_builder_output.get("optimized_prompts")

    existing_artifacts = await tool_context.list_artifacts()

    generated_images = []

    for prompt in optimized_prompts:
        scene_id = prompt.get("scene_id")
        enhanced_prompt = prompt.get("enhanced_prompt")
        filename = f"scene_{scene_id}_image.jpeg"

        if filename in existing_artifacts:
            generated_images.append(
                {
                    "scene_id": scene_id,
                    "prompt": enhanced_prompt[:100],
                    "filename": filename,
                }
            )
            continue

        image = client.images.generate(
            model="gpt-image-1",
            prompt=enhanced_prompt,
            n=1,
            moderation="low",
            output_format="jpeg",
            background="opaque",
            size="1024x1536",
            quality="low",
        )

        image_bytes = base64.b64decode(image.data[0].b64_json)
        artifact = types.Part(
            inline_data=types.Blob(
                mime_type="image/jpeg",
                data=image_bytes,
            )
        )

        await tool_context.save_artifact(
            filename=filename,
            artifact=artifact,
        )

        # result = client.models.generate_images(
        #     model="gemini-2.5-flash-image",
        #     prompt=enhanced_prompt,
        #     config=types.GenerateImagesConfig(
        #         number_of_images=1,
        #         output_mime_type="image/jpeg",
        #         aspect_ratio="9:16",
        #     ),
        # )

        # if result.generated_images:
        #     # SDK가 반환한 PIL Image 객체
        #     image = result.generated_images[0]

        #     # PIL Image -> raw bytes
        #     buffered = io.BytesIO()
        #     image.image.save(buffered, format="JPEG")
        #     image_bytes = buffered.getvalue()

        #     # types.Part
        #     artifact = types.Part.from_bytes(
        #         data=image_bytes,
        #         mime_type="image/jpeg",
        #     )

        #     # save
        #     await tool_context.save_artifact(
        #         filename=filename,
        #         artifact=artifact,
        #     )

        generated_images.append(
            {
                "scene_id": scene_id,
                "prompt": enhanced_prompt[:100],
                "filename": filename,
            }
        )

    return {
        "total_images": len(generated_images),
        "generated_images": generated_images,
        "status": "complete",
    }
