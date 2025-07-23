import os
import tempfile
import traceback
import speech_recognition as sr
from pydub import AudioSegment
from werkzeug.utils import secure_filename
import re
import base64
import tempfile
import warnings
import io
import cohere
from flask import Flask, request, jsonify, render_template_string
from PyPDF2 import PdfReader
from PIL import Image
from groq import Groq
import google.generativeai as genai
import subprocess
import ffmpeg  # for audio conversion
# Set the path to ffmpeg.exe
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"
# Suppress warnings
warnings.filterwarnings('ignore')

# Load API keys from environment variables
# IMPORTANT: Replace these with your actual API keys
GROQ_API_KEY = ""  # Replace with your Groq API key
COHERE_API_KEY = ""  # Replace with your Cohere API key
GEMINI_API_KEY = ""  # Replace with your Google Gemini API key


# Initialize clients
groq_client = Groq(api_key=GROQ_API_KEY)
cohere_client = cohere.Client(COHERE_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
vision_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
text_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

# Initialize Flask app
app = Flask(__name__)

# Set FFmpeg paths explicitly
ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
ffprobe_path = r"C:\ffmpeg\bin\ffprobe.exe"

AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

# Configure upload settings
UPLOAD_FOLDER = 'audio_uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac'}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart PDF Chat Assistant</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #1e40af;
            --background-color: #f8fafc;
            --chat-user-bg: #e0f2fe;
            --chat-bot-bg: #ffffff;
            --border-color: #e2e8f0;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--background-color);
            color: var(--text-primary);
            line-height: 1.5;
        }

        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .app-header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .app-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 0.5rem;
        }

        .app-subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }

        .main-content {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }

        @media (min-width: 1024px) {
            .main-content {
                grid-template-columns: 300px 1fr;
            }
        }

        .upload-section {
            padding: 2rem;
            background: var(--background-color);
            border-radius: 0.75rem;
            text-align: center;
        }

        .upload-icon {
            font-size: 3rem;
            color: var(--primary-color);
            margin-bottom: 1rem;
        }

        .file-input-wrapper {
            position: relative;
            margin-bottom: 1rem;
        }

        .file-input {
            display: none;
        }

        .file-input-label {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background-color: var(--primary-color);
            color: white;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .file-input-label:hover {
            background-color: var(--secondary-color);
        }

        .upload-status {
            margin-top: 1rem;
            padding: 0.75rem;
            border-radius: 0.5rem;
            display: none;
        }

        .upload-status.success {
            display: block;
            background-color: #dcfce7;
            color: #166534;
        }

        .upload-status.error {
            display: block;
            background-color: #fee2e2;
            color: #991b1b;
        }

        .chat-section {
            display: flex;
            flex-direction: column;
            height: 600px;
        }

        .chat-messages {
            flex-grow: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            background: var(--background-color);
            border-radius: 0.75rem;
            margin-bottom: 1rem;
        }

        .message {
            max-width: 80%;
            padding: 1rem;
            border-radius: 0.75rem;
            position: relative;
        }

        .message.user {
            background-color: var(--chat-user-bg);
            align-self: flex-end;
            border-bottom-right-radius: 0.25rem;
        }

        .message.bot {
            background-color: var(--chat-bot-bg);
            align-self: flex-start;
            border-bottom-left-radius: 0.25rem;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        }

        .message-header {
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }

        .message-content {
            word-wrap: break-word;
        }

        .input-container {
            display: flex;
            gap: 0.75rem;
            background: white;
            padding: 0.75rem;
            border-radius: 0.75rem;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        }

        .message-input {
            flex-grow: 1;
            padding: 0.75rem;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            font-size: 1rem;
            transition: border-color 0.2s;
        }

        .message-input:focus {
            outline: none;
            border-color: var(--primary-color);
        }

        .send-button {
            padding: 0.75rem 1.5rem;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: background-color 0.2s;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .send-button:hover {
            background-color: var(--secondary-color);
        }

        .send-button:disabled {
            background-color: var(--text-secondary);
            cursor: not-allowed;
        }

        .loader {
            display: inline-block;
            width: 1.5rem;
            height: 1.5rem;
            border: 3px solid #f3f3f3;
            border-top: 3px solid var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 1rem auto;
        }

        @keyframes spin {
            0% {
                transform: rotate(0deg);
            }

            100% {
                transform: rotate(360deg);
            }
        }

        .empty-state {
            text-align: center;
            color: var(--text-secondary);
            padding: 2rem;
        }

        .empty-state i {
            font-size: 3rem;
            margin-bottom: 1rem;
        }

        .upload-section {
            padding: 2rem;
            background: var(--background-color);
            border-radius: 0.75rem;
            text-align: center;
            position: relative;
        }

        .upload-box {
            border: 2px dashed var(--border-color);
            border-radius: 1rem;
            padding: 2rem;
            cursor: pointer;
            transition: border-color 0.3s, background-color 0.3s;
            margin-bottom: 1rem;
            position: relative;
        }

        .upload-box:hover {
            border-color: var(--primary-color);
            background-color: rgba(37, 99, 235, 0.05);
        }

        .upload-box.drag-over {
            border-color: var(--primary-color);
            background-color: rgba(37, 99, 235, 0.1);
        }

        .preview-container {
            margin-top: 1rem;
            display: none;
        }

        .preview-image {
            max-width: 100%;
            max-height: 200px;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }

        /* Updated file info styles for better overflow handling */
        .file-info {
            background-color: white;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-top: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            gap: 1rem;
            /* Add gap between filename and button */
            flex-wrap: nowrap;
            /* Prevent wrapping */
        }

        .file-info {
            background-color: white;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-top: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .file-info i {
            margin-right: 0.5rem;
        }

        .remove-file {
            background: none;
            border: none;
            color: #ef4444;
            cursor: pointer;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            transition: background-color 0.2s;
        }

        .remove-file:hover {
            background-color: #fee2e2;
        }

        .upload-icon {
            font-size: 3rem;
            color: var(--primary-color);
            margin-bottom: 1rem;
        }

        .upload-text {
            margin-bottom: 1rem;
        }

        .upload-text h3 {
            margin: 0;
            color: var(--text-primary);
        }

        .upload-text p {
            color: var(--text-secondary);
            margin: 0.5rem 0;
        }

        .supported-files {
            font-size: 0.875rem;
            color: var(--text-secondary);
        }

        .api-switcher {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            justify-content: center;
        }

        .api-button {
            padding: 0.75rem 1.5rem;
            border: 2px solid var(--primary-color);
            border-radius: 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
            background: white;
            color: var(--primary-color);
            font-weight: 600;
        }

        .api-button.active {
            background: var(--primary-color);
            color: white;
        }

        .api-button:hover {
            background: var(--primary-color);
            color: white;
        }

        .api-indicator {
            position: fixed;
            top: 1rem;
            right: 1rem;
            padding: 0.5rem 1rem;
            background: var(--primary-color);
            color: white;
            border-radius: 0.5rem;
            font-size: 0.875rem;
            font-weight: 600;
            z-index: 1000;
        }

        /* Additional styles for audio preview */
        .audio-preview {
            display: flex;
            align-items: center;
            gap: 1rem;
            background-color: white;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-top: 1rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .audio-preview audio {
            flex-grow: 1;
        }

        .side-menu {
            position: fixed;
            left: -300px;
            top: 0;
            height: 100vh;
            width: 300px;
            background: white;
            box-shadow: 2px 0 5px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            z-index: 1000;
            display: flex;
            flex-direction: column;
        }

        .side-menu.open {
            left: 0;
        }

        .menu-header {
            padding: 1.5rem;
            background: var(--primary-color);
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .close-menu {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            font-size: 1.2rem;
        }

        .chat-history {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }

        .chat-session {
            display: flex;
            align-items: stretch;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            transition: all 0.2s;
        }

        .chat-session:hover {
            background: var(--background-color);
        }

        .chat-session.active {
            border-color: var(--primary-color);
            background: var(--chat-user-bg);
        }

        .session-content {
            flex-grow: 1;
            padding: 1rem;
            cursor: pointer;
        }

        .delete-session-button {
            padding: 0 1rem;
            border: none;
            background: none;
            color: #ef4444;
            cursor: pointer;
            transition: background-color 0.2s;
            display: flex;
            align-items: center;
            border-left: 1px solid var(--border-color);
        }

        .delete-session-button:hover {
            background-color: #fee2e2;
        }

        .session-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }

        .session-title {
            font-weight: 600;
            color: var(--text-primary);
        }

        .session-date {
            weight: 60px;
            heighr: 60px;
            margin-left: 1rem;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }

        .session-preview {
            font-size: 0.875rem;
            color: var(--text-secondary);
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }

        .menu-trigger {
            position: fixed;
            left: 1rem;
            top: 1rem;
            padding: 0.5rem;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.5rem;
            cursor: pointer;
            z-index: 1001;
            transition: background-color 0.3s, opacity 0.3s;
            opacity: 1;
        }

        .menu-trigger.hidden {
            opacity: 0;
            pointer-events: none;
        }

        .menu-hover-zone {
            position: fixed;
            left: 0;
            top: 0;
            width: 60px;
            /* Wider than the button to make it easier to hover */
            height: 60px;
            /* Taller than the button to make it easier to hover */
            z-index: 1000;
        }

        .new-chat-button {
            margin: 1rem;
            padding: 0.75rem 1.5rem;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: background-color 0.2s;
            font-weight: bold;
        }

        .new-chat-button:hover {
            background-color: var(--secondary-color);
        }

        .menu-buttons {
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .clear-history-button {
            padding: 0.75rem 1.5rem;
            background-color: #ef4444;
            color: white;
            border: none;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: background-color 0.2s;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        .clear-history-button:hover {
            background-color: #dc2626;
        }

        .delete-session-button {
            background: none;
            border: none;
            color: #ef4444;
            cursor: pointer;
            font-size: 1rem;
            margin-left: 0.5rem;
            transition: color 0.2s;
        }

        .delete-session-button:hover {
            color: #dc2626;
        }

        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 1rem;
            background: var(--chat-bot-bg);
            border-radius: 0.75rem;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
            margin-bottom: 1rem;
            align-self: flex-start;
            border-bottom-left-radius: 0.25rem;
        }

        .typing-indicator .dots {
            display: flex;
            gap: 0.3rem;
        }

        .typing-indicator .dot {
            width: 0.5rem;
            height: 0.5rem;
            background: var(--text-secondary);
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }

        .typing-indicator .dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-indicator .dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typing {

            0%,
            60%,
            100% {
                transform: translateY(0);
                opacity: 0.4;
            }

            30% {
                transform: translateY(-4px);
                opacity: 1;
            }
        }

        .response-timer {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-left: 0.5rem;
        }

        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 1rem;
            background: var(--chat-bot-bg);
            border-radius: 0.75rem;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
            margin-bottom: 1rem;
            align-self: flex-start;
            border-bottom-left-radius: 0.25rem;
        }

        .typing-indicator-content {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .session-preview {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }
    </style>
</head>

<body>
    <div class="menu-hover-zone" id="menuHoverZone"></div>

    <button class="menu-trigger" id="menuTrigger">
        <i class="fas fa-history"></i>
    </button>

    <div class="side-menu" id="sideMenu">
        <div class="menu-header">
            <h2>Chat History</h2>
            <button class="close-menu" id="closeMenu">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="chat-history" id="chatHistory">
            <!-- Chat sessions will be added here dynamically -->
        </div>
        <div class="menu-buttons">
            <button class="new-chat-button" id="newChatButton">New Chat</button>
            <button class="clear-history-button" id="clearHistoryButton">
                <i class="fas fa-trash"></i> Clear History
            </button>
        </div>
    </div>

    <div class="container">
        <header class="app-header">
            <h1 class="app-title">Smart Document Chat Assistant</h1>
            <p class="app-subtitle">Upload PDFs, images, or audio and start asking questions</p>

            <!-- API Switcher remains the same -->
            <div class="api-switcher">
                <button class="api-button active" data-api="gemini">Gemini</button>
                <button class="api-button" data-api="cohere">Cohere</button>
                <button class="api-button" data-api="groq">Groq</button>
            </div>
        </header>

        <!-- Current API Indicator remains the same -->
        <div class="api-indicator">
            Currently using: <span id="currentApi">Gemini</span>
        </div>

        <main class="main-content">
            <section class="upload-section">
                <div id="uploadBox" class="upload-box">
                    <input type="file" id="fileInput" class="file-input" accept=".pdf,image/*,audio/*"
                        style="display: none;">
                    <div class="upload-icon">
                        <i class="fas fa-cloud-upload-alt"></i>
                    </div>
                    <div class="upload-text">
                        <h3>Drag and drop or click to upload</h3>
                        <p>Upload your PDF, image, or audio file</p>
                    </div>
                    <div class="supported-files">
                        Supported formats: PDF, JPG, PNG, GIF, MP3, WAV, M4A
                    </div>
                </div>

                <div id="previewContainer" class="preview-container">
                    <div id="fileInfo" class="file-info">
                        <span>
                            <i class="fas fa-file"></i>
                            <span id="fileName">No file selected</span>
                            <span id="fileSize" style="margin-left: 10px; color: #6b7280;"></span>
                        </span>
                        <button class="remove-file" onclick="removeFile()">
                            <i class="fas fa-times"></i> Remove
                        </button>
                    </div>
                    <img id="imagePreview" class="preview-image" style="display: none;">
                    <div id="audioPreview" class="audio-preview" style="display: none;">
                        <audio id="audioPlayer" controls></audio>
                    </div>
                </div>

                <div id="uploadStatus" class="upload-status"></div>
            </section>

            <section class="chat-section">
                <div id="chatMessages" class="chat-messages">
                    <div class="empty-state">
                        <i class="fas fa-comments"></i>
                        <p>Upload a file and start asking questions</p>
                    </div>
                </div>
                <div class="input-container">
                    <input type="text" id="userInput" class="message-input"
                        placeholder="Upload a file to start chatting..." disabled>
                    <button class="send-button" disabled id="sendButton">
                        <i class="fas fa-paper-plane"></i> Send
                    </button>
                </div>
            </section>
        </main>
    </div>

    <script>
        let currentApi = 'Gemini'; // Global variable to track current API
        let currentContent = {
            type: null,  // 'pdf', 'image', or 'audio'
            data: null
        };

        const uploadBox = document.getElementById('uploadBox');
        const fileInput = document.getElementById('fileInput');
        const previewContainer = document.getElementById('previewContainer');
        const imagePreview = document.getElementById('imagePreview');
        const fileName = document.getElementById('fileName');
        const uploadStatus = document.getElementById('uploadStatus');
        const userInput = document.getElementById('userInput');
        const sendButton = document.getElementById('sendButton');
        const chatMessages = document.getElementById('chatMessages');
        const currentApiIndicator = document.getElementById('currentApi');
        const apiButtons = document.querySelectorAll('.api-button');

        const chatSessions = new Map(); // Store chat sessions
        const sideMenu = document.getElementById('sideMenu');
        const menuTrigger = document.getElementById('menuTrigger');
        const closeMenu = document.getElementById('closeMenu');
        const chatHistory = document.getElementById('chatHistory');
        const newChatButton = document.getElementById('newChatButton');
        const clearHistoryButton = document.getElementById('clearHistoryButton');

        let currentSessionId = null;

        // Menu toggle functions
        menuTrigger.addEventListener('click', () => {
            sideMenu.classList.add('open');
        });

        closeMenu.addEventListener('click', () => {
            sideMenu.classList.remove('open');
        });

        // New Chat button functionality
        newChatButton.addEventListener('click', () => {
            createNewSession();
            sideMenu.classList.remove('open'); // Optionally close the menu after starting a new chat
        });

        // Chat session management
        function createNewSession() {
            // Ensure we clear any existing data
            if (currentSessionId && chatSessions.has(currentSessionId)) {
                const existingSession = chatSessions.get(currentSessionId);
                existingSession.messages = [];
                existingSession.content = { type: null, data: null };
                existingSession.lastUploadedFile = null;
            }




            const sessionId = generateUniqueSessionId();
            const session = {
                id: sessionId,
                title: `Chat Session ${chatSessions.size + 1}`,
                date: new Date(),
                messages: [],
                content: {
                    type: null,
                    data: null
                },
                lastUploadedFile: null
            };

            chatSessions.set(sessionId, session);
            currentSessionId = sessionId;

            currentContent = {
                type: null,
                data: null
            };

            updateChatHistory();
            chatMessages.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-comments"></i>
            <p>Upload a file and start asking questions</p>
        </div>
    `;
            enableChat();

            previewContainer.style.display = 'none';

            saveChatSessions();
        }

        function generateUniqueSessionId() {
            // Combine timestamp with a random component
            return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        }

        function truncateText(text, maxLength = 20) {
            if (!text || text.length <= maxLength) return text;
            return text.substring(0, maxLength) + '...';
        }

        function updateChatHistory() {
            chatHistory.innerHTML = '';
            const sortedSessions = Array.from(chatSessions.values())
                .sort((a, b) => b.date - a.date);

            sortedSessions.forEach(session => {
                const sessionElement = document.createElement('div');
                sessionElement.className = `chat-session ${session.id === currentSessionId ? 'active' : ''}`;

                // Create the session content div (clickable area)
                const sessionContent = document.createElement('div');
                sessionContent.className = 'session-content';

                // Shorten file name for session title
                const sessionTitle = session.lastUploadedFile
                    ? shortenFileName(session.lastUploadedFile.name, 15)  // Reduced length for better layout
                    : `Chat Session ${chatSessions.size}`;

                // Truncate last message for preview
                const lastMessagePreview = session.messages.length
                    ? truncateText(session.messages[session.messages.length - 1].text)
                    : 'No messages yet';

                sessionContent.innerHTML = `
            <div class="session-header">
                <span class="session-title">${session.title}</span>
                <span class="session-date">${formatDate(session.date)}</span>
            </div>
            <div class="session-preview">
                ${lastMessagePreview}
            </div>
        `;

                // Create delete button
                const deleteButton = document.createElement('button');
                deleteButton.className = 'delete-session-button';
                deleteButton.innerHTML = '<i class="fas fa-trash"></i>';

                // Add click handlers
                sessionContent.addEventListener('click', () => loadSession(session.id));
                deleteButton.addEventListener('click', (e) => {
                    e.stopPropagation();
                    deleteSession(session.id);
                });

                // Assemble the session element
                sessionElement.appendChild(sessionContent);
                sessionElement.appendChild(deleteButton);
                chatHistory.appendChild(sessionElement);
            });
        }
        function formatDate(date) {
            return new Date(date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        function loadSession(sessionId) {
            const session = chatSessions.get(sessionId);
            if (!session) return;

            currentSessionId = sessionId;
            currentContent = { ...session.content };

            // Clear existing messages before restoring
            chatMessages.innerHTML = '';

            // Restore chat messages
            session.messages.forEach(msg => {
                if (msg.sender === 'bot' && msg.apiName) {
                    currentApi = msg.apiName;
                }
                const messageDiv = createMessageElement(msg.sender, msg.text, msg.responseTime);
                chatMessages.appendChild(messageDiv);
            });

            // Restore file preview if exists
            if (session.lastUploadedFile) {
                // Use shortenFileName for display
                fileName.textContent = shortenFileName(session.lastUploadedFile.name);
                previewContainer.style.display = 'block';

                // Reset all previews first
                imagePreview.style.display = 'none';
                audioPreview.style.display = 'none';

                if (session.lastUploadedFile.type.startsWith('image/')) {
                    imagePreview.src = session.lastUploadedFile.data;
                    imagePreview.style.display = 'block';
                } else if (session.lastUploadedFile.type.startsWith('audio/')) {
                    audioPlayer.src = session.lastUploadedFile.data;
                    audioPreview.style.display = 'flex';
                }
            } else {
                previewContainer.style.display = 'none';
            }

            enableChat();
            updateChatHistory();
            saveChatSessions();
            sideMenu.classList.remove('open');
        }


        function clearChatHistory() {
            chatSessions.clear();
            currentSessionId = null;
            currentContent = { type: null, data: null };
            localStorage.removeItem('chatSessions');
            localStorage.removeItem('currentSessionId');
            updateChatHistory();
            createNewSession();
        }

        // API Switcher Event Listeners
        apiButtons.forEach(button => {
            button.addEventListener('click', function () {
                // Remove active class from all buttons
                apiButtons.forEach(btn => btn.classList.remove('active'));

                // Add active class to clicked button
                this.classList.add('active');

                // Update current API
                currentApi = this.getAttribute('data-api').charAt(0).toUpperCase() + this.getAttribute('data-api').slice(1);
                currentApiIndicator.textContent = currentApi;
            });
        });

        // Drag and drop handlers
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadBox.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadBox.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadBox.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            uploadBox.classList.add('drag-over');
        }

        function unhighlight(e) {
            uploadBox.classList.remove('drag-over');
        }

        uploadBox.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const file = dt.files[0];
            handleFile(file);
        }

        // Click to upload
        uploadBox.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                handleFile(e.target.files[0]);
            }
        });
        function shortenFileName(fileName, maxLength = 17) {
            if (!fileName || fileName.length <= maxLength) return fileName;

            const extension = fileName.split('.').pop();
            const nameWithoutExtension = fileName.substring(0, fileName.lastIndexOf('.'));

            if (nameWithoutExtension.length > maxLength - extension.length - 3) {
                return `${nameWithoutExtension.substring(0, maxLength - extension.length - 3)}...${extension}`;
            }

            return fileName;
        }



        async function handleFile(file) {
            if (!file) return;

            // Check file size (e.g., 10MB maximum)
            const MAX_FILE_SIZE = 100 * 1024 * 1024; // 10MB in bytes
            if (file.size > MAX_FILE_SIZE) {
                uploadStatus.textContent = `File too large. Maximum size is 10MB`;
                uploadStatus.className = 'upload-status error';
                return;
            }

            // Reset status
            uploadStatus.className = 'upload-status';
            uploadStatus.textContent = '';

            // Show shortened file name
            fileName.textContent = shortenFileName(file.name);
            previewContainer.style.display = 'block';

            // Reset previous previews
            imagePreview.style.display = 'none';
            audioPreview.style.display = 'none';

            let fileData = null;

            if (file.type.startsWith('image/')) {
                currentContent.type = 'image';
                const reader = new FileReader();
                reader.onload = async (e) => {
                    fileData = e.target.result;
                    imagePreview.src = fileData;
                    imagePreview.style.display = 'block';
                    await uploadFile(file, '/upload_image', fileData);
                }
                reader.readAsDataURL(file);
            } else if (file.type === 'application/pdf') {
                currentContent.type = 'pdf';
                await uploadFile(file, '/upload', null);
            } else if (file.type.startsWith('audio/')) {
                currentContent.type = 'audio';
                const reader = new FileReader();
                reader.onload = async (e) => {
                    fileData = e.target.result;
                    audioPlayer.src = fileData;
                    audioPreview.style.display = 'flex';
                    await uploadFile(file, '/upload_audio', fileData);
                }
                reader.readAsDataURL(file);
            } else {
                uploadStatus.textContent = 'Unsupported file type';
                uploadStatus.classList.add('error');
                return;
            }

            // Handle session management
            if (!currentSessionId || !chatSessions.has(currentSessionId)) {
                createNewSession();
            } else {
                const session = chatSessions.get(currentSessionId);
                session.content = { ...currentContent };
                session.lastUploadedFile = {
                    name: file.name,
                    type: file.type,
                    data: fileData
                };
            }

            enableChat();
            saveChatSessions();
        }
        // Add event listeners for page load and unload
        window.addEventListener('load', loadChatSessions);
        window.addEventListener('beforeunload', saveChatSessions);

        function removeFile() {
            // Reset file input
            fileInput.value = '';

            // Hide preview container
            previewContainer.style.display = 'none';

            // Reset content
            currentContent = {
                type: null,
                data: null
            };

            // Disable chat and update placeholder
            userInput.disabled = true;
            sendButton.disabled = true;
            userInput.placeholder = "Upload a file to start chatting...";

            // Reset upload status
            uploadStatus.textContent = '';
            uploadStatus.className = 'upload-status';

            // Restore empty state in chat messages
            chatMessages.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-comments"></i>
            <p>Upload a file and start asking questions</p>
        </div>
    `;
        }

        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;

            // Store the current session ID when sending the message
            const requestSessionId = currentSessionId;

            appendMessage('user', message);
            userInput.value = '';
            userInput.disabled = true;
            sendButton.disabled = true;

            // Create typing indicator with timer and current API name
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator';
            typingIndicator.innerHTML = `
                <div class="typing-indicator-content">
                    <div class="message-header">${currentApi}</div>
                    <div class="dots">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                    <div class="response-timer">0.0s</div>
                </div>
            `;

            // Only append typing indicator if we're still in the same session
            if (requestSessionId === currentSessionId) {
                chatMessages.appendChild(typingIndicator);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            // Start timer
            const startTime = Date.now();
            const timerInterval = setInterval(() => {
                if (typingIndicator.parentNode) {  // Only update if indicator is still in DOM
                    const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
                    const timerElement = typingIndicator.querySelector('.response-timer');
                    if (timerElement) {
                        timerElement.textContent = `${elapsedTime}s`;
                    }
                }
            }, 100);

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message,
                        content_type: currentContent.type,
                        content_data: currentContent.data,
                        api: currentApi.toLowerCase(),
                        sessionId: requestSessionId  // Include session ID in request
                    }),
                });
                const result = await response.json();

                // Calculate final response time
                const responseTime = ((Date.now() - startTime) / 1000).toFixed(1);

                // Clear timer interval
                clearInterval(timerInterval);

                // Remove typing indicator if it exists
                if (typingIndicator.parentNode) {
                    typingIndicator.remove();
                }

                if (result.success) {
                    // Store response in the correct session
                    const session = chatSessions.get(requestSessionId);
                    if (session) {
                        session.messages.push({
                            sender: 'bot',
                            text: result.response,
                            responseTime,
                            apiName: currentApi
                        });
                        saveChatSessions();

                        // Only display if we're still in the same session
                        if (requestSessionId === currentSessionId) {
                            appendMessage('bot', result.response, responseTime);
                        }
                    }
                } else {
                    const errorMessage = result.error || "I apologize, but I encountered an error processing your request.";
                    if (requestSessionId === currentSessionId) {
                        appendMessage('bot', errorMessage, responseTime);
                    }
                }
            } catch (error) {
                // Clear timer interval
                clearInterval(timerInterval);

                // Remove typing indicator if it exists
                if (typingIndicator.parentNode) {
                    typingIndicator.remove();
                }

                if (requestSessionId === currentSessionId) {
                    appendMessage('bot', "I apologize, but I encountered an error processing your request. Please try again.");
                }
                console.error(error);
            }

            userInput.disabled = false;
            sendButton.disabled = false;
            userInput.focus();
        }
        async function uploadFile(file, endpoint, fileData) {
    try {
        // Show upload status immediately
        uploadStatus.textContent = "Uploading file...";
        uploadStatus.className = 'upload-status success';
        userInput.disabled = true;
        sendButton.disabled = true;
        userInput.placeholder = "Uploading file...";

        const formData = new FormData();
        const fileKey = endpoint === '/upload' ? 'pdf' :
            endpoint === '/upload_image' ? 'image' : 'audio';
        formData.append(fileKey, file);

        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        const result = await response.json();

        // Validate the response content immediately
        if (endpoint === '/upload' && (!result.content || typeof result.content !== 'string')) {
            throw new Error('Invalid PDF content received from server');
        }

        // Create new session if needed
        if (!currentSessionId || !chatSessions.has(currentSessionId)) {
            createNewSession();
        }

        // Clear existing messages
        if (chatMessages.querySelector('.empty-state')) {
            chatMessages.innerHTML = '';
        }

        // Set current content based on file type
        if (endpoint === '/upload') {
            currentContent = {
                type: 'pdf',
                data: result.content.trim()
            };
            // Save PDF content immediately
            localStorage.setItem('currentContent', JSON.stringify(currentContent));
        } else {
            currentContent = endpoint === '/upload_image'
                ? { type: 'image', data: result.image_data || fileData }
                : { type: 'audio', data: result.transcription };
        }

        // Update session data
        const session = chatSessions.get(currentSessionId);
        if (session) {
            session.content = { ...currentContent };
            session.lastUploadedFile = {
                name: file.name,
                type: file.type,
                data: fileData
            };

            // Add upload message if it doesn't exist
            const uploadMessage = `New file uploaded: ${file.name}`;
            if (!session.messages.some(msg => msg.sender === 'bot' && msg.text === uploadMessage)) {
                appendMessage('bot', uploadMessage);
            }

            saveChatSessions();
        }

        // Update UI for success
        uploadStatus.textContent = "File uploaded successfully!";
        uploadStatus.className = 'upload-status success';
        userInput.disabled = false;
        sendButton.disabled = false;
        userInput.placeholder = "Type your question...";
        previewContainer.style.display = 'block';

    } catch (error) {
        console.error('Upload error:', error);
        uploadStatus.textContent = `Upload failed: ${error.message}. Please try again.`;
        uploadStatus.className = 'upload-status error';

        if (!file.type.startsWith('audio/')) {
            previewContainer.style.display = 'none';
        }

        currentContent = { type: null, data: null };
        userInput.disabled = true;
        sendButton.disabled = true;
        userInput.placeholder = "Upload a file to start chatting...";

        // Clear localStorage on error
        localStorage.removeItem('currentContent');
    }
}




        function enableChat() {
            userInput.disabled = false;
            sendButton.disabled = false;

            // Only clear messages if this is a brand new session with no messages
            if (currentSessionId) {
                const session = chatSessions.get(currentSessionId);
                if (!session || !session.messages || session.messages.length === 0) {
                    chatMessages.innerHTML = '';
                }
            }
        }

        function appendMessage(sender, text, responseTime = null) {
            const messageDiv = createMessageElement(sender, text, responseTime);
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            if (currentSessionId) {
                const session = chatSessions.get(currentSessionId);
                if (session) {
                    // Only add messages that are unique
                    const isDuplicate = session.messages.some(msg =>
                        msg.sender === sender &&
                        msg.text === text &&
                        (responseTime ? msg.responseTime === responseTime : true)
                    );

                    if (!isDuplicate) {
                        session.messages.push({
                            sender,
                            text,
                            responseTime,
                            apiName: sender === 'bot' ? currentApi : null
                        });

                        updateChatHistory();
                        saveChatSessions();
                    }
                }
            }
        }
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });


        function loadChatSessions() {
            try {
                const savedSessions = localStorage.getItem('chatSessions');

                if (savedSessions) {
                    const sessionsData = JSON.parse(savedSessions);
                    chatSessions.clear();

                    sessionsData.forEach(([id, sessionData]) => {
                        const restoredSession = {
                            ...sessionData,
                            date: new Date(sessionData.date),
                            // Ensure last uploaded file is preserved
                            lastUploadedFile: sessionData.lastUploadedFile || null
                        };

                        chatSessions.set(id, restoredSession);
                    });

                    // Create new session if no valid sessions exist
                    if (chatSessions.size === 0) {
                        createNewSession();
                    } else {
                        updateChatHistory();
                    }
                } else {
                    createNewSession();
                }
            } catch (error) {
                console.error('Session load error');
                createNewSession();
            }
        }

        function saveChatSessions() {
            // Only save sessions with messages
            const validSessions = Array.from(chatSessions.entries())
                .filter(([id, session]) => session.messages && session.messages.length > 0);

            try {
                localStorage.setItem('chatSessions', JSON.stringify(validSessions));
            } catch (error) {
                console.error('Save sessions failed');
            }
        }

        // Add event listener for clear history button
        clearHistoryButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear all chat history? This action cannot be undone.')) {
                clearChatHistory();
                sideMenu.classList.remove('open');
            }
        });

        // New helper function to create message elements
        function createMessageElement(sender, text, responseTime = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;

            const header = document.createElement('div');
            header.className = 'message-header';
            header.textContent = sender === 'user' ? 'You' : currentApi;

            // Add response time if available
            if (responseTime && sender === 'bot') {
                const timeSpan = document.createElement('span');
                timeSpan.className = 'response-timer';
                timeSpan.textContent = `${responseTime}s`;
                header.appendChild(timeSpan);
            }

            const content = document.createElement('div');
            content.className = 'message-content';

            let formattedText = text
                .replace(/(^\d+\.\s+)\*\*(.+?)\*\*(?=\s|$)/gm, (match, number, heading) => {
                    return `<div style="margin: 1rem 0; font-size: 1.5rem; font-weight: bold;">${number}${heading}</div>`;
                })
                .replace(/^(?!\d+\.)\s*\*\*(.+?)\*\*(?=\s|$)/gm, (match, heading) => {
                    return `<div style="margin: 1rem 0; font-size: 1.5rem; font-weight: bold;">${heading}</div>`;
                })
                .replace(/^\*\s+\*\*(.+?)\*\*(?=\s|$)/gm, (match, bullet) => {
                    return `<div style="border-radius: 10px; padding: 10px; margin: 1rem 0; font-size: 1.5rem; font-weight: bold;">• ${bullet}</div>`;
                })
                .replace(/^\*\s+((?!\*\*).+)/gm, (match, bullet) => {
                    return `<div style="border-radius: 10px; padding: 10px; margin: 1rem 0;">• ${bullet}</div>`;
                })
                .replace(/(^\d+\.\s+)(.+?)(?=\s|$)/gm, (match, number, content) => {
                    return `<div style="margin: 1rem 0;">${number}${content}</div>`;
                })
                .trim();

            content.innerHTML = formattedText;
            messageDiv.appendChild(header);
            messageDiv.appendChild(content);

            return messageDiv;
        }

        // Add the deleteSession function
        function deleteSession(sessionId) {
            chatSessions.delete(sessionId);
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                chatMessages.innerHTML = '';
                previewContainer.style.display = 'none';
                createNewSession();
            }
            updateChatHistory();
            saveChatSessions();
        }

        const menuHoverZone = document.getElementById('menuHoverZone');
        let menuTimeout;

        menuHoverZone.addEventListener('mouseenter', () => {
            clearTimeout(menuTimeout);
            sideMenu.classList.add('open');
            menuTrigger.classList.add('hidden');
        });

        sideMenu.addEventListener('mouseenter', () => {
            clearTimeout(menuTimeout);
        });

        menuHoverZone.addEventListener('mouseleave', () => {
            menuTimeout = setTimeout(() => {
                if (!sideMenu.matches(':hover')) {
                    sideMenu.classList.remove('open');
                    menuTrigger.classList.remove('hidden');
                }
            }, 300);
        });

        sideMenu.addEventListener('mouseleave', () => {
            menuTimeout = setTimeout(() => {
                sideMenu.classList.remove('open');
                menuTrigger.classList.remove('hidden');
            }, 300);
        });

        closeMenu.addEventListener('click', () => {
            sideMenu.classList.remove('open');
            menuTrigger.classList.remove('hidden');
        });

        // 页面加载时恢复内容
        document.addEventListener('DOMContentLoaded', () => {
            const savedContent = localStorage.getItem('currentContent');
            if (savedContent) {
                currentContent = JSON.parse(savedContent);
                console.log('Content restored:', currentContent);
            }
        });

        // Add this near the other event listeners in the script section
        sendButton.addEventListener('click', () => {
            sendMessage();
        });


    </script>
</body>


</html>
'''

def clean_base64_data(base64_string):
    """
    Clean and validate base64 image data
    """
    # Remove data URL prefix if present
    if base64_string.startswith('data:image'):
        base64_string = re.sub('^data:image/.+;base64,', '', base64_string)

    # Ensure the string contains valid base64 characters
    if not re.match('^[A-Za-z0-9+/]+={0,2}$', base64_string):
        raise ValueError("Invalid base64 string")

    return base64_string

def process_image(image_file):
    """
    Process uploaded image and convert to base64 string with proper formatting
    """
    try:
        # Read the image using PIL
        img = Image.open(image_file)

        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize image if it's too large
        max_size = (1600, 1600)  # Maximum dimensions
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Create a byte buffer to store the image
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        # Convert to base64
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return image_base64
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")

def extract_text_from_pdf(pdf_file):
    """
    Extract text from a PDF file.
    """
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded.'})
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected.'})
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            pdf_text = extract_text_from_pdf(temp_file.name)
        os.unlink(temp_file.name)
        return jsonify({'success': True, 'content': pdf_text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image uploaded.'})
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No image selected.'})
    try:
        # Process the image and convert to base64
        image_base64 = process_image(file)
        return jsonify({'success': True, 'image_data': image_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# Update the existing chat route to include audio handling
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        content_type = data.get('content_type', '')
        content_data = data.get('content_data', '')
        selected_api = data.get('api', 'gemini')  # Default to Gemini

      #  print(f"Chat Request Details:")
      #  print(f"Message: {user_message}")
      #  print(f"Content Type: {content_type}")
      #  print(f"Selected API: {selected_api}")

        # Validation checks
        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400

        if content_type == 'image':
            # Handle image-based queries
            if selected_api == 'gemini':
                return handle_gemini_vision(user_message, content_data)
            elif selected_api == 'cohere':
                return handle_cohere_vision(user_message, content_data)
            elif selected_api == 'groq':
                return handle_groq_vision(user_message, content_data)

        elif content_type == 'audio':
            if selected_api == 'gemini':
                return handle_gemini_audio(user_message, content_data)
            elif selected_api == 'cohere':
                return handle_cohere_audio(user_message, content_data)
            elif selected_api == 'groq':
                return handle_groq_audio(user_message, content_data)

        else:
            # Handle PDF-based queries
            if selected_api == 'gemini':
                return handle_gemini_text(user_message, content_data)
            elif selected_api == 'cohere':
                return handle_cohere_text(user_message, content_data)
            elif selected_api == 'groq':
                return handle_groq_text(user_message, content_data)

    except Exception as e:
        print(f"Chat Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def handle_gemini_audio(user_message, audio_transcription):
    try:
        # Extensive logging
       # print(f"Gemini Audio Input - Transcription: {audio_transcription}")
       # print(f"Gemini Audio Input - User Message: {user_message}")

        full_prompt = f"""
        Audio Transcription: {audio_transcription}

        User Question: {user_message}

        Please provide a detailed response based on the audio content and the user's question.
        """

    #    print(f"Full Prompt: {full_prompt}")

        response = text_model.generate_content(full_prompt)

        print(f"Gemini Response: {response.text}")

        return jsonify({'success': True, 'response': response.text})
    except Exception as e:
        print(f"Gemini Audio API Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f"Gemini Audio API Error: {str(e)}"})

def handle_cohere_audio(user_message, audio_transcription):
    try:
        # Extensive logging
       # print(f"Cohere Audio Input - Transcription: {audio_transcription}")
       # print(f"Cohere Audio Input - User Message: {user_message}")

        full_prompt = f"""
        Audio Transcription: {audio_transcription}

        User Question: {user_message}

        Please provide a detailed response based on the audio content and the user's question.
        """

       # print(f"Full Prompt: {full_prompt}")

        response = cohere_client.chat(
            message=full_prompt,
            model='command-r7b-arabic-02-2025',
            temperature=0.4
        )

        print(f"Cohere Response: {response.text}")

        return jsonify({
            'success': True,
            'response': response.text
        })
    except Exception as e:
        print(f"Cohere Audio API Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f"Cohere Audio API Error: {str(e)}"
        })

def handle_groq_audio(user_message, audio_transcription):
    try:
        full_prompt = f"""
        Audio Transcription: {audio_transcription}

        User Question: {user_message}

        Please provide a detailed response based on the audio content and the user's question.
        Carefully analyze the transcription and generate a relevant response.
        """

        response = groq_client.chat.completions.create(
            model="Meta-Llama/Llama-4-Scout-17b-16e-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant that can analyze audio transcriptions and answer questions about them."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            temperature=0.4
        )

        return jsonify({
            'success': True,
            'response': response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Groq Audio API Error: {str(e)}"
        })




def handle_gemini_vision(user_message, image_data):
    try:
        clean_base64 = clean_base64_data(image_data)
        prompt_parts = [
            user_message,
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": clean_base64
                }
            }
        ]
        response = vision_model.generate_content(prompt_parts)
        return jsonify({'success': True, 'response': response.text})
    except Exception as e:
        return jsonify({'success': False, 'error': f"Gemini Vision API Error: {str(e)}"})

def handle_cohere_vision(user_message, image_data):
    return jsonify({
        'success': False,
        'error': "Cohere does not support image processing via chat API."
    })


def handle_groq_vision(user_message, image_data):
    try:
        clean_base64 = clean_base64_data(image_data)

        response = groq_client.chat.completions.create(
            model="Meta-Llama/Llama-4-Scout-17b-16e-Instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyze the image and help me with this specific question: {user_message}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{clean_base64}"}
                        }
                    ]
                }
            ]
        )

        return jsonify({
            'success': True,
            'response': response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Groq Vision API Error: {str(e)}"
        })


def handle_gemini_text(user_message, content_data):
    try:
        prompt = f"""
        Context from PDF:
        {content_data}

        User Question: {user_message}

        Please provide a detailed and accurate response based on the PDF content above.
        """
        response = text_model.generate_content(prompt)
        return jsonify({'success': True, 'response': response.text})
    except Exception as e:
        return jsonify({'success': False, 'error': f"Gemini Text API Error: {str(e)}"})

def handle_cohere_text(user_message, content_data):
    try:
        prompt = f"""
        Context from PDF:
        {content_data}

        User Question: {user_message}

        Please provide a detailed and accurate response based on the PDF content above.
        """

        response = cohere_client.chat(
            message=prompt,
            model='command-r7b-arabic-02-2025',
            temperature=0.4
        )

        return jsonify({
            'success': True,
            'response': response.text
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Cohere API Error: {str(e)}"
        })

def handle_groq_text(user_message, content_data):
    try:
        prompt = f"""
        Context from PDF:
        {content_data}

        User Question: {user_message}

        Please provide a detailed and accurate response based on the PDF content above.
        Focus on answering the specific question while maintaining context from the document.
        If the answer cannot be found in the PDF content, please indicate that.
        """

        response = groq_client.chat.completions.create(
            model="Meta-Llama/Llama-4-Scout-17b-16e-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant that provides accurate and detailed answers based on the given context."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4
        )

        return jsonify({
            'success': True,
            'response': response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Groq API Error: {str(e)}"
        })




def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(audio_path) as source:
            print("Opened audio file successfully")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

        # First try English recognition with multiple variants
        english_variants = [
            ('en-GB', 'English (UK)'),
            ('en-US', 'English (US)')

        ]

        # Try English recognition first
        for lang_code, lang_name in english_variants:
            try:
                print(f"Attempting recognition with {lang_name}")
                text = recognizer.recognize_google(
                    audio_data,
                    language=lang_code
                )

                # Validate the transcription result
                if text and isinstance(text, str) and not text.replace('.', '').replace(' ', '').isnumeric():
                    return {
                        'text': text,
                        'language': lang_name,
                        'confidence': 0.8
                    }
            except sr.RequestError as e:
                print(f"API Error for {lang_name}: {str(e)}")
                continue
            except sr.UnknownValueError:
                print(f"Could not understand audio with {lang_name}")
                continue
            except Exception as e:
                print(f"Error with {lang_name}: {str(e)}")
                continue

        # If English fails, try Chinese variants
        chinese_variants = [
                    ('ko', 'Korean'),
            ('zh-CN', 'Chinese (Mainland)'),
            ('zh-TW', 'Chinese (Taiwan)'),


        ('es', 'Spanish'),  #gemini not support
        ('fr', 'French'),
        ('hi', 'Hindi'),
        ]
        # japanese, German, Italian, Portuguese, Russian, thai,malay
        for lang_code, lang_name in chinese_variants:
            try:
                text = recognizer.recognize_google(
                    audio_data,
                    language=lang_code
                )
                if text and isinstance(text, str):
                    return {
                        'text': text,
                        'language': lang_name,
                        'confidence': 0.8
                    }
            except Exception as e:
                print(f"Failed for {lang_name}: {str(e)}")
                continue

        # If Google API fails, try offline Sphinx for English
        try:
            text = recognizer.recognize_sphinx(audio_data)
            if text and isinstance(text, str) and not text.replace('.', '').replace(' ', '').isnumeric():
                return {
                    'text': text,
                    'language': 'English (Sphinx)',
                    'confidence': 0.6
                }
        except Exception as sphinx_error:
            print(f"Sphinx fallback failed: {sphinx_error}")

        return {
            'text': "Could not recognize speech content",
            'language': None,
            'confidence': 0
        }

    except Exception as e:
        print(f"Critical transcription error: {str(e)}")
        print(traceback.format_exc())
        return {
            'text': "Audio processing error",
            'language': None,
            'confidence': 0
        }

def process_audio_upload(file_path):
    """
    Process audio file from a file path instead of file object
    """
    try:
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'File not found'
            }

        # Convert to WAV format
        wav_path = convert_audio_to_wav_from_path(file_path)

        try:
            # Get transcription
            transcription_result = transcribe_audio(wav_path)

            # Get audio duration
            audio = AudioSegment.from_file(wav_path)
            duration = len(audio) / 1000

            return {
                'success': True,
                'filename': os.path.basename(file_path),
                'transcription': transcription_result['text'],
                'detected_language': transcription_result['language'],
                'confidence': transcription_result['confidence'],
                'duration': duration
            }

        finally:
            # Clean up temporary WAV file
            if os.path.exists(wav_path):
                os.remove(wav_path)

    except Exception as e:
        print(f"Audio processing error: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': f'Audio processing error: {str(e)}'
        }

def convert_audio_to_wav_from_path(input_path):
    """
    Convert audio file to WAV format from a file path
    """
    try:
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f'converted_{os.getpid()}.wav')

        # Use FFmpeg for conversion
        subprocess.run([
            ffmpeg_path,
            '-i', input_path,
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            output_path
        ], check=True, capture_output=True)

        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Converted WAV file not created: {output_path}")

        return output_path

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg conversion error: {e.stderr.decode()}")
        raise
    except Exception as e:
        print(f"Conversion error: {str(e)}")
        raise

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    try:
        if 'audio' not in request.files:
            app.logger.warning("No audio file in request")
            return jsonify({'success': False, 'error': 'No audio file'}), 400

        audio_file = request.files['audio']

        # Save the audio file to a temporary location
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, secure_filename(audio_file.filename))

        try:
            audio_file.save(temp_path)

            # Process the saved audio file
            result = process_audio_upload(temp_path)

            return jsonify(result)

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        app.logger.error(f"Audio upload error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Audio upload error: {str(e)}'
        }), 500

def run_app():
    print("App is running. Access it at: http://localhost:5000")
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    run_app()