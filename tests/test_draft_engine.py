import unittest

import pandas as pd

from draft_engine import (
    analyze_team,
    find_best_lane_assignment,
    get_unavailable_heroes,
    recommend_bans,
    recommend_next_picks,
)


def build_hero(
    hero,
    role,
    primary_lane,
    secondary_lane,
    true_power_score,
    contest_rate,
    meta_tier,
):
    all_lanes = [lane for lane in [primary_lane, secondary_lane] if lane]
    return {
        "Hero": hero,
        "Role": role,
        "Primary Lane": primary_lane,
        "Secondary Lane": secondary_lane,
        "All Lanes": all_lanes,
        "True Power Score": true_power_score,
        "Contest Rate (%)": contest_rate,
        "Meta Tier": meta_tier,
    }


class DraftEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta_df = pd.DataFrame(
            [
                build_hero("Gloo", "Tank", "EXP Lane", "Roamer", 73.6, 93.13, "S-Tier (Absolute Meta / Must Ban)"),
                build_hero("Diggie", "Support", "Roamer", None, 34.8, 20.05, "A-Tier (Comfort Staple)"),
                build_hero("Claude", "Marksman", "Gold Lane", None, -3.0, 3.09, "C-Tier (Situational / Average)"),
                build_hero("Zhuxin", "Mage", "Mid Lane", None, 24.4, 23.22, "A-Tier (Comfort Staple)"),
                build_hero("Freya", "Fighter", "Jungler", "EXP Lane", 64.2, 82.75, "S-Tier (Absolute Meta / Must Ban)"),
                build_hero("Fanny", "Assassin", "Jungler", None, -24.6, 5.45, "D-Tier (Out of Meta / Weak)"),
                build_hero("Ling", "Assassin", "Jungler", None, -14.6, 0.36, "D-Tier (Out of Meta / Weak)"),
                build_hero("Lolita", "Support", "Roamer", None, 22.4, 0.63, "Hidden OP (The Specialist)"),
                build_hero("Karrie", "Marksman", "Gold Lane", "Jungler", 21.8, 20.78, "A-Tier (Comfort Staple)"),
                build_hero("Akai", "Tank", "Roamer", "Jungler", 5.2, 2.70, "B-Tier (Reliable / Strong)"),
                build_hero("Zhask", "Mage", "Mid Lane", None, -8.4, 0.21, "C-Tier (Situational / Average)"),
            ]
        )

    def heroes(self, *hero_names):
        return (
            self.meta_df[self.meta_df["Hero"].isin(hero_names)]
            .set_index("Hero")
            .reindex(hero_names)
            .reset_index()
        )

    def test_get_unavailable_heroes_combines_locked_and_banned(self):
        team_df = self.heroes("Gloo", "Diggie")
        enemy_df = self.heroes("Claude")

        unavailable = get_unavailable_heroes(team_df, enemy_df, ["Freya", "Zhuxin"])

        self.assertSetEqual(unavailable, {"Gloo", "Diggie", "Claude", "Freya", "Zhuxin"})

    def test_find_best_lane_assignment_covers_all_five_lanes(self):
        team_df = self.heroes("Zhuxin", "Claude", "Gloo", "Freya", "Diggie")

        assignment = find_best_lane_assignment(team_df)

        self.assertEqual(set(assignment.values()), {"Mid Lane", "Gold Lane", "EXP Lane", "Jungler", "Roamer"})
        self.assertEqual(len(assignment), 5)

    def test_analyze_team_flags_lane_collision_when_lanes_cannot_be_filled(self):
        team_df = self.heroes("Claude", "Karrie", "Fanny", "Ling", "Diggie")

        analysis = analyze_team(team_df)
        issue_titles = {issue["title"] for issue in analysis["issues"]}

        self.assertIn("Lane collision detected", issue_titles)

    def test_recommend_next_picks_excludes_locked_and_banned_heroes(self):
        team_df = self.heroes("Gloo", "Diggie")
        enemy_df = self.heroes("Claude", "Zhuxin")
        banned_heroes = ["Freya", "Lolita"]

        recommendations = recommend_next_picks(
            self.meta_df,
            team_df,
            enemy_df,
            banned_heroes=banned_heroes,
            limit=len(self.meta_df),
        )
        recommendation_names = {item["Hero"] for item in recommendations}

        self.assertNotIn("Gloo", recommendation_names)
        self.assertNotIn("Claude", recommendation_names)
        self.assertNotIn("Freya", recommendation_names)
        self.assertNotIn("Lolita", recommendation_names)

    def test_recommend_next_picks_include_enemy_specific_reasoning(self):
        team_df = self.heroes("Gloo", "Diggie")
        enemy_df = self.heroes("Claude", "Zhuxin")

        recommendations = recommend_next_picks(
            self.meta_df,
            team_df,
            enemy_df,
            banned_heroes=[],
            limit=len(self.meta_df),
        )
        freya_recommendation = next(item for item in recommendations if item["Hero"] == "Freya")

        self.assertIn("Claude", freya_recommendation["Summary"])
        self.assertIn("Zhuxin", freya_recommendation["Summary"])
        self.assertTrue(
            any("enemy backliners" in reason.lower() for reason in freya_recommendation["Why"])
        )

    def test_recommend_bans_exclude_banned_heroes_and_reference_enemy_synergy(self):
        team_df = self.heroes("Gloo", "Diggie")
        enemy_df = self.heroes("Fanny", "Ling")
        banned_heroes = ["Freya"]

        recommendations = recommend_bans(
            self.meta_df,
            team_df,
            enemy_df,
            banned_heroes=banned_heroes,
            limit=len(self.meta_df),
        )
        recommendation_names = {item["Hero"] for item in recommendations}

        self.assertNotIn("Freya", recommendation_names)

        unbanned_recommendations = recommend_bans(
            self.meta_df,
            team_df,
            enemy_df,
            banned_heroes=[],
            limit=len(self.meta_df),
        )
        freya_recommendation = next(item for item in unbanned_recommendations if item["Hero"] == "Freya")

        self.assertIn("Fanny", freya_recommendation["Summary"])
        self.assertTrue(
            any("enemy dive" in reason.lower() for reason in freya_recommendation["Why"])
        )

    def test_recommend_next_picks_respects_hero_pool_lock(self):
        team_df = self.heroes("Gloo", "Diggie")
        enemy_df = self.heroes("Claude", "Zhuxin")

        recommendations = recommend_next_picks(
            self.meta_df,
            team_df,
            enemy_df,
            banned_heroes=[],
            limit=10,
            hero_pool=["Freya", "Karrie"],
        )
        recommendation_names = {item["Hero"] for item in recommendations}

        self.assertSetEqual(recommendation_names, {"Freya", "Karrie"})

    def test_pick_order_mode_parameter_is_supported_for_picks_and_bans(self):
        team_df = self.heroes("Gloo", "Diggie")
        enemy_df = self.heroes("Claude", "Zhuxin")

        pick_recommendations = recommend_next_picks(
            self.meta_df,
            team_df,
            enemy_df,
            banned_heroes=[],
            limit=5,
            pick_order_mode="Last Pick",
        )
        ban_recommendations = recommend_bans(
            self.meta_df,
            team_df,
            enemy_df,
            banned_heroes=[],
            limit=5,
            pick_order_mode="Early Priority",
        )

        self.assertTrue(len(pick_recommendations) > 0)
        self.assertTrue(len(ban_recommendations) > 0)


if __name__ == "__main__":
    unittest.main()