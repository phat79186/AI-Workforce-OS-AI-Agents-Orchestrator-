"""Software Engineering Domain Department."""

from domains.base_domain import BaseDomain, DomainMetadata


class SoftwareEngineeringDomain(BaseDomain):
    """Software Engineering Domain containing coding, debugging, testing, and review workflows."""

    def __init__(self) -> None:
        metadata = DomainMetadata(
            name="software_engineering",
            description="Software Engineering department handling development, bugfixes, refactoring, and automated testing.",
            roles=["coder", "debugger", "tester", "reviewer", "security_auditor", "devops_engineer"],
            workflows=["feature", "bugfix", "refactor", "release"],
        )
        super().__init__(metadata)
