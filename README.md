# 🧠 Shrudaya: Voice-Driven AI Friend

![VED](https://cdn.dribbble.com/users/345826/screenshots/1820014/media/e44dde0239810eb9dee133d8e860572f.gif)

Shrudaya is a voice-based AI companion that listens, thinks, and speaks — combining speech recognition, LLM reasoning, and voice synthesis in one seamless loop.

## 🌟 Features

* 🎧 Voice recording
* 🧠 Real-time transcription using **Sarvam AI**
* 💬 Conversation powered by **Mistral LLM**
* 🗣️ Speech synthesis using **ElevenLabs**
* 😄 Friendly, witty assistant personality
* ⟳ Continuous looped conversations
* 🧹 Modular architecture

---

## ✨ Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/TheRealNeelaksh/Shrudaya.git
cd Shrudaya
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # On Windows
# or
source venv/bin/activate  # On Mac/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ Make sure your machine supports audio input/output.

---

## 🔑 Environment Variables

Create a `.env` file in the root directory and add:

```env
SARVAM_API_KEY=your_sarvam_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

---

## 🎯 Running the App

```bash
python main.py
```

Shrudaya will:

1. Record your voice
2. Transcribe using Sarvam AI
3. Generate a witty reply using Mistral
4. Speak it out loud using ElevenLabs
5. Repeat!

---

## 📆 Submodules

This repo uses **[Sesame AI CSM](https://github.com/sesame-ai/csm)** for future TTS integration.

After cloning:

```bash
git submodule update --init --recursive
```

---

## 🧠 Folder Structure

```
Shrudaya/
├── brain/               # Mistral-based chat logic
├── stt/                 # SarvamAI STT
├── tts/                 # ElevenLabs TTS and CSM submodule
├── face/                # Visual face rendering (future UI)
├── test/                # Prototypes & testing scripts
├── ved_log.txt          # Conversation log
├── main.py              # Voice AI loop runner
├── .env                 # Your API keys (not committed)
├── requirements.txt
└── README.md
```

---

## 🧠 Credits

* **Mistral LLM** – Reasoning and language
* **Sarvam AI** – Accurate Indian English transcription
* **ElevenLabs** – High-quality voice synthesis
* **Sesame AI CSM** – Offline TTS engine (coming soon)

---

## ❤️ By Neelaksh – with wit, wisdom, and waveforms
