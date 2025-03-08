import sys
import os
import random
import requests
from dotenv import load_dotenv
import openai
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from google_images_download import google_images_download

# Load environment variables
load_dotenv()

# OpenAI setup
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set in .env")

client = OpenAI(api_key=api_key)

# Unsplash setup (kept for reference)
unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
if not unsplash_key:
    raise ValueError("UNSPLASH_ACCESS_KEY not set in .env")

# Spiritual teachers
spiritual_teachers = [
    "Neville Goddard", "Buddha", "Jesus", "Robert Hawkins", 
    "Eckhart Tolle", "Ram Dass", "Florence Scovel Shinn"
]

def generate_spiritual_quote():
    """Generates a spiritual quote from a random teacher."""
    selected_teacher = random.choice(spiritual_teachers)
    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a spiritual guide."},
                {"role": "user", "content": f"Short, impactful quote from {selected_teacher}. Quote and teacher name only, separated by ' - '."}
            ],
            temperature=0.7
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error: {e}")
        return None

def fetch_wikimedia_image(teacher):
    """Fetches a teacher image from Wikimedia Commons."""
    query = f"{teacher} portrait" if teacher not in ["Buddha", "Jesus"] else f"{teacher} depiction"
    url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if not data["query"]["search"]:
            print(f"No Wikimedia results for {teacher}")
            return None
        title = data["query"]["search"][0]["title"]
        # Get direct image URL
        info_url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={title}&prop=imageinfo&iiprop=url&format=json"
        info_response = requests.get(info_url)
        info_response.raise_for_status()
        info_data = info_response.json()
        pages = info_data["query"]["pages"]
        image_url = next(iter(pages.values()))["imageinfo"][0]["url"]
        image_response = requests.get(image_url, stream=True)
        image_response.raise_for_status()
        return Image.open(image_response.raw).convert("RGBA")
    except Exception as e:
        print(f"Error fetching Wikimedia image for {teacher}: {e}")
        return None

def fetch_google_image(teacher):
    """Fetches a teacher image from Google Images."""
    try:
        response = google_images_download.googleimagesdownload()
        paths = response.download({
            "keywords": f"{teacher} portrait" if teacher not in ["Buddha", "Jesus"] else f"{teacher} depiction",
            "limit": 1,
            "output_directory": "temp_images",
            "no_directory": True  # Avoid nested folders
        })
        if not paths or not paths[0].get(f"{teacher} portrait" if teacher not in ["Buddha", "Jesus"] else f"{teacher} depiction"):
            print(f"No Google images found for {teacher}")
            return None
        image_path = paths[0][f"{teacher} portrait" if teacher not in ["Buddha", "Jesus"] else f"{teacher} depiction"][0]
        img = Image.open(image_path).convert("RGBA")
        os.remove(image_path)
        return img
    except Exception as e:
        print(f"Error fetching Google image for {teacher}: {e}")
        return None

def overlay_quote_on_image(quote, output_dir="/Users/BadBerries/ai-projects/insta-quote-bot/outputs"):
    """Overlays a quote on images from Wikimedia and Google, saves with source in filename."""
    try:
        quote_text, teacher = quote.split(" - ", 1)
    except ValueError:
        quote_text, teacher = quote, "Unknown"

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(output_dir, exist_ok=True)

    try:
        font = ImageFont.truetype("Arial.ttf", 50)
    except:
        font = ImageFont.load_default()

    for source, fetch_func in [("wikimedia", fetch_wikimedia_image), ("google", fetch_google_image)]:
        output_filename = f"quote_{source}_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)

        teacher_img = fetch_func(teacher)
        if not teacher_img:
            img = Image.new("RGB", (1080, 1080), color=(50, 50, 50))
        else:
            img = teacher_img.resize((1080, 1080), Image.Resampling.LANCZOS).convert("RGB")

        draw = ImageDraw.Draw(img)
        full_text = f"{quote_text}\n- {teacher}"
        draw.multiline_text((540, 540), full_text, font=font, fill=(255, 255, 255), anchor="mm", align="center")

        img.save(output_path)
        print(f"Image saved as {output_path}")

if __name__ == "__main__":
    quote = generate_spiritual_quote()
    if quote:
        print(f"Generated Quote:\n{quote}")
        overlay_quote_on_image(quote)
    else:
        print("Failed to generate quote.")