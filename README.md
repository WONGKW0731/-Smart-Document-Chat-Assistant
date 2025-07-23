# How to Install FFmpeg 🎬

A straightforward guide to installing FFmpeg, the powerful multimedia framework, on your operating system.

## Table of Contents
* [Windows](#windows-)
* [macOS](#macos-)
* [Linux](#linux-)

---

## Windows 💻

### 1. Download FFmpeg
-   Go to the official FFmpeg website: [ffmpeg.org/download.html](https://ffmpeg.org/download.html).
-   Choose a Windows build from a trusted source like [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).

### 2. Extract the Files
-   Download the ZIP archive.
-   Extract its contents to a memorable location, such as `C:\ffmpeg`.

### 3. Add FFmpeg to PATH
1.  Open the **Start Menu**, type `Environment Variables`, and select **Edit the system environment variables**.
2.  In the System Properties window, click the **Environment Variables...** button.
3.  Under the **System Variables** section, find and select the `Path` variable, then click **Edit...**.
4.  Click **New** and add the path to the `bin` folder inside your FFmpeg directory (e.g., `C:\ffmpeg\bin`).
5.  Click **OK** to close all windows.

### 4. Verify the Installation
-   Open a new Command Prompt or PowerShell window and run:
    ```bash
    ffmpeg -version
    ```
-   You should see the FFmpeg version information displayed.

---

## macOS 🍎

### 1. Install with Homebrew (Recommended)
-   If you don't have Homebrew, install it first from [brew.sh](https://brew.sh/).
-   Open your **Terminal** and run the following command:
    ```bash
    brew install ffmpeg
    ```
-   Homebrew will handle the installation and path configuration automatically.

### 2. Verify the Installation
-   In the Terminal, run:
    ```bash
    ffmpeg -version
    ```
-   The installed version details will be displayed if the setup was successful.

---

## Linux 🐧

### 1. Install from a Package Manager
-   Open your terminal and use the command corresponding to your distribution.

-   **Debian/Ubuntu:**
    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```

-   **Fedora:**
    ```bash
    sudo dnf install ffmpeg
    ```

-   **Arch Linux:**
    ```bash
    sudo pacman -S ffmpeg
    ```

### 2. Verify the Installation
-   In the terminal, run:
    ```bash
    ffmpeg -version
    ```
-   The output should confirm that FFmpeg is installed correctly.

### Optional: Compile from Source
If the repository version is outdated or you need specific features, you can compile FFmpeg from its source code. Follow the official [FFmpeg Compilation Guide](https://trac.ffmpeg.org/wiki/CompilationGuide) for detailed instructions tailored to your distribution.
