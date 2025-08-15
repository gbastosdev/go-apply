## AI ATS-PROOF
- Create a RAG that uses the user's CV (resume) to rate it.
- User has to put in the requirements from the opportunity (bullet points).
- User has to load in his resume to make the AI read it.
- AI has to be able to act as a recruiter using ATS.
- Ai has to be able to rate the user's resume, based on the opportunity given.

# Usage:
## (Opitional) Create your local venv for python: 
- ``python -m venv venv``
- If on windows -> Navigate to "venv/Scripts/activate.bat" or "venv/Scripts/Activate.ps1" (If you're on powershell).
- If on Mac -> Navigate to "venv/bin/" and use "source activate".
    - Switch back to project root folder and run:
        - ``pip install -r requirements.txt``.

## Local development with Docker:
- Open bash terminal and run the following command to concede permissions to .sh file:
    - ``chmod +x start-ollama.sh``
- After, just run the command to create Docker image for Ollama and the container. Finally, the bash file will run Tinyllama image to host our AI.
    - ``./start-ollama.sh``

## Starting FastAPI Backend App:
- Just hit F5 to run the application.
