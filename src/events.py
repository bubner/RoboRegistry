"""
    Event creation and management functionality for RoboRegistry
    @author: Lucas Bubner, 2023
"""
from flask import Blueprint, render_template, request, session, redirect, abort, send_file
from wrappers import login_required, must_be_event_owner
from random import randint
from pytz import all_timezones, timezone
from datetime import datetime
from re import sub
from qr_gen import generate_qrcode
from os import getenv

import db
import utils

events_bp = Blueprint("events", __name__, template_folder="templates")


@events_bp.route("/events/view")
@login_required
def viewall():
    """
        View all personally affiliated events.
    """
    registered_events, created_events = db.get_my_events()
    return render_template("dash/view.html.jinja", created_events=created_events, registered_events=registered_events, user=db.get_user_data())


@events_bp.route("/events/view/<string:uid>")
@login_required
def viewevent(uid: str):
    """
        View a specific user-owned event.
    """
    data = db.get_event(uid)
    if not data:
        abort(404)

    registered = owned = False
    for key, value in data["registered"].items():
        if value == "owner" and key == session["uid"]:
            owned = True
            break
        elif key == uid:
            registered = True
            break

    # Calculate time to event
    start_time = datetime.strptime(
        f"{data['date']} {data['start_time']}", "%Y-%m-%d %H:%M")
    end_time = datetime.strptime(
        f"{data['date']} {data['end_time']}", "%Y-%m-%d %H:%M")

    days, hours, minutes = utils.get_time_diff(datetime.now(), start_time)
    time_to_end = utils.get_time_diff(datetime.now(), end_time)

    if days > 0:
        time = ""
        if days >= 7:
            time += f"{days // 7} week(s) "
        time += f"{days % 7} day(s) {hours} hour(s)"
    elif hours > 0:
        time = f"{hours} hour(s) {minutes} minute(s)"
    elif minutes > 0:
        time = f"{minutes} minute(s)"
    elif time_to_end[1] > 0:
        time = f"Ends in {time_to_end[1]} hours {time_to_end[2]} minute(s)"
    elif time_to_end[2] > 0:
        time = f"Ends in {time_to_end[2]} minute(s)"
    else:
        time = "Event has ended."

    can_register = time.startswith("Ends") or time.startswith("Event")
    tz = timezone(data["timezone"])
    offset = tz.utcoffset(datetime.now()).total_seconds() / 3600

    if not data:
        abort(409)

    return render_template("event/event.html.jinja", user=db.get_user_data(), event=data, registered=registered, owned=owned, mapbox_api_key=getenv("MAPBOX_API_KEY"), time=time, can_register=can_register, timezone=tz, offset=offset)


@events_bp.route("/events/create", methods=["GET", "POST"])
@login_required
def create():
    """
        Create a new event on the system.
    """
    user = db.get_user_data()
    mapbox_api_key = getenv("MAPBOX_API_KEY")
    if request.method == "POST":
        if not (name := request.form.get("event_name")):
            return render_template("event/create.html.jinja", error="Please enter an event name.", user=user, mapbox_api_key=mapbox_api_key)
        if not (date := request.form.get("event_date")):
            return render_template("event/create.html.jinja", error="Please enter an event date.", user=user, mapbox_api_key=mapbox_api_key)

        if len(name) > 16:
            return render_template("event/create.html.jinja", error="Event name can only be 16 characters.", user=user, mapbox_api_key=mapbox_api_key)

        # Sanitise the name by removing everything that isn't alphanumeric and space
        # If the string is completely empty, return an error
        name = sub(r'[^a-zA-Z0-9 ]+', '', name)
        if not name:
            return render_template("event/create.html.jinja", error="Please enter a valid event name.", user=user, mapbox_api_key=mapbox_api_key)

        # Generate an event UID
        event_uid = sub(r'[^a-zA-Z0-9]+', '-', name.lower()
                        ) + "-" + date.replace("-", "")
        if db.get_event(event_uid):
            return render_template("event/create.html.jinja", error="An event with that name and date already exists.", user=user, mapbox_api_key=mapbox_api_key)

        # Create the event and generate a UID
        event = {
            "name": name,
            # UIDs are in the form of <event name seperated by dashes><date seperated by dashes>
            "creator": session["uid"],
            "date": date,
            "start_time": request.form.get("event_start_time"),
            "end_time": request.form.get("event_end_time"),
            "description": request.form.get("event_description"),
            "email": request.form.get("event_email") or user["email"],
            "location": request.form.get("event_location"),
            "limit": request.form.get("event_limit"),
            "timezone": request.form.get("event_timezone"),
            "registered": {session["uid"]: "owner"},
            "checkin_code": str(randint(1000, 9999))
        }

        if not event["limit"] or int(event["limit"]) >= 1000:
            event["limit"] = -1

        # Make sure all fields were filled
        if not all(event.values()):
            return render_template("event/create.html.jinja", error="Please fill out all fields.", user=user, mapbox_api_key=mapbox_api_key, timezones=all_timezones)

        # Make sure start time is before end time
        if datetime.strptime(event["start_time"], "%H:%M") > datetime.strptime(event["end_time"], "%H:%M"):
            return render_template("event/create.html.jinja", error="Please enter a start time before the end time.", user=user, mapbox_api_key=mapbox_api_key, timezones=all_timezones)

        if event["date"] + event["start_time"] < datetime.now().strftime("%Y-%m-%d%H:%M"):
            return render_template("event/create.html.jinja", error="Please enter a date and time in the future.", user=user, mapbox_api_key=mapbox_api_key, timezones=all_timezones)

        db.add_event(event_uid, event)
        return redirect(f"/events/view/{event_uid}")
    else:
        return render_template("event/create.html.jinja", user=user, mapbox_api_key=mapbox_api_key, timezones=all_timezones)


@events_bp.route("/events/delete/<string:event_id>", methods=["GET", "POST"])
@login_required
@must_be_event_owner
def delete(event_id: str):
    """
        Delete an event from the system.
    """
    if request.method == "POST":
        db.delete_event(event_id)
        return redirect("/events/view")
    else:
        return render_template("event/delete.html.jinja", event=db.get_event(event_id), user=db.get_user_data())


@events_bp.route("/events/register/<string:event_id>", methods=["GET", "POST"])
@login_required
def event_register(event_id: str):
    """
        Register a user for an event.
    """
    event = db.get_event(event_id)
    if request.method == "POST":
        if event["limit"] != -1 and len(event["registered"]) >= event["limit"]:
            event["registered"][session["uid"]] = "excess"
            db.update_event(event_id, event)
            return render_template("event/register.html.jinja", event=event, status="Failed: EVENT_FULL", message="This event has reached it's maximum capacity. Your registration has been placed on a waitlist, and we'll automatically add you if a spot frees up.", user=db.get_user_data())

        event["registered"][session["uid"]] = datetime.now()
        db.update_event(event_id, event)
        return render_template("event/register.html.jinja", event=event, status="Registration successful", message="Your registration was successfully recorded. Go to the dashboard to view all your registered events, and remember your Affiliation Name for check-in on the day.", user=db.get_user_data())
    else:
        if session["uid"] in event["registered"]:
            return render_template("event/register_done.html.jinja", event=event, status="Failed: REGIS_ALR", message="You are already registered for this event. If you wish to unregister from this event, please go to the event view tab and unregister from there.", user=db.get_user_data())
        return render_template("event/register.html.jinja", event=event, user=db.get_user_data())


# @events_bp.route("/events/unregister/<string:event_id>", methods=["GET", "POST"])

@events_bp.route("/events/gen/<string:event_id>", methods=["GET", "POST"])
@login_required
@must_be_event_owner
def gen(event_id: str):
    """
        Generate a QR code for an event.
    """
    if request.method == "POST":
        # Interpret data
        size = request.form.get("size")
        qr_type = request.form.get("type")
        if not size or not qr_type:
            return render_template("event/gen.html.jinja", error="Please fill out all fields.", event=db.get_event(event_id), user=db.get_user_data())
        # Generate QR code based on input
        qrcode = generate_qrcode(db.get_event(event_id), size, qr_type)
        if not qrcode:
            return render_template("event/gen.html.jinja", error="An error occurred while generating the QR code.", event=db.get_event(event_id), user=db.get_user_data())
        # Send file to user
        return send_file(qrcode, mimetype="image/png")
    else:
        return render_template("event/gen.html.jinja", event=db.get_event(event_id), user=db.get_user_data())
