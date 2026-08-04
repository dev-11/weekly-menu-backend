MEAL_TYPES = ["breakfast", "lunch", "dinner"]
SLOT_TYPES = MEAL_TYPES + ["dessert"]
SLOT_LABELS = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "dessert": "Dessert"}


class InsightsService:
    def build_report(self, weeks):
        slots = self._filled_slots(weeks)
        stats = self._dish_stats(slots)
        return {
            "mostCooked": stats[:8],
            "repeatWarnings": self._repeat_warnings(slots),
            "varietyByType": self._variety_by_type(slots),
            "sourceBreakdown": self._source_breakdown(slots),
            "onlyOnce": [{"name": d["name"]} for d in stats if d["count"] == 1],
        }

    @staticmethod
    def _dish_name(meal):
        return (meal.get("title") or meal.get("dish") or "").strip()

    def _filled_slots(self, weeks):
        slots = []
        for week in weeks:
            for day in week.get("days", []):
                meals = day.get("meals", {})
                for meal_type in MEAL_TYPES:
                    meal = meals.get(meal_type)
                    if meal:
                        slots.append((meal_type, meal))
            dessert = week.get("weekendDessert")
            if dessert:
                slots.append(("dessert", dessert))
        return [(slot_type, meal) for slot_type, meal in slots if self._dish_name(meal)]

    def _dish_stats(self, slots):
        stats = {}
        for _, meal in slots:
            name = self._dish_name(meal)
            key = name.lower()
            if key not in stats:
                stats[key] = {"name": name, "count": 0, "sources": {"home": 0, "ordered": 0, "ateOut": 0}}
            stats[key]["count"] += 1
            source = meal.get("source", "home")
            if source in stats[key]["sources"]:
                stats[key]["sources"][source] += 1
        return sorted(stats.values(), key=lambda d: (-d["count"], d["name"]))

    def _variety_by_type(self, slots):
        by_type = {}
        for slot_type, meal in slots:
            entry = by_type.setdefault(slot_type, {"unique": set(), "total": 0})
            entry["unique"].add(self._dish_name(meal).lower())
            entry["total"] += 1
        return [
            {
                "type": slot_type,
                "label": SLOT_LABELS[slot_type],
                "unique": len(by_type[slot_type]["unique"]),
                "total": by_type[slot_type]["total"],
            }
            for slot_type in SLOT_TYPES
            if slot_type in by_type
        ]

    def _repeat_warnings(self, slots):
        by_type = {}
        totals = {}
        for slot_type, meal in slots:
            name = self._dish_name(meal)
            key = name.lower()
            dish_map = by_type.setdefault(slot_type, {})
            dish_map.setdefault(key, {"name": name, "count": 0})
            dish_map[key]["count"] += 1
            totals[slot_type] = totals.get(slot_type, 0) + 1

        warnings = []
        for slot_type, dish_map in by_type.items():
            total = totals[slot_type]
            for stat in dish_map.values():
                share = stat["count"] / total
                if stat["count"] >= 3 and share >= 0.25:
                    warnings.append({
                        "label": SLOT_LABELS[slot_type],
                        "name": stat["name"],
                        "count": stat["count"],
                        "total": total,
                        "share": share,
                    })
        warnings.sort(key=lambda w: -w["share"])
        return warnings

    @staticmethod
    def _source_breakdown(slots):
        counts = {"home": 0, "ordered": 0, "ateOut": 0}
        for _, meal in slots:
            source = meal.get("source", "home")
            if source in counts:
                counts[source] += 1
        counts["total"] = len(slots)
        return counts
