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
DIVE_HEROES = {
    "Aamon",
    "Arlott",
    "Benedetta",
    "Chou",
    "Dyrroth",
    "Fanny",
    "Freya",
    "Gusion",
    "Guinevere",
    "Hanzo",
    "Hayabusa",
    "Helcurt",
    "Joy",
    "Julian",
    "Karina",
    "Khaleed",
    "Lancelot",
    "Lapu-Lapu",
    "Ling",
    "Natalia",
    "Nolan",
    "Paquito",
    "Phoveus",
    "Saber",
    "Selena",
    "Suyou",
    "Yin",
    "Yu Zhong",
}
PEEL_HEROES = {
    "Akai",
    "Atlas",
    "Baxia",
    "Carmilla",
    "Diggie",
    "Edith",
    "Estes",
    "Floryn",
    "Hylos",
    "Kaja",
    "Khufra",
    "Lolita",
    "Minotaur",
    "Rafaela",
    "Tigreal",
    "Valir",
}
SUSTAIN_DAMAGE_HEROES = {
    "Claude",
    "Hanabi",
    "Ixia",
    "Karrie",
    "Melissa",
    "Moskov",
    "Natan",
    "Roger",
    "Sun",
    "X.Borg",
}
AOE_CONTROL_HEROES = {
    "Akai",
    "Atlas",
    "Aurora",
    "Cecilion",
    "Gord",
    "Khufra",
    "Lolita",
    "Lylia",
    "Minotaur",
    "Odette",
    "Pharsa",
    "Tigreal",
    "Valir",
    "Vexana",
    "Xavier",
    "Yve",
    "Zhuxin",
}
BACKLINE_ROLES = {"Mage", "Marksman", "Support"}
SQUISHY_ROLES = {"Assassin", "Mage", "Marksman", "Support"}
PICK_ORDER_MODES = {
    "Balanced",
    "Early Priority",
    "Mid Draft",
    "Last Pick",
}


def _normalize_pick_order_mode(pick_order_mode):
    if pick_order_mode in PICK_ORDER_MODES:
        return pick_order_mode
    return "Balanced"


def _phase_driver_multiplier(driver_name, pick_order_mode):
    mode = _normalize_pick_order_mode(pick_order_mode)

    if mode == "Early Priority":
        multipliers = {
            "Meta power": 1.2,
            "Contest leverage": 1.3,
            "Contest pressure": 1.2,
            "Tier pressure": 1.25,
            "Flex value": 1.35,
            "Flex threat": 1.25,
            "Lane coverage": 0.75,
            "Frontline fix": 0.85,
            "Damage rebalance": 0.85,
            "Scaling insurance": 0.85,
            "Projected team upgrade": 0.9,
        }
        return multipliers.get(driver_name, 1.0)

    if mode == "Mid Draft":
        return 1.0

    if mode == "Last Pick":
        multipliers = {
            "Meta power": 0.85,
            "Contest leverage": 0.75,
            "Contest pressure": 0.85,
            "Tier pressure": 0.9,
            "Projected team upgrade": 1.25,
            "Lane coverage": 1.3,
            "Frontline fix": 1.35,
            "Damage rebalance": 1.25,
            "Scaling insurance": 1.2,
            "Lane flexibility": 1.25,
            "Flex value": 0.9,
            "Enemy comp fit": 1.2,
            "Dive synergy": 1.25,
            "Comp completion": 1.15,
            "Backline threat": 1.25,
            "Frontline threat": 1.2,
            "Mixed damage threat": 1.15,
            "Anti-dive": 1.2,
            "Melee punish": 1.15,
            "Magic soak": 1.2,
            "Backline punish": 1.2,
            "Frontline shred": 1.2,
        }
        return multipliers.get(driver_name, 1.1)

    return 1.0


def _apply_pick_order_multipliers(score_drivers, pick_order_mode):
    adjusted = {}
    for driver_name, driver_value in score_drivers.items():
        adjusted[driver_name] = driver_value * _phase_driver_multiplier(driver_name, pick_order_mode)
    return adjusted


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


def get_unavailable_heroes(team_df, enemy_df=None, banned_heroes=None):
    unavailable_heroes = set()

    if team_df is not None and not team_df.empty:
        unavailable_heroes.update(team_df["Hero"].dropna().astype(str).tolist())

    if enemy_df is not None and not enemy_df.empty:
        unavailable_heroes.update(enemy_df["Hero"].dropna().astype(str).tolist())

    if banned_heroes:
        unavailable_heroes.update(str(hero_name).strip() for hero_name in banned_heroes if str(hero_name).strip())

    return unavailable_heroes


def _hero_list_text(hero_names, limit=2):
    if not hero_names:
        return ""

    visible_names = hero_names[:limit]
    if len(visible_names) == 1:
        return visible_names[0]

    return ", ".join(visible_names[:-1]) + f" and {visible_names[-1]}"


def is_dive_source(hero_name, role_name, lane_options):
    return hero_name in DIVE_HEROES or role_name == "Assassin" or (role_name == "Fighter" and "Jungler" in lane_options)


def is_peel_source(hero_name, role_name, lane_options):
    return hero_name in PEEL_HEROES or role_name in {"Tank", "Support"} or "Roamer" in lane_options


def is_sustain_damage_source(hero_name, role_name, lane_options):
    return hero_name in SUSTAIN_DAMAGE_HEROES or role_name == "Marksman" or "Gold Lane" in lane_options


def is_aoe_control_source(hero_name, role_name):
    return hero_name in AOE_CONTROL_HEROES or role_name in {"Mage", "Tank", "Support"}


def _build_composition_profile(team_df):
    if team_df.empty:
        return {
            "frontline_heroes": [],
            "backline_heroes": [],
            "squishy_heroes": [],
            "dive_heroes": [],
            "melee_pressure_heroes": [],
            "scaling_heroes": [],
            "magic_heroes": [],
            "lane_heroes": {lane_name: [] for lane_name in REQUIRED_LANES},
        }

    profile = {
        "frontline_heroes": [],
        "backline_heroes": [],
        "squishy_heroes": [],
        "dive_heroes": [],
        "melee_pressure_heroes": [],
        "scaling_heroes": [],
        "magic_heroes": [],
        "lane_heroes": {lane_name: [] for lane_name in REQUIRED_LANES},
    }

    for _, row in team_df.iterrows():
        hero_name = row["Hero"]
        role_name = row["Role"]
        lane_options = _lane_options(row)

        if role_name in FRONTLINE_ROLES:
            profile["frontline_heroes"].append(hero_name)

        if role_name in BACKLINE_ROLES:
            profile["backline_heroes"].append(hero_name)

        if role_name in SQUISHY_ROLES:
            profile["squishy_heroes"].append(hero_name)

        if is_dive_source(hero_name, role_name, lane_options):
            profile["dive_heroes"].append(hero_name)

        if role_name in {"Tank", "Fighter", "Assassin"} or "Roamer" in lane_options or "EXP Lane" in lane_options:
            profile["melee_pressure_heroes"].append(hero_name)

        if is_scaling_source(hero_name, role_name, lane_options):
            profile["scaling_heroes"].append(hero_name)

        if is_magic_source(hero_name, role_name):
            profile["magic_heroes"].append(hero_name)

        for lane_name in lane_options:
            if lane_name in profile["lane_heroes"]:
                profile["lane_heroes"][lane_name].append(hero_name)

    return profile


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


def _sentence_case(text):
    if not text:
        return text
    return text[0].upper() + text[1:]


def _lower_sentence_start(text):
    if not text:
        return text
    return text[0].lower() + text[1:]


def _is_enemy_specific_reason(reason_text):
    lowered_reason = reason_text.lower()
    return "enemy" in lowered_reason or " backline" in lowered_reason or "frontline " in lowered_reason


def _prioritize_reasons(reasons):
    prioritized = []
    seen = set()
    enemy_specific_reason = next((reason for reason in reasons if _is_enemy_specific_reason(reason)), None)

    if enemy_specific_reason:
        prioritized.append(enemy_specific_reason)
        seen.add(enemy_specific_reason)

    for reason in reasons:
        if reason in seen:
            continue
        prioritized.append(reason)
        seen.add(reason)

    return prioritized


def _summarize_pick_recommendation(hero_name, reasons, projected_changes):
    prioritized_reasons = _prioritize_reasons(reasons)
    lead_reason = prioritized_reasons[0] if prioritized_reasons else "High raw meta power"
    top_change = projected_changes[0]["detail"] if projected_changes else "Projected team structure stays stable."
    return f"{hero_name} is recommended because it {_lower_sentence_start(lead_reason)}. {top_change}"


def _summarize_ban_recommendation(hero_name, reasons, score_drivers):
    prioritized_reasons = _prioritize_reasons(reasons)
    lead_reason = prioritized_reasons[0] if prioritized_reasons else "High contest and power score"
    summary_reason = _lower_sentence_start(lead_reason)
    if summary_reason.startswith("would "):
        reason_clause = f"because it {summary_reason}"
    else:
        reason_clause = f"because of {summary_reason}"
    top_driver = _format_score_drivers(score_drivers)
    if top_driver:
        return f"{hero_name} is a ban target {reason_clause}. Strongest threat driver: {top_driver[0]['detail']}"
    return f"{hero_name} is a ban target {reason_clause}."


def _add_enemy_pickup_pressure(score_drivers, reasons, hero_name, role_name, lane_options, enemy_profile):
    enemy_backline = enemy_profile["backline_heroes"]
    enemy_frontline = enemy_profile["frontline_heroes"]
    enemy_dive = enemy_profile["dive_heroes"]
    enemy_melee = enemy_profile["melee_pressure_heroes"]
    enemy_magic = enemy_profile["magic_heroes"]

    if len(enemy_backline) >= 2 and is_dive_source(hero_name, role_name, lane_options):
        target_text = _hero_list_text(enemy_backline)
        score_drivers["Backline punish"] = 11
        reasons.append(f"pressures enemy backliners like {target_text}")

    if len(enemy_frontline) >= 2 and is_sustain_damage_source(hero_name, role_name, lane_options):
        target_text = _hero_list_text(enemy_frontline)
        score_drivers["Frontline shred"] = 10
        reasons.append(f"helps burn through enemy frontline {target_text}")

    if len(enemy_dive) >= 2 and is_peel_source(hero_name, role_name, lane_options):
        target_text = _hero_list_text(enemy_dive)
        score_drivers["Anti-dive"] = 9
        reasons.append(f"stabilizes against dive from {target_text}")

    if len(enemy_melee) >= 3 and is_aoe_control_source(hero_name, role_name):
        target_text = _hero_list_text(enemy_melee)
        score_drivers["Melee punish"] = 7
        reasons.append(f"punishes clustered melee from {target_text}")

    if len(enemy_magic) >= 2 and role_name in FRONTLINE_ROLES and ("Roamer" in lane_options or "EXP Lane" in lane_options):
        target_text = _hero_list_text(enemy_magic)
        score_drivers["Magic soak"] = 5
        reasons.append(f"adds a sturdier front line into enemy magic from {target_text}")


def _add_enemy_ban_pressure(score_drivers, reasons, hero_name, role_name, lane_options, team_profile, enemy_profile):
    enemy_frontline = enemy_profile["frontline_heroes"]
    enemy_backline = enemy_profile["backline_heroes"]
    enemy_dive = enemy_profile["dive_heroes"]
    enemy_scaling = enemy_profile["scaling_heroes"]
    team_backline = team_profile["backline_heroes"]
    team_frontline = team_profile["frontline_heroes"]

    if enemy_frontline and is_sustain_damage_source(hero_name, role_name, lane_options):
        target_text = _hero_list_text(enemy_frontline)
        score_drivers["Enemy comp fit"] = 9
        reasons.append(f"would slot cleanly behind enemy frontline {target_text}")

    if enemy_dive and (is_dive_source(hero_name, role_name, lane_options) or hero_name in {"Angela", "Mathilda", "Floryn"}):
        target_text = _hero_list_text(enemy_dive)
        score_drivers["Dive synergy"] = 8
        reasons.append(f"would amplify enemy dive from {target_text}")

    if enemy_backline and role_name in FRONTLINE_ROLES and ("Roamer" in lane_options or "EXP Lane" in lane_options):
        target_text = _hero_list_text(enemy_backline)
        score_drivers["Comp completion"] = 7
        reasons.append(f"would round out enemy damage cores like {target_text}")

    if team_backline and is_dive_source(hero_name, role_name, lane_options):
        target_text = _hero_list_text(team_backline)
        score_drivers["Backline threat"] = 8
        reasons.append(f"would threaten your backline {target_text}")

    if team_frontline and is_sustain_damage_source(hero_name, role_name, lane_options):
        target_text = _hero_list_text(team_frontline)
        score_drivers["Frontline threat"] = 6
        reasons.append(f"would pressure your frontline {target_text}")

    if enemy_scaling and is_magic_source(hero_name, role_name):
        target_text = _hero_list_text(enemy_scaling)
        score_drivers["Damage diversification"] = 4
        reasons.append(f"would diversify damage around enemy scaling cores {target_text}")


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


def recommend_next_picks(
    meta_df,
    team_df,
    enemy_df=None,
    banned_heroes=None,
    limit=5,
    pick_order_mode="Balanced",
    hero_pool=None,
):
    enemy_df = enemy_df if enemy_df is not None else meta_df.iloc[0:0]
    baseline = analyze_team(team_df)
    enemy_profile = _build_composition_profile(enemy_df)
    locked_heroes = get_unavailable_heroes(team_df, enemy_df, banned_heroes)
    allowed_heroes = None
    if hero_pool:
        allowed_heroes = {str(hero_name).strip() for hero_name in hero_pool if str(hero_name).strip()}
    recommendations = []

    for _, row in meta_df.iterrows():
        hero_name = row["Hero"]
        if hero_name in locked_heroes:
            continue
        if allowed_heroes is not None and hero_name not in allowed_heroes:
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

        _add_enemy_pickup_pressure(score_drivers, reasons, hero_name, role_name, lane_options, enemy_profile)
        score_drivers = _apply_pick_order_multipliers(score_drivers, pick_order_mode)

        if not reasons:
            reasons.append("leans on high raw meta power")

        prioritized_reasons = _prioritize_reasons(reasons)
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
            "Why": [_sentence_case(reason) for reason in prioritized_reasons[:3]],
            "Summary": _summarize_pick_recommendation(hero_name, prioritized_reasons, projected_changes),
            "Score Drivers": score_breakdown[:4],
            "Projected Changes": projected_changes[:4],
        })

    recommendations.sort(key=lambda item: item["Recommendation Score"], reverse=True)
    return recommendations[:limit]


def recommend_bans(
    meta_df,
    team_df,
    enemy_df=None,
    banned_heroes=None,
    limit=5,
    pick_order_mode="Balanced",
):
    enemy_df = enemy_df if enemy_df is not None else meta_df.iloc[0:0]
    team_analysis = analyze_team(team_df)
    team_profile = _build_composition_profile(team_df)
    enemy_profile = _build_composition_profile(enemy_df)
    locked_heroes = get_unavailable_heroes(team_df, enemy_df, banned_heroes)
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

        _add_enemy_ban_pressure(score_drivers, reasons, hero_name, role_name, lane_options, team_profile, enemy_profile)
        score_drivers = _apply_pick_order_multipliers(score_drivers, pick_order_mode)

        if not reasons:
            reasons.append("leans on high contest and power score")

        prioritized_reasons = _prioritize_reasons(reasons)
        threat_score = sum(score_drivers.values())
        score_breakdown = _format_score_drivers(score_drivers)

        recommendations.append({
            "Hero": hero_name,
            "Role": role_name,
            "Primary Lane": row["Primary Lane"],
            "True Power Score": round(float(row["True Power Score"]), 1),
            "Contest Rate (%)": round(float(row["Contest Rate (%)"]), 2),
            "Threat Score": round(threat_score, 1),
            "Why": [_sentence_case(reason) for reason in prioritized_reasons[:3]],
            "Summary": _summarize_ban_recommendation(hero_name, prioritized_reasons, score_drivers),
            "Score Drivers": score_breakdown[:4],
            "Projected Changes": [],
        })

    recommendations.sort(key=lambda item: item["Threat Score"], reverse=True)
    return recommendations[:limit]