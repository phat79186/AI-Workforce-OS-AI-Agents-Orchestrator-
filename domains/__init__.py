"""Domains package containing Layer 2 Domain Ecosystem departments."""

from domains.base_domain import BaseDomain, DomainMetadata
from domains.software_engineering import SoftwareEngineeringDomain
from domains.research import ResearchDomain
from domains.data_analysis import DataAnalysisDomain
from domains.content_creation import ContentCreationDomain
from domains.documentation import DocumentationDomain
from domains.devops import DevOpsDomain
from domains.knowledge_management import KnowledgeManagementDomain

__all__ = [
    "BaseDomain",
    "DomainMetadata",
    "SoftwareEngineeringDomain",
    "ResearchDomain",
    "DataAnalysisDomain",
    "ContentCreationDomain",
    "DocumentationDomain",
    "DevOpsDomain",
    "KnowledgeManagementDomain",
]
