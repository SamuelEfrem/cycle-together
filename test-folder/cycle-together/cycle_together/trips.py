from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, make_response
import flask_login
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from . import db, model

bp = Blueprint("trips", __name__, url_prefix="/trips")

UPLOAD_FOLDER = 'cycle_together/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_participant(trip, user):
    for p in trip.participations:
        if p.user_id == user.id:
            return p
    return None

def can_edit_trip(trip, user):
    participation = is_participant(trip, user)
    return participation and participation.can_edit

@bp.route("/browse")
@flask_login.login_required
def browse():
    difficulty = request.args.get('difficulty')
    max_distance = request.args.get('max_distance')
    min_budget = request.args.get('min_budget')
    max_budget = request.args.get('max_budget')
    search = request.args.get('search')
    
    query = db.select(model.TripProposal).where(
        model.TripProposal.status == model.TripStatus.open
    )
    
    if difficulty:
        query = query.where(model.TripProposal.difficulty == model.DifficultyLevel[difficulty])
    if max_distance:
        query = query.where(model.TripProposal.distance_km <= float(max_distance))
    if min_budget:
        query = query.where(model.TripProposal.budget_per_person >= float(min_budget))
    if max_budget:
        query = query.where(model.TripProposal.budget_per_person <= float(max_budget))
    if search:
        search_pattern = f'%{search}%'
        query = query.where(
            db.or_(
                model.TripProposal.title.like(search_pattern),
                model.TripProposal.description.like(search_pattern),
                model.TripProposal.destination.like(search_pattern)
            )
        )
    
    query = query.order_by(model.TripProposal.created_at.desc())
    trips = db.session.execute(query).scalars().all()
    
    return render_template("trips/browse.html", trips=trips)

@bp.route("/my-trips")
@flask_login.login_required
def my_trips():
    participations = flask_login.current_user.participations
    trips = [p.trip for p in participations]
    return render_template("trips/my_trips.html", trips=trips)

@bp.route("/create")
@flask_login.login_required
def create():
    return render_template("trips/create.html")

@bp.route("/create", methods=["POST"])
@flask_login.login_required
def create_post():
    try:
        title = request.form.get("title")
        description = request.form.get("description")
        departure = request.form.get("departure_location")
        destination = request.form.get("destination")
        route = request.form.get("route_description")
        distance = float(request.form.get("distance_km"))
        difficulty = model.DifficultyLevel[request.form.get("difficulty")]
        
        start_min = datetime.strptime(request.form.get("start_date_min"), "%Y-%m-%d").date()
        start_max = datetime.strptime(request.form.get("start_date_max"), "%Y-%m-%d").date()
        duration_min = int(request.form.get("duration_days_min"))
        duration_max = int(request.form.get("duration_days_max"))
        
        budget = float(request.form.get("budget_per_person"))
        max_participants = int(request.form.get("max_participants"))
        
        image_url = None
        if 'trip_image' in request.files:
            file = request.files['trip_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{flask_login.current_user.id}_{datetime.now().timestamp()}_{file.filename}")
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                image_url = f"/static/uploads/{filename}"
        
        trip = model.TripProposal(
            title=title,
            description=description,
            departure_location=departure,
            destination=destination,
            route_description=route,
            distance_km=distance,
            difficulty=difficulty,
            start_date_min=start_min,
            start_date_max=start_max,
            duration_days_min=duration_min,
            duration_days_max=duration_max,
            budget_per_person=budget,
            max_participants=max_participants,
            status=model.TripStatus.open,
            creator_id=flask_login.current_user.id,
            image_url=image_url
        )
        db.session.add(trip)
        db.session.flush()
        
        participation = model.TripParticipation(
            user_id=flask_login.current_user.id,
            trip_id=trip.id,
            can_edit=True
        )
        db.session.add(participation)
        db.session.commit()
        
        flash("Trip created successfully!")
        return redirect(url_for("trips.detail", trip_id=trip.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating trip: {str(e)}")
        return redirect(url_for("trips.create"))

@bp.route("/<int:trip_id>")
@flask_login.login_required
def detail(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip:
        abort(404)
    
    participation = is_participant(trip, flask_login.current_user)
    if not participation:
        flash("You must be a participant to view trip details")
        return redirect(url_for("trips.browse"))
    
    messages = db.session.execute(
        db.select(model.Message)
        .where(model.Message.trip_id == trip_id)
        .order_by(model.Message.created_at.desc())
    ).scalars().all()
    
    meetups = db.session.execute(
        db.select(model.Meetup)
        .where(model.Meetup.trip_id == trip_id)
        .order_by(model.Meetup.meetup_datetime)
    ).scalars().all()
    
    return render_template("trips/detail.html", 
                         trip=trip, 
                         participation=participation,
                         messages=messages,
                         meetups=meetups)

@bp.route("/<int:trip_id>/join", methods=["POST"])
@flask_login.login_required
def join(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip:
        abort(404)
    
    if trip.status != model.TripStatus.open:
        flash("This trip is not accepting new participants")
        return redirect(url_for("trips.browse"))
    
    if is_participant(trip, flask_login.current_user):
        flash("You are already a participant")
        return redirect(url_for("trips.detail", trip_id=trip_id))
    
    if len(trip.participations) >= trip.max_participants:
        flash("Trip is full")
        return redirect(url_for("trips.browse"))
    
    participation = model.TripParticipation(
        user_id=flask_login.current_user.id,
        trip_id=trip_id,
        can_edit=False
    )
    db.session.add(participation)
    db.session.commit()
    
    flash("Successfully joined the trip!")
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/leave", methods=["POST"])
@flask_login.login_required
def leave(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip:
        abort(404)
    
    participation = is_participant(trip, flask_login.current_user)
    if not participation:
        flash("You are not a participant")
        return redirect(url_for("trips.browse"))
    
    if participation.can_edit and trip.status not in [model.TripStatus.finalized, model.TripStatus.cancelled]:
        editors = [p for p in trip.participations if p.can_edit]
        if len(editors) == 1:
            flash("You cannot leave - you are the only editor")
            return redirect(url_for("trips.detail", trip_id=trip_id))
    
    db.session.delete(participation)
    db.session.commit()
    
    flash("You have left the trip")
    return redirect(url_for("trips.browse"))

@bp.route("/<int:trip_id>/edit")
@flask_login.login_required
def edit(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip:
        abort(404)
    
    if not can_edit_trip(trip, flask_login.current_user):
        flash("You don't have permission to edit this trip")
        return redirect(url_for("trips.detail", trip_id=trip_id))
    
    return render_template("trips/edit.html", trip=trip)

@bp.route("/<int:trip_id>/edit", methods=["POST"])
@flask_login.login_required
def edit_post(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip or not can_edit_trip(trip, flask_login.current_user):
        abort(403)
    
    try:
        if not trip.departure_final:
            trip.departure_location = request.form.get("departure_location")
        if not trip.destination_final:
            trip.destination = request.form.get("destination")
        if not trip.route_final:
            trip.route_description = request.form.get("route_description")
        if not trip.dates_final:
            trip.start_date_min = datetime.strptime(request.form.get("start_date_min"), "%Y-%m-%d").date()
            trip.start_date_max = datetime.strptime(request.form.get("start_date_max"), "%Y-%m-%d").date()
            trip.duration_days_min = int(request.form.get("duration_days_min"))
            trip.duration_days_max = int(request.form.get("duration_days_max"))
        if not trip.budget_final:
            trip.budget_per_person = float(request.form.get("budget_per_person"))
        
        trip.title = request.form.get("title")
        trip.description = request.form.get("description")
        trip.distance_km = float(request.form.get("distance_km"))
        trip.difficulty = model.DifficultyLevel[request.form.get("difficulty")]
        
        db.session.commit()
        flash("Trip updated successfully")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating trip: {str(e)}")
    
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/lock-field", methods=["POST"])
@flask_login.login_required
def lock_field(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip or not can_edit_trip(trip, flask_login.current_user):
        abort(403)
    
    field = request.form.get("field")
    
    if field == "departure":
        trip.departure_final = True
    elif field == "destination":
        trip.destination_final = True
    elif field == "dates":
        trip.dates_final = True
    elif field == "route":
        trip.route_final = True
    elif field == "budget":
        trip.budget_final = True
    
    db.session.commit()
    flash(f"{field.capitalize()} marked as final")
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/close", methods=["POST"])
@flask_login.login_required
def close_trip(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip or not can_edit_trip(trip, flask_login.current_user):
        abort(403)
    
    trip.status = model.TripStatus.closed_to_new
    db.session.commit()
    
    flash("Trip closed to new participants")
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/finalize", methods=["POST"])
@flask_login.login_required
def finalize(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip or not can_edit_trip(trip, flask_login.current_user):
        abort(403)
    
    trip.status = model.TripStatus.finalized
    db.session.commit()
    
    flash("Trip finalized!")
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/cancel", methods=["POST"])
@flask_login.login_required
def cancel(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip or not can_edit_trip(trip, flask_login.current_user):
        abort(403)
    
    trip.status = model.TripStatus.cancelled
    db.session.commit()
    
    flash("Trip cancelled")
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/message", methods=["POST"])
@flask_login.login_required
def post_message(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip:
        abort(404)
    
    if not is_participant(trip, flask_login.current_user):
        abort(403)
    
    if trip.status in [model.TripStatus.finalized, model.TripStatus.cancelled]:
        flash("Cannot post to finalized/cancelled trips")
        return redirect(url_for("trips.detail", trip_id=trip_id))
    
    text = request.form.get("text")
    if text:
        message = model.Message(
            text=text,
            author_id=flask_login.current_user.id,
            trip_id=trip_id
        )
        db.session.add(message)
        db.session.commit()
    
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/meetup", methods=["POST"])
@flask_login.login_required
def create_meetup(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip or not can_edit_trip(trip, flask_login.current_user):
        abort(403)
    
    try:
        title = request.form.get("title")
        location = request.form.get("location")
        meetup_date = request.form.get("meetup_date")
        meetup_time = request.form.get("meetup_time")
        description = request.form.get("description")
        
        meetup_datetime = datetime.strptime(f"{meetup_date} {meetup_time}", "%Y-%m-%d %H:%M")
        
        meetup = model.Meetup(
            title=title,
            location=location,
            meetup_datetime=meetup_datetime,
            description=description,
            trip_id=trip_id,
            creator_id=flask_login.current_user.id
        )
        db.session.add(meetup)
        db.session.commit()
        
        flash("Meetup created!")
    except Exception as e:
        flash(f"Error: {str(e)}")
    
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/permissions/<int:user_id>", methods=["POST"])
@flask_login.login_required
def toggle_permissions(trip_id, user_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip:
        abort(404)
    
    # ONLY THE CREATOR CAN MANAGE PERMISSIONS
    if trip.creator_id != flask_login.current_user.id:
        flash("Only the trip creator can manage edit permissions")
        return redirect(url_for("trips.detail", trip_id=trip_id))
    
    # Find participant
    participation = None
    for p in trip.participations:
        if p.user_id == user_id:
            participation = p
            break
    
    if not participation:
        flash("User is not a participant")
        return redirect(url_for("trips.detail", trip_id=trip_id))
    
    # Can't change creator's own permissions
    if user_id == flask_login.current_user.id:
        flash("Cannot change your own permissions")
        return redirect(url_for("trips.detail", trip_id=trip_id))
    
    # TOGGLE PERMISSION
    participation.can_edit = not participation.can_edit
    db.session.commit()
    
    action = "granted" if participation.can_edit else "revoked"
    flash(f"Edit permission {action} for {participation.user.name}")
    return redirect(url_for("trips.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/participants")
@flask_login.login_required
def get_participants(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'count': len(trip.participations),
        'max': trip.max_participants
    })

@bp.route("/<int:trip_id>/messages")
@flask_login.login_required
def get_messages(trip_id):
    trip = db.session.get(model.TripProposal, trip_id)
    if not trip:
        return jsonify({'error': 'Not found'}), 404
    
    if not is_participant(trip, flask_login.current_user):
        return jsonify({'error': 'Not authorized'}), 403
    
    messages = db.session.execute(
        db.select(model.Message)
        .where(model.Message.trip_id == trip_id)
        .order_by(model.Message.created_at.desc())
    ).scalars().all()
    
    messages_data = []
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'text': msg.text,
            'author_name': msg.author.name,
            'author_id': msg.author.id,
            'timestamp': msg.created_at.strftime('%b %d, %Y at %H:%M')
        })
    
    return jsonify({'messages': messages_data})