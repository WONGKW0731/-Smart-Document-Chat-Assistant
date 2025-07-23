Of course\! Here is a comprehensive README.md file for your project, explaining what the application does and detailing the crucial setup steps a user needs to follow.

-----

# Smart Document Chat Assistant 🤖

This project is a versatile, web-based chat assistant built with Flask that allows you to interact with various types of documents using powerful Large Language Models (LLMs). You can upload a PDF, an image, or an audio file and ask questions about its content. The application supports switching between multiple AI providers: **Google Gemini**, **Cohere**, and **Groq**.

  

-----

## ✨ Features

  * **Multi-Modal Interaction**: Chat with different file types.
      * 📖 **PDFs**: Upload a PDF and ask questions about its text content.
      * 🖼️ **Images**: Upload an image and use vision-enabled models to analyze it.
      * 🎤 **Audio**: Upload common audio formats (`.mp3`, `.wav`, etc.), have them automatically transcribed, and then ask questions about the transcription.
  * **Dynamic AI Switching**: Seamlessly switch between **Gemini**, **Cohere**, and **Groq** APIs to compare responses or use your preferred model.
  * **Chat History**: Your conversations are saved in browser sessions, allowing you to resume previous chats.
  * **User-Friendly Interface**: A clean, modern UI with drag-and-drop file uploads, file previews, and a real-time chat display.

-----

## 🛠️ Tech Stack

  * **Backend**: Flask (Python)
  * **Frontend**: HTML, CSS, JavaScript (served directly from Flask)
  * **AI Models**:
      * `google-generativeai` for Google Gemini
      * `cohere` for Cohere
      * `groq` for Groq
  * **Core Python Libraries**:
      * `PyPDF2` for PDF text extraction.
      * `Pillow` for image processing.
      * `pydub` & `SpeechRecognition` for audio processing and transcription.

-----

## ⚠️ Important: Before You Start

This application relies on external services and a crucial local dependency. Please review these points carefully before installation.

### 1\. API Keys

You **must** have valid API keys for the services you intend to use (Gemini, Cohere, Groq). The application will not work without them.

### 2\. FFmpeg Installation

**FFmpeg** is a critical dependency required for processing audio files (converting them to a compatible format for transcription). It must be installed separately on your system.

  * **Windows**:

    1.  Download a static build from [ffmpeg.org](https://ffmpeg.org/download.html).
    2.  Extract the folder (e.g., to `C:\ffmpeg`).
    3.  Add the `bin` directory (e.g., `C:\ffmpeg\bin`) to your system's **PATH** environment variable.

  * **macOS** (using Homebrew):

    ```bash
    brew install ffmpeg
    ```

  * **Linux** (using apt for Debian/Ubuntu):

    ```bash
    sudo apt update && sudo apt install ffmpeg
    ```

-----

## 🚀 Getting Started

Follow these steps to set up and run the project on your local machine.

### 1\. Clone the Repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2\. Create a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS & Linux
python3 -m venv venv
source venv/bin/activate
```

### 3\. Install Dependencies

[cite\_start]Install all the required Python packages using the `requirements.txt` file[cite: 1].

```bash
pip install -r requirements.txt
```

### 4\. Configure Your API Keys

Open the `NLP.py` file and replace the empty placeholder strings with your actual API keys.

```python
# NLP.py - Lines 21-23

# IMPORTANT: Replace these with your actual API keys
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"
COHERE_API_KEY = "YOUR_COHERE_API_KEY_HERE"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
```

### 5\. Configure FFmpeg Path (Crucial Step\!)

The script needs to know where the FFmpeg executable is located. The current code has a **hardcoded path for Windows**. You **must** update this if your path is different or if you are on macOS or Linux.

  * **If you added FFmpeg to your system PATH (recommended)**, you can try commenting out or deleting the hardcoded lines. The `pydub` library often finds it automatically.
  * **If not**, update the paths in `NLP.py` to point to your FFmpeg executables.

<!-- end list -->

```python
# NLP.py - Lines 14-15 and 33-36

# For Windows (adjust if your path is different)
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"

# You might need to adjust these paths as well
ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
ffprobe_path = r"C:\ffmpeg\bin\ffprobe.exe"
```

For **macOS/Linux**, the paths are typically found automatically if installed via a package manager. If not, you may need to find them (`which ffmpeg`) and set the path accordingly (e.g., `/usr/bin/ffmpeg` or `/opt/homebrew/bin/ffmpeg`).

### 6\. Run the Application

Once the setup is complete, run the Flask application:

```bash
python NLP.py
```

Open your web browser and navigate to **[http://127.0.0.1:5000](https://www.google.com/search?q=http://127.0.0.1:5000)** to start using the chat assistant\!

-----

## 📝 How to Use

1.  **Select an AI**: Choose your preferred AI model (Gemini, Cohere, or Groq) using the buttons at the top.
2.  **Upload a File**: Drag and drop a PDF, image, or audio file into the upload box, or click to select one.
3.  **Wait for Processing**: The file will be uploaded and processed. For audio, transcription may take a moment.
4.  **Start Chatting**: Once the file is ready, the input box will be enabled. Type your question and press Enter or click the "Send" button.
5.  **Manage Chats**: Use the history panel on the left to switch between different chat sessions or clear your history.
