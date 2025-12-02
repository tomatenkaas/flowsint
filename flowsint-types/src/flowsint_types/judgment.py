from typing import Optional, Self
from pydantic import Field, HttpUrl, model_validator
from .flowsint_base import FlowsintType
from .registry import flowsint_type


@flowsint_type
class Judgment(FlowsintType):
    """Represents a legal judgment with its ECLI, URL, and summary."""

    url: HttpUrl = Field(
        ..., 
        description="The Deeplink URL to the judgment", 
        title="Judgment URL", 
        json_schema_extra={"primary": True}
    )
    ecli: Optional[str] = Field(
        None, 
        description="The ECLI code of the judgment (e.g., ECLI:NL:RBGEL:2021:733)", 
        title="ECLI Code"
    )
    summary: Optional[str] = Field(
        None, 
        description="The full text fragment (summary) of the judgment.", 
        title="Summary"
    )
    publication_date: Optional[str] = Field(
        None, 
        description="The date the judgment was published.", 
        title="Publication Date"
    )
    
    @model_validator(mode='after')
    def compute_label(self) -> Self:
        # Ensures that the label set by the enricher (the excerpt) is preserved. 
        # If no label is set, it falls back to ECLI or URL.
        if not self.label: 
            if self.ecli:
                self.label = self.ecli
            else:
                self.label = str(self.url)
        return self

    @classmethod
    def from_string(cls, line: str):
        """Parse a judgment from a raw string."""
        return cls(url=line.strip())