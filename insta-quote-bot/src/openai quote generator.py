import sys
import os
import random
from dotenv import load_dotenv
import openai
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Debugging Info (can be removed in production)
print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("sys.path:", sys.path)

# Retrieve API credentials securely
api_key = os.getenv("OPENAI_API_KEY")
oai_org = os.getenv("OPENAI_ORGANIZATION")
oai_proj = os.getenv("OPENAI_PROJECT")

# Ensure API key is set
if not api_key:
    raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")

# Initialize OpenAI client
client = OpenAI(
    organization=oai_org, 
    project=oai_proj,
    api_key=api_key
)

# List of spiritual teachers
spiritual_teachers = [
    "Neville Goddard", "Buddha", "Jesus", "Robert Hawkins", "Eckhart Tolle", 
    "Ram Dass", "Florence Scovel Shinn"
]
selected_teacher = random.choice(spiritual_teachers)

def generate_spiritual_quote():
    """Generates a spiritual quote from a randomly selected teacher."""
    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant providing spiritual wisdom."},
                {"role": "user", "content": f"Give me a short, impactful quote from {selected_teacher}. Just 
provide the quote and the name of the teacher, with no additional explanation."}
            ],
            temperature=0.8
        )
        return completion.choices[0].message["content"]
    except Exception as e:
        print("Error generating quote:", e)
        return None

if __name__ == "__main__":
    quote = generate_spiritual_quote()
    if quote:
        print(f"Generated Quote:\n{quote}")
    else:
        print("Failed to generate quote.")

