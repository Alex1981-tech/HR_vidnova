from django.urls import path

from .peopleforce_compat import (
    PeopleForceCompatEmployeeDetailView,
    PeopleForceCompatEmployeesView,
    PeopleForceCompatTimesheetEntriesBulkView,
    PeopleForceCompatTimesheetEntriesView,
    PeopleForceCompatTimesheetEntryDetailView,
)


employees_view = PeopleForceCompatEmployeesView.as_view()
employee_detail_view = PeopleForceCompatEmployeeDetailView.as_view()
timesheet_entries_view = PeopleForceCompatTimesheetEntriesView.as_view()
timesheet_entry_detail_view = PeopleForceCompatTimesheetEntryDetailView.as_view()
timesheet_entries_bulk_view = PeopleForceCompatTimesheetEntriesBulkView.as_view()


urlpatterns = [
    path("employees", employees_view, name="peopleforce-compat-employees"),
    path("employees/", employees_view, name="peopleforce-compat-employees-slash"),
    path("employees/<str:employee_id>", employee_detail_view, name="peopleforce-compat-employee-detail"),
    path("employees/<str:employee_id>/", employee_detail_view, name="peopleforce-compat-employee-detail-slash"),
    path("time/timesheet_entries", timesheet_entries_view, name="peopleforce-compat-timesheet-entries"),
    path("time/timesheet_entries/", timesheet_entries_view, name="peopleforce-compat-timesheet-entries-slash"),
    path("time/timesheet_entries/bulk", timesheet_entries_bulk_view, name="peopleforce-compat-timesheet-entries-bulk"),
    path("time/timesheet_entries/bulk/", timesheet_entries_bulk_view, name="peopleforce-compat-timesheet-entries-bulk-slash"),
    path("time/timesheet_entries/<int:entry_id>", timesheet_entry_detail_view, name="peopleforce-compat-timesheet-entry-detail"),
    path("time/timesheet_entries/<int:entry_id>/", timesheet_entry_detail_view, name="peopleforce-compat-timesheet-entry-detail-slash"),
]
