from django.core.management.base import BaseCommand
from apps.students.models import Student
from apps.students.services import _normalize_phone


class Command(BaseCommand):
    help = "Delete all students except the provided keep list (phones)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-phones",
            dest="keep_phones",
            help="Comma-separated list of phone numbers to keep (optional)",
            default=None,
        )

    def handle(self, *args, **options):
        default_keep = [
            "0953 457 532",
            "0911 223 344",
        ]
        raw = options.get("keep_phones")
        if raw:
            keeps = [p.strip() for p in raw.split(",") if p.strip()]
        else:
            keeps = default_keep

        normalized_keep = set(_normalize_phone(p) for p in keeps if p)

        to_delete = []
        for s in Student.objects.only("id", "phone", "name").iterator():
            if _normalize_phone(s.phone) not in normalized_keep:
                to_delete.append(s.id)

        if not to_delete:
            self.stdout.write(self.style.SUCCESS("No students to delete."))
            return

        deleted_count, _ = Student.objects.filter(id__in=to_delete).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} student records."))
