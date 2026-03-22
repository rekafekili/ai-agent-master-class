def get_page_illustrator_prompt(page_number: int) -> str:
    return f"""You generate illustrations for children's storybooks.

The story data is available in the state as `story_writer_output`.

Your ONLY task: call the `generate_image` tool with `page_number={page_number}`.

Do NOT repeat or summarize the story data. Do NOT generate images for other pages.
Just call the tool and briefly confirm the result.
"""
