"""
    Static image generation for RoboRegistry.
    @author: Lucas Bubner
"""

from datetime import datetime
from io import BytesIO

import qrcode
import qrcode.constants
import qrcode.image.pil
from flask import abort
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pytz import timezone
from requests.exceptions import HTTPError

import db


def _wrap_text(draw, text, font, max_width):
    """Word-wrap text to fit within max_width."""
    words = text.split()
    if not words:
        return [text]
    lines = []
    current_line = words[0]
    for word in words[1:]:
        test_line = f"{current_line} {word}"
        if draw.textlength(test_line, font) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines


def _char_wrap(draw, text, font, max_width):
    """Character-level wrapping as a last resort for text without spaces."""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if draw.textlength(test_line, font) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines if lines else [text]


def _fit_text(draw, text, font_path, font_size, max_width, min_font_size=20,
              max_height=None, line_spacing=1.3):
    """
    Fit text within max_width (and optionally max_height) by word-wrapping
    and scaling down the font size.
    Returns (lines, font) where lines is a list of wrapped text lines.
    """
    def _fits(lines, font):
        if not all(draw.textlength(line, font) <= max_width for line in lines):
            return False
        if max_height is not None:
            total_height = len(lines) * int(font.size * line_spacing)
            if total_height > max_height:
                return False
        return True

    font = ImageFont.truetype(font_path, font_size)
    if _fits([text], font):
        return [text], font

    while font_size >= min_font_size:
        font = ImageFont.truetype(font_path, font_size)
        lines = _wrap_text(draw, text, font, max_width)
        if _fits(lines, font):
            return lines, font
        font_size -= 2

    # Final fallback: character-level wrapping at minimum size
    font = ImageFont.truetype(font_path, min_font_size)
    return _char_wrap(draw, text, font, max_width), font


def _draw_fitted_text(draw, text, font_path, font_size, max_width, template_width, y,
                      color=(0, 0, 0), min_font_size=20, line_spacing=1.3, max_height=None):
    """
    Draw text centered horizontally, wrapping and scaling to fit within max_width
    and optionally max_height. Returns the total height consumed by the drawn text.
    """
    lines, font = _fit_text(draw, text, font_path, font_size, max_width, min_font_size,
                            max_height=max_height, line_spacing=line_spacing)
    line_height = int(font.size * line_spacing)
    for i, line in enumerate(lines):
        line_width = draw.textlength(line, font)
        x = (template_width - line_width) / 2
        draw.text((x, y + i * line_height), line, color, font=font)
    return len(lines) * line_height


def generate_qrcode(event, size, qr_type) -> BytesIO:
    """
        Generates a QR code for RoboRegistry registration or check-in
        @return: QR code image as a BytesIO object
    """
    img = qrcode.make(
        f"https://roboregistry.app.bubner.me/events/{qr_type}/{event.get('uid')}" + (f"?code={event.get('checkin_code')}" if qr_type == "ci" else ""),
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L if size == "large" else qrcode.constants.ERROR_CORRECT_H,
        box_size=20 if size == "large" else 16,
        border=0 if size == "large" else 2,
        image_factory=qrcode.image.pil.PilImage,
    )

    # Backwards compatibility with older code using Pillow
    qr_img = img.get_image()

    # Open the RoboRegistry template depending on size and type
    if size == "large" and qr_type == "register":
        template = Image.open("static/assets/rr_qr_template_large_register.png")
    elif size == "large" and qr_type == "ci":
        template = Image.open("static/assets/rr_qr_template_large_checkin.png")
    else:
        # Make a fresh template for small QR codes
        template = Image.new("RGB", (qr_img.size[0] + 20, qr_img.size[1] + 20), color="white")
        # Give it a yellow border
        template = ImageOps.expand(template, border=15, fill=(255, 217, 0))

    # Calculate the position to place the QR code in the center
    qr_width, qr_height = qr_img.size
    template_width, template_height = template.size
    x = (template_width - qr_width) // 2
    y = (template_height - qr_height) // 2

    # Paste the QR code onto the template
    template.paste(qr_img, (x, y, x + qr_width, y + qr_height))

    # Only add extra metadata if the image is large
    if size == "large":
        # Add text using PIL library
        draw = ImageDraw.Draw(template)
        font = ImageFont.truetype("static/assets/Roboto-Regular.ttf", 54)
        boldfont = ImageFont.truetype("static/assets/Roboto-Black.ttf", 54)
        bigfont = ImageFont.truetype("static/assets/Roboto-Black.ttf", 140)

        # Maximum text width with padding on each side
        max_text_width = template_width - 200

        # Add URL
        text = f"https://roboregistry.app.bubner.me/events/{qr_type}/{event.get('uid')}"
        _draw_fitted_text(draw, text, "static/assets/Roboto-Black.ttf", 54,
                          max_text_width, template_width, template_height - boldfont.size - 1000,
                          min_font_size=24)

        # Add event name and constrain height so it doesn't overflow into the QR code
        title_y = 800 + bigfont.size
        title_max_height = y - title_y - 120  # Template gap
        text = event.get("name").upper()
        _draw_fitted_text(draw, text, "static/assets/Roboto-Black.ttf", 140,
                          max_text_width, template_width, title_y,
                          min_font_size=40, max_height=title_max_height)

        if qr_type == "register":
            # Add event details
            text = f"{event.get('date')} | {event.get('start_time')} - {event.get('end_time')}"
            _draw_fitted_text(draw, text, "static/assets/Roboto-Regular.ttf", 54,
                              max_text_width, template_width, template_height - font.size - 700,
                              min_font_size=30)

            # Add location
            text = event.get("location")
            _draw_fitted_text(draw, text, "static/assets/Roboto-Regular.ttf", 54,
                              max_text_width, template_width, template_height - font.size - 600,
                              min_font_size=24)

            # Add email
            if event.get("email") != "N/A":
                text = "For inquiries contact: " + event.get("email")
                _draw_fitted_text(draw, text, "static/assets/Roboto-Black.ttf", 54,
                                  max_text_width, template_width, template_height - boldfont.size - 480,
                                  min_font_size=24)
        else:
            # Add event check-in code
            text = str(event.get("checkin_code"))
            _draw_fitted_text(draw, text, "static/assets/Roboto-Black.ttf", 140,
                              max_text_width, template_width, template_height - bigfont.size - 480,
                              min_font_size=60)

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
        template.paste(logo, (2000, 100, 2000 + logo.width, 100 + logo.height), logo)

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
