"""Documentation Domain Department."""

from domains.base_domain import BaseDomain, DomainMetadata


class DocumentationDomain(BaseDomain):
    """Documentation Domain handling API and Architecture documentation."""

    def __init__(self) -> None:
        metadata = DomainMetadata(
            name="documentation",
            description="Documentation department curating architecture specs, ADRs, and API docs.",
            roles=["doc_writer", "api_archivist"],
            workflows=["generate_api_docs", "adr_curation"],
        )
        super().__init__(metadata)
