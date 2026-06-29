from django.test import TestCase

from apps.knowledge.models import KnowledgeCategory
from apps.knowledge.serializers import KnowledgeCategorySerializer


class KnowledgeCategorySerializerTests(TestCase):
    def test_conditions_write_to_audience_filters_and_clear_direct_ids(self):
        category = KnowledgeCategory.objects.create(
            name="Стара категорія",
            slug="old",
            visibility_mode=KnowledgeCategory.VisibilityMode.SPECIFIC,
            audience_employee_ids=[10, 11],
        )
        payload = {
            "name": category.name,
            "visibility_mode": KnowledgeCategory.VisibilityMode.SPECIFIC,
            "conditions": [{"field": "department", "operator": "is", "value": ["5"]}],
        }

        serializer = KnowledgeCategorySerializer(category, data=payload, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.audience_employee_ids, [])
        self.assertEqual(
            updated.audience_filters,
            {
                "employee_status": "active",
                "conditions": [{"field": "department", "operator": "is", "value": [5]}],
            },
        )

    def test_representation_maps_legacy_direct_ids_to_employee_condition(self):
        category = KnowledgeCategory.objects.create(
            name="За списком",
            slug="direct-list",
            visibility_mode=KnowledgeCategory.VisibilityMode.SPECIFIC,
            audience_employee_ids=[20, 21],
        )

        data = KnowledgeCategorySerializer(category).data

        self.assertEqual(
            data["conditions"],
            [{"field": "employee", "operator": "is", "value": [20, 21]}],
        )
