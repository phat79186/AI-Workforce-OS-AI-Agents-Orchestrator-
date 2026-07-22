"""Research Domain Department."""

from domains.base_domain import BaseDomain, DomainMetadata


class ResearchDomain(BaseDomain):
    """Research Domain handling tech surveys, web research, and Obsidian synthesis."""

    def __init__(self) -> None:
        metadata = DomainMetadata(
            name="research",
            description="Research department conducting web searches, technology evaluation, and knowledge vault publishing.",
            roles=["researcher", "analyst", "knowledge_synthesizer"],
            workflows=["deep_research", "tech_survey", "obsidian_publish"],
        )
        super().__init__(metadata)
