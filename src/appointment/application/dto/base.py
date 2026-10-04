"""Base Pydantic model for every DTO.

Enforces camelCase JSON serialization (norm 5.3.5) while keeping Python
snake_case in the code. `populate_by_name=True` allows construction using
either name, which is convenient in tests.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    """Base for DTOs that must serialize to camelCase JSON."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
