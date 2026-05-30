from google import genai
from dotenv import load_dotenv
import os
import re

load_dotenv()
client = genai.Client()

# Load prompt once when the module is imported
PROMPT_PATH = os.path.join(os.path.dirname(__file__), 'prompt.txt')
with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
    PROMPT_TEMPLATE = f.read()

def get_a_dialogue(primary_language, cambridge_level, secondary_language, dialogue_length):

    # Fill in the variables from the text file
    prompt = PROMPT_TEMPLATE.format(
        primary_language=primary_language,
        cambridge_level=cambridge_level,
        secondary_language=secondary_language,
        dialogue_length=dialogue_length
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    lines = response.text.split('\n')
    dialogue_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(r'(\d+)\.\s+([\w\s]+):\s+(.+?)\s*\[(.+?)\]', line)
        if match:
            dialogue_lines.append({
                "id": int(match[1]),
                "name": match[2].strip(),
                "primary_lang": match[3].strip(),
                "secondary_lang": match[4].strip()
            })

    return dialogue_lines