# Web Services and Applications

### Author
**Aldas Zarnauskas**

---

## Table of contents
* [Overview](#overview)
* [Project](#project)
* [Requirements](#requirements)
* [License](#license)
* [Reference](#reference)

---

## Overview
This repository contains the project work for the **Web Services and Applications** module at **Atlantic Technological University, Galway**.  
The module is part of the *Level 8 Higher Diploma in Computational and Data Analytical Science* program.

---

## Project

### Active Recall Language Learning

A Flask web application for language learning through active recall and dialogue practice, powered by Google Gemini AI.

**Live Demo:** https://aldas.pythonanywhere.com

### Features
- AI generated dialogues using Google Gemini API
- Translation practice with active recall — type your translation before revealing the answer
- Text to speech pronunciation using the Web Speech API


### How to Run Locally

1. Clone the repository
```bash
git clone https://github.com/aldaszarnauskas/web_services_and_applications.git
```

2. Navigate to the project folder
```bash
cd web_services_and_applications/project
```

3. Create a virtual environment and activate it
```bash
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

4. Install dependencies
```bash
pip install -r requirements.txt
```

5. Create a `.env` file in the project folder with your credentials

SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_api_key

6. Run the app
```bash
python hello_world.py
```

7. Open your browser at `http://127.0.0.1:5000`


### Database
Two tables linked by a foreign key:
- **accounts** — stores user login details (id, username, password, email)
- **default_choices** — stores saved language preferences per user (primary language, secondary language, level, dialogue length)


---

## Requirements
Dependencies for this project are listed in [requirements.txt](requirements.txt).  
To install them, run:

```bash
pip install -r requirements.txt
```

---

## License
No license specified.

---

## Reference
- Flask quickstart — initial version of the website:
  https://flask.palletsprojects.com/en/stable/quickstart/#a-minimal-application

- Login and registration page tutorial:
  https://www.geeksforgeeks.org/python/login-and-registration-project-using-flask-and-mysql/

- Google Gemini API quickstart:
  https://ai.google.dev/gemini-api/docs/quickstart

- Google Gemini Text-to-Speech (TTS):
  https://ai.google.dev/gemini-api/docs/speech-generation

- SQLAlchemy working with metadata (multiple SQL tables):
  https://docs.sqlalchemy.org/en/20/tutorial/metadata.html#tutorial-working-with-metadata

- Flask-SQLAlchemy quickstart:
  https://flask-sqlalchemy.readthedocs.io/en/stable/quickstart/#check-the-sqlalchemy-documentation

- HTML select form elements:
  https://www.w3schools.com/html/html_form_elements.asp

- CSS background image:
  https://www.w3schools.com/css/css_background_image.asp

- Top navigation bar:
  https://www.w3schools.com/howto/howto_js_topnav.asp

- AI assistance — Claude (Anthropic) used throughout development for guidance on Flask, SQLAlchemy, JavaScript, CSS and debugging:
  https://claude.ai/share/c53e3330-dee2-416d-95c2-b2b53206f6af