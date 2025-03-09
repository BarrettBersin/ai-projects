# utils.py
import os
import random
import requests
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO
import textwrap

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not set in .env")
openai_client = OpenAI(api_key=openai_api_key)

stability_api_key = os.getenv("STABILITY_API_KEY")
if not stability_api_key:
    raise ValueError("STABILITY_API_KEY not set in .env")

def generate_spiritual_quote(teacher):
    """Generates a random, unique spiritual quote for a specific teacher using OpenAI."""
    # Add randomness to the prompt
    randomness_prompts = [
        "Provide a lesser-known, short, impactful quote from {teacher}.",
        "Generate a creative, short, impactful quote inspired by {teacher}'s teachings.",
        "Give me a unique, concise quote from {teacher} that’s not widely repeated.",
        "Craft an original, short, powerful quote in the style of {teacher}."
    ]
    prompt = random.choice(randomness_prompts).format(teacher=teacher) + " Quote and teacher name only, separated by ' - '."

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a spiritual guide with deep knowledge of diverse teachings."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.2,  # Higher temperature for more creativity
            top_p=0.9,        # Use nucleus sampling for varied outputs
            max_tokens=50     # Limit length to keep quotes short
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error generating quote for {teacher}: {e}")
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

    response = requests.post(host, headers=headers, files=files, data=params)
    if not response.ok:
        raise Exception(f"HTTP {response.status_code}: {response.text}")
    return response

def generate_stable_diffusion_image(teacher):
    """Generates an image using Stability AI's Stable Image Ultra (v2beta)."""
    host = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
    params = {
        "prompt": f"An inspiring, artistic image representing {teacher}",
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

def process_image(quote, teacher, output_dir="/Users/BadBerries/ai-projects/insta-quote-bot/outputs"):
    """Generates and saves a plain image and an image with quote overlay for a teacher."""
    try:
        quote_text, _ = quote.split(" - ", 1)
    except ValueError:
        quote_text = quote

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    source_dir = os.path.join(output_dir, "stable_diffusion")
    os.makedirs(source_dir, exist_ok=True)
    
    plain_filename = f"plain_{teacher}_{timestamp}.png"
    overlay_filename = f"quote_{teacher}_{timestamp}.png"
    plain_path = os.path.join(source_dir, plain_filename)
    overlay_path = os.path.join(source_dir, overlay_filename)

    # Generate and save plain image
    teacher_img = generate_stable_diffusion_image(teacher)
    if not teacher_img:
        img = Image.new("RGB", (1080, 1080), color=(50, 50, 50))
        print(f"Warning: No image found for {teacher}; using blank background.")
    else:
        img = teacher_img.resize((1080, 1080), Image.Resampling.LANCZOS).convert("RGBA")
    img.save(plain_path)
    print(f"Plain image saved as {plain_path}")

    # Load font for overlay
    try:
        font_path = "Arial.ttf"
        font_size = 80
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
        font_size = 40

    # Prepare text
    draw = ImageDraw.Draw(img)
    max_width = int(img.width * 0.9)
    full_text = f"{quote_text}\n- {teacher}"

    wrapped_text = ""
    for line in full_text.split('\n'):
        wrapped_lines = textwrap.fill(line, width=40)
        wrapped_text += wrapped_lines + '\n'
    wrapped_text = wrapped_text.strip()

    # Adjust font size
    text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    while text_width > max_width and font_size > 30:
        font_size -= 5
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

    while text_width < max_width * 0.85 and font_size < 120:
        font_size += 5
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

    # Position text
    text_x = (img.width - text_width) // 2
    text_y = img.height - text_height - 100
    if text_y < img.height * 0.5:
        text_y = int(img.height * 0.5)

    # Create overlay
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    rect_padding = 40
    rect_x1 = text_x - rect_padding
    rect_y1 = text_y - rect_padding
    rect_x2 = text_x + text_width + rect_padding
    rect_y2 = text_y + text_height + rect_padding
    rectangle_color = (0, 0, 0, 150)
    overlay_draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=rectangle_color)

    img = Image.alpha_composite(img, overlay)

    # Draw text
    draw = ImageDraw.Draw(img)
    draw.multiline_text((text_x, text_y), wrapped_text, font=font, fill=(255, 255, 255), align="center")

    # Save overlay image
    img.save(overlay_path)
    print(f"Overlay image saved as {overlay_path}")