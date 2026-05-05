import pandas as pd
from quiz_data import CLASSIFIERS as _CLASSIFIERS

# {classifier_name: bidirectional}, for scoring
CLASSIFIER_TYPES = {name: bidirectional for name, bidirectional in _CLASSIFIERS}

# dataframe stuff
df = pd.read_csv("Most-Recent-Cohorts-Institution.csv", low_memory=False)

columns_needed = [
    "INSTNM",
    "STABBR",
    "CONTROL",
    "REGION",       
    "ADM_RATE",     
    "UGDS",
    "LOCALE",
    "NPT4_PUB",
    "NPT4_PRIV",
    "MD_EARN_WNE_P10",
    "SAT_AVG",       
    "ENDOWBEGIN",   
    "HBCU",
    "PBI",
    "ANNHI",
    "TRIBAL",
    "AANAPII"
]

df = df[columns_needed].copy()

for col in ["ADM_RATE", "UGDS", "LOCALE", "NPT4_PUB", "NPT4_PRIV",
            "MD_EARN_WNE_P10", "REGION", "SAT_AVG", "ENDOWBEGIN"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

############################################################


def classify_size(ugds):
    if pd.isna(ugds):
        return "Unknown"
    if ugds < 5000:
        return "Small"
    elif ugds < 15000:
        return "Medium"
    return "Large"


def classify_locale(locale_code):
    if pd.isna(locale_code):
        return "Unknown"

    locale_code = int(locale_code)

    if locale_code in [11, 12, 13]:
        return "Urban"
    elif locale_code in [21, 22, 23]:
        return "Suburban"
    elif locale_code in [31, 32, 33]:
        return "Town"
    elif locale_code in [41, 42, 43]:
        return "Rural"
    return "Unknown"


def get_net_price(row):
    # public = NPT4_PUB, otherwise use NPT4_PRIV
    if row["CONTROL"] == 1:
        return row["NPT4_PUB"]
    return row["NPT4_PRIV"]


df["school_size"] = df["UGDS"].apply(classify_size)
df["locale_label"] = df["LOCALE"].apply(classify_locale)
df["net_price"] = df.apply(get_net_price, axis=1)

############################################################

def gpa_to_adm_range(gpa):
    """map student GPA to the ADM_RATE range where they're competitive."""
    if gpa >= 3.9:
        return (0.0, 0.15)
    elif gpa >= 3.7:
        return (0.15, 0.35)
    elif gpa >= 3.5:
        return (0.35, 0.55)
    elif gpa >= 3.0:
        return (0.55, 0.75)
    else:
        return (0.75, 1.01)

############################################################
# For nature & climate scoring: 

# how much natural/outdoor access each REGION code implies (0–1)
REGION_NATURE = {
    7: 1.00,  # Rocky Mountains (CO, ID, MT, UT, WY)
    8: 0.85,  # Far West         (AK, CA, HI, NV, OR, WA)
    1: 0.70,  # New England      (CT, ME, MA, NH, RI, VT)
    4: 0.65,  # Plains           (IA, KS, MN, MO, NE, ND, SD)
    3: 0.60,  # Great Lakes      (IL, IN, MI, OH, WI)
    5: 0.55,  # Southeast        (AL, AR, FL, GA, KY, LA, MS, NC, SC, TN, VA, WV)
    6: 0.50,  # Southwest        (AZ, NM, OK, TX)
    2: 0.25,  # Mid East         (DE, DC, MD, NJ, NY, PA)
}

# how cold/snowy winters are per REGION (0=mild, 1=very cold)
REGION_COLD = {
    3: 1.00,  # Great Lakes
    4: 0.95,  # Plains
    1: 0.90,  # New England
    7: 0.80,  # Rocky Mountains
    2: 0.65,  # Mid East
    8: 0.30,  # Far West (mild Pacific coast / HI offset)
    5: 0.20,  # Southeast
    6: 0.15,  # Southwest
}
############################################################
# intermediate step for scoring
def get_school_features(row, home_state=None):
    """Normalize a school row's data columns to 0-1 per classifier.

    Returns {classifier_name: [(feature_norm, weight), ...]}
    A classifier can have multiple (feature, weight) pairs when it's backed
    by more than one column (e.g. prestige_orientation uses ADM_RATE + SAT_AVG
    + ENDOWBEGIN). Each pair is scored independently and summed.
    """
    features = {}
    region = row.get("REGION")

    # UGDS = stim_tol
    size_norm = {"Small": 0.0, "Medium": 0.5, "Large": 1.0}
    if row["school_size"] in size_norm:
        features["stimulation_tolerance"] = [(size_norm[row["school_size"]], 80)]

    # LOCALE = urban_pull
    locale_norm = {"Rural": 0.0, "Town": 0.25, "Suburban": 0.5, "Urban": 1.0}
    if row["locale_label"] in locale_norm:
        features["urban_pull"] = [(locale_norm[row["locale_label"]], 80)]

    # REGION_NATURE & LOCALE = nature_pull
    if pd.notna(region):
        nature_base = REGION_NATURE.get(int(region), 0.5)
        locale_mod = {"Rural": 0.15, "Town": 0.10, "Suburban": 0.0, "Urban": -0.15}
        nature_feature = max(0.0, min(1.0, nature_base + locale_mod.get(row["locale_label"], 0.0)))
        features["nature_pull"] = [(nature_feature, 80)]

    # REGION_COLD = climate_tolerance
    if pd.notna(region):
        features["climate_tolerance"] = [(REGION_COLD.get(int(region), 0.5), 60)]

    # in home state? = novelty_seeking
    if home_state and pd.notna(row["STABBR"]):
        features["novelty_seeking"] = [(0.0 if row["STABBR"] == home_state else 1.0, 60)]

    # ADM_RATE & SAT_AVG & ENDOWBEGIN = prestige_orientation
    prestige_pairs = []
    if pd.notna(row["ADM_RATE"]):
        prestige_pairs.append((1.0 - row["ADM_RATE"], 80))
    if pd.notna(row.get("SAT_AVG")):
        prestige_pairs.append((min((row["SAT_AVG"] - 800) / 800, 1.0), 40))
    if pd.notna(row.get("ENDOWBEGIN")) and row["ENDOWBEGIN"] > 0:
        prestige_pairs.append((min(row["ENDOWBEGIN"] / 5_000_000_000, 1.0), 20))
    if prestige_pairs:
        features["prestige_orientation"] = prestige_pairs

    # ADM_RATE & SAT_AVG = ceiling_seeking
    ceiling_pairs = []
    if pd.notna(row["ADM_RATE"]):
        ceiling_pairs.append((1.0 - row["ADM_RATE"], 60))
    if pd.notna(row.get("SAT_AVG")):
        ceiling_pairs.append((min((row["SAT_AVG"] - 800) / 800, 1.0), 40))
    if ceiling_pairs:
        features["ceiling_seeking"] = ceiling_pairs

    # net_price = cost_sensitivity
    if pd.notna(row["net_price"]) and row["net_price"] > 0:
        features["cost_sensitivity"] = [(1.0 - min(row["net_price"] / 60_000, 1.0), 100)]

    # MD_EARN_WNE_P10 = roi_orientation"
    if pd.notna(row["MD_EARN_WNE_P10"]):
        features["roi_orientation"] = [(min(row["MD_EARN_WNE_P10"] / 100_000, 1.0), 80)]

    # mission flag? = community_focus
    has_mission = any(row.get(flag) == 1 for flag in ["HBCU", "PBI", "ANNHI", "TRIBAL", "AANAPII"])
    features["community_focus"] = [(1.0 if has_mission else 0.0, 80)]

    return features


def score_school_from_classifiers(row, classifier_scores, home_state=None, user_gpa=None, user_sat=None):
    """Scores schools based on their classifiers"""
    score = 0.0
    school_features = get_school_features(row, home_state)

    for clf_name, clf_score in classifier_scores.items():
        if clf_name not in school_features:
            continue
        bidirectional = CLASSIFIER_TYPES.get(clf_name, False)
        for feature_norm, weight in school_features[clf_name]:
            if bidirectional:
                score += (1 - abs(clf_score - feature_norm)) * weight
            else:
                score += feature_norm * clf_score * weight

    # boost score if more realistic choice for user
    if user_gpa and pd.notna(row["ADM_RATE"]):
        adm_min, adm_max = gpa_to_adm_range(user_gpa)
        if adm_min <= row["ADM_RATE"] < adm_max:
            score += 60
        elif row["ADM_RATE"] >= adm_max:
            score += 20

    if user_sat and pd.notna(row.get("SAT_AVG")):
        diff = user_sat - row["SAT_AVG"]
        if -100 <= diff <= 150:
            score += 60
        elif diff > 150:
            score += 20
        elif -200 <= diff < -100:
            score += 20

    return score


def get_match_reasons(row, classifier_scores, home_state=None, user_gpa=None, user_sat=None):
    """return list of short english explanations for recommendation."""
    reasons = []

    st = classifier_scores.get("stimulation_tolerance", 0.5)
    if st > 0.65 and row["school_size"] == "Large":
        reasons.append("Large campus")
    elif st < 0.35 and row["school_size"] == "Small":
        reasons.append("Small campus")

    up = classifier_scores.get("urban_pull", 0.5)
    if up > 0.65 and row["locale_label"] == "Urban":
        reasons.append("Urban setting")
    elif up < 0.35 and row["locale_label"] in ("Rural", "Town"):
        reasons.append("Rural setting")

    np_ = classifier_scores.get("nature_pull", 0.5)
    region = row.get("REGION")
    if np_ > 0.6 and pd.notna(region) and REGION_NATURE.get(int(region), 0) >= 0.65:
        reasons.append("Nature access")

    ct = classifier_scores.get("climate_tolerance", 0.5)
    if pd.notna(region):
        cold = REGION_COLD.get(int(region), 0.5)
        if ct > 0.65 and cold >= 0.75:
            reasons.append("Cold climate")
        elif ct < 0.35 and cold <= 0.25:
            reasons.append("Mild climate")

    po = classifier_scores.get("prestige_orientation", 0.5)
    cs = classifier_scores.get("ceiling_seeking", 0.5)
    if pd.notna(row["ADM_RATE"]):
        if po > 0.65 and row["ADM_RATE"] < 0.25:
            reasons.append("Highly selective")
        elif cs > 0.65 and row["ADM_RATE"] < 0.35:
            reasons.append("Academically competitive")

    cost_s = classifier_scores.get("cost_sensitivity", 0.5)
    if cost_s > 0.65 and pd.notna(row["net_price"]) and row["net_price"] < 20_000:
        reasons.append("Affordable")

    roi = classifier_scores.get("roi_orientation", 0.5)
    if roi > 0.65 and pd.notna(row["MD_EARN_WNE_P10"]) and row["MD_EARN_WNE_P10"] > 55_000:
        reasons.append("Strong graduate earnings")

    cf = classifier_scores.get("community_focus", 0.5)
    if cf > 0.65:
        if any(row.get(flag) == 1 for flag in ["HBCU", "PBI", "ANNHI", "TRIBAL", "AANAPII"]):
            reasons.append("Minority-serving institution")

    ns = classifier_scores.get("novelty_seeking", 0.5)
    if home_state and pd.notna(row["STABBR"]):
        if ns > 0.65 and row["STABBR"] != home_state:
            reasons.append("Out of state")
        elif ns < 0.35 and row["STABBR"] == home_state:
            reasons.append("Close to home")

    if user_gpa and pd.notna(row["ADM_RATE"]):
        adm_min, adm_max = gpa_to_adm_range(user_gpa)
        if adm_min <= row["ADM_RATE"] < adm_max:
            reasons.append("Matches your profile")

    if user_sat and pd.notna(row.get("SAT_AVG")):
        diff = user_sat - row["SAT_AVG"]
        if -100 <= diff <= 150 and "Matches your profile" not in reasons:
            reasons.append("Matches your profile")

    return reasons

# main recommendation engine
def get_recommendations_from_classifiers(classifier_scores, home_state=None, user_gpa=None, user_sat=None, limit=5):
    """Return ranked college recommendations driven by classifier scores & user profile data."""
    filtered = df[df["INSTNM"].notna()].copy()

    filtered["match_score"] = filtered.apply(
        lambda row: score_school_from_classifiers(row, classifier_scores, home_state, user_gpa, user_sat),
        axis=1,
    )
    filtered = filtered.sort_values("match_score", ascending=False).head(limit)

    results = []
    for _, row in filtered.iterrows():
        results.append({
            "name":           row["INSTNM"],
            "state":          row["STABBR"],
            "size":           row["school_size"],
            "locale":         row["locale_label"],
            "net_price":      None if pd.isna(row["net_price"])       else int(row["net_price"]),
            "admission_rate": None if pd.isna(row["ADM_RATE"])        else round(row["ADM_RATE"] * 100, 1),
            "sat_avg":        None if pd.isna(row.get("SAT_AVG"))     else int(row["SAT_AVG"]),
            "salary":         None if pd.isna(row["MD_EARN_WNE_P10"]) else int(row["MD_EARN_WNE_P10"]),
            "match_score":    round(row["match_score"], 1),
            "reasons":        get_match_reasons(row, classifier_scores, home_state, user_gpa, user_sat),
        })

    return results

