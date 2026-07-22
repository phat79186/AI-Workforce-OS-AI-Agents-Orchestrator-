"""Content Creation Domain Department."""

from domains.base_domain import BaseDomain, DomainMetadata


class ContentCreationDomain(BaseDomain):
    """Content Creation Domain handling writing and copy editing."""

    def __init__(self) -> None:
        metadata = DomainMetadata(
            name="content_creation",
            description="Content Creation department producing technical blog posts, documentation, and copy.",
            roles=["writer", "editor"],
            workflows=["draft_blog", "technical_writing"],
        )
        super().__init__(metadata)
