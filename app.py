import os

from flask import Flask, flash, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from recommendations import get_recommendations
from models import db, User, Message, Profile, SavedSchool, Scholarship, SavedScholarship

############################################################

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# init database
db.init_app(app)
with app.app_context():
    db.create_all()

# qssign Login View
login_manager = LoginManager()
# redirect to the login page if authentication fails
login_manager.login_view = "login"
login_manager.init_app(app)

# query user from the database based on user ID
@login_manager.user_loader
def load_user(user_id):
    # Query user from database based on user ID
    return db.session.get(User, int(user_id))


############################################################

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/takequiz")
@login_required
def takequiz():
    return render_template("quiz.html")

@app.route("/recommend", methods=["POST"])
@login_required
def recommend():
    answers = request.get_json()
    recommendations = get_recommendations(answers)
    return jsonify(recommendations)

#apply login functionality
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user:
            if user.check_password(password):
                login_user(user, remember=True)
                return redirect(url_for('home'))
            else:
                return "Incorrect password."
        else:
            return "Email does not exist."
        
    return render_template("login.html", user=current_user)

# register user
@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get("email")
        username = request.form.get("username")
        password1 = request.form.get("password")
        password2 = request.form.get("password2")
        role = request.form.get('role')

        email_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()

        error = None
        # validation
        if email_exists:
            error = "Email is already in use."
        elif username_exists:
            error = "Username is already in use."
        elif password1 != password2:
            error = "Passwords don't match!"
        elif len(username) < 2:
            error = "Username is too short."
        elif len(password1) < 6:
            error = "Password is too short."
        elif len(email) < 4:
            error = "Email is not valid."
        
        if error:
            return render_template(
                "signup.html",
                user=current_user,
                error=error,
                email=email,
                username=username,
                role=role
            )
        
        # add user to db
        new_user = User(email=email, username=username, role=role)
        new_user.set_password(password1)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user, remember=True)
        return redirect(url_for('create_profile'))

    return render_template("signup.html", user=current_user)

@app.route("/create-profile", methods=["GET", "POST"])
@login_required
def create_profile():
    existing_profile = Profile.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        full_name = request.form.get("full_name")
        education_level = request.form.get("education_level")
        hometown = request.form.get("hometown")
        high_school = request.form.get("high_school")
        college = request.form.get("college")
        bio = request.form.get("bio")
        interests = request.form.get("interests")
        file = request.files.get("photo")
        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath) 

        if existing_profile:
            existing_profile.full_name = full_name
            existing_profile.education_level = education_level
            existing_profile.hometown = hometown
            existing_profile.high_school = high_school
            existing_profile.college = college
            existing_profile.bio = bio
            existing_profile.interests = interests
            existing_profile.photo = filename
        else:
            new_profile = Profile(
                user_id=current_user.id,
                full_name=full_name,
                education_level=education_level,
                hometown=hometown,
                high_school=high_school,
                college=college,
                bio=bio,
                interests=interests,
                photo=filename
            )
            db.session.add(new_profile)

        db.session.commit()
        return redirect(url_for("my_profile"))

    return render_template("create_profile.html", profile=existing_profile)

@app.route("/profiles")
@login_required
def profiles():
    all_profiles = Profile.query.filter(Profile.user_id != current_user.id).all()
    return render_template("profiles.html", profiles=all_profiles)

@app.route("/my-profile")
@login_required
def my_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first()

    if not profile:
        return redirect(url_for("create_profile"))

    return render_template("my_profile.html", profile=profile)

@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():

    student_roles = [
        "High School Student",
        "College Student",
        "Prospective Student"
    ]

    advisor_roles = [
        "Career Advisor",
        "College Application Advisor",
        "College Recruiter"
    ]

    if current_user.role in student_roles:
        users = User.query.filter(
            User.id != current_user.id,
            User.role.in_(advisor_roles)
        ).all()
    else:
        users = User.query.filter(
            User.id != current_user.id,
            User.role.in_(student_roles)
        ).all()
     
    users = User.query.filter(User.id != current_user.id).all()

    if request.method == "POST":
        receiver_id = request.form.get("receiver_id")
        body = request.form.get("body")

        if receiver_id and body:
            new_message = Message(
                sender_id=current_user.id,
                receiver_id=receiver_id,
                body=body
            )

            db.session.add(new_message)
            db.session.commit()

            return redirect(url_for("messages"))

    all_messages = Message.query.filter(
        (Message.sender_id == current_user.id) |
        (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()

    return render_template(
        "messages.html",
        users=users,
        messages=all_messages
    )

@app.route("/save-match", methods=["POST"])
@login_required
def save_match():
    data = request.get_json()

    college_name = data.get("college_name")
    website = data.get("website")

    existing = SavedSchool.query.filter_by(
        user_id=current_user.id,
        college_name=college_name
    ).first()

    if not existing:
        match_score = data.get("match_score")

        saved = SavedSchool(
            user_id=current_user.id,
            college_name=college_name,
            website=website,
            match_score=match_score
        )
        db.session.add(saved)
        db.session.commit()

    return jsonify({"status": "success"})

@app.route("/saved-matches")
@login_required
def saved_matches():
    matches = SavedSchool.query.filter_by(user_id=current_user.id).all()
    return render_template("saved_matches.html", matches=matches)

@app.route("/scholarships")
@login_required
def scholarships():
    category = request.args.get("category")
    major = request.args.get("major")

    query = Scholarship.query

    if category:
        query = query.filter_by(category=category)

    if major:
        query = query.filter_by(major=major)

    all_scholarships = query.all()

    return render_template("scholarships.html", scholarships=all_scholarships)

@app.route("/save-scholarship/<int:scholarship_id>", methods=["POST"])
@login_required
def save_scholarship(scholarship_id):
    existing = SavedScholarship.query.filter_by(
        user_id=current_user.id,
        scholarship_id=scholarship_id
    ).first()

    if not existing:
        saved = SavedScholarship(
            user_id=current_user.id,
            scholarship_id=scholarship_id
        )

        db.session.add(saved)
        db.session.commit()

    return redirect(url_for("scholarships"))

@app.route("/saved-scholarships")
@login_required
def saved_scholarships():
    saved = SavedScholarship.query.filter_by(user_id=current_user.id).all()
    return render_template("saved_scholarships.html", saved=saved)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)