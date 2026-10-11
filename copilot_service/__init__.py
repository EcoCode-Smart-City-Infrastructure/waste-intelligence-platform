"""
AI Copilot Service for Waste Intelligence Platform

An embedded AI co-pilot assistant that provides natural language interface
to the waste intelligence platform's data, ML outputs, and knowledge graph.

Architecture:
- FastAPI-based microservice
- OpenRouter integration for LLM access
- Context Manager for data aggregation
- Tool Router for backend service calls
- Guardrail Engine for safety and compliance
- Audit Logger for traceability
"""

__version__ = "1.0.0"
