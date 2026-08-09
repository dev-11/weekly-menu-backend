import re

MEAL_TYPES = ["breakfast", "lunch", "dinner"]
SLOT_TYPES = MEAL_TYPES + ["dessert"]
SLOT_LABELS = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "dessert": "Dessert"}
SOURCE_LABELS = {"home": "Home cooked", "ordered": "Ordered", "ateOut": "Eat out"}


class InsightsService:
    def build_report(self, weeks):
        slots = self._filled_slots(weeks)
        stats = self._dish_stats(slots)
        return {
            "favourites": {
                "all": stats[:8],
                "byType": self._dish_stats_by_type(slots),
                "ordered": self._favourites_by_source(stats, "ordered"),
                "ateOut": self._favourites_by_source(stats, "ateOut"),
            },
            "repeatWarnings": self._repeat_warnings(slots),
            "varietyByType": self._variety_by_type(slots),
            "sourceBreakdown": self._source_breakdown(slots),
            "sourceByType": self._source_by_type(slots),
            "typeSourceBreakdown": self._type_source_breakdown(slots),
            "onlyOnce": [{"name": d["name"], "url": d["url"]} for d in stats if d["count"] == 1],
        }

    # Every distinct home-cooked dish across all stored weeks, with how many
    # times it's been made and the most recent date. Unlike the slots used
    # elsewhere in this file, this needs each meal's date (to find the most
    # recent one), so it walks the weeks itself rather than going through
    # _filled_slots.
    def get_recipes(self, weeks):
        entries = []
        for week in weeks:
            days = week.get("days", [])
            for day in days:
                meals = day.get("meals", {})
                for meal_type in MEAL_TYPES:
                    meal = meals.get(meal_type)
                    if meal and meal.get("source", "home") == "home":
                        entries.append((day.get("date"), meal))
            dessert = week.get("weekendDessert")
            if dessert and dessert.get("source", "home") == "home":
                # Not tied to one specific day (shared across the whole
                # weekend) — the last day of the week is a reasonable stand-in
                # so it still contributes sensibly to "last cooked".
                dessert_date = days[-1]["date"] if days else week.get("weekStart")
                entries.append((dessert_date, dessert))

        stats = {}
        for date, meal in entries:
            name = self._dish_name(meal)
            if not name:
                continue
            key = name.lower()
            if key not in stats:
                stats[key] = {"name": name, "url": None, "count": 0, "lastCooked": None}
            if stats[key]["url"] is None:
                stats[key]["url"] = self._dish_url(meal)
            stats[key]["count"] += 1
            if date and (stats[key]["lastCooked"] is None or date > stats[key]["lastCooked"]):
                stats[key]["lastCooked"] = date

        # Most recently cooked first; dishes with no known date (shouldn't
        # happen in practice) sort last rather than crashing the comparison.
        return sorted(stats.values(), key=lambda d: d["lastCooked"] or "", reverse=True)

    @staticmethod
    def _dish_name(meal):
        return (meal.get("title") or meal.get("dish") or "").strip()

    # Mirrors the frontend's isLikelyUrl (utils/week.ts) — the display name
    # above collapses title-or-dish into one string, losing the URL once a
    # title's been resolved, so this is tracked separately alongside it to
    # let a dish stay clickable (linking to the original dish, same as
    # Plan/History) regardless of whether its title ever resolved.
    @staticmethod
    def _dish_url(meal):
        dish = meal.get("dish") or ""
        return dish if re.match(r"^https?://\S+$", dish, re.IGNORECASE) else None

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
                stats[key] = {"name": name, "url": None, "count": 0, "sources": {"home": 0, "ordered": 0, "ateOut": 0}}
            if stats[key]["url"] is None:
                stats[key]["url"] = self._dish_url(meal)
            stats[key]["count"] += 1
            source = meal.get("source", "home")
            if source in stats[key]["sources"]:
                stats[key]["sources"][source] += 1
        return sorted(stats.values(), key=lambda d: (-d["count"], d["name"]))

    def _dish_stats_by_type(self, slots):
        by_type = {}
        for slot_type, meal in slots:
            name = self._dish_name(meal)
            key = name.lower()
            type_stats = by_type.setdefault(slot_type, {})
            if key not in type_stats:
                type_stats[key] = {"name": name, "url": None, "count": 0, "sources": {"home": 0, "ordered": 0, "ateOut": 0}}
            if type_stats[key]["url"] is None:
                type_stats[key]["url"] = self._dish_url(meal)
            type_stats[key]["count"] += 1
            source = meal.get("source", "home")
            if source in type_stats[key]["sources"]:
                type_stats[key]["sources"][source] += 1

        result = {}
        for slot_type in SLOT_TYPES:
            if slot_type not in by_type:
                continue
            stats = sorted(by_type[slot_type].values(), key=lambda d: (-d["count"], d["name"]))
            result[slot_type] = stats[:8]
        return result

    @staticmethod
    def _favourites_by_source(stats, source):
        filtered = [d for d in stats if d["sources"][source] > 0]
        filtered.sort(key=lambda d: (-d["sources"][source], d["name"]))
        return [{"name": d["name"], "url": d["url"], "count": d["sources"][source]} for d in filtered[:8]]

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
            dish_map.setdefault(key, {"name": name, "url": None, "count": 0})
            if dish_map[key]["url"] is None:
                dish_map[key]["url"] = self._dish_url(meal)
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
                        "url": stat["url"],
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

    @staticmethod
    def _source_by_type(slots):
        by_source = {"home": {}, "ordered": {}, "ateOut": {}}
        totals = {"home": 0, "ordered": 0, "ateOut": 0}
        for slot_type, meal in slots:
            source = meal.get("source", "home")
            if source not in by_source:
                continue
            counts = by_source[source]
            counts[slot_type] = counts.get(slot_type, 0) + 1
            totals[source] += 1

        result = {}
        for source, counts in by_source.items():
            total = totals[source]
            breakdown = [
                {
                    "type": slot_type,
                    "label": SLOT_LABELS[slot_type],
                    "count": counts[slot_type],
                    "share": counts[slot_type] / total if total else 0,
                }
                for slot_type in SLOT_TYPES
                if slot_type in counts
            ]
            breakdown.sort(key=lambda b: -b["count"])
            result[source] = breakdown
        return result

    @staticmethod
    def _type_source_breakdown(slots):
        by_type = {}
        totals = {}
        for slot_type, meal in slots:
            source = meal.get("source", "home")
            if source not in SOURCE_LABELS:
                continue
            counts = by_type.setdefault(slot_type, {})
            counts[source] = counts.get(source, 0) + 1
            totals[slot_type] = totals.get(slot_type, 0) + 1

        result = []
        for slot_type in SLOT_TYPES:
            if slot_type not in by_type:
                continue
            total = totals[slot_type]
            counts = by_type[slot_type]
            sources = [
                {
                    "key": source,
                    "label": SOURCE_LABELS[source],
                    "count": counts[source],
                    "share": counts[source] / total if total else 0,
                }
                for source in ("home", "ordered", "ateOut")
                if source in counts
            ]
            sources.sort(key=lambda s: -s["count"])
            result.append({"type": slot_type, "label": SLOT_LABELS[slot_type], "total": total, "sources": sources})
        return result
