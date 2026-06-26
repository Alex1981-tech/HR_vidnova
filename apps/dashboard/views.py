import calendar
from datetime import date

from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import ConfiguredReadOnlyOrAuthenticated
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest
from apps.skud.models import IntegrationRun, WorkDaySummary


class OverviewView(APIView):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def get(self, request):
        employees = Employee.objects.values("status").annotate(count=Count("id"))
        workday_exceptions = WorkDaySummary.objects.exclude(status=WorkDaySummary.Status.OK).count()
        pending_leave = LeaveRequest.objects.filter(status=LeaveRequest.Status.SUBMITTED).count()
        last_runs = [
            {
                "system": run.system.name,
                "job": run.job_name,
                "status": run.status,
                "started_at": run.started_at,
                "rows_inserted": run.rows_inserted,
            }
            for run in IntegrationRun.objects.select_related("system").order_by("-started_at")[:5]
        ]
        return Response(
            {
                "employees_by_status": list(employees),
                "workday_exceptions": workday_exceptions,
                "pending_leave_requests": pending_leave,
                "last_integration_runs": last_runs,
            }
        )


UK_MONTHS_SHORT = [
    "січ.", "лют.", "бер.", "квіт.", "трав.", "черв.",
    "лип.", "серп.", "вер.", "жовт.", "лист.", "груд.",
]

UK_MONTHS_FULL = [
    "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
    "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень",
]


def _recent_months(window):
    today = date.today()
    months = []
    year, month = today.year, today.month
    for _ in range(window):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()
    return months


class HeadcountReportView(APIView):
    """Аналітика чисельності персоналу: найм/звільнення/total за останні N місяців,
    середній приріст і плинність, розподіл за підрозділами та локаціями."""

    permission_classes = [ConfiguredReadOnlyOrAuthenticated]
    months_window = 13

    def get(self, request):
        today = date.today()
        months = []
        year, month = today.year, today.month
        for _ in range(self.months_window):
            months.append((year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        months.reverse()

        employees = list(Employee.objects.values("hired_on", "dismissed_on"))

        monthly = []
        for (year, month) in months:
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            hired = sum(1 for e in employees if e["hired_on"] and first_day <= e["hired_on"] <= last_day)
            terminated = sum(
                1 for e in employees if e["dismissed_on"] and first_day <= e["dismissed_on"] <= last_day
            )
            total = sum(
                1
                for e in employees
                if e["hired_on"]
                and e["hired_on"] <= last_day
                and (not e["dismissed_on"] or e["dismissed_on"] > last_day)
            )
            monthly.append(
                {
                    "month": f"{year}-{month:02d}",
                    "label": f"{UK_MONTHS_SHORT[month - 1]} {str(year)[2:]}",
                    "hired": hired,
                    "terminated": terminated,
                    "total": total,
                }
            )

        total_hired = sum(row["hired"] for row in monthly)
        total_terminated = sum(row["terminated"] for row in monthly)
        avg_headcount = (sum(row["total"] for row in monthly) / len(monthly)) or 1

        metrics = {
            "growth_count": total_hired,
            "growth_pct": round(total_hired / avg_headcount * 100 / self.months_window, 1),
            "turnover_count": total_terminated,
            "turnover_pct": round(total_terminated / avg_headcount * 100 / self.months_window, 1),
        }

        active = Employee.objects.filter(status=Employee.Status.ACTIVE)
        total_active = active.count() or 1

        def distribution(field_name, fallback):
            rows = (
                active.values(field_name)
                .annotate(count=Count("id"))
                .order_by("-count")
            )
            return [
                {
                    "name": row[field_name] or fallback,
                    "count": row["count"],
                    "pct": round(row["count"] / total_active * 100, 2),
                }
                for row in rows
            ]

        return Response(
            {
                "monthly": monthly,
                "metrics": metrics,
                "by_department": distribution("department__name", "Без підрозділу"),
                "by_clinic": distribution("clinic__name", "Без локації"),
            }
        )


def _avg_headcount(employees, months):
    totals = []
    for (year, month) in months:
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        totals.append(
            sum(
                1
                for e in employees
                if e["hired_on"]
                and e["hired_on"] <= last_day
                and (not e["dismissed_on"] or e["dismissed_on"] > last_day)
            )
        )
    return (sum(totals) / len(totals)) or 1


class TurnoverReportView(APIView):
    """Плинність: звільнення за місяцями (+ накопичено), середня плинність,
    середній стаж тих, хто пішов, розподіл звільнень за підрозділом/локацією."""

    permission_classes = [ConfiguredReadOnlyOrAuthenticated]
    months_window = 13

    def get(self, request):
        months = _recent_months(self.months_window)
        employees = list(Employee.objects.values("hired_on", "dismissed_on"))

        monthly = []
        cumulative = 0
        for (year, month) in months:
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            terminated = sum(
                1 for e in employees if e["dismissed_on"] and first_day <= e["dismissed_on"] <= last_day
            )
            cumulative += terminated
            monthly.append(
                {
                    "month": f"{year}-{month:02d}",
                    "label": f"{UK_MONTHS_SHORT[month - 1]} {str(year)[2:]}",
                    "terminated": terminated,
                    "cumulative": cumulative,
                }
            )

        window_start = date(months[0][0], months[0][1], 1)
        window_end = date(months[-1][0], months[-1][1], calendar.monthrange(months[-1][0], months[-1][1])[1])
        leaver_tenures = [
            (e["dismissed_on"] - e["hired_on"]).days
            for e in employees
            if e["dismissed_on"] and e["hired_on"] and window_start <= e["dismissed_on"] <= window_end
        ]
        total_terminated = sum(row["terminated"] for row in monthly)
        avg_headcount = _avg_headcount(employees, months)
        turnover_pct = round(total_terminated / avg_headcount * 100, 1)
        avg_tenure_months = round((sum(leaver_tenures) / len(leaver_tenures)) / 30.44, 1) if leaver_tenures else 0

        metrics = {
            "turnover_count": total_terminated,
            "turnover_pct": turnover_pct,
            "monthly_pct": round(turnover_pct / self.months_window, 1),
            "avg_tenure_months": avg_tenure_months,
        }

        leavers = Employee.objects.filter(dismissed_on__gte=window_start, dismissed_on__lte=window_end)
        total_leavers = leavers.count() or 1

        def distribution(field_name, fallback):
            rows = leavers.values(field_name).annotate(count=Count("id")).order_by("-count")
            return [
                {
                    "name": row[field_name] or fallback,
                    "count": row["count"],
                    "pct": round(row["count"] / total_leavers * 100, 2),
                }
                for row in rows
            ]

        return Response(
            {
                "monthly": monthly,
                "metrics": metrics,
                "by_department": distribution("department__name", "Без підрозділу"),
                "by_clinic": distribution("clinic__name", "Без локації"),
            }
        )


TENURE_BUCKETS = [
    ("менше ніж 3 місяці", 0, 90),
    ("менше ніж 6 місяців", 90, 182),
    ("менше ніж 1 рік", 182, 365),
    ("1-2 роки", 365, 730),
    ("3-4 роки", 730, 1825),
    ("5-10 років", 1825, 3650),
    ("10+ років", 3650, 10**9),
]


class TenureReportView(APIView):
    """Стаж: розподіл за тривалістю стажу, річниці за місяцями, середній/найдовший
    строк роботи, середній стаж за підрозділом/локацією."""

    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def get(self, request):
        today = date.today()
        active = list(
            Employee.objects.filter(status=Employee.Status.ACTIVE)
            .values("hired_on", "department__name", "clinic__name")
        )

        buckets = [{"label": label, "count": 0} for (label, _lo, _hi) in TENURE_BUCKETS]
        anniversaries = [{"label": UK_MONTHS_FULL[i], "count": 0} for i in range(12)]
        tenures_days = []
        dept_days = {}
        clinic_days = {}

        for e in active:
            if not e["hired_on"]:
                continue
            days = (today - e["hired_on"]).days
            if days < 0:
                continue
            tenures_days.append(days)
            for idx, (_label, lo, hi) in enumerate(TENURE_BUCKETS):
                if lo <= days < hi:
                    buckets[idx]["count"] += 1
                    break
            anniversaries[e["hired_on"].month - 1]["count"] += 1
            dept = e["department__name"] or "Не зазначено"
            clinic = e["clinic__name"] or "Не зазначено"
            dept_days.setdefault(dept, []).append(days)
            clinic_days.setdefault(clinic, []).append(days)

        avg_years = round(sum(tenures_days) / len(tenures_days) / 365.25, 1) if tenures_days else 0

        longest_emp = (
            Employee.objects.filter(status=Employee.Status.ACTIVE, hired_on__isnull=False)
            .order_by("hired_on")
            .first()
        )
        if longest_emp:
            longest = {
                "years": round((today - longest_emp.hired_on).days / 365.25, 1),
                "name": longest_emp.full_name,
            }
        else:
            longest = {"years": 0, "name": ""}

        def avg_table(source):
            rows = [
                {"name": name, "years": round(sum(days) / len(days) / 365.25, 1)}
                for name, days in source.items()
            ]
            return sorted(rows, key=lambda r: r["years"], reverse=True)

        return Response(
            {
                "buckets": buckets,
                "anniversaries": anniversaries,
                "metrics": {"avg_years": avg_years, "longest": longest},
                "by_department": avg_table(dept_days),
                "by_clinic": avg_table(clinic_days),
            }
        )
