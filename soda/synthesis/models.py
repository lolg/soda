from pydantic import BaseModel


class NameSuggestions(BaseModel):
    summary: str
    options: list[str]