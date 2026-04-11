from flask import Flask, flash, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from recommendations import get_recommendations
from models import db, User

############################################################

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

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

        email_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()
        # validation
        if email_exists:
            return "Email is already in use."
        elif username_exists:
            return "Username is already in use."
        elif password1 != password2:
            return "Passwords don't match!"
        elif len(username) < 2:
            return "Username is too short."
        elif len(password1) < 6:
            return "Password is too short."
        elif len(email) < 4:
            return "Email is not valid."
        else:
            # add user to db
            new_user = User(email=email, username=username)
            new_user.set_password(password1)

            db.session.add(new_user)
            db.session.commit()

            login_user(new_user, remember=True)
            return redirect(url_for('home'))

    return render_template("signup.html", user=current_user)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)