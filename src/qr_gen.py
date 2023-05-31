"""
    Helper function to generate QR codes for RoboRegistry
    @author: Lucas Bubner
"""
import qrcode
import qrcode.constants

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from datetime import datetime
from pytz import UTC


def generate_qrcode(event, size, qr_type):
    """
        Generates a QR code for RoboRegistry registration or check-in
        @return: QR code image as a BytesIO object
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L if size == "large" else qrcode.constants.ERROR_CORRECT_H,
        box_size=20 if size == "large" else 16,
        border=0 if size == "large" else 2,
    )
    qr.add_data(f"https://rbreg.vercel.app/events/{qr_type}/{event.get('uid')}")
    qr.make(fit=True)

    # Generate QR code image
    img = qr.make_image(fill_color="black", back_color="white")

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
        bigfont = ImageFont.truetype("static/assets/Roboto-Black.ttf", 160)

        # Add URL
        text = f"https://roboregistry.vercel.app/events/{qr_type}/{event.get('uid')}"
        text_width, text_height = draw.textsize(text, boldfont)
        draw.text(((template_width - text_width) // 2, template_height - text_height - 1000), text, (0, 0, 0), font=boldfont)

        # Add event name
        text = event.get('name').upper()
        text_width, text_height = draw.textsize(text, bigfont)
        draw.text(((template_width - text_width) // 2, 800 + text_height), text, (0, 0, 0), font=bigfont)

        if qr_type == "register":
            # Add generation time
            text = datetime.now(UTC).strftime("%Y/%m/%d, %H:%M:%S UTC")
            text_width, text_height = draw.textsize(text, smallfont)
            draw.text(((template_width - text_width) // 2 + 220, template_height - text_height - 180), text, (0, 0, 0), font=smallfont)

            # Add event details
            text = f"{event.get('date')} | {event.get('start_time')} - {event.get('end_time')}"
            text_width, text_height = draw.textsize(text, font)
            draw.text(((template_width - text_width) // 2, template_height - text_height - 700), text, (0, 0, 0), font=font)

            # Add location
            text = event.get('location')
            text_width, text_height = draw.textsize(text, smallfont if len(text) > 90 else font)
            draw.text(((template_width - text_width) // 2, template_height - text_height - 600), text, (0, 0, 0), font=smallfont if len(text) > 90 else font)

            # Add email
            text = event.get('email')
            text_width, text_height = draw.textsize(text, boldfont)
            draw.text(((template_width - text_width) // 2 + 360, template_height - text_height - 480), text, (0, 0, 0), font=boldfont)
        else:
            # Add event check-in code
            text = str(event.get('checkin_code'))
            text_width, text_height = draw.textsize(text, bigfont)
            draw.text(((template_width - text_width) // 2, template_height - text_height - 480), text, (0, 0, 0), font=bigfont)

    # Save image to an in memory object
    img_file = BytesIO()
    template.save(img_file, "PNG")
    img_file.seek(0)

    # Return object to send in Flask
    return img_file
