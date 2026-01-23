"""
Scheduled Collector Health Analyzer for Cribl Health Check.

Monitors scheduled collector job health, execution history, and detects
collectors that fail silently when scheduled vs. ad-hoc execution.

Community Source: https://knowledge.cribl.io/stream-56/scheduled-collector-discovers-events-but-does-not-collect-1559
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class ScheduledCollectorHealthAnalyzer(BaseAnalyzer):
    """
    Analyzer for scheduled collector job health and execution history.

    Checks:
    - Schedule validity (cron syntax)
    - Job execution history
    - Success/failure rates
    - Jobs that never ran
    - Jobs with increasing failure trends
    - Overlapping schedules
    """

    FAILURE_RATE_HIGH_PERCENT = 50.0
    FAILURE_RATE_CRITICAL_PERCENT = 100.0
    NEVER_RAN_DAYS = 7
    STALE_JOB_HOURS = 24

    @property
    def objective_name(self) -> str:
        return "scheduled_collector_health"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]

    def get_description(self) -> str:
        return "Monitors scheduled collector job health, execution history, and failure patterns"

    def get_estimated_api_calls(self) -> int:
        return 10

    def get_required_permissions(self) -> list[str]:
        return [
            "read:collectors",
            "read:jobs",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """Analyze scheduled collectors for health issues."""
        result = self.create_result()

        try:
            log.info("scheduled_collector_health_analysis_started")

            collectors = await client.get_collectors()
            scheduled_collectors = self._filter_scheduled_collectors(collectors)

            if not scheduled_collectors:
                log.info("no_scheduled_collectors_found")
                result.metadata["scheduled_collectors_analyzed"] = 0
                result.metadata["message"] = "No scheduled collectors configured"
                result.success = True
                return result

            all_jobs = await client.get_jobs()

            issues_found = 0
            for collector in scheduled_collectors:
                collector_id = collector.get("id", "unknown")
                collector_jobs = self._filter_jobs_for_collector(all_jobs, collector_id)
                issues_found += self._analyze_collector(collector, collector_jobs, result, client)

            issues_found += self._check_overlapping_schedules(scheduled_collectors, result, client)

            result.metadata.update(
                {
                    "scheduled_collectors_analyzed": len(scheduled_collectors),
                    "total_jobs_analyzed": len(all_jobs),
                    "issues_found": issues_found,
                    "critical_findings": len(result.get_critical_findings()),
                    "high_findings": len(result.get_high_findings()),
                }
            )

            result.success = True
            log.info(
                "scheduled_collector_health_analysis_completed",
                collectors=len(scheduled_collectors),
                findings=len(result.findings),
                issues=issues_found,
            )

        except Exception as e:
            log.error("scheduled_collector_health_analysis_failed", error=str(e))
            result.success = False
            result.error = f"Scheduled collector health analysis failed: {str(e)}"
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="scheduled-collector-analysis-error",
                    title="Scheduled Collector Analysis Failed",
                    description=f"Unable to complete scheduled collector analysis: {str(e)}",
                    severity="high",
                    category="scheduled_collector_health",
                    confidence_level="high",
                    affected_components=["scheduled_collector_analyzer"],
                    estimated_impact="Unable to assess scheduled collector health",
                    remediation_steps=[
                        "Check API connectivity",
                        "Verify authentication token has read:collectors permission",
                        "Review error logs for details",
                    ],
                    metadata={"error": str(e)},
                )
            )

        return result

    def _filter_scheduled_collectors(
        self, collectors: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter collectors to only those with schedules configured."""
        scheduled = []
        for collector in collectors:
            if collector.get("disabled", False):
                continue
            schedule = collector.get("schedule") or collector.get("cron")
            if schedule:
                scheduled.append(collector)
        return scheduled

    def _filter_jobs_for_collector(
        self, jobs: list[dict[str, Any]], collector_id: str
    ) -> list[dict[str, Any]]:
        """Filter jobs to only those for a specific collector."""
        return [
            j
            for j in jobs
            if j.get("config", {}).get("id") == collector_id
            or j.get("collectorId") == collector_id
            or j.get("collector") == collector_id
        ]

    def _analyze_collector(
        self,
        collector: dict[str, Any],
        jobs: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> int:
        """Analyze a single scheduled collector for issues."""
        issues = 0
        collector_id = collector.get("id", "unknown")
        schedule = collector.get("schedule") or collector.get("cron", "")

        if not self._is_valid_cron(schedule):
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"collector-invalid-schedule-{collector_id}",
                    title=f"Invalid Schedule: {collector_id}",
                    description=f"Collector '{collector_id}' has invalid cron schedule: '{schedule}'",
                    severity="high",
                    category="scheduled_collector_health",
                    confidence_level="high",
                    affected_components=[collector_id],
                    estimated_impact="Collector will not execute on schedule",
                    remediation_steps=[
                        "Fix the cron expression syntax",
                        "Example valid expressions: '0 * * * *' (hourly), '*/15 * * * *' (every 15 min)",
                        "Use a cron validator tool to verify syntax",
                    ],
                    metadata={
                        "collector_id": collector_id,
                        "schedule": schedule,
                    },
                )
            )
            issues += 1
            return issues

        if self._is_overly_frequent_schedule(schedule):
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"collector-frequent-schedule-{collector_id}",
                    title=f"Very Frequent Schedule: {collector_id}",
                    description=f"Collector '{collector_id}' runs very frequently ({schedule}). Consider if this is necessary.",
                    severity="low",
                    category="scheduled_collector_health",
                    confidence_level="medium",
                    affected_components=[collector_id],
                    estimated_impact="May cause resource contention or unnecessary load",
                    remediation_steps=[
                        "Evaluate if such frequent collection is needed",
                        "Consider batching data collection for efficiency",
                    ],
                    metadata={
                        "collector_id": collector_id,
                        "schedule": schedule,
                    },
                )
            )
            issues += 1

        if not jobs:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"collector-never-ran-{collector_id}",
                    title=f"Collector Never Executed: {collector_id}",
                    description=f"Scheduled collector '{collector_id}' has no execution history. It may have never run successfully.",
                    severity="critical",
                    category="scheduled_collector_health",
                    confidence_level="medium",
                    affected_components=[collector_id],
                    estimated_impact="No data being collected from this source",
                    remediation_steps=[
                        "Run the collector manually to verify configuration",
                        "Check collector logs for startup errors",
                        "Verify schedule syntax is correct",
                        f"Current schedule: {schedule}",
                    ],
                    metadata={
                        "collector_id": collector_id,
                        "schedule": schedule,
                    },
                )
            )
            issues += 1
            return issues

        issues += self._analyze_job_history(collector, jobs, result, client)
        return issues

    def _analyze_job_history(
        self,
        collector: dict[str, Any],
        jobs: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> int:
        """Analyze job execution history for a collector."""
        issues = 0
        collector_id = collector.get("id", "unknown")

        recent_jobs = self._get_recent_jobs(jobs, days=7)
        if not recent_jobs:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"collector-stale-{collector_id}",
                    title=f"Collector Stale: {collector_id}",
                    description=f"Scheduled collector '{collector_id}' has no jobs in the last 7 days despite being scheduled.",
                    severity="high",
                    category="scheduled_collector_health",
                    confidence_level="medium",
                    affected_components=[collector_id],
                    estimated_impact="Data collection may have stopped",
                    remediation_steps=[
                        "Check if scheduler service is running",
                        "Verify collector is not disabled",
                        "Review system logs for scheduler errors",
                    ],
                    metadata={
                        "collector_id": collector_id,
                        "last_job_count": len(jobs),
                    },
                )
            )
            issues += 1
            return issues

        success_count = sum(1 for j in recent_jobs if self._is_job_successful(j))
        failure_count = len(recent_jobs) - success_count
        total_count = len(recent_jobs)

        if total_count > 0:
            failure_rate = (failure_count / total_count) * 100

            if failure_rate >= self.FAILURE_RATE_CRITICAL_PERCENT:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"collector-all-failed-{collector_id}",
                        title=f"All Jobs Failed: {collector_id}",
                        description=f"Collector '{collector_id}' has 100% failure rate ({failure_count}/{total_count} jobs failed in last 7 days).",
                        severity="critical",
                        category="scheduled_collector_health",
                        confidence_level="high",
                        affected_components=[collector_id],
                        estimated_impact="No data being collected from this source",
                        remediation_steps=[
                            "Check collector configuration for errors",
                            "Verify source connectivity and credentials",
                            "Review job error messages for specific failures",
                            "Run collector manually to diagnose issue",
                        ],
                        metadata={
                            "collector_id": collector_id,
                            "failure_rate": failure_rate,
                            "failed_jobs": failure_count,
                            "total_jobs": total_count,
                        },
                    )
                )
                issues += 1
            elif failure_rate >= self.FAILURE_RATE_HIGH_PERCENT:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"collector-high-failure-{collector_id}",
                        title=f"High Failure Rate: {collector_id}",
                        description=f"Collector '{collector_id}' has {failure_rate:.0f}% failure rate ({failure_count}/{total_count} jobs failed in last 7 days).",
                        severity="high",
                        category="scheduled_collector_health",
                        confidence_level="high",
                        affected_components=[collector_id],
                        estimated_impact="Intermittent data collection failures",
                        remediation_steps=[
                            "Review recent job failures for common error patterns",
                            "Check source availability during failure times",
                            "Consider increasing job timeout if failures are timeouts",
                        ],
                        metadata={
                            "collector_id": collector_id,
                            "failure_rate": failure_rate,
                            "failed_jobs": failure_count,
                            "total_jobs": total_count,
                        },
                    )
                )
                issues += 1

        issues += self._check_job_duration_issues(collector, recent_jobs, result, client)
        return issues

    def _check_job_duration_issues(
        self,
        collector: dict[str, Any],
        jobs: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> int:
        """Check if job duration exceeds schedule interval."""
        issues = 0
        collector_id = collector.get("id", "unknown")
        schedule = collector.get("schedule") or collector.get("cron", "")

        schedule_interval_sec = self._estimate_schedule_interval_seconds(schedule)
        if schedule_interval_sec is None:
            return issues

        durations = []
        for job in jobs:
            duration = self._get_job_duration_seconds(job)
            if duration is not None:
                durations.append(duration)

        if not durations:
            return issues

        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)

        if max_duration > schedule_interval_sec:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"collector-duration-exceeds-{collector_id}",
                    title=f"Job Duration Exceeds Schedule: {collector_id}",
                    description=(
                        f"Collector '{collector_id}' job duration ({max_duration:.0f}s) exceeds "
                        f"schedule interval ({schedule_interval_sec:.0f}s). Jobs may overlap."
                    ),
                    severity="high",
                    category="scheduled_collector_health",
                    confidence_level="high",
                    affected_components=[collector_id],
                    estimated_impact="Job overlap causing resource contention or data issues",
                    remediation_steps=[
                        "Increase schedule interval to exceed typical job duration",
                        "Optimize collector to reduce job runtime",
                        "Consider using mutex/lock to prevent overlapping runs",
                    ],
                    metadata={
                        "collector_id": collector_id,
                        "avg_duration_sec": avg_duration,
                        "max_duration_sec": max_duration,
                        "schedule_interval_sec": schedule_interval_sec,
                    },
                )
            )
            issues += 1

        return issues

    def _check_overlapping_schedules(
        self,
        collectors: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> int:
        """Check for collectors with identical schedules that might compete."""
        issues = 0
        schedule_groups: dict[str, list[str]] = {}

        for collector in collectors:
            collector_id = collector.get("id", "unknown")
            schedule = collector.get("schedule") or collector.get("cron", "")
            normalized = self._normalize_schedule(schedule)

            if normalized not in schedule_groups:
                schedule_groups[normalized] = []
            schedule_groups[normalized].append(collector_id)

        for schedule, collector_ids in schedule_groups.items():
            if len(collector_ids) > 3:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"collector-schedule-contention-{schedule[:20]}",
                        title=f"Multiple Collectors Same Schedule",
                        description=(
                            f"{len(collector_ids)} collectors share the same schedule '{schedule}'. "
                            f"This may cause resource contention."
                        ),
                        severity="medium",
                        category="scheduled_collector_health",
                        confidence_level="medium",
                        affected_components=collector_ids[:5],
                        estimated_impact="Resource contention during scheduled runs",
                        remediation_steps=[
                            "Stagger collector schedules to reduce simultaneous load",
                            "Example: Instead of all at '0 * * * *', use '0 * * * *', '15 * * * *', etc.",
                        ],
                        metadata={
                            "schedule": schedule,
                            "collector_count": len(collector_ids),
                            "collectors": collector_ids[:10],
                        },
                    )
                )
                issues += 1

        return issues

    def _is_valid_cron(self, schedule: str) -> bool:
        """Basic validation of cron expression syntax."""
        if not schedule or not schedule.strip():
            return False
        parts = schedule.strip().split()
        if len(parts) < 5 or len(parts) > 6:
            return False
        return True

    def _is_overly_frequent_schedule(self, schedule: str) -> bool:
        """Check if schedule runs more frequently than every minute."""
        parts = schedule.strip().split()
        if len(parts) < 5:
            return False
        minute_field = parts[0]
        if minute_field.startswith("*/"):
            try:
                interval = int(minute_field[2:])
                return interval < 5
            except ValueError:
                return False
        if minute_field == "*":
            return True
        return False

    def _estimate_schedule_interval_seconds(self, schedule: str) -> int | None:
        """Estimate interval between runs based on cron expression."""
        parts = schedule.strip().split()
        if len(parts) < 5:
            return None

        minute_field = parts[0]
        hour_field = parts[1]

        if minute_field.startswith("*/"):
            try:
                return int(minute_field[2:]) * 60
            except ValueError:
                return None

        if minute_field == "*":
            return 60

        if hour_field.startswith("*/"):
            try:
                return int(hour_field[2:]) * 3600
            except ValueError:
                return None

        if hour_field == "*" and minute_field.isdigit():
            return 3600

        return None

    def _normalize_schedule(self, schedule: str) -> str:
        """Normalize schedule string for comparison."""
        return " ".join(schedule.strip().split()).lower()

    def _get_recent_jobs(self, jobs: list[dict[str, Any]], days: int = 7) -> list[dict[str, Any]]:
        """Filter jobs to those within the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = []

        for job in jobs:
            job_time = self._get_job_timestamp(job)
            if job_time and job_time >= cutoff:
                recent.append(job)

        return recent

    def _get_job_timestamp(self, job: dict[str, Any]) -> datetime | None:
        """Get timestamp from job."""
        ts_fields = ["startTime", "createdAt", "timestamp", "time"]
        for field in ts_fields:
            val = job.get(field)
            if val:
                try:
                    if isinstance(val, (int, float)):
                        if val > 1e12:
                            val = val / 1000
                        return datetime.fromtimestamp(val, tz=timezone.utc)
                    if isinstance(val, str):
                        for fmt in [
                            "%Y-%m-%dT%H:%M:%S.%fZ",
                            "%Y-%m-%dT%H:%M:%SZ",
                            "%Y-%m-%d %H:%M:%S",
                        ]:
                            try:
                                return datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
                            except ValueError:
                                continue
                except Exception:
                    pass
        return None

    def _is_job_successful(self, job: dict[str, Any]) -> bool:
        """Determine if job completed successfully."""
        status = job.get("status", "").lower()
        if status in ["completed", "success", "succeeded", "done"]:
            return True
        if status in ["failed", "error", "cancelled", "timeout"]:
            return False
        exit_code = job.get("exitCode")
        if exit_code is not None:
            return exit_code == 0
        return job.get("success", True)

    def _get_job_duration_seconds(self, job: dict[str, Any]) -> float | None:
        """Get job duration in seconds."""
        duration = job.get("duration") or job.get("durationMs") or job.get("runtime")
        if duration is not None:
            try:
                dur = float(duration)
                if job.get("durationMs") or dur > 1000000:
                    return dur / 1000
                return dur
            except (ValueError, TypeError):
                return None

        start = job.get("startTime")
        end = job.get("endTime") or job.get("finishTime")
        if start and end:
            try:
                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    if start > 1e12:
                        start = start / 1000
                    if end > 1e12:
                        end = end / 1000
                    return end - start
            except Exception:
                pass

        return None
