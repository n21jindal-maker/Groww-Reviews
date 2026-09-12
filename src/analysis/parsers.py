from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field
from typing import List
from src.models import ClusteringResult, ActionIdea

# Model wrapper for the Action Idea chain to parse as a list
class ActionIdeas(BaseModel):
    actions: List[ActionIdea] = Field(description="A list of specific, actionable improvement ideas", min_length=3, max_length=3)

# Parsers
theme_parser = PydanticOutputParser(pydantic_object=ClusteringResult)
quote_parser = StrOutputParser()
action_parser = PydanticOutputParser(pydantic_object=ActionIdeas)

def get_theme_parser(llm):
    # OutputFixingParser is deprecated/moved in LangChain 0.3, 
    # relying on LCEL chain.with_retry(stop_after_attempt=3) which is more robust.
    return theme_parser

def get_action_parser(llm):
    return action_parser
