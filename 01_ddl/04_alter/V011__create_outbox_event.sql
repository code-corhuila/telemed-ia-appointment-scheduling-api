CREATE TABLE appointment_scheduling.outbox_event (
    id              uuid         NOT NULL DEFAULT gen_random_uuid(),
    event_type      varchar(100) NOT NULL,
    payload         jsonb        NOT NULL,
    correlation_id  varchar(100),
    status          varchar(20)  NOT NULL DEFAULT 'PENDING',
    created_at      timestamptz  NOT NULL DEFAULT now(),
    published_at    timestamptz,
    CONSTRAINT pk_outbox_event PRIMARY KEY (id),
    CONSTRAINT ck_outbox_event_status CHECK (status IN ('PENDING', 'PUBLISHED', 'FAILED'))
);
CREATE INDEX idx_outbox_event_pending ON appointment_scheduling.outbox_event (created_at) WHERE status = 'PENDING';
