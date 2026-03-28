from flask import Flask, render_template, request, jsonify
import pandas as pd

app = Flask(__name__)

df = pd.read_csv("Most-Recent-Cohorts-Institution.csv", low_memory=False)

columns_needed = [
    "INSTNM",
    "STABBR",
    "CONTROL",
    "ADM_RATE",
    "UGDS",
    "LOCALE",
    "NPT4_PUB",
    "NPT4_PRIV",
    "MD_EARN_WNE_P10",
    "HBCU",
    "PBI",
    "ANNHI",
    "TRIBAL",
    "AANAPII"
]

df = df[columns_needed].copy()

for col in ["ADM_RATE", "UGDS", "LOCALE", "NPT4_PUB", "NPT4_PRIV", "MD_EARN_WNE_P10"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")


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
    # Public = NPT4_PUB, otherwise use NPT4_PRIV
    if row["CONTROL"] == 1:
        return row["NPT4_PUB"]
    return row["NPT4_PRIV"]


df["school_size"] = df["UGDS"].apply(classify_size)
df["locale_label"] = df["LOCALE"].apply(classify_locale)
df["net_price"] = df.apply(get_net_price, axis=1)


def score_school(row, answers):
    score = 0

    priorities = answers.get("priorities", [])
    weights = {
        "cost": 3 if "cost" in priorities else 1,
        "location": 3 if "location" in priorities else 1,
        "salary": 3 if "salary" in priorities else 1,
        "size": 3 if "size" in priorities else 1,
        "major": 3 if "major" in priorities else 1,
    }

    # Budget score
    budget = answers.get("budget")
    if budget and pd.notna(row["net_price"]):
        try:
            budget = float(budget)
            cost_diff = abs(budget - row["net_price"])
            cost_score = max(0, 100 - (cost_diff / 500))
            score += cost_score * weights["cost"]
        except ValueError:
            pass

    # Size score
    size = answers.get("size")
    if size:
        size_map = {
            "small": "Small",
            "medium": "Medium",
            "large": "Large"
        }
        if row["school_size"] == size_map.get(size.lower()):
            score += 100 * weights["size"]

    # Locale score
    locale = answers.get("locale")
    if locale:
        locale_map = {
            "urban": "Urban",
            "suburban": "Suburban",
            "rural": "Rural"
        }
        if row["locale_label"] == locale_map.get(locale.lower()):
            score += 100 * weights["location"]

    # Salary score
    salary_goal = answers.get("salaryGoal")
    if salary_goal and pd.notna(row["MD_EARN_WNE_P10"]):
        try:
            salary_goal = float(salary_goal)
            salary_diff = abs(salary_goal - row["MD_EARN_WNE_P10"])
            salary_score = max(0, 100 - (salary_diff / 1000))
            score += salary_score * weights["salary"]
        except ValueError:
            pass

    # State preference
    location_pref = answers.get("locationPreference")
    if location_pref == "in-state":
        home_state = answers.get("homeState")
        if home_state and row["STABBR"] == home_state:
            score += 100
    elif location_pref == "out-of-state":
        preferred_state = answers.get("preferredStates")
        if preferred_state and row["STABBR"] == preferred_state:
            score += 100

    # Special mission
    special = answers.get("specialMission")
    if special and special != "none" and special in row.index:
        if row[special] == 1:
            score += 100

    # Selectivity
    selectivity = answers.get("selectivity")
    if selectivity and pd.notna(row["ADM_RATE"]):
        admit_pct = row["ADM_RATE"] * 100

        if selectivity == "very selective":
            score += max(0, 100 - admit_pct)
        elif selectivity == "selective":
            score += max(0, 100 - abs(admit_pct - 50))
        elif selectivity == "not selective":
            score += admit_pct

    return score


def get_recommendations(answers, limit=5):
    filtered = df.copy()

    # Remove rows with no school name
    filtered = filtered[filtered["INSTNM"].notna()].copy()

    filtered["match_score"] = filtered.apply(lambda row: score_school(row, answers), axis=1)
    filtered = filtered.sort_values("match_score", ascending=False).head(limit)

    results = []
    for _, row in filtered.iterrows():
        results.append({
            "name": row["INSTNM"],
            "state": row["STABBR"],
            "size": row["school_size"],
            "locale": row["locale_label"],
            "net_price": None if pd.isna(row["net_price"]) else int(row["net_price"]),
            "admission_rate": None if pd.isna(row["ADM_RATE"]) else round(row["ADM_RATE"] * 100, 1),
            "salary": None if pd.isna(row["MD_EARN_WNE_P10"]) else int(row["MD_EARN_WNE_P10"]),
            "match_score": round(row["match_score"], 1)
        })

    return results


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/recommend", methods=["POST"])
def recommend():
    answers = request.get_json()
    recommendations = get_recommendations(answers)
    return jsonify(recommendations)


if __name__ == "__main__":
    app.run(debug=True)