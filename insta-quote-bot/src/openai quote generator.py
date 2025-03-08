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

# OpenAI setup (for quote and DALL·E 3 image generation)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not set in .env")
openai_client = OpenAI(api_key=openai_api_key)

# Stability AI setup (for Stable Diffusion Ultra)
stability_api_key = os.getenv("STABILITY_API_KEY")
if not stability_api_key:
    print("Warning: STABILITY_API_KEY not set; Stable Diffusion will be skipped.")

# Spiritual teachers
spiritual_teachers = [
    "Neville Goddard", "Buddha", "Jesus", "Robert Hawkins", 
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
            temperature=0.7
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
    if not stability_api_key:
        print("Stability API key missing; skipping Stable Diffusion.")
        return None
    
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

def generate_openai_image(teacher):
    """Generates an image using OpenAI's DALL·E 3."""
    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=f"A photorealistic portrait of {teacher}",
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = response.data[0].url
        image_response = requests.get(image_url, stream=True)
        image_response.raise_for_status()
        return Image.open(image_response.raw).convert("RGBA")
    except Exception as e:
        print(f"Error generating OpenAI image for {teacher}: {e}")
        return None

def overlay_quote_on_image(quote, output_dir="/Users/BadBerries/ai-projects/insta-quote-bot/outputs"):
    """Overlays a quote on images from OpenAI and Stability AI, saving each in its own folder."""
    try:
        quote_text, teacher = quote.split(" - ", 1)
    except ValueError:
        quote_text, teacher = quote, "Unknown"

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    try:
        font = ImageFont.truetype("Arial.ttf", 50)
    except:
        font = ImageFont.load_default()

    sources = {
        "openai": generate_openai_image,
        "stable_diffusion": generate_stable_diffusion_image
    }

    for source, fetch_func in sources.items():
        # Create a subfolder for each source
        source_dir = os.path.join(output_dir, source)
        os.makedirs(source_dir, exist_ok=True)
        
        # Define output path
        output_filename = f"quote_{teacher}_{timestamp}.png"
        output_path = os.path.join(source_dir, output_filename)

        # Generate the image
        teacher_img = fetch_func(teacher)
        if not teacher_img:
            img = Image.new("RGB", (1080, 1080), color=(50, 50, 50))
            print(f"Warning: No image found for {teacher} using {source}; using blank background.")
        else:
            img = teacher_img.resize((1080, 1080), Image.Resampling.LANCZOS).convert("RGB")

        # Overlay the quote
        draw = ImageDraw.Draw(img)
        full_text = f"{quote_text}\n- {teacher}"
        draw.multiline_text((540, 540), full_text, font=font, fill=(255, 255, 255), anchor="mm", align="center")

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