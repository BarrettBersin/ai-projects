import sys
import os
import random
import requests
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO

# Load environment variables
load_dotenv()

# OpenAI setup (for quote generation only)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not set in .env")
openai_client = OpenAI(api_key=openai_api_key)

# Stability AI setup (for Stable Diffusion Ultra)
stability_api_key = os.getenv("STABILITY_API_KEY")
if not stability_api_key:
    raise ValueError("STABILITY_API_KEY not set in .env")

# Spiritual teachers
spiritual_teachers = [
    "Neville Goddard", "Buddha", "Jesus", "David R. Hawkins", 
    "Eckhart Tolle", "Ram Dass", "Florence Scovel Shinn",
    "Hermes Trismegistus"
]

def generate_spiritual_quote():
    """Generates a spiritual quote from a random teacher using OpenAI."""
    selected_teacher = random.choice(spiritual_teachers)
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a spiritual guide."},
                {"role": "user", "content": f"Short, impactful quote from {selected_teacher}. Quote and teacher name only, separated by ' - '."}
            ],
            temperature=0.95
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error generating quote: {e}")
        return None

def send_generation_request(host, params, files=None):
    """Sends a generation request to Stability AI's API."""
    headers = {
        "Accept": "image/*",
        "Authorization": f"Bearer {stability_api_key}"
    }

    if files is None:
        files = {}

    image = params.pop("image", None)
    mask = params.pop("mask", None)
    if image is not None and image != '':
        files["image"] = open(image, 'rb')
    if mask is not None and mask != '':
        files["mask"] = open(mask, 'rb')
    if len(files) == 0:
        files["none"] = ''

    response = requests.post(
        host,
        headers=headers,
        files=files,
        data=params
    )
    if not response.ok:
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    return response

def generate_stable_diffusion_image(teacher):
    """Generates an image using Stability AI's Stable Image Ultra (v2beta)."""
    host = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
    params = {
        "prompt": f"A photorealistic portrait of {teacher}",
        "negative_prompt": "blurry, low quality",
        "aspect_ratio": "1:1",
        "seed": 0,
        "output_format": "png"
    }
    
    try:
        response = send_generation_request(host, params)
        finish_reason = response.headers.get("finish-reason")
        if finish_reason == 'CONTENT_FILTERED':
            print(f"Image for {teacher} failed NSFW classifier; skipping.")
            return None
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Error generating Stable Diffusion image for {teacher}: {e}")
        return None

def overlay_quote_on_image(quote, output_dir="/Users/BadBerries/ai-projects/insta-quote-bot/outputs"):
    """Overlays a quote on an image from Stability AI, placing the text near the bottom with a semi-transparent background."""
    try:
        quote_text, teacher = quote.split(" - ", 1)
    except ValueError:
        quote_text, teacher = quote, "Unknown"

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    source_dir = os.path.join(output_dir, "stable_diffusion")
    os.makedirs(source_dir, exist_ok=True)
    
    # Define output filename
    output_filename = f"quote_{teacher}_{timestamp}.png"
    output_path = os.path.join(source_dir, output_filename)

    # Load font with fallback
    try:
        font_path = "Arial.ttf"  # Change to your font file path if needed
        font_size = 120  # Start with a large font
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    # Generate the image
    teacher_img = generate_stable_diffusion_image(teacher)
    if not teacher_img:
        img = Image.new("RGB", (1080, 1080), color=(50, 50, 50))
        print(f"Warning: No image found for {teacher} using Stable Diffusion; using blank background.")
    else:
        img = teacher_img.resize((1080, 1080), Image.Resampling.LANCZOS).convert("RGBA")

    # Prepare text
    draw = ImageDraw.Draw(img)
    max_width = int(img.width * 0.95)  # 95% of the image width
    full_text = f"{quote_text}\n- {teacher}"

    # Dynamically adjust font size for maximum width
    while font.getbbox(full_text)[2] > max_width and font_size > 30:  # Prevent infinite loop
        font_size -= 5
        font = ImageFont.truetype(font_path, font_size)

    # If text is too small, increase it
    while font.getbbox(full_text)[2] < max_width * 0.8 and font_size < 180:  # Ensure text fills width
        font_size += 5
        font = ImageFont.truetype(font_path, font_size)

    # Get text bounding box
    text_bbox = draw.multiline_textbbox((0, 0), full_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Position text near the bottom
    text_x = (img.width - text_width) // 2
    text_y = img.height - text_height - 80  # Adjust so it doesn't get cut off

    # Ensure text doesn't go out of bounds
    if text_y < img.height * 0.65:
        text_y = int(img.height * 0.65)

    # Ensure image is in RGBA mode before alpha compositing
    img = img.convert("RGBA")  
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Draw a semi-transparent rectangle as background
    rect_padding = 30
    rect_x1 = text_x - rect_padding
    rect_y1 = text_y - rect_padding
    rect_x2 = text_x + text_width + rect_padding
    rect_y2 = text_y + text_height + rect_padding

    rectangle_color = (0, 0, 0, 180)  # Semi-transparent black
    overlay_draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=rectangle_color)

    # Convert overlay to RGBA before merging
    overlay = overlay.convert("RGBA")  

    # Merge overlay onto image
    img = Image.alpha_composite(img, overlay)

    # Draw the quote text on top of the background
    draw = ImageDraw.Draw(img)
    draw.multiline_text((text_x, text_y), full_text, font=font, fill=(255, 255, 255), align="center")

    # Save the image
    img.save(output_path)
    print(f"Image saved as {output_path}")

if __name__ == "__main__":
    quote = generate_spiritual_quote()
    if quote:
        print(f"Generated Quote:\n{quote}")
        overlay_quote_on_image(quote)
    else:
        print("Failed to generate quote.")