# ComfyUI Output Plucker

**ComfyUI Output Plucker** is a lightweight, embedded file manager extension for ComfyUI. It adds a floating overlay to your workspace, allowing you to browse, manage, and inspect your generated images and videos without ever leaving the browser interface.

## 🚀 Features

- **Seamless Overlay Interface**: Access your output folder via a floating "📂 Plucker" button directly inside ComfyUI.
- **Media Browser**:
  - Grid view for images and videos.
  - Auto-playing video previews (muted/looped).
  - Subdirectory navigation support.
- **Pagination**: Efficiently browse folders with thousands of images using built-in pagination controls.
- **File Management**:
  - **Save/Favorite**: One-click copy of files to a dedicated `Saved` subdirectory.
  - **Delete**: Remove unwanted generations directly from the UI (handles paired `.png` + `.gif` deletion automatically).
- **Metadata Extraction**:
  - 📋 **Copy Workflow**: Extract and copy the full embedded ComfyUI workflow/metadata JSON to your clipboard.
  - 📝 **Copy Prompt**: Intelligently extract and copy just the positive prompt text.

## 🛠 Tech Stack

- **Backend**: Python (ComfyUI `server.PromptServer`, `aiohttp`, `Pillow`)
- **Frontend**: HTML5, Vanilla JavaScript, CSS
- **Integration**: ComfyUI Javascript Extension API

## 📋 Prerequisites

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installed and running.
- Python dependencies (these are standard in ComfyUI environments):
  - `aiohttp`
  - `Pillow`

## 📦 Installation

1.  Navigate to your ComfyUI custom nodes directory:
    ```bash
    cd ComfyUI/custom_nodes/
    ```
2.  Clone this repository:
    ```bash
    git clone [https://github.com/your-username/comfyui-output-plucker.git](https://github.com/your-username/comfyui-output-plucker.git)
    ```
3.  Restart ComfyUI.

## 🎮 Usage

1.  Open **ComfyUI** in your browser.
2.  Look for the **"📂 Plucker"** floating button in the top-right corner of the window (near the queue/settings menu).
3.  Click the button to open the **Output Plucker** modal.
4.  **Navigation**:
    - Use the `Up`, `Next`, and `Prev` buttons to navigate pages and folders.
    - Double-click an image/video to toggle fullscreen view.
5.  **Actions** (Hover over an item):
    - 💾 **Save**: Copies the file to `ComfyUI/output/Saved/`.
    - 📋 **Clipboard**: Copies the full generation metadata.
    - 📝 **Note**: Copies the positive prompt text.
    - 🗑️ **Trash**: Permanently deletes the file.

## ⚙️ Configuration

The extension automatically detects your ComfyUI output directory using `folder_paths.get_output_directory()`.

- **Saved Folder**: Files are saved to a subdirectory named `Saved` within your output folder.
- **Grid Size**: Currently set to 12 items per page (configurable in `web/index.html` source if needed).

## 📄 License

This project is open-source. Feel free to modify and adapt it to your workflow.
