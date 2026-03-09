from collections import Counter

import pandas as pd

REQUIRED_LANES = ["Mid Lane", "Gold Lane", "EXP Lane", "Jungler", "Roamer"]
FRONTLINE_ROLES = {"Tank", "Fighter"}
MAGIC_DAMAGE_HEROES = {
    "Aamon",
    "Alice",
    "Chang'e",
    "Cyclops",
    "Esmeralda",
    "Eudora",
    "Gord",
    "Guinevere",
    "Gusion",
    "Harith",
    "Harley",
    "Joy",
    "Julian",
    "Kadita",
    "Kagura",
    "Karina",
    "Lunox",
    "Luo Yi",
    "Lylia",
    "Novaria",
    "Odette",
    "Pharsa",
    "Selena",
    "Silvanna",
    "Vale",
    "Valentina",
    "Valir",
    "Vexana",
    "Xavier",
    "Yve",
    "Zetian",
    "Zhask",
    "Zhuxin",
}
SCALING_HEROES = {"Harith", "Kimmy", "Natan", "Roger"}


def is_magic_source(hero_name, role_name):
    return role_name == "Mage" or hero_name in MAGIC_DAMAGE_HEROES


def is_scaling_source(hero_name, role_name, lane_options):
    return role_name == "Marksman" or hero_name in SCALING_HEROES or "Gold Lane" in lane_options


def _lane_options(row):
    lanes = []
    for lane_name in row.get("All Lanes", []):
        if lane_name in REQUIRED_LANES and lane_name not in lanes:
            lanes.append(lane_name)
    return lanes


def find_best_lane_assignment(team_df):
    if team_df.empty:
        return {}

    lane_options = {
        row["Hero"]: _lane_options(row)
        for _, row in team_df.iterrows()
    }
    hero_names = sorted(lane_options, key=lambda hero_name: (len(lane_options[hero_name]), hero_name))
    best_assignment = {}

    def backtrack(index, used_lanes, current_assignment):
        nonlocal best_assignment

        if len(current_assignment) > len(best_assignment):
            best_assignment = current_assignment.copy()

        if index >= len(hero_names):
            return

        remaining_heroes = len(hero_names) - index
        if len(current_assignment) + remaining_heroes <= len(best_assignment):
            return

        hero_name = hero_names[index]
        for lane_name in lane_options[hero_name]:
            if lane_name in used_lanes:
                continue

            current_assignment[hero_name] = lane_name
            used_lanes.add(lane_name)
            backtrack(index + 1, used_lanes, current_assignment)
            used_lanes.remove(lane_name)
            del current_assignment[hero_name]

        backtrack(index + 1, used_lanes, current_assignment)

    backtrack(0, set(), {})
    return best_assignment


def _normalize_power_score(value):
    normalized = ((float(value) + 35.0) / 110.0) * 100.0
    return max(0, min(100, round(normalized)))


def _category_score_map(analysis):
    return {category["label"]: category["score"] for category in analysis.get("categories", [])}


def _build_projected_changes(baseline, projected):
    baseline_scores = _category_score_map(baseline)
    projected_scores = _category_score_map(projected)
    changes = []

    for label_name, projected_score in projected_scores.items():
        baseline_score = baseline_scores.get(label_name, 0)
        delta_value = projected_score - baseline_score
        if delta_value == 0:
            continue

        direction = "improves" if delta_value > 0 else "reduces"
        changes.append({
            "label": label_name,
            "delta": delta_value,
            "direction": direction,
            "detail": f"{label_name} {direction} by {abs(delta_value)} points.",
        })

    changes.sort(key=lambda item: abs(item["delta"]), reverse=True)
    return changes


def _format_score_drivers(score_drivers):
    ordered_drivers = sorted(score_drivers.items(), key=lambda item: item[1], reverse=True)
    return [
        {
            "label": label_name,
            "value": round(driver_value, 1),
            "detail": f"{label_name} contributed {driver_value:+.1f}.",
        }
        for label_name, driver_value in ordered_drivers
        if driver_value > 0
    ]


def _summarize_pick_recommendation(hero_name, reasons, projected_changes):
    lead_reason = reasons[0] if reasons else "High raw meta power"
    top_change = projected_changes[0]["detail"] if projected_changes else "Projected team structure stays stable."
    return f"{hero_name} is recommended because it {lead_reason.lower()}. {top_change}"


def _summarize_ban_recommendation(hero_name, reasons, score_drivers):
    lead_reason = reasons[0] if reasons else "High contest and power score"
    top_driver = _format_score_drivers(score_drivers)
    if top_driver:
        return f"{hero_name} is a ban target because of {lead_reason.lower()}. Strongest threat driver: {top_driver[0]['detail']}"
    return f"{hero_name} is a ban target because of {lead_reason.lower()}."


def analyze_team(team_df):
    if team_df.empty:
        return {
            "team_score": 0,
            "frontline_count": 0,
            "magic_sources": 0,
            "marksman_count": 0,
            "lane_assignment": {},
            "missing_lanes": REQUIRED_LANES.copy(),
            "average_power": 0.0,
            "average_contest": 0.0,
            "categories": [],
            "issues": [],
            "summary": "Lock heroes to generate a structured draft report.",
        }

    role_counts = Counter(team_df["Role"].tolist())
    lane_assignment = find_best_lane_assignment(team_df)
    assigned_lanes = set(lane_assignment.values())
    magic_sources = 0
    scaling_sources = 0

    for _, row in team_df.iterrows():
        lane_options = _lane_options(row)
        if is_magic_source(row["Hero"], row["Role"]):
            magic_sources += 1
        if is_scaling_source(row["Hero"], row["Role"], lane_options):
            scaling_sources += 1

    frontline_count = role_counts["Tank"] + role_counts["Fighter"]
    marksman_count = role_counts["Marksman"]
    hero_count = len(team_df)
    average_power = round(float(team_df["True Power Score"].mean()), 1)
    average_contest = round(float(team_df["Contest Rate (%)"].mean()), 2)
    missing_lanes = [lane_name for lane_name in REQUIRED_LANES if lane_name not in assigned_lanes]
    flex_candidates = sum(len(_lane_options(row)) > 1 for _, row in team_df.iterrows())

    lane_score = round((len(assigned_lanes) / len(REQUIRED_LANES)) * 100)
    frontline_score = min(frontline_count * 45, 100)
    if hero_count >= 3 and frontline_count == 0:
        frontline_score = 10

    if 1 <= magic_sources <= 2:
        damage_score = 100
    elif magic_sources in {0, 3}:
        damage_score = 65
    else:
        damage_score = 30

    if marksman_count == 1:
        scaling_score = 100
    elif scaling_sources >= 1:
        scaling_score = 75
    else:
        scaling_score = 35

    flexibility_score = min(100, 40 + (flex_candidates * 20))
    power_score = _normalize_power_score(average_power)

    team_score = round(
        (lane_score * 0.30)
        + (frontline_score * 0.20)
        + (damage_score * 0.20)
        + (scaling_score * 0.15)
        + (flexibility_score * 0.05)
        + (power_score * 0.10)
    )

    categories = [
        {
            "label": "Lane Plan",
            "score": lane_score,
            "detail": f"{len(assigned_lanes)}/5 lanes can be assigned cleanly right now.",
        },
        {
            "label": "Frontline",
            "score": frontline_score,
            "detail": f"{frontline_count} frontline hero(es) locked.",
        },
        {
            "label": "Damage Mix",
            "score": damage_score,
            "detail": f"{magic_sources} reliable magic damage source(s).",
        },
        {
            "label": "Scaling",
            "score": scaling_score,
            "detail": f"{marksman_count} marksman and {scaling_sources} late-game source(s).",
        },
        {
            "label": "Meta Power",
            "score": power_score,
            "detail": f"Average power score: {average_power}.",
        },
    ]

    issues = []
    if hero_count >= 3 and frontline_count == 0:
        issues.append({
            "severity": "error",
            "title": "No frontline",
            "detail": "The draft lacks a tank or fighter anchor and will struggle to start or absorb fights.",
        })

    if hero_count >= 3 and magic_sources == 0:
        issues.append({
            "severity": "warning",
            "title": "All-physical damage profile",
            "detail": "Enemy armor itemization becomes much easier when no reliable magic source is present.",
        })
    elif magic_sources >= 3:
        issues.append({
            "severity": "warning",
            "title": "Overloaded magic damage",
            "detail": "Three or more magic sources can make your damage profile too predictable.",
        })

    if marksman_count > 1:
        issues.append({
            "severity": "warning",
            "title": "Double marksman risk",
            "detail": "Multiple marksmen usually weaken your early map control and frontline durability.",
        })
    elif hero_count == 5 and scaling_sources == 0:
        issues.append({
            "severity": "warning",
            "title": "Weak late-game insurance",
            "detail": "A full draft with no clear late-game carry can stall out on sieges and objectives.",
        })

    if hero_count == 5 and len(lane_assignment) < 5:
        issues.append({
            "severity": "error",
            "title": "Lane collision detected",
            "detail": "The current five-man draft cannot be assigned into all five core lanes cleanly.",
        })
    elif missing_lanes:
        issues.append({
            "severity": "info",
            "title": "Open lanes remain",
            "detail": f"Still uncovered: {', '.join(missing_lanes)}.",
        })

    if not issues and hero_count == 5:
        summary = "Draft is structurally stable across lanes, frontline, damage profile, and scaling."
    else:
        summary = f"Draft score {team_score}/100 with {len(issues)} key issue(s) flagged."

    return {
        "team_score": team_score,
        "frontline_count": frontline_count,
        "magic_sources": magic_sources,
        "marksman_count": marksman_count,
        "lane_assignment": lane_assignment,
        "missing_lanes": missing_lanes,
        "average_power": average_power,
        "average_contest": average_contest,
        "categories": categories,
        "issues": issues,
        "summary": summary,
    }


def recommend_next_picks(meta_df, team_df, enemy_df=None, limit=5):
    enemy_df = enemy_df if enemy_df is not None else meta_df.iloc[0:0]
    baseline = analyze_team(team_df)
    locked_heroes = set(team_df["Hero"].tolist()) | set(enemy_df["Hero"].tolist())
    recommendations = []

    for _, row in meta_df.iterrows():
        hero_name = row["Hero"]
        if hero_name in locked_heroes:
            continue

        candidate_df = meta_df[meta_df["Hero"] == hero_name]
        projected_df = pd.concat([team_df, candidate_df], ignore_index=True)
        projected = analyze_team(projected_df)
        lane_options = _lane_options(row)
        role_name = row["Role"]
        score_drivers = {
            "Projected team upgrade": (projected["team_score"] - baseline["team_score"]) * 1.8,
            "Meta power": float(row["True Power Score"]) * 0.9,
            "Contest leverage": float(row["Contest Rate (%)"]) * 0.15,
        }
        reasons = []

        if any(lane_name in baseline["missing_lanes"] for lane_name in lane_options):
            score_drivers["Lane coverage"] = 18
            reasons.append("Fills an uncovered lane")

        if baseline["frontline_count"] == 0 and role_name in FRONTLINE_ROLES:
            score_drivers["Frontline fix"] = 16
            reasons.append("Adds frontline stability")

        if baseline["magic_sources"] == 0 and is_magic_source(hero_name, role_name):
            score_drivers["Damage rebalance"] = 14
            reasons.append("Restores magic damage")

        if baseline["marksman_count"] == 0 and is_scaling_source(hero_name, role_name, lane_options):
            score_drivers["Scaling insurance"] = 12
            reasons.append("Improves late-game scaling")

        if len(projected["lane_assignment"]) > len(baseline["lane_assignment"]):
            score_drivers["Lane flexibility"] = 10
            reasons.append("Improves lane assignment flexibility")

        if len(lane_options) > 1:
            score_drivers["Flex value"] = 5
            reasons.append("Can flex between lanes")

        if not reasons:
            reasons.append("leans on high raw meta power")

        recommendation_score = sum(score_drivers.values())
        projected_changes = _build_projected_changes(baseline, projected)
        score_breakdown = _format_score_drivers(score_drivers)

        recommendations.append({
            "Hero": hero_name,
            "Role": role_name,
            "Primary Lane": row["Primary Lane"],
            "True Power Score": round(float(row["True Power Score"]), 1),
            "Contest Rate (%)": round(float(row["Contest Rate (%)"]), 2),
            "Recommendation Score": round(recommendation_score, 1),
            "Why": [reason.capitalize() for reason in reasons[:3]],
            "Summary": _summarize_pick_recommendation(hero_name, reasons, projected_changes),
            "Score Drivers": score_breakdown[:4],
            "Projected Changes": projected_changes[:4],
        })

    recommendations.sort(key=lambda item: item["Recommendation Score"], reverse=True)
    return recommendations[:limit]


def recommend_bans(meta_df, team_df, enemy_df=None, limit=5):
    enemy_df = enemy_df if enemy_df is not None else meta_df.iloc[0:0]
    team_analysis = analyze_team(team_df)
    locked_heroes = set(team_df["Hero"].tolist()) | set(enemy_df["Hero"].tolist())
    recommendations = []

    for _, row in meta_df.iterrows():
        hero_name = row["Hero"]
        if hero_name in locked_heroes:
            continue

        role_name = row["Role"]
        lane_options = _lane_options(row)
        score_drivers = {
            "Meta power": float(row["True Power Score"]) * 1.1,
            "Contest pressure": float(row["Contest Rate (%)"]) * 0.65,
        }
        reasons = []

        if str(row["Meta Tier"]).startswith("S-Tier"):
            score_drivers["Tier pressure"] = 12
            reasons.append("s-tier meta pressure")

        if len(lane_options) > 1:
            score_drivers["Flex threat"] = 6
            reasons.append("flexible draft threat")

        if team_analysis["frontline_count"] == 0 and role_name in {"Assassin", "Fighter"} and "Jungler" in lane_options:
            score_drivers["Fragile draft punish"] = 8
            reasons.append("punishes a fragile backline")

        if team_analysis["magic_sources"] == 0 and is_magic_source(hero_name, role_name):
            score_drivers["Mixed damage threat"] = 4
            reasons.append("adds hard-to-match mixed damage")

        if not reasons:
            reasons.append("leans on high contest and power score")

        threat_score = sum(score_drivers.values())
        score_breakdown = _format_score_drivers(score_drivers)

        recommendations.append({
            "Hero": hero_name,
            "Role": role_name,
            "Primary Lane": row["Primary Lane"],
            "True Power Score": round(float(row["True Power Score"]), 1),
            "Contest Rate (%)": round(float(row["Contest Rate (%)"]), 2),
            "Threat Score": round(threat_score, 1),
            "Why": [reason.capitalize() for reason in reasons[:3]],
            "Summary": _summarize_ban_recommendation(hero_name, reasons, score_drivers),
            "Score Drivers": score_breakdown[:4],
            "Projected Changes": [],
        })

    recommendations.sort(key=lambda item: item["Threat Score"], reverse=True)
    return recommendations[:limit]