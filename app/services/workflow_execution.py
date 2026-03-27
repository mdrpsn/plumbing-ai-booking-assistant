from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import WorkflowRun
from app.services.follow_up import FOLLOW_UP_WORKFLOW_TYPE, process_follow_up_workflow
from app.services.notification_service import NotificationService


@dataclass(frozen=True)
class WorkflowJob:
    workflow_run_id: int
    workflow_type: str


@dataclass(frozen=True)
class WorkflowExecutionResult:
    evaluated: int
    sent: int
    skipped: int
    workflow_ids: list[int]


class WorkflowJobQueue:
    def get_due_jobs(self, db: Session, *, now_at: datetime) -> list[WorkflowJob]:
        workflow_runs = db.scalars(
            select(WorkflowRun)
            .where(
                WorkflowRun.status == "pending",
                WorkflowRun.scheduled_for <= now_at,
            )
            .order_by(WorkflowRun.scheduled_for.asc(), WorkflowRun.id.asc())
        ).all()
        return [
            WorkflowJob(
                workflow_run_id=workflow_run.id,
                workflow_type=workflow_run.workflow_type,
            )
            for workflow_run in workflow_runs
        ]


class WorkflowExecutionService:
    def __init__(
        self,
        notification_service: NotificationService,
        job_queue: WorkflowJobQueue | None = None,
    ) -> None:
        self.notification_service = notification_service
        self.job_queue = job_queue or WorkflowJobQueue()

    def process_due_workflows(
        self,
        db: Session,
        *,
        now_at: datetime | None = None,
    ) -> WorkflowExecutionResult:
        evaluation_time = _normalize_datetime(now_at or datetime.now(UTC))
        jobs = self.job_queue.get_due_jobs(db, now_at=evaluation_time)

        sent = 0
        skipped = 0
        workflow_ids: list[int] = []

        for job in jobs:
            workflow_ids.append(job.workflow_run_id)

            if job.workflow_type != FOLLOW_UP_WORKFLOW_TYPE:
                continue

            outcome = process_follow_up_workflow(
                db,
                workflow_run_id=job.workflow_run_id,
                notification_service=self.notification_service,
                evaluation_time=evaluation_time,
            )
            if outcome == "sent":
                sent += 1
            elif outcome == "skipped":
                skipped += 1

        db.commit()
        return WorkflowExecutionResult(
            evaluated=len(jobs),
            sent=sent,
            skipped=skipped,
            workflow_ids=workflow_ids,
        )


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
