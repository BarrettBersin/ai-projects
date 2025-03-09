# teachers/tolle.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import generate_spiritual_quote, process_image

if __name__ == "__main__":
    teacher = "Hermes Trismegistus"
    quote = generate_spiritual_quote(teacher)
    if quote:
        print(f"Generated Quote:\n{quote}")
        process_image(quote, teacher)
    else:
        print(f"Failed to generate quote for {teacher}.")