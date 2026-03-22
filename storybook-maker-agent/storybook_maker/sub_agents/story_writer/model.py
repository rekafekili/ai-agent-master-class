from pydantic import BaseModel, Field
from typing import List


class StoryPage(BaseModel):
    page_number: int = Field(description="Page number (1-5)")
    text: str = Field(description="Story text for this page in Korean")
    illustration_description: str = Field(
        description="Detailed illustration description in English for image generation"
    )


class StoryOutput(BaseModel):
    title: str = Field(description="Story title in Korean")
    theme: str = Field(description="The original theme provided by the user")
    style: str = Field(
        description="Consistent art style for all illustrations (e.g., 'soft watercolor children's book illustration')"
    )
    pages: List[StoryPage] = Field(description="List of 5 story pages")
