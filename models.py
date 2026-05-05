# Migration note — new tables added (pass to db.create_all()):
#   question, classifier, question_classifier, quiz_response, quiz_answer, quiz_result
#
# Existing tables (unchanged):
#   user, profile, message, saved_school, scholarship, saved_scholarship

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    username = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(150))
    role = db.Column(db.String(100))

    quiz_responses = db.relationship("QuizResponse", backref="user", lazy=True)

    def __repr__(self):
        return f'{self.username}'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)

    photo = db.Column(db.String(300))
    full_name = db.Column(db.String(100), nullable=False)
    education_level = db.Column(db.String(100))
    hometown = db.Column(db.String(100))
    high_school = db.Column(db.String(150))
    college = db.Column(db.String(150))
    bio = db.Column(db.Text)
    interests = db.Column(db.Text)
    gpa = db.Column(db.Float)
    sat_score = db.Column(db.Integer)

    user = db.relationship("User", backref="profile")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())

    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="received_messages")


class SavedSchool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    college_name = db.Column(db.String(150), nullable=False)
    match_score = db.Column(db.Integer)
    website = db.Column(db.String(300))


class Scholarship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.String(50))
    deadline = db.Column(db.String(50))
    eligibility = db.Column(db.Text)
    category = db.Column(db.String(100))
    major = db.Column(db.String(100))
    link = db.Column(db.String(300))


class SavedScholarship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    scholarship_id = db.Column(db.Integer, db.ForeignKey("scholarship.id"), nullable=False)

    scholarship = db.relationship("Scholarship")

class Question(db.Model):
    """A single quiz question (1-5 response)."""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)

    classifiers = db.relationship("QuestionClassifier", backref="question", lazy=True)
    answers = db.relationship("QuizAnswer", backref="question", lazy=True)

    def __repr__(self):
        return f'<Question {self.id}: {self.text[:40]}>'


class Classifier(db.Model):
    """Scoring dimension inferred from quiz answers."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # true = rewards schools that *match* the user's level
    # false = rewards schools proportional to the feature value
    bidirectional = db.Column(db.Boolean, nullable=False, default=False)

    questions = db.relationship("QuestionClassifier", backref="classifier", lazy=True)

    def __repr__(self):
        kind = "bidirectional" if self.bidirectional else "unidirectional"
        return f'<Classifier {self.name} ({kind})>'

# many to many
class QuestionClassifier(db.Model):
    """Linking table for questions and classifiers."""
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    classifier_id = db.Column(db.Integer, db.ForeignKey("classifier.id"), nullable=False)
    
    # how strongly quiz answer impacts classifier
    weight = db.Column(db.Float, nullable=False, default=1.0)

    # if true, higher quiz answers increase classifier score
    # if false, higher quiz answers decrease classifier score
    positive = db.Column(db.Boolean, nullable=False, default=True) 

    def __repr__(self):
        direction = "+" if self.positive else "-"
        return f'<QuestionClassifier q={self.question_id} → {self.classifier_id} w={self.weight}{direction}>'

class QuizResponse(db.Model):
    """One quiz attempt by a user."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    # all QuizAnswer rows for this attempt
    answers = db.relationship("QuizAnswer", backref="quiz", lazy=True)
    # associated QuizResult
    result = db.relationship("QuizResult", backref="quiz", uselist=False)

    def __repr__(self):
        return f'<QuizResponse id={self.id} user={self.user_id} at={self.created_at}>'

class QuizAnswer(db.Model):
    """A single answer (1-5) within one quiz attempt."""
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz_response.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    answer = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<QuizAnswer quiz={self.quiz_id} q={self.question_id} val={self.answer}>'


class QuizResult(db.Model):
    """Stores everything computed after a quiz attempt is scored.
    classifier_scores — normalized 0-1 score per classifier
    recommendations — ranked college JSON info returned to the user
    """
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz_response.id"), unique=True, nullable=False)

    classifier_scores = db.Column(db.JSON, nullable=False)
    recommendations = db.Column(db.JSON, nullable=False)

    def __repr__(self):
        return f'<QuizResult quiz={self.quiz_id} classifiers={list(self.classifier_scores.keys()) if self.classifier_scores else []}>'
