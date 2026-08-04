import unittest

from services.insights_service import InsightsService


def _meal(dish, source="home", title=None):
    meal = {"dish": dish, "source": source}
    if title:
        meal["title"] = title
    return meal


def _week(week_start, dinners, dessert=None):
    return {
        "weekStart": week_start,
        "days": [
            {"date": f"{week_start}-day{i}", "meals": {"breakfast": _meal(""), "lunch": _meal(""), "dinner": dinner}}
            for i, dinner in enumerate(dinners)
        ],
        "weekendDessert": dessert or _meal(""),
    }


class TestInsightsService(unittest.TestCase):
    def setUp(self):
        self.service = InsightsService()

    def test_most_cooked_counts_and_sorts(self):
        weeks = [_week("2026-01-05", [_meal("Cold Plate"), _meal("Cold Plate"), _meal("Tacos")])]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["mostCooked"][0],
            {"name": "Cold Plate", "count": 2, "sources": {"home": 2, "ordered": 0, "ateOut": 0}},
        )

    def test_dish_name_prefers_resolved_title_over_raw_url(self):
        weeks = [_week("2026-01-05", [
            _meal("https://cooking.nytimes.com/recipes/1", title="Sheet-Pan Feta"),
            _meal("https://cooking.nytimes.com/recipes/1", title="Sheet-Pan Feta"),
        ])]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["mostCooked"][0],
            {"name": "Sheet-Pan Feta", "count": 2, "sources": {"home": 2, "ordered": 0, "ateOut": 0}},
        )

    def test_most_cooked_tracks_source_breakdown(self):
        weeks = [_week("2026-01-05", [
            _meal("Pizza", source="ordered"),
            _meal("Pizza", source="ordered"),
            _meal("Pizza", source="home"),
        ])]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["mostCooked"][0],
            {"name": "Pizza", "count": 3, "sources": {"home": 1, "ordered": 2, "ateOut": 0}},
        )

    def test_empty_and_blank_dishes_are_excluded(self):
        weeks = [_week("2026-01-05", [_meal(""), _meal("   ")])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["mostCooked"], [])
        self.assertEqual(report["sourceBreakdown"], {"home": 0, "ordered": 0, "ateOut": 0, "total": 0})

    def test_only_once_lists_dishes_cooked_exactly_once(self):
        weeks = [_week("2026-01-05", [_meal("Cold Plate"), _meal("Cold Plate"), _meal("Tacos")])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["onlyOnce"], [{"name": "Tacos"}])

    def test_repeat_warning_needs_three_occurrences_and_quarter_share(self):
        weeks = [_week("2026-01-05", [_meal("Cold Plate")] * 3 + [_meal(f"Other {i}") for i in range(9)])]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["repeatWarnings"],
            [{"label": "Dinner", "name": "Cold Plate", "count": 3, "total": 12, "share": 0.25}],
        )

    def test_repeat_warning_excludes_dishes_below_threshold(self):
        weeks = [_week("2026-01-05", [_meal("Cold Plate"), _meal("Cold Plate"), _meal("Tacos")])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["repeatWarnings"], [])

    def test_variety_by_type_counts_unique_vs_total(self):
        weeks = [_week("2026-01-05", [_meal("Cold Plate"), _meal("Cold Plate"), _meal("Tacos")])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["varietyByType"], [{"type": "dinner", "label": "Dinner", "unique": 2, "total": 3}])

    def test_source_breakdown_counts_each_source(self):
        weeks = [_week("2026-01-05", [
            _meal("Cold Plate", source="home"),
            _meal("Pizza", source="ordered"),
            _meal("Diner", source="ateOut"),
        ])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["sourceBreakdown"], {"home": 1, "ordered": 1, "ateOut": 1, "total": 3})

    def test_dessert_slot_included(self):
        weeks = [_week("2026-01-05", [], dessert=_meal("Pie"))]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["mostCooked"],
            [{"name": "Pie", "count": 1, "sources": {"home": 1, "ordered": 0, "ateOut": 0}}],
        )
        self.assertEqual(report["varietyByType"], [{"type": "dessert", "label": "Dessert", "unique": 1, "total": 1}])


if __name__ == "__main__":
    unittest.main()
