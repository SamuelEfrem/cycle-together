from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import flask_login
from . import db, model

bp = Blueprint("auth", __name__)

@bp.route("/signup")
def signup():
    return render_template("auth/signup.html")

@bp.route("/signup", methods=["POST"])
def signup_post():
    email = request.form.get("email")
    name = request.form.get("name")
    password = request.form.get("password")
    password_repeat = request.form.get("password_repeat")
    bio = request.form.get("bio", "")
    
    if password != password_repeat:
        flash("Passwords don't match")
        return redirect(url_for("auth.signup"))
    
    query = db.select(model.User).where(model.User.email == email)
    user = db.session.execute(query).scalar_one_or_none()
    
    if user:
        flash("Email already registered")
        return redirect(url_for("auth.signup"))
    
    password_hash = generate_password_hash(password)
    new_user = model.User(email=email, name=name, password=password_hash, bio=bio)
    db.session.add(new_user)
    db.session.commit()
    
    flash("Successfully signed up! Please login.")
    return redirect(url_for("auth.login"))

@bp.route("/login")
def login():
    if flask_login.current_user.is_authenticated:
        return redirect(url_for("trips.browse"))
    return render_template("auth/login.html")

@bp.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email")
    password = request.form.get("password")
    
    query = db.select(model.User).where(model.User.email == email)
    user = db.session.execute(query).scalar_one_or_none()
    
    if user and check_password_hash(user.password, password):
        flask_login.login_user(user)
        return redirect(url_for("trips.browse"))
    
    flash("Invalid email or password")
    return redirect(url_for("auth.login"))

@bp.route("/logout")
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for("main.landing"))

@bp.route("/profile")
@flask_login.login_required
def profile():
    return render_template("auth/profile.html", user=flask_login.current_user)

@bp.route("/profile/edit", methods=["POST"])
@flask_login.login_required
def edit_profile():
    name = request.form.get("name")
    bio = request.form.get("bio")
    
    flask_login.current_user.name = name
    flask_login.current_user.bio = bio
    db.session.commit()
    
    flash("Profile updated successfully")
    return redirect(url_for("auth.profile"))

@bp.route("/user/<int:user_id>")
@flask_login.login_required
def view_user(user_id):
    user = db.session.get(model.User, user_id)
    if not user:
        flash("User not found")
        return redirect(url_for("trips.browse"))
    return render_template("auth/profile.html", user=user, view_only=True)