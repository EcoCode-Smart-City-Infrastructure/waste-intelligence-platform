"""
Audit Logger for AI Copilot Service.

Provides comprehensive logging of all copilot interactions for
compliance, debugging, and security auditing.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from threading import Lock

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Audit logger that records all copilot interactions.
    
    Logs include:
    - User queries
    - Context used
    - Tools called
    - LLM responses
    - Operator actions
    - Timestamps
    - Session IDs
    """
    
    def __init__(self, log_path: Optional[str] = None):
        """Initialize audit logger."""
        settings = get_settings()
        self.log_path = Path(log_path or settings.audit_log_path)
        self._lock = Lock()
        
        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize file if it doesn't exist
        if not self.log_path.exists():
            with open(self.log_path, 'w') as f:
                f.write("""# AI Copilot Audit Log
# Format: JSON lines
# Fields: timestamp, audit_id, user_id, session_id, event_type, data
""")
    
    def _generate_audit_id(self) -> str:
        """Generate a unique audit ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        import random
        random_part = f"{random.randint(0, 999999):06d}"
        return f"AUDIT-{timestamp}-{random_part}"
    
    def log(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        audit_id: Optional[str] = None
    ) -> str:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (query, response, tool_call, action, etc.)
            user_id: ID of the user making the request
            session_id: Session ID for grouping related events
            data: Additional data to log
            audit_id: Pre-generated audit ID (or None to generate one)
        
        Returns:
            The audit ID for this event
        """
        if audit_id is None:
            audit_id = self._generate_audit_id()
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        record = {
            "timestamp": timestamp,
            "audit_id": audit_id,
            "event_type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "data": data or {}
        }
        
        # Add context from data if present
        if isinstance(data, dict):
            record["data"] = data
        
        # Log to file
        with self._lock:
            try:
                with open(self.log_path, 'a') as f:
                    f.write(json.dumps(record) + '\n')
                logger.debug(f"Audit logged: {event_type} - {audit_id}")
            except Exception as e:
                logger.error(f"Failed to write audit log: {str(e)}")
        
        # Also log to standard logging
        logger.info(f"Audit: {event_type} - audit_id={audit_id}, user={user_id}, session={session_id}")
        
        return audit_id
    
    def log_query(
        self,
        user_id: str,
        question: str,
        context: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """Log a user query."""
        audit_id = self._generate_audit_id()
        
        data = {
            "question": question,
            "context": context,
            "action": "query"
        }
        
        return self.log(
            event_type="query",
            user_id=user_id,
            session_id=session_id,
            data=data,
            audit_id=audit_id
        )
    
    def log_response(
        self,
        audit_id: str,
        answer: str,
        used_tools: List[str],
        context_summary: Dict[str, Any],
        model: str,
        tokens_used: int = 0
    ) -> str:
        """Log an LLM response."""
        data = {
            "answer": answer,
            "used_tools": used_tools,
            "context_summary": context_summary,
            "model": model,
            "tokens_used": tokens_used,
            "action": "response"
        }
        
        return self.log(
            event_type="response",
            audit_id=audit_id,
            data=data
        )
    
    def log_tool_call(
        self,
        audit_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Dict[str, Any],
        duration_ms: float = 0.0
    ) -> str:
        """Log a tool call."""
        data = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_output,
            "duration_ms": duration_ms,
            "action": "tool_call"
        }
        
        return self.log(
            event_type="tool_call",
            audit_id=audit_id,
            data=data
        )
    
    def log_operator_action(
        self,
        audit_id: str,
        user_id: str,
        action: str,
        details: Dict[str, Any]
    ) -> str:
        """Log an operator action taken based on copilot suggestion."""
        data = {
            "action": action,
            "details": details,
            "action_type": "operator_action"
        }
        
        return self.log(
            event_type="operator_action",
            user_id=user_id,
            audit_id=audit_id,
            data=data
        )
    
    def log_guardrail_violation(
        self,
        audit_id: str,
        violation_type: str,
        details: str,
        action: str
    ) -> str:
        """Log a guardrail violation."""
        data = {
            "violation_type": violation_type,
            "details": details,
            "action": action,
            "action_type": "guardrail_violation"
        }
        
        return self.log(
            event_type="guardrail_violation",
            audit_id=audit_id,
            data=data
        )
    
    def log_error(
        self,
        audit_id: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None
    ) -> str:
        """Log an error."""
        data = {
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "action_type": "error"
        }
        
        return self.log(
            event_type="error",
            audit_id=audit_id,
            data=data
        )
    
    def get_audit_records(
        self,
        audit_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit records from the log file.
        
        Args:
            audit_id: Filter by audit ID
            user_id: Filter by user ID
            session_id: Filter by session ID
            event_type: Filter by event type
            limit: Maximum number of records to return
        
        Returns:
            List of audit record dictionaries
        """
        records = []
        
        if not self.log_path.exists():
            return records
        
        try:
            with open(self.log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        record = json.loads(line)
                        
                        # Apply filters
                        if audit_id and record.get("audit_id") != audit_id:
                            continue
                        if user_id and record.get("user_id") != user_id:
                            continue
                        if session_id and record.get("session_id") != session_id:
                            continue
                        if event_type and record.get("event_type") != event_type:
                            continue
                        
                        records.append(record)
                        
                        if len(records) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read audit log: {str(e)}")
        
        return records
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all audit records for a specific session."""
        return self.get_audit_records(session_id=session_id)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
