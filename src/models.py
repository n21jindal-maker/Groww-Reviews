from pydantic import BaseModel, Field
from typing import List, Optional

class Review(BaseModel):
    reviewId: str
    score: int = Field(ge=1, le=5)
    text: str
    at: str
    appVersion: Optional[str] = None

class ThemeAssignment(BaseModel):
    theme_name: str = Field(description="A short, descriptive label for this theme")
    review_ids: List[str] = Field(description="List of review IDs assigned to this theme")
    count: int = Field(description="Number of reviews in this theme")

class ClusteringResult(BaseModel):
    themes: List[ThemeAssignment] = Field(max_length=5, description="Top themes identified from the reviews")

class ActionIdea(BaseModel):
    theme_name: str
    action: str = Field(description="Specific, actionable improvement idea")

class PulseNote(BaseModel):
    themes: List[ThemeAssignment]
    quotes: List[str]
    actions: List[ActionIdea]
