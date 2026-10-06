"""Generic pagination envelope (norm 5.3.6)."""

from pydantic import Field, field_validator

from appointment.application.dto.base import CamelCaseModel


class PaginationQuery(CamelCaseModel):
    """Query parameters shared by every paginated listing."""

    page: int = 1
    limit: int = 20

    @field_validator("page")
    @classmethod
    def _page_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page must be >= 1")
        return v

    @field_validator("limit")
    @classmethod
    def _limit_must_be_in_range(cls, v: int) -> int:
        if not 1 <= v <= 100:
            raise ValueError("limit must be between 1 and 100")
        return v


class PageMeta(CamelCaseModel):
    """Metadata of a paginated response."""

    page: int
    limit: int
    total: int
    total_pages: int = Field(serialization_alias="totalPages")

    @classmethod
    def of(cls, *, page: int, limit: int, total: int) -> "PageMeta":
        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(page=page, limit=limit, total=total, total_pages=total_pages)


class PaginatedResponse[T](CamelCaseModel):
    """Standard paginated envelope: {data, meta}."""

    data: list[T]
    meta: PageMeta
