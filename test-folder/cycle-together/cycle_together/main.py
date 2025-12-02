from flask import Blueprint, render_template, redirect, url_for
import flask_login
from . import model

bp = Blueprint("main", __name__)

@bp.route("/")
def landing():
    if flask_login.current_user.is_authenticated:
        return redirect(url_for("trips.browse"))
    return render_template("landing.html")

@bp.route("/dashboard")
@flask_login.login_required
def dashboard():
    user_trips = flask_login.current_user.participations
    
    total_trips = len(user_trips)
    active_trips = len([p for p in user_trips if p.trip.status in [model.TripStatus.open, model.TripStatus.closed_to_new]])
    finalized_trips = len([p for p in user_trips if p.trip.status == model.TripStatus.finalized])
    total_distance = sum([p.trip.distance_km for p in user_trips]) if user_trips else 0
    created_trips = len(flask_login.current_user.created_trips)
    
    difficulty_stats = {}
    for p in user_trips:
        diff = p.trip.difficulty.name
        difficulty_stats[diff] = difficulty_stats.get(diff, 0) + 1
    
    return render_template("main/dashboard.html",
                         total_trips=total_trips,
                         active_trips=active_trips,
                         finalized_trips=finalized_trips,
                         total_distance=total_distance,
                         created_trips=created_trips,
                         difficulty_stats=difficulty_stats,
                         recent_trips=user_trips[:5])