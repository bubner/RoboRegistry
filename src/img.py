"""
    Static image generation for RoboRegistry.
    @author: Lucas Bubner
"""

from datetime import datetime
from io import BytesIO

import qrcode
import qrcode.constants
from PIL import Image, ImageDraw, ImageFont, ImageOps
from flask import abort
from pytz import timezone
from requests.exceptions import HTTPError

import db


def generate_qrcode(event, size, qr_type) -> BytesIO:
    """
        Generates a QR code for RoboRegistry registration or check-in
        @return: QR code image as a BytesIO object
    """
    img = qrcode.make(
        f"https://rbreg.vercel.app/events/{qr_type}/{event.get('uid')}?code={event.get('checkin_code')}",
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L if size == "large" else qrcode.constants.ERROR_CORRECT_H,
        box_size=20 if size == "large" else 16,
        border=0 if size == "large" else 2,
    )

    # Open the RoboRegistry template depending on size and type
    if size == "large" and qr_type == "register":
        template = Image.open("static/assets/rr_qr_template_large_register.png")
    elif size == "large" and qr_type == "ci":
        template = Image.open("static/assets/rr_qr_template_large_checkin.png")
    else:
        # Make a fresh template for small QR codes
        template = Image.new("RGB", (img.size[0] + 20, img.size[1] + 20), color="white")
        # Give it a yellow border
        template = ImageOps.expand(template, border=15, fill=(255, 217, 0))

    # Calculate the position to place the QR code in the center
    qr_width, qr_height = img.size
    template_width, template_height = template.size
    x = (template_width - qr_width) // 2
    y = (template_height - qr_height) // 2

    # Paste the QR code onto the template
    template.paste(img, (x, y))

    # Only add extra metadata if the image is large
    if size == "large":
        # Add text using PIL library
        draw = ImageDraw.Draw(template)
        smallfont = ImageFont.truetype("static/assets/Roboto-Regular.ttf", 36)
        font = ImageFont.truetype("static/assets/Roboto-Regular.ttf", 54)
        boldfont = ImageFont.truetype("static/assets/Roboto-Black.ttf", 54)
        bigfont = ImageFont.truetype("static/assets/Roboto-Black.ttf", 140)

        # Add URL
        text = f"https://roboregistry.vercel.app/events/{qr_type}/{event.get('uid')}"
        text_width, text_height = draw.textlength(text, boldfont), boldfont.size
        draw.text(((template_width - text_width) // 2, template_height - text_height - 1000), text, (0, 0, 0),
                  font=boldfont)

        # Add event name
        text = event.get("name").upper()
        text_width, text_height = draw.textlength(text, bigfont), bigfont.size
        draw.text(((template_width - text_width) // 2, 800 + text_height), text, (0, 0, 0), font=bigfont)

        if qr_type == "register":
            # Add event details
            text = f"{event.get('date')} | {event.get('start_time')} - {event.get('end_time')}"
            text_width, text_height = draw.textlength(text, font), font.size
            draw.text(((template_width - text_width) // 2, template_height - text_height - 700), text, (0, 0, 0),
                      font=font)

            # Add location
            text = event.get("location")
            text_width, text_height = draw.textlength(text, smallfont if len(text) > 90 else font), smallfont.size if len(text) > 90 else font.size
            draw.text(((template_width - text_width) // 2, template_height - text_height - 600), text, (0, 0, 0),
                      font=smallfont if len(text) > 90 else font)

            # Add email
            text = "For inquiries contact: " + event.get("email")
            text_width, text_height = draw.textlength(text, boldfont), boldfont.size
            draw.text(((template_width - text_width) // 2, template_height - text_height - 480), text, (0, 0, 0),
                      font=boldfont)
        else:
            # Add event check-in code
            text = str(event.get("checkin_code"))
            text_width, text_height = draw.textlength(text, bigfont), bigfont.size
            draw.text(((template_width - text_width) // 2, template_height - text_height - 480), text, (0, 0, 0),
                      font=bigfont)

    # Save image to an in memory object
    img_file = BytesIO()
    template.save(img_file, "PNG")
    img_file.seek(0)

    # Return object to send in Flask
    return img_file


def generate_man_ci(event):
    """
        Generate an A4 paper sheet with checkboxes for manual check-in
        @returns Array of BytesIO objects for all pages needed
    """
    try:
        data = db.get_event_data(event.get("uid"))
    except HTTPError:
        abort(403)

    # Collect all of the entities and sort by time
    entities = []
    if event.get("registered"):
        for uid, registered in event.get("registered").items():
            # Access private data to get the full entity name
            # We are authorised to do this because we are the event owner
            name = data.get(uid, {}).get("contactName")
            entity = registered.get("entity").split(" | ")[1]
            entities.append((f"{name}|{entity}", registered.get("registered_time")))

        # Reformat the entities
        entities = sorted(entities, key=lambda x: x[1])

        # Split into name and affilliation
        for i, values in enumerate(entities):
            name = values[0].split("|")[0]
            affil = values[0].split("|")[1]
            # Generic limits for length to prevent overrun
            if len(affil) > 24:
                affil = affil[:24] + "..."
            if len(name) > 24:
                name = name[:24] + "..."
            entities[i] = (name, affil)

    def _queue(entities) -> BytesIO:
        """
            Process one page of entities
        """
        # Make an A4 paper sheet
        template = Image.new("RGB", (2480, 3508), color="white")

        # Write the event name
        draw = ImageDraw.Draw(template)
        font = ImageFont.truetype("static/assets/Roboto-Black.ttf", 60)
        text = event.get("name").upper()
        draw.text((100, 150), text, (0, 0, 0), font=font)

        # Horizontal rule
        draw.line((100, 300, 2380, 300), fill=(0, 0, 0), width=5)

        # RoboRegistry logo in the top right
        logo = Image.open("static/assets/rr.png")
        logo = logo.resize((int(logo.size[0] * 0.5), int(logo.size[1] * 0.5)))
        template.paste(logo, (2000, 100), logo)

        # For every entity, write their name and affilliation
        font = ImageFont.truetype("static/assets/Roboto-Regular.ttf", 40)
        boldfont = ImageFont.truetype("static/assets/Roboto-Black.ttf", 40)

        # Draw header
        draw.text((100, 360), "All RoboRegistry registrations", (0, 0, 0), font=boldfont)

        # Draw time of printing in the timezone of the event
        current_localised_time = datetime.now(timezone(event.get("timezone"))).strftime("%Y-%m-%d %I:%M %p %Z")
        text = "as of " + current_localised_time.strip()
        draw.text((100, 420), text, (0, 0, 0), font=font)

        maxlen = len(text) // 1.2
        for i, entity in enumerate(entities):
            # Draw a checkbox
            draw.rectangle((100, 500 + i * 120, 150, 550 + i * 120), fill=(255, 255, 255), outline=(0, 0, 0), width=5)
            # Draw the name
            text = entity[0]
            # Calculate the longest name
            maxlen = len(text) if len(text) > maxlen else maxlen
            draw.text((200, 500 + i * 120), text, (0, 0, 0), font=boldfont)
            # Draw the affilliation under the name
            text = entity[1]
            maxlen = len(text) if len(text) > maxlen else maxlen
            draw.text((200, 500 + i * 120 + 50), text, (0, 0, 0), font=font)

        # Draw a vertical line to separate the registered from the extra walk-ins, using maxlen to calculate the position
        draw.line((100 + 200 + maxlen * 20, 300, 100 + 200 + maxlen * 20, 3508), fill=(0, 0, 0), width=5)

        # Draw a table header for the extra walk-ins, with the values Name, Affiliation, and Time
        font = ImageFont.truetype("static/assets/Roboto-Black.ttf", 40)
        draw.text((100 + 200 + maxlen * 20 + 100 + (500 - font.getbbox("Name")[2]) // 2, 400), "Name", (0, 0, 0),
                  font=font)
        draw.text((100 + 200 + maxlen * 20 + 100 + 500 + (500 - font.getbbox("Affiliation")[2]) // 2, 400),
                  "Affiliation", (0, 0, 0), font=font)
        draw.text((100 + 200 + maxlen * 20 + 100 + 500 + 500 + (500 - font.getbbox("Time")[2]) // 2, 400), "Time",
                  (0, 0, 0), font=font)

        # Draw table cells
        font = ImageFont.truetype("static/assets/Roboto-Regular.ttf", 40)
        for i in range(30):
            draw.line((100 + 200 + maxlen * 20 + 100, 500 + i * 100, template.width - 100, 500 + i * 100),
                      fill=(0, 0, 0), width=3)
            # Make vertical lines that seperate the columns
            draw.line((100 + 200 + maxlen * 20 + 100 + 500, 400, 100 + 200 + maxlen * 20 + 100 + 500, 3508),
                      fill=(0, 0, 0), width=3)
            draw.line((100 + 200 + maxlen * 20 + 100 + 500 + 500, 400, 100 + 200 + maxlen * 20 + 100 + 500 + 500, 3508),
                      fill=(0, 0, 0), width=3)
            draw.line((100 + 200 + maxlen * 20 + 100 + 500 + 500 + 500, 400,
                       100 + 200 + maxlen * 20 + 100 + 500 + 500 + 500, 3508),
                      fill=(0, 0, 0), width=3)

        buf = BytesIO()
        template.save(buf, "PNG")
        buf.seek(0)

        return buf

    bufs = []

    # Maximum 25 per page due to size
    if len(entities) > 0:
        while len(entities) > 25:
            # Get registrations that are not on this page
            left = entities[25:]
            bufs.append(_queue(entities[:25]))
            entities = left
        # Queue the remaining registrations
        bufs.append(_queue(entities))

    if len(bufs) == 0:
        # If there are no registrations, just queue an empty page
        bufs.append(_queue([]))

    return bufs
