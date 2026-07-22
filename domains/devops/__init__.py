"""DevOps Domain Department."""

from domains.base_domain import BaseDomain, DomainMetadata


class DevOpsDomain(BaseDomain):
    """DevOps Domain handling CI/CD and infrastructure."""

    def __init__(self) -> None:
        metadata = DomainMetadata(
            name="devops",
            description="DevOps department managing Docker, Kubernetes, and CI/CD pipelines.",
            roles=["devops_engineer", "cloud_architect"],
            workflows=["docker_build", "cicd_deploy"],
        )
        super().__init__(metadata)
