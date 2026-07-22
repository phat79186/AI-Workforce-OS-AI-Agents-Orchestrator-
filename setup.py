"""
Setup script for AI Coding Tools Collaborative
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="ai-coding-tools",
    version="2.0.0",
    description="AI Coding Tools — Orchestrator and Agentic Team systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI Coding Tools Team",
    python_requires=">=3.8",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "orchestrator": ["config/*.yaml"],
        "agentic_team": ["config/*.yaml"],
    },
    install_requires=[
        "click>=8.1.0",
        "pyyaml>=6.0",
        "colorama>=0.4.6",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "tenacity>=8.2.0",
        "python-dotenv>=1.0.0",
        "structlog>=23.1.0",
        "prometheus-client>=0.17.0",
        "httpx>=0.27.0",
        "psutil>=5.9.0",
        "flask>=3.0.0",
        "flask-socketio>=5.3.0",
        "flask-cors>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.11.0",
            "pytest-timeout>=2.1.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
            "bandit>=1.7.5",
            "pre-commit>=3.3.3",
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
