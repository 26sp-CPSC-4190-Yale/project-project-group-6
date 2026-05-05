# (name, bidirectional)
# bidirectional=True  → alignment formula: rewards schools that match the user's level
#                        e.g. stimulation_tolerance=0.8 rewards large campuses,
#                             stimulation_tolerance=0.2 rewards small ones
# bidirectional=False → direct formula: higher classifier score rewards more of the feature
#                        e.g. cost_sensitivity=0.9 strongly rewards cheap schools;
#                             cost_sensitivity=0.1 contributes almost nothing
CLASSIFIERS = [
    ("stimulation_tolerance", True),
    ("urban_pull",            True),
    ("novelty_seeking",       True),
    ("nature_pull",           True),
    ("climate_tolerance",     True),
    ("prestige_orientation",  True),
    ("ceiling_seeking",       False),
    ("cost_sensitivity",      False),
    ("roi_orientation",       False),
    ("community_focus",       False),
]

QUESTIONS = [
    (
        "When a lot is going on around me, I find it hard to focus.",
        [("stimulation_tolerance", 2, False)],
    ),
    (
        "I get restless when my surroundings feel too quiet or slow.",
        [("stimulation_tolerance", 2, True), ("urban_pull", 1, True)],
    ),
    (
        "I like walking into a room where nobody knows who I am.",
        [("novelty_seeking", 2, True)],
    ),
    (
        "I feel most at home in places that feel familiar and known.",
        [("novelty_seeking", 2, False)],
    ),
    (
        "I like knowing everything I need is within walking distance.",
        [("urban_pull", 2, True)],
    ),
    (
        "On a free weekend, I'd want the option to leave campus and find something to do.",
        [("urban_pull", 2, True)],
    ),
    (
        "Access to green space and the outdoors is something I'd notice if it were missing.",
        [("nature_pull", 2, True)],
    ),
    (
        "I would be okay living somewhere with long, cold winters.",
        [("climate_tolerance", 1, True)],
    ),
    (
        "I'd rather have a degree that opens doors before I walk in the room.",
        [("prestige_orientation", 3, True)],
    ),
    (
        "Where you went to school stops mattering at some point in your career.",
        [("prestige_orientation", 2, False)],
    ),
    (
        "I actively look for situations where I'm not the smartest person in the room.",
        [("ceiling_seeking", 2, True)],
    ),
    (
        "I'd rather fail at something ambitious than succeed at something easy.",
        [("ceiling_seeking", 2, True)],
    ),
    (
        "I care more about the quality of my specific program than the university's overall reputation.",
        [("prestige_orientation", 2, False), ("roi_orientation", 1, True)],
    ),
    (
        "I'm worried that student loan debt will limit my options after graduation.",
        [("cost_sensitivity", 3, True)],
    ),
    (
        "I would choose a less-famous school if it offered me a full scholarship.",
        [("cost_sensitivity", 2, True), ("prestige_orientation", 1, False)],
    ),
    (
        "It's important to me that graduates from my school get good jobs with strong salaries.",
        [("roi_orientation", 3, True)],
    ),
    (
        "I'm comfortable paying more for a school that offers a better experience or network.",
        [("cost_sensitivity", 2, False)],
    ),
    (
        "Being around people who share my cultural background is important to me.",
        [("community_focus", 2, True), ("novelty_seeking", 1, False)],
    ),
]
