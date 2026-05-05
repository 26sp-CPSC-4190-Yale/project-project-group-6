from app import app, db
from models import Scholarship

scholarships = [
    Scholarship(
        name="Coca-Cola Scholars Program",
        amount="$20,000",
        deadline="Fall",
        eligibility="High school seniors with leadership and service experience.",
        category="Leadership",
        major="Any",
        link="https://www.coca-colascholarsfoundation.org/apply/"
    ),
    Scholarship(
        name="The Gates Scholarship",
        amount="Full cost of attendance",
        deadline="Fall",
        eligibility="Pell-eligible high school seniors with strong academic records.",
        category="Need-Based",
        major="Any",
        link="https://www.thegatesscholarship.org/"
    ),
    Scholarship(
        name="Society of Women Engineers Scholarship",
        amount="Varies",
        deadline="Winter/Spring",
        eligibility="Students pursuing engineering or technology-related fields.",
        category="STEM",
        major="Engineering",
        link="https://swe.org/scholarships/"
    )
]

with app.app_context():
    db.create_all()

    for scholarship in scholarships:
        exists = Scholarship.query.filter_by(name=scholarship.name).first()
        if not exists:
            db.session.add(scholarship)

    db.session.commit()
    print("Scholarships added!")