from pydantic import BaseModel, Field
from typing import List


class SceneOutput(BaseModel):
    id: int = Field(description="Scene ID Number")
    narration: str = Field(description="What the narrator of this scene shoud say")
    visual_description: str = Field(
        description="Detailed dscription for image generation"
    )
    embedded_text: str = Field(description="Text overlay for the image")
    embedded_text_location: str = Field(
        description="Where to position the text on the image (i.e. 'to center', 'bottom-center', 'top-left')"
    )
    duration: int = Field(description="Duration in seconds for this scene")


class ContentPlanOutput(BaseModel):
    topic: str
    total_duration: int
    scenes: List[SceneOutput]
