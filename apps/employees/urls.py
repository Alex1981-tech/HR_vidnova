from rest_framework.routers import DefaultRouter

from .views import (
    ClinicViewSet,
    DepartmentLevelViewSet,
    DepartmentViewSet,
    DivisionViewSet,
    EmployeeDocumentFolderViewSet,
    EmployeeDocumentViewSet,
    EmployeeViewSet,
    EmploymentTypeViewSet,
    GenderViewSet,
    HolidayPolicyViewSet,
    HolidayViewSet,
    JobLevelViewSet,
    ManagerAssignmentViewSet,
    MedicalSpecialtyViewSet,
    PositionViewSet,
    ProbationPolicyViewSet,
    TeamViewSet,
    TerminationReasonViewSet,
    TerminationTypeViewSet,
    WorkingPatternViewSet,
)

router = DefaultRouter()
router.register("clinics", ClinicViewSet, basename="clinic")
router.register("departments", DepartmentViewSet, basename="department")
router.register("department-levels", DepartmentLevelViewSet, basename="department-level")
router.register("positions", PositionViewSet, basename="position")
router.register("divisions", DivisionViewSet, basename="division")
router.register("employment-types", EmploymentTypeViewSet, basename="employment-type")
router.register("holiday-policies", HolidayPolicyViewSet, basename="holiday-policy")
router.register("holidays", HolidayViewSet, basename="holiday")
router.register("working-patterns", WorkingPatternViewSet, basename="working-pattern")
router.register("probation-policies", ProbationPolicyViewSet, basename="probation-policy")
router.register("job-levels", JobLevelViewSet, basename="job-level")
router.register("genders", GenderViewSet, basename="gender")
router.register("termination-reasons", TerminationReasonViewSet, basename="termination-reason")
router.register("termination-types", TerminationTypeViewSet, basename="termination-type")
router.register("medical-specialties", MedicalSpecialtyViewSet, basename="medical-specialty")
router.register("teams", TeamViewSet, basename="team")
router.register("document-folders", EmployeeDocumentFolderViewSet, basename="employee-document-folder")
router.register("documents", EmployeeDocumentViewSet, basename="employee-document")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("manager-assignments", ManagerAssignmentViewSet, basename="manager-assignment")

urlpatterns = router.urls
