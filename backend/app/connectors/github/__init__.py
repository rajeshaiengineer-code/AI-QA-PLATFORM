"""
GitHub connector package.

Implements BaseConnector against the GitHub REST API (PAT auth).
"""

from app.connectors.github.connector import GitHubConnector

__all__ = ["GitHubConnector"]
