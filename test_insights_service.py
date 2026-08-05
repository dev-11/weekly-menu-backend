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
            report["favourites"]["all"][0],
            {"name": "Cold Plate", "count": 2, "sources": {"home": 2, "ordered": 0, "ateOut": 0}},
        )

    def test_dish_name_prefers_resolved_title_over_raw_url(self):
        weeks = [_week("2026-01-05", [
            _meal("https://cooking.nytimes.com/recipes/1", title="Sheet-Pan Feta"),
            _meal("https://cooking.nytimes.com/recipes/1", title="Sheet-Pan Feta"),
        ])]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["favourites"]["all"][0],
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
            report["favourites"]["all"][0],
            {"name": "Pizza", "count": 3, "sources": {"home": 1, "ordered": 2, "ateOut": 0}},
        )

    def test_empty_and_blank_dishes_are_excluded(self):
        weeks = [_week("2026-01-05", [_meal(""), _meal("   ")])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["favourites"]["all"], [])
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

    def test_source_by_type_breaks_down_each_source_by_meal_type(self):
        weeks = [{
            "weekStart": "2026-01-05",
            "days": [
                {"date": "d0", "meals": {
                    "breakfast": _meal(""),
                    "lunch": _meal("Pizza", source="ordered"),
                    "dinner": _meal("Curry", source="ordered"),
                }},
                {"date": "d1", "meals": {
                    "breakfast": _meal(""),
                    "lunch": _meal("Pizza", source="ordered"),
                    "dinner": _meal("Diner", source="ateOut"),
                }},
            ],
            "weekendDessert": _meal(""),
        }]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["sourceByType"]["ordered"],
            [
                {"type": "lunch", "label": "Lunch", "count": 2, "share": 2 / 3},
                {"type": "dinner", "label": "Dinner", "count": 1, "share": 1 / 3},
            ],
        )
        self.assertEqual(
            report["sourceByType"]["ateOut"],
            [{"type": "dinner", "label": "Dinner", "count": 1, "share": 1.0}],
        )

    def test_source_by_type_empty_for_unused_source(self):
        weeks = [_week("2026-01-05", [_meal("Cold Plate")])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["sourceByType"]["ordered"], [])
        self.assertEqual(report["sourceByType"]["ateOut"], [])

    def test_type_source_breakdown_splits_each_meal_type_by_source(self):
        weeks = [{
            "weekStart": "2026-01-05",
            "days": [
                {"date": "d0", "meals": {
                    "breakfast": _meal(""),
                    "lunch": _meal("Pizza", source="ordered"),
                    "dinner": _meal("Cold Plate", source="home"),
                }},
                {"date": "d1", "meals": {
                    "breakfast": _meal(""),
                    "lunch": _meal("Diner", source="ateOut"),
                    "dinner": _meal("Cold Plate", source="home"),
                }},
            ],
            "weekendDessert": _meal(""),
        }]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["typeSourceBreakdown"],
            [
                {
                    "type": "lunch",
                    "label": "Lunch",
                    "total": 2,
                    "sources": [
                        {"key": "ordered", "label": "Ordered", "count": 1, "share": 0.5},
                        {"key": "ateOut", "label": "Eat out", "count": 1, "share": 0.5},
                    ],
                },
                {
                    "type": "dinner",
                    "label": "Dinner",
                    "total": 2,
                    "sources": [{"key": "home", "label": "Home cooked", "count": 2, "share": 1.0}],
                },
            ],
        )

    def test_type_source_breakdown_excludes_types_with_no_filled_slots(self):
        weeks = [_week("2026-01-05", [_meal("Cold Plate")])]

        report = self.service.build_report(weeks)

        types = [t["type"] for t in report["typeSourceBreakdown"]]
        self.assertEqual(types, ["dinner"])

    def test_dessert_slot_included(self):
        weeks = [_week("2026-01-05", [], dessert=_meal("Pie"))]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["favourites"]["all"],
            [{"name": "Pie", "count": 1, "sources": {"home": 1, "ordered": 0, "ateOut": 0}}],
        )
        self.assertEqual(report["varietyByType"], [{"type": "dessert", "label": "Dessert", "unique": 1, "total": 1}])

    def test_favourites_by_type_ranks_dishes_within_each_meal_type(self):
        weeks = [{
            "weekStart": "2026-01-05",
            "days": [
                {"date": "d0", "meals": {
                    "breakfast": _meal("Yoghurt", source="home"),
                    "lunch": _meal("Pizza", source="ordered"),
                    "dinner": _meal("Cold Plate", source="home"),
                }},
                {"date": "d1", "meals": {
                    "breakfast": _meal("Yoghurt", source="home"),
                    "lunch": _meal("Salad", source="home"),
                    "dinner": _meal("Cold Plate", source="home"),
                }},
            ],
            "weekendDessert": _meal(""),
        }]

        report = self.service.build_report(weeks)

        self.assertEqual(
            report["favourites"]["byType"]["breakfast"],
            [{"name": "Yoghurt", "count": 2, "sources": {"home": 2, "ordered": 0, "ateOut": 0}}],
        )
        self.assertEqual(
            report["favourites"]["byType"]["lunch"],
            [
                {"name": "Pizza", "count": 1, "sources": {"home": 0, "ordered": 1, "ateOut": 0}},
                {"name": "Salad", "count": 1, "sources": {"home": 1, "ordered": 0, "ateOut": 0}},
            ],
        )
        self.assertEqual(
            report["favourites"]["byType"]["dinner"],
            [{"name": "Cold Plate", "count": 2, "sources": {"home": 2, "ordered": 0, "ateOut": 0}}],
        )
        self.assertNotIn("dessert", report["favourites"]["byType"])

    def test_favourites_ordered_and_ateout_rank_by_that_sources_count(self):
        weeks = [_week("2026-01-05", [
            _meal("Pizza", source="ordered"),
            _meal("Pizza", source="ordered"),
            _meal("Diner", source="ateOut"),
            _meal("Cold Plate", source="home"),
        ])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["favourites"]["ordered"], [{"name": "Pizza", "count": 2}])
        self.assertEqual(report["favourites"]["ateOut"], [{"name": "Diner", "count": 1}])

    def test_favourites_ordered_excludes_dishes_never_ordered(self):
        weeks = [_week("2026-01-05", [_meal("Cold Plate", source="home")])]

        report = self.service.build_report(weeks)

        self.assertEqual(report["favourites"]["ordered"], [])
        self.assertEqual(report["favourites"]["ateOut"], [])


if __name__ == "__main__":
    unittest.main()
