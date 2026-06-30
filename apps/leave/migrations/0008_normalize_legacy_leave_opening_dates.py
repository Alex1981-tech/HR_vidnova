from django.db import migrations


def _baseline_on(balance):
    if balance.updated_at:
        return balance.updated_at.date()
    if balance.created_at:
        return balance.created_at.date()
    return balance.effective_on


def forwards(apps, schema_editor):
    LeaveBalance = apps.get_model("leave", "LeaveBalance")
    LeaveLedgerEntry = apps.get_model("leave", "LeaveLedgerEntry")

    entries = LeaveLedgerEntry.objects.filter(
        kind="opening_balance",
        source_model="LeaveBalance",
        idempotency_key__startswith="legacy-balance:",
    )
    for entry in entries.iterator():
        if not entry.source_id:
            continue
        try:
            balance = LeaveBalance.objects.get(pk=entry.source_id)
        except LeaveBalance.DoesNotExist:
            continue
        baseline_on = _baseline_on(balance)
        if not baseline_on:
            continue
        entry.occurred_on = baseline_on
        entry.description = "Поточний баланс з PeopleForce на дату імпорту"
        entry.save(update_fields=["occurred_on", "description"])


def backwards(apps, schema_editor):
    LeaveBalance = apps.get_model("leave", "LeaveBalance")
    LeaveLedgerEntry = apps.get_model("leave", "LeaveLedgerEntry")

    entries = LeaveLedgerEntry.objects.filter(
        kind="opening_balance",
        source_model="LeaveBalance",
        idempotency_key__startswith="legacy-balance:",
    )
    for entry in entries.iterator():
        if not entry.source_id:
            continue
        try:
            balance = LeaveBalance.objects.get(pk=entry.source_id)
        except LeaveBalance.DoesNotExist:
            continue
        if not balance.effective_on:
            continue
        entry.occurred_on = balance.effective_on
        entry.description = "Початковий баланс з PeopleForce"
        entry.save(update_fields=["occurred_on", "description"])


class Migration(migrations.Migration):

    dependencies = [
        ("leave", "0007_backfill_leave_policies_from_legacy_balances"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
