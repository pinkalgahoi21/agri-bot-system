# 🌱 Kisan AI Advisor (Agri-Bot System)

A production-grade, multi-channel agricultural advisory system designed to assist Indian farmers with crop diseases, weather forecasts, government schemes, and general farming practices.

Farmers can interact with the AI seamlessly via a **modern web interface** or directly through **Telegram**, supporting both voice notes and photos.

## ✨ Features

- 📸 **Crop Disease Diagnosis**: Upload a photo of a sick plant. The system uses Groq Vision to identify the disease and recommends verified treatments.
- 🗣️ **Voice-First Interface**: Farmers can send voice notes in their native language. The system transcribes them using OpenAI Whisper, generates a multilingual response, and sends back an audio reply (TTS).
- 🛡️ **Safe Chemical Recommendations**: Built with a local ChromaDB Vector Database containing official pesticide safety manuals. The AI is strictly restricted from hallucinating chemical names and relies entirely on RAG (Retrieval-Augmented Generation) for medicine.
- 🌦️ **Real-time Weather**: Integrated with OpenWeather API to provide hyper-local farming advice.
- 🏛️ **Government Schemes**: Live search integration to help farmers find active agricultural subsidies and programs.

## 🏗️ Architecture

This is a decoupled, modern system consisting of three parts:

1. **FastAPI Backend (`/backend`)**: The core AI engine powered by LangGraph, LangChain, and Groq. Handles RAG, tools, Whisper STT, gTTS, and SQLite user profiles.
2. **React Frontend (`/frontend`)**: A beautiful, glassmorphic Single Page Application (SPA) built with Vite, Tailwind-like styling, and React.
3. **Telegram Proxy (`/telegram_bot`)**: A lightweight worker that proxies Telegram messages, photos, and voice notes directly to the FastAPI backend.

## 🚀 Deployment

This system is fully configured for free deployment on modern PaaS providers.

### 1. Render (Backend + Telegram Bot)
The project includes a `render.yaml` Blueprint.
- Connect your GitHub to Render.
- Deploy as a **Web Service**.
- The `start.sh` script will automatically boot both the FastAPI backend and the Telegram Bot in the same free container.

### 2. Vercel (Frontend)
- Import the repository into Vercel.
- Set the Root Directory to `frontend`.
- Add the `VITE_API_URL` environment variable pointing to your Render backend URL (e.g., `https://your-render-url.onrender.com/api`).
