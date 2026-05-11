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
        contents=f"""Generate a natural, coherent dialogue of exactly {dialogue_length} sentences at {cambridge_level} level in {primary_language}.

The dialogue must:
- Be a realistic conversation with a clear topic and context (e.g. at a cafe, job interview, buying groceries)
- Use exactly 2 speakers with authentic {secondary_language} names that are common in {secondary_language}-speaking countries
- Keep the same two names throughout the entire dialogue
- Make the conversation flow naturally — each line should follow logically from the previous one
- Match the {cambridge_level} difficulty level throughout

For the translation in brackets:
- Write natural, idiomatic {secondary_language} as a native speaker would actually say it
- Do NOT translate word for word — translate the meaning and feeling instead
- Use natural expressions, contractions and phrases common in {secondary_language}
- If a phrase has a well known equivalent in {secondary_language} use that instead of a literal translation

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