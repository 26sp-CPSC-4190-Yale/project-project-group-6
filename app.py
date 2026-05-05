import os
import random

from flask import Flask, flash, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from recommendations import get_recommendations_from_classifiers
from models import (
    db, User, Message, Profile, SavedSchool, Scholarship, SavedScholarship,
    Question, Classifier, QuestionClassifier, QuizResponse, QuizAnswer, QuizResult, 
)

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

    # auto-seed quiz questions (skip if alr populated)
    if Question.query.count() == 0:
        from quiz_data import CLASSIFIERS as _CLS, QUESTIONS as _QS
        for name, bidirectional in _CLS:
            if not Classifier.query.filter_by(name=name).first():
                db.session.add(Classifier(name=name, bidirectional=bidirectional))
        db.session.commit()
        _classifier_map = {c.name: c for c in Classifier.query.all()}
        for text, loadings in _QS:
            q = Question(text=text)
            db.session.add(q)
            db.session.flush()
            for clf_name, weight, positive in loadings:
                db.session.add(QuestionClassifier(
                    question_id=q.id,
                    classifier_id=_classifier_map[clf_name].id,
                    weight=weight,
                    positive=positive,
                ))
        db.session.commit()

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
    questions = Question.query.all()
    random.shuffle(questions)
    return render_template("quiz.html", questions=questions)

@app.route("/recommend", methods=["POST"])
@login_required
def recommend():
    data = request.get_json()
    raw_answers = data.get("answers", {})  # {"question_id": answer_int}

    # Accumulate weighted scores per classifier
    classifier_raw = {}
    classifier_max = {}

    for qc in QuestionClassifier.query.all():
        q_id = str(qc.question_id)
        if q_id not in raw_answers:
            continue
        answer = int(raw_answers[q_id])  # 1–5
        name = qc.classifier.name

        if name not in classifier_raw:
            classifier_raw[name] = 0.0
            classifier_max[name] = 0.0

        contribution = (answer - 1) / 4.0 if qc.positive else (5 - answer) / 4.0
        classifier_raw[name] += contribution * qc.weight
        classifier_max[name] += 1.0 * qc.weight

    classifier_scores = {
        name: round(classifier_raw[name] / classifier_max[name], 4)
        for name in classifier_raw
        if classifier_max[name] > 0
    }

    # pull relevant user profile data
    home_state = None
    user_gpa = None
    user_sat = None
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if profile:
        if profile.hometown:
            parts = profile.hometown.rsplit(",", 1)
            if len(parts) == 2:
                home_state = parts[1].strip()[:2].upper()
        user_gpa = profile.gpa
        user_sat = profile.sat_score

    recommendations = get_recommendations_from_classifiers(
        classifier_scores, home_state=home_state, user_gpa=user_gpa, user_sat=user_sat
    )

    # save quiz attempt
    quiz = QuizResponse(user_id=current_user.id)
    db.session.add(quiz)
    db.session.flush()

    for q_id, answer in raw_answers.items():
        db.session.add(QuizAnswer(
            quiz_id=quiz.id,
            question_id=int(q_id),
            answer=int(answer)
        ))

    db.session.add(QuizResult(
        quiz_id=quiz.id,
        classifier_scores=classifier_scores,
        recommendations=recommendations
    ))
    db.session.commit()

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
        gpa_raw = request.form.get("gpa")
        sat_raw = request.form.get("sat_score")
        gpa = float(gpa_raw) if gpa_raw else None
        sat_score = int(sat_raw) if sat_raw else None
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
            existing_profile.gpa = gpa
            existing_profile.sat_score = sat_score
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
                photo=filename,
                gpa=gpa,
                sat_score=sat_score,
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

@app.route("/quiz-history")
@login_required
def quiz_history():
    quizzes = QuizResponse.query.filter_by(user_id=current_user.id)\
        .order_by(QuizResponse.created_at.desc()).all()
    return render_template("quiz_history.html", quizzes=quizzes)

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
    app.run(debug=True, ssl_context="adhoc")