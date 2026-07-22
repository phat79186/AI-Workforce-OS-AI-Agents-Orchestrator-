"""Data Analysis Domain Department."""

from domains.base_domain import BaseDomain, DomainMetadata


class DataAnalysisDomain(BaseDomain):
    """Data Analysis Domain handling data processing and analytics."""

    def __init__(self) -> None:
        metadata = DomainMetadata(
            name="data_analysis",
            description="Data Analysis department executing data transformations, statistics, and reporting.",
            roles=["data_analyst", "data_engineer"],
            workflows=["data_pipeline", "stat_summary"],
        )
        super().__init__(metadata)
