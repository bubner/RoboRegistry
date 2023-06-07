"""
    Event creation and management functionality for RoboRegistry
    @author: Lucas Bubner, 2023
"""
from flask import Blueprint, render_template, request, session, redirect, abort, send_file, flash, make_response, get_flashed_messages
from wrappers import login_required, must_be_event_owner, event_must_be_running
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
    done_events = {}
    deletions = []
    # Remove registered events that have already occurred, and add them to a seperate list
    for key, value in registered_events.items():
        if datetime.strptime(value["date"], "%Y-%m-%d") < datetime.now():
            deletions.append(key)
            done_events[key] = value
    for key in deletions:
        del registered_events[key]
    return render_template("dash/view.html.jinja", created_events=created_events, registered_events=registered_events, done_events=done_events, user=db.get_user_data())


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
        elif key == session["uid"]:
            registered = True
            break

    # Calculate time to event
    start_time = datetime.strptime(
        f"{data['date']} {data['start_time']}", "%Y-%m-%d %H:%M")
    end_time = datetime.strptime(
        f"{data['date']} {data['end_time']}", "%Y-%m-%d %H:%M")

    days, hours, minutes = utils.get_time_diff(datetime.now(), start_time)
    time_to_end = utils.get_time_diff(datetime.now(), end_time)

    time = ""
    if days >= 0:
        if days >= 1:
            if days >= 7:
                time += f"{days // 7} week(s) "
            time += f"{days % 7} day(s) {hours} hour(s)"
        elif hours > 0:
            time = f"{hours} hour(s) {minutes} minute(s)"
        elif minutes > 0:
            time = f"{minutes} minute(s)"
    elif time_to_end[0] >= 0:
        if time_to_end[1] > 0:
            time = f"Ends in {time_to_end[1]} hours {time_to_end[2]} minute(s)"
        else:
            time = f"Ends in {time_to_end[2]} minute(s)"
    else:
        time = "Event has ended."

    can_register = time.startswith("Ends") or time.startswith("Event")
    tz = timezone(data["timezone"])
    offset = tz.utcoffset(datetime.now()).total_seconds() / 3600

    if not data:
        abort(409)

    return render_template("event/event.html.jinja", user=db.get_user_data(), event=data, registered=registered, owned=owned, mapbox_api_key=getenv("MAPBOX_API_KEY"), time=time, can_register=can_register, timezone=tz, offset=offset)


@events_bp.route("/events", methods=["GET", "POST"])
@login_required
def redirector():
    """
        Manage redirector for /events
    """
    if request.method == "POST":
        if not (target := request.form.get("event_url")):
            return render_template("dash/redirector.html.jinja", user=db.get_user_data(), error="Missing url!")
        if not (event := db.get_event(target)):
            res = make_response(redirect(target))
            # Test to see if it is a url and/or if it is a 404
            if not target.startswith("http") or res.status_code == 404:
                return render_template("dash/redirector.html.jinja", user=db.get_user_data(), error="Hmm, we can't seem to find that event.")
            return res
        return redirect(f"/events/view/{event['uid']}")
    else:
        return render_template("dash/redirector.html.jinja", user=db.get_user_data())


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
            "limit": utils.limitTo999(request.form.get("event_limit")),
            "timezone": request.form.get("event_timezone"),
            "registered": {session["uid"]: "owner"},
            "checkin_code": randint(1000, 9999)
        }

        if not event["limit"]:
            event["limit"] = -1

        # Make sure all fields were filled
        if not all(event.values()):
            return render_template("event/create.html.jinja", error="Please fill out all fields.", user=user, mapbox_api_key=mapbox_api_key, timezones=all_timezones, old_data=event)

        # Make sure start time is before end time
        if datetime.strptime(event["start_time"], "%H:%M") > datetime.strptime(event["end_time"], "%H:%M"):
            return render_template("event/create.html.jinja", error="Please enter a start time before the end time.", user=user, mapbox_api_key=mapbox_api_key, timezones=all_timezones, old_data=event)

        if event["date"] + event["start_time"] < datetime.now().strftime("%Y-%m-%d%H:%M"):
            return render_template("event/create.html.jinja", error="Please enter a date and time in the future.", user=user, mapbox_api_key=mapbox_api_key, timezones=all_timezones, old_data=event)

        db.add_event(event_uid, event)
        return redirect(f"/events/view/{event_uid}")
    else:
        return render_template("event/create.html.jinja", user=user, mapbox_api_key=mapbox_api_key, timezones=all_timezones, old_data={})


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
    user = db.get_user_data()
    # Check to see if the event is over, and decline registration if it is
    if event["date"] + event["end_time"] < datetime.now().strftime("%Y-%m-%d%H:%M"):
        return render_template("event/done.html.jinja", event=event, user=user, status="Failed: EVENT_AUTO_CLOSED", error="This event has already ended. Registation has been automatically disabled.")

    if request.method == "POST":
        # Store registered users data
        edits = {
            "registered_data": {
                session["uid"]: {
                    "teamName": request.form.get("teamName"),
                    "role": request.form.get("role"),
                    "teamNumber": request.form.get("teamNumber") or "N/A",
                    "numPeople": request.form.get("numPeople"),
                    "numStudents": utils.limitTo999(request.form.get("numStudents")),
                    "numMentors": utils.limitTo999(request.form.get("numMentors")),
                    "numAdults": utils.limitTo999(request.form.get("numAdults")),
                    "contactName": request.form.get("contactName") or f"{user['first_name']} {user['last_name']}",
                    "contactEmail": user["email"],
                    "contactPhone": request.form.get("contactPhone") or "N/A",
                }
            },
            "registered": {
                session["uid"]: "pending"
            }
        }
        # Ensure that all required fields are filled
        if not all(event["registered_data"][session["uid"]].values()):
            return render_template("event/done.html.jinja", event=event, status="Failed: MISSING_FIELDS", message="Please fill out all required fields.", user=user)

        # Check for event capacity
        if event["limit"] != -1 and len(event["registered"]) >= event["limit"]:
            edits["registered"][session["uid"]] = "excess"
            db.update_event(event_id, edits)
            return render_template("event/done.html.jinja", event=event, status="Failed: EVENT_FULL", message="This event has reached it's maximum capacity. Your registration has been placed on a waitlist, and we'll automatically add you if a spot frees up.", user=user)

        # Log event registration
        edits["registered"][session["uid"]] = str(datetime.now())
        db.update_event(event_id, edits)
        return render_template("event/done.html.jinja", event=event, status="Registration successful", message="Your registration was successfully recorded. Go to the dashboard to view all your registered events, and remember to bring a smart device for QR code check-in on the day.", user=user)
    else:
        if session["uid"] in event["registered"]:
            return render_template("event/done.html.jinja", event=event, status="Failed: REGIS_ALR", message="You are already registered for this event. If you wish to unregister from this event, please go to the event view tab and unregister from there.", user=user)
        return render_template("event/register.html.jinja", event=event, user=user, mapbox_api_key=getenv("MAPBOX_API_KEY"))


@events_bp.route("/events/unregister/<string:event_id>", methods=["GET", "POST"])
@login_required
def event_unregister(event_id: str):
    if request.method == "POST":
        event = db.get_event(event_id)
        if session["uid"] in event["registered"]:
            del event["registered"][session["uid"]]
            del event["registered_data"][session["uid"]]
            db.update_event(event_id, event)
            return render_template("event/done.html.jinja", event=event, status="Unregistration successful", message="Your registration was successfully removed.", user=db.get_user_data())
        else:
            return render_template("event/done.html.jinja", event=event, status="Failed: REGIS_NF", message="You are not registered for this event.", user=db.get_user_data())
    else:
        return render_template("event/unregister.html.jinja", event=db.get_event(event_id), user=db.get_user_data())


@events_bp.route("/events/gen/<string:event_id>", methods=["GET", "POST"])
@login_required
@must_be_event_owner
def gen(event_id: str):
    """
        Generate a QR code for an event.
    """
    # Check if the event is done, reject if it is
    if db.get_event(event_id)["date"] + db.get_event(event_id)["end_time"] < datetime.now().strftime("%Y-%m-%d%H:%M"):
        return render_template("event/done.html.jinja", event=db.get_event(event_id), status="Failed: QR_GEN_FAIL", message="Unable to generate QR codes for an event that has ended, as registration and check-in links are no longer active.", user=db.get_user_data())
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


@events_bp.route("/events/ci/<string:event_id>", methods=["GET", "POST"])
# @event_must_be_running
def checkin(event_id: str):
    """
        Check in to an event.
    """
    event = db.get_event(event_id)
    if request.method == "POST":
        raise NotImplementedError
    else:
        return render_template("event/gatekeep.html.jinja", event=event)


@events_bp.route("/events/ci/<string:event_id>/manual", methods=["GET", "POST"])
# @event_must_be_running
@login_required
def manual(event_id: str):
    """
        Check in to an event using email associated with registration.
    """
    event = db.get_event(event_id)
    registered, owned = db.get_my_events()
    if event_id in owned.keys():
        return render_template("event/done.html.jinja", event=event, status="Failed: EVENT_OWNER", message="The currently logged in RoboRegistry account is the owner of this event. The owner cannot check in to their own event.", user=db.get_user_data())
    if event_id not in registered.keys():
        return render_template("event/done.html.jinja", event=event, status="Failed: NO_AFFIL", message="The currently logged in RoboRegistry account has not registered for this event. The event owner will have to manually record your presence through their Dashboard.", user=db.get_user_data())
    if request.method == "POST":
        # Attempt a manual registration using the affiliated email
        edits = {
            "checked_in": {
                session['uid']: str(datetime.now())
            }
        }
        db.update_event(event_id, edits)
        return render_template("event/done.html.jinja", event=event, status="Check in successful", message="Your check in has been recorded successfully by registered email verification. You can safely close this tab.", user=db.get_user_data())
    else:
        return render_template("event/manual.html.jinja", event=event, user=db.get_user_data(), data=registered[event_id]["registered_data"][session["uid"]])
