from app import app, db
from models import User, Profile

fake_people = [
    {
        "email": "advisor1@test.com",
        "username": "MsJohnson",
        "password": "password123",
        "role": "College Application Advisor",
        "full_name": "Maya Johnson",
        "education_level": "Advisor or Recruiter",
        "hometown": "Atlanta, GA",
        "high_school": "",
        "college": "Spelman College",
        "bio": "I help students build strong college lists and polish their essays.",
        "interests": "college essays, HBCUs, scholarships, first-generation students",
        "photo": None
    },
    {
        "email": "careercoach@test.com",
        "username": "CoachTaylor",
        "password": "password123",
        "role": "Career Advisor",
        "full_name": "Jordan Taylor",
        "education_level": "Advisor or Recruiter",
        "hometown": "Chicago, IL",
        "high_school": "",
        "college": "University of Michigan",
        "bio": "I support students interested in business, tech, and internships.",
        "interests": "technology careers, business, resumes, interview prep",
        "photo": None
    },
    {
        "email": "student1@test.com",
        "username": "AriStudent",
        "password": "password123",
        "role": "Prospective Student",
        "full_name": "Ari Brooks",
        "education_level": "In High School",
        "hometown": "Detroit, MI",
        "high_school": "Cass Technical High School",
        "college": "",
        "bio": "Interested in computer science, scholarships, and out-of-state colleges.",
        "interests": "computer science, scholarships, urban campuses, career support",
        "photo": "ari.jpg"
    }
]

with app.app_context():
    db.create_all()

    for person in fake_people:
        user = User.query.filter_by(email=person["email"]).first()

        if not user:
            user = User(
                email=person["email"],
                username=person["username"],
                role=person["role"]
            )
            user.set_password(person["password"])
            db.session.add(user)
            db.session.commit()

        profile = Profile.query.filter_by(user_id=user.id).first()

        if not profile:
            profile = Profile(
                user_id=user.id,
                photo=person["photo"],
                full_name=person["full_name"],
                education_level=person["education_level"],
                hometown=person["hometown"],
                high_school=person["high_school"],
                college=person["college"],
                bio=person["bio"],
                interests=person["interests"]
            )
            db.session.add(profile)

    db.session.commit()
    print("Fake profiles added!")