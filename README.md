# Active Recall Language Learning App — Flask & Google Gemini AI

*Web Services and Applications module, ATU*

### Author
**Aldas Zarnauskas**

---

## Table of Contents
* [Overview](#overview)
* [Assignments](#assignments)
* [Project](#project)
* [Repository Structure](#repository-structure)
* [Requirements](#requirements)
* [License](#license)

---

## Overview
This repository contains the assignments and project work for the **Web Services and Applications** module at **Atlantic Technological University, Galway**.
The module is part of the *Level 8 Higher Diploma in Computational and Data Analytical Science* program.

The purpose of this repository is to organize and showcase coursework completed throughout the module.

---

## Assignments

The assignments are located in the [`assignments/`](./assignments/) folder.

1. **assignment2-carddraw**
   → [assignment2-carddraw.ipynb](assignments/assignment2-carddraw.ipynb)
   Uses the [Deck of Cards API](https://deckofcardsapi.com/) to draw 5 cards from a shuffled deck.

2. **assignment03-cso**
   → [assignment03-cso.py](assignments/assignment03-cso.py)
   Downloads Ireland's exchequer account (historical series) data from the [CSO API](https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/FIQ02/CSV/1.0/en) as a CSV file and converts it to a JSON file.

3. **assignment04-github**
   → [assignment04-github.ipynb](assignments/assignment04-github.ipynb)
   Reads `andrew.txt` from a GitHub repository, replaces every occurrence of "Andrew" with "Aldas", and pushes the updated file back to the repository.

---

## Project

### Active Recall Language Learning

A Flask web application for language learning through active recall and dialogue practice, powered by Google Gemini AI.

**Live Demo:** https://aldas.pythonanywhere.com

Key features:
- AI-generated dialogues using the Google Gemini API
- Translation practice with active recall — type your translation before revealing the answer
- Text-to-speech pronunciation using the Web Speech API

Full documentation, including setup instructions, database schema, and references, is available in the [project README](./project/README.md).

---

## Repository Structure

* **`assignments/`** – Assignment notebooks and scripts for the module.
* **`data/`** – Data files used by the assignments.
* **`project/`** – The Active Recall Language Learning Flask application (see its [README](./project/README.md)).
* **`requirements.txt`** – Python dependencies for the assignments.

---

## Requirements

Dependencies are listed in [requirements.txt](requirements.txt).
To install them, run:

```bash
pip install -r requirements.txt
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
