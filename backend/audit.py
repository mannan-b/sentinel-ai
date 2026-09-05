import uuid
import hashlib
from datetime import datetime
from typing import List, Optional, Tuple
from backend.models import AuditEvent

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

class AuditLogger:
    """
    Centralized Tamper-Evident Audit Trail Logger.
    Maintains a cryptographically linked SHA-256 hash chain of forensic & operational finance events.
    """

    def __init__(self):
        self.events: List[AuditEvent] = []
        self._latest_hash: str = GENESIS_HASH

    def _compute_hash(
        self,
        prev_hash: str,
        event_id: str,
        timestamp: str,
        action: str,
        actor: str,
        affected_record: str,
        new_state: str,
        reason: str
    ) -> str:
        payload = f"{prev_hash}|{event_id}|{timestamp}|{action}|{actor}|{affected_record}|{new_state}|{reason}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def log(
        self,
        action: str,
        actor: str,
        affected_record: str,
        new_state: str,
        reason: str,
        previous_state: Optional[str] = None
    ) -> AuditEvent:
        event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        prev_h = self._latest_hash
        event_h = self._compute_hash(
            prev_hash=prev_h,
            event_id=event_id,
            timestamp=timestamp,
            action=action,
            actor=actor,
            affected_record=affected_record,
            new_state=new_state,
            reason=reason
        )
        
        event = AuditEvent(
            event_id=event_id,
            timestamp=timestamp,
            action=action,
            actor=actor,
            affected_record=affected_record,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason,
            event_hash=event_h,
            previous_hash=prev_h
        )
        
        self.events.insert(0, event) # Most recent first for display
        self._latest_hash = event_h
        return event

    def verify_chain_integrity(self) -> Tuple[bool, str]:
        """
        Validates the full chronological hash chain from genesis to the most recent entry.
        """
        if not self.events:
            return True, "Audit log is empty."

        # Verify in chronological order (oldest to newest)
        chrono_events = list(reversed(self.events))
        expected_prev = GENESIS_HASH

        for idx, ev in enumerate(chrono_events):
            if ev.previous_hash != expected_prev:
                return False, f"Broken link at event {ev.event_id} (index {idx}): expected prev_hash {expected_prev}, got {ev.previous_hash}"
            
            recomputed = self._compute_hash(
                prev_hash=ev.previous_hash,
                event_id=ev.event_id,
                timestamp=ev.timestamp,
                action=ev.action,
                actor=ev.actor,
                affected_record=ev.affected_record,
                new_state=ev.new_state,
                reason=ev.reason
            )
            if recomputed != ev.event_hash:
                return False, f"Hash corruption detected at event {ev.event_id}: recorded {ev.event_hash}, recomputed {recomputed}"
            
            expected_prev = ev.event_hash

        return True, f"Cryptographic audit chain verified. {len(self.events)} events intact."

    def get_events(self, limit: int = 100) -> List[AuditEvent]:
        return self.events[:limit]

    def clear(self):
        self.events = []
        self._latest_hash = GENESIS_HASH

# Global shared audit instance
audit_trail = AuditLogger()

