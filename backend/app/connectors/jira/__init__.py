"""
Jira Cloud connector package.

Implements BaseConnector against Jira Cloud REST API v3.
"""

from app.connectors.jira.connector import JiraConnector

__all__ = ["JiraConnector"]
