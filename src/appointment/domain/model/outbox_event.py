from dataclasses import dataclass, asdict
from datetime import datetime
import json

@dataclass
class OutboxEvent:
    event_type: str
    payload: dict
    id: str | None = None
    correlation_id: str | None = None
    status: str = "PENDING"
    created_at: datetime | None = None

    def to_json(self) -> str:
        envelope = {
            "eventId": self.id,
            "eventType": self.event_type,
            "occurredAt": self.created_at.isoformat().replace("+00:00", "Z") if self.created_at else None,
            "correlationId": self.correlation_id or "",
            "version": 1,
            "payload": self.payload
        }
        return json.dumps(envelope)
