"""Knowledge Management Domain Department."""

from domains.base_domain import BaseDomain, DomainMetadata


class KnowledgeManagementDomain(BaseDomain):
    """Knowledge Management Domain managing PKM and Obsidian Vaults."""

    def __init__(self) -> None:
        metadata = DomainMetadata(
            name="knowledge_management",
            description="Knowledge Management department organizing Obsidian vaults and personal knowledge graphs.",
            roles=["vault_curator", "knowledge_graph_architect"],
            workflows=["vault_indexing", "graph_synthesis"],
        )
        super().__init__(metadata)
