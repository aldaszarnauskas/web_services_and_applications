from google import genai
from dotenv import load_dotenv
import os
import re


# The client gets the API key from the environment variable `GEMINI_API_KEY`.
load_dotenv()
client = genai.Client()

def get_a_dialogue(primary_language, cambridge_level, secondary_language, dialogue_length):



    response = client.models.generate_content(
        model="gemini-2.5-flash-lite", 
        contents=f"""Please generate {dialogue_length} sentences in {cambridge_level} {primary_language} in a dialogue form.
            Follow this format EXACTLY with no bold text, no markdown, no extra formatting:

            1. Name: Text in {primary_language} [Translation in {secondary_language}]
            2. Name: Text in {primary_language} [Translation in {secondary_language}]

            Only output the numbered lines, nothing else."""
    )


    lines = response.text.split('\n')
        
    dialogue_lines = []
        
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match: "1.  Jonas: Labas! [Hello!]"
        match = re.match(r'(\d+)\.\s+(\w+):\s+(.+?)\s*\[(.+?)\]', line)
        #print(line)
        if match:
                
            dialogue_lines.append({
                "id": int(match[1]),
                "name": match[2].strip(),
                "primary_lang": match[3].strip(),
                "secondary_lang": match[4].strip()
            })
    
    return dialogue_lines