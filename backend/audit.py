import uuid
from datetime import datetime
from typing import List, Optional
from backend.models import AuditEvent

class AuditLogger:
    """
    Centralized Audit Trail Logger.
    Maintains an immutable sequence of forensic & operational finance events.
    """

    def __init__(self):
        self.events: List[AuditEvent] = []

    def log(
        self,
        action: str,
        actor: str,
        affected_record: str,
        new_state: str,
        reason: str,
        previous_state: Optional[str] = None
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            action=action,
            actor=actor,
            affected_record=affected_record,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason
        )
        self.events.insert(0, event) # Most recent first
        return event

    def get_events(self, limit: int = 100) -> List[AuditEvent]:
        return self.events[:limit]

    def clear(self):
        self.events = []

# Global shared audit instance
audit_trail = AuditLogger()
