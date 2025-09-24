# 🎤 Live Speech Translator
  
A tiny, full-stack app that listens to your computer’s microphone, recognizes speech, translates it to your chosen language, and shows the latest translation in a sleek web UI — all running locally.

- Backend: Flask + threading + SpeechRecognition + deep-translator
- Frontend: Plain HTML/CSS/JS served by Flask (auto-opens in your browser)
<p align="center">
  
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&amp;logoColor=white" />
  <img alt="Flask" src="https://img.shields.io/badge/Flask-2.3%2B-000000?logo=flask&amp;logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/Local%20Only-Dev-orange?logo=homeassistant&amp;logoColor=white" />
</p>

![image](https://github.com/MdSaifAli063/Live-Speech-Translator/blob/1795f1c3a6c4556ee220e3732ead4674f07070c4/Screenshot%202025-09-21%20005025.png)

---

## ✨ Features

- 🎙️ Live microphone capture (local machine)
- 🧠 Speech recognition via Google Web Speech API
- 🌐 Translation via Google (deep-translator)
- 🔁 Start/Stop control with live status polling
- 🧩 Works out-of-the-box: Run backend and get UI auto-opened
- 🖥️ Responsive, colorful UI

> Note: The microphone used is the one on the machine running the backend (not the browser’s mic).

---

## 🗂️ Project Structure


project-root/ ├─ index.html # Frontend (served by Flask) └─ server/ ├─ app.py # Flask backend (serves API + index.html + static assets) └─ requirements.txt # Python dependencies


---

## 🚀 Quick Start

1) Prerequisites
- Python 3.9+ recommended
- A working microphone with OS permissions granted to your terminal/IDE
- Internet access (for recognition/translation services)

2) Create a virtual environment
```bash
cd project-root
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

Install dependencies
pip install -r server/requirements.txt

PyAudio may require system libraries:

Windows
pip install pipwin
pipwin install pyaudio

macOS
brew install portaudio
pip install pyaudio

Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio
pip install pyaudio

Run the backend
python server/app.py

It will auto-open http://localhost:5000 in your default browser
The UI calls the backend endpoints on the same origin

🧭 How It Works

Click Start in the UI to POST /start with your chosen source/target languages
A background thread captures mic audio, recognizes text, translates it, and updates shared state
The UI polls GET /status to show the latest translated text
Click Stop to gracefully end the background worker
🔌 API Reference
Base URL (local): http://localhost:5000

POST /start
Body (JSON):
{
  "sourceLang": "en",
  "targetLang": "hi"
}

Response:
{ "message": "Listening and translating...", "translatedText": "Starting speech recognition..." }

GET /stop
Response:
{ "message": "Stopped." }

GET /status
Response:
{
  "running": true,
  "translatedText": "Hello world",
  "sourceLang": "en",
  "targetLang": "hi"
}

🌍 Language Codes

Source → SpeechRecognition locale mapping (examples)
en → en-US
hi → hi-IN
gu → gu-IN
cn / zh / zh-CN → zh-CN
ko → ko-KR
deep-translator target codes
en, hi, gu, zh-CN, ko
If a given code fails for source language, translation falls back to auto-detect.

🧪 Curl Tests (optional)

# Start (English → Hindi)
curl -X POST http://localhost:5000/start \
  -H "Content-Type: application/json" \
  -d "{\"sourceLang\":\"en\",\"targetLang\":\"hi\"}"

# Status
curl http://localhost:5000/status

# Stop
curl http://localhost:5000/stop

🧰 Configuration Tips

Change port/host
In server/app.py (bottom):
host = "127.0.0.1"
port = 5000
app.run(host="0.0.0.0", port=port, debug=True)

Update port as needed. If you deploy to another machine, make sure firewalls allow that port.
Serving static assets
Place index.html and any referenced files (css/js/images/fonts) in the project root (same folder as index.html)
The backend serves common static file types without interfering with /start, /stop, /status
CORS
CORS is enabled for all origins by default for local development:
CORS(app, resources={r"/*": {"origins": "*"}})

For production, restrict it to your frontend origin.

🛟 Troubleshooting

“Microphone error” or “Invalid input device”
Ensure a default recording device is selected
Grant microphone permissions to your terminal/IDE (macOS: System Settings → Privacy & Security → Microphone)
SpeechRecognition RequestError
Requires internet; check connectivity and try again
No translation appears
Confirm the backend is running
Check browser console/network for fetch errors
Speak clearly and pause slightly; the worker uses ~7s phrase chunks
PyAudio installation fails
Use the OS-specific steps above (pipwin on Windows, Homebrew on macOS, apt on Ubuntu/Debian)

🧹 .gitignore

A minimal Python/web project ignore set:

# Python
__pycache__/
*.py[cod]
*$py.class
*.log

# Environments
.venv/
venv/
env/
ENV/
.conda/
.pyvenv.cfg

# Packaging
build/
dist/
*.egg-info/
.eggs/
wheels/

# Coverage / testing
.coverage
.coverage.*
htmlcov/
.pytest_cache/

# Editors
.vscode/
.idea/
*.iml

# Frontend
node_modules/
.cache/
dist/
public/build/


💡 Notes

This app is for local/dev usage. It relies on third-party services for recognition and translation.
The backend UI auto-opens in your default browser when you run server/app.py.
Enjoy translating! 🌟
