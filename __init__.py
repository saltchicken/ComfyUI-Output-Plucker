import os
import shutil
import json
from aiohttp import web
from PIL import Image
from PIL.PngImagePlugin import PngInfo

# ComfyUI Imports
import folder_paths
from server import PromptServer

# Configuration
WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


# We get the standard output and input directories from ComfyUI
OUTPUT_DIR = folder_paths.get_output_directory()
INPUT_DIR = folder_paths.get_input_directory()


ROOT_FOLDERS = {"Output": OUTPUT_DIR, "Input": INPUT_DIR}

SAVED_FOLDER_NAME = "Saved"


routes = PromptServer.instance.app.router

# ----------------------------------------------------------------------------
# Helper: Parse Virtual Path
# ----------------------------------------------------------------------------


def parse_virtual_path(vpath):
    """
    Converts a virtual path (e.g., "Output/subfolder/image.png")
    into a real system path, preventing directory traversal.
    """
    if not vpath:
        return None, None

    # Standardize separators
    parts = vpath.replace("\\", "/").split("/")
    root_name = parts[0]

    if root_name not in ROOT_FOLDERS:
        return None, None

    real_root = ROOT_FOLDERS[root_name]

    if len(parts) > 1:
        # Join the rest of the path
        sub_path = os.path.join(*parts[1:])
        full_path = os.path.abspath(os.path.join(real_root, sub_path))
    else:
        # Just the root folder itself
        full_path = os.path.abspath(real_root)

    # Security check: Ensure we haven't escaped the root
    if not full_path.startswith(os.path.abspath(real_root)):
        return None, None

    return root_name, full_path


# ----------------------------------------------------------------------------
# Route Handlers
# ----------------------------------------------------------------------------


async def serve_index(request):
    file_path = os.path.join(os.path.dirname(__file__), "web/index.html")
    return web.FileResponse(file_path)


async def media_list(request):
    params = request.rel_url.query
    subdir = params.get("subdir", "")
    offset = int(params.get("offset", 0))
    limit = int(params.get("limit", 20))

    if not subdir:
        items = []
        for key, val in ROOT_FOLDERS.items():
            items.append(
                {
                    "type": "dir",
                    "name": key,
                    "path": key,  # This becomes the 'subdir' for the next request
                    "fullpath": val,
                }
            )
        # Sort roots alphabetically
        items.sort(key=lambda x: x["name"])
        return web.json_response(
            {"total": len(items), "items": items, "current_path": ""}
        )

    root_name, target_dir = parse_virtual_path(subdir)

    if not target_dir:
        return web.json_response({"error": "Invalid path"}, status=400)

    if not os.path.exists(target_dir):
        return web.json_response({"error": "Directory not found"}, status=404)

    try:
        items = []
        all_entries = []
        mp4_files = set()

        with os.scandir(target_dir) as entries:
            for entry in entries:
                all_entries.append(entry)
                if entry.is_file() and entry.name.lower().endswith(".mp4"):
                    mp4_files.add(entry.name)

        # Process entries
        for entry in all_entries:
            # Real path relative to the physical root (e.g. "subfolder/image.png")
            rel_real = os.path.relpath(entry.path, ROOT_FOLDERS[root_name])

            # Virtual path for frontend (e.g. "Output/subfolder/image.png")
            # We force forward slashes for web consistency
            virtual_path = f"{root_name}/{rel_real}".replace("\\", "/")

            if entry.is_dir():
                items.append(
                    {
                        "type": "dir",
                        "name": entry.name,
                        "path": virtual_path,
                        "fullpath": entry.path,
                    }
                )
            elif entry.is_file() and entry.name.lower().endswith(
                (".gif", ".mp4", ".png", ".jpg", ".jpeg", ".webp")
            ):
                if entry.name.lower().endswith(".png"):
                    base_name = os.path.splitext(entry.name)[0]
                    if f"{base_name}.mp4" in mp4_files:
                        continue

                items.append(
                    {
                        "type": "file",
                        "name": entry.name,
                        "path": virtual_path,
                        "fullpath": entry.path,
                    }
                )

        items.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))

        total = len(items)
        paginated_items = items[offset : offset + limit]

        return web.json_response(
            {"total": total, "items": paginated_items, "current_path": subdir}
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def delete_file(request):
    filename = request.rel_url.query.get("filename")
    if not filename:
        return web.json_response({"error": "Missing filename"}, status=400)

    root_name, safe_path = parse_virtual_path(filename)

    if not safe_path:
        return web.json_response({"error": "Invalid file path"}, status=400)

    try:
        if os.path.exists(safe_path):
            os.remove(safe_path)

        if filename.lower().endswith((".gif", ".mp4")):
            base_path = os.path.splitext(safe_path)[0]
            png_path = f"{base_path}.png"
            if os.path.exists(png_path):
                os.remove(png_path)

        return web.json_response({"message": f"{filename} deleted"})
    except FileNotFoundError:
        return web.json_response({"error": "File not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def save_file(request):
    filename = request.rel_url.query.get("filename")

    root_name, source_path = parse_virtual_path(filename)

    if not source_path:
        return web.json_response({"error": "Invalid file path"}, status=400)

    if not os.path.exists(source_path):
        return web.json_response({"error": "File not found"}, status=404)

    # regardless of whether source came from Input or Output
    saved_dir = os.path.join(OUTPUT_DIR, SAVED_FOLDER_NAME)
    os.makedirs(saved_dir, exist_ok=True)

    base_name = os.path.basename(filename)
    dest_path = os.path.join(saved_dir, base_name)

    counter = 1
    name, ext = os.path.splitext(base_name)
    while os.path.exists(dest_path):
        dest_path = os.path.join(saved_dir, f"{name}_{counter}{ext}")
        counter += 1

    try:
        # ‼️ Changed: Use shutil.move for atomic, safer, and faster operation (renames on same fs)
        shutil.move(source_path, dest_path)

        if filename.lower().endswith((".gif", ".mp4")):
            source_base = os.path.splitext(source_path)[0]
            png_source = f"{source_base}.png"

            if os.path.exists(png_source):
                dest_base = os.path.splitext(dest_path)[0]
                dest_png_path = f"{dest_base}.png"
                # ‼️ Changed: Use move for paired preview file
                shutil.move(png_source, dest_png_path)

        return web.json_response(
            {"message": f"Saved to {os.path.relpath(dest_path, OUTPUT_DIR)}"}
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def get_metadata(request):
    filename = request.rel_url.query.get("filename")
    key = request.rel_url.query.get("key")

    root_name, safe_path = parse_virtual_path(filename)

    if not safe_path:
        return web.json_response({"error": "Invalid file path"}, status=400)

    target_path = safe_path
    if filename.lower().endswith(".mp4"):
        base_path = os.path.splitext(safe_path)[0]
        png_path = f"{base_path}.png"
        if os.path.exists(png_path):
            target_path = png_path

    if not os.path.exists(target_path):
        return web.json_response({"error": "File not found"}, status=404)

    try:
        with Image.open(target_path) as img:
            info = img.info

            if key == "prompt_text":
                if "prompt" not in info:
                    return web.json_response(
                        {"found": False, "message": "No prompt data found"}
                    )

                try:
                    prompt_data = json.loads(info["prompt"])
                    found_texts = []

                    samplers = [
                        (id, node)
                        for id, node in prompt_data.items()
                        if "Sampler" in node.get("class_type", "")
                    ]

                    for _, sampler in samplers:
                        positive_link = sampler.get("inputs", {}).get("positive")
                        if positive_link and isinstance(positive_link, list):
                            from_node_id = positive_link[0]
                            if from_node_id in prompt_data:
                                source_node = prompt_data[from_node_id]
                                text_val = source_node.get("inputs", {}).get("text")
                                if isinstance(text_val, str) and text_val.strip():
                                    found_texts.append(text_val)

                    if found_texts:
                        return web.json_response(
                            {"metadata": "\n\n".join(list(set(found_texts)))}
                        )
                    else:
                        fallback_texts = []
                        for _, node in prompt_data.items():
                            if "CLIPTextEncode" in node.get("class_type", ""):
                                title = node.get("_meta", {}).get("title", "").lower()
                                if "negative" in title:
                                    continue
                                text_val = node.get("inputs", {}).get("text")
                                if isinstance(text_val, str) and len(text_val) > 5:
                                    fallback_texts.append(text_val)

                        if fallback_texts:
                            return web.json_response(
                                {"metadata": "\n\n".join(list(set(fallback_texts)))}
                            )

                        return web.json_response(
                            {
                                "found": False,
                                "message": "Could not identify prompt text",
                            }
                        )

                except Exception as e:
                    return web.json_response(
                        {"found": False, "message": f"Error parsing: {str(e)}"}
                    )

            if key:
                if key in info:
                    return web.json_response({"metadata": info[key]})
                else:
                    return web.json_response(
                        {"found": False, "message": f"Key '{key}' not found"}
                    )

            if "workflow" in info:
                return web.json_response({"metadata": info["workflow"]})
            elif "prompt" in info:
                return web.json_response({"metadata": info["prompt"]})
            else:
                return web.json_response(
                    {"found": False, "message": "No ComfyUI metadata found"}
                )

    except Exception as e:
        return web.json_response({"found": False, "message": str(e)})


routes.add_get("/plucker/view", serve_index)


# Frontend requests /plucker/files/Output/... or /plucker/files/Input/...
routes.add_static("/plucker/files/Output", OUTPUT_DIR)
routes.add_static("/plucker/files/Input", INPUT_DIR)

routes.add_get("/plucker/media-list", media_list)
routes.add_delete("/plucker/delete", delete_file)
routes.add_post("/plucker/save", save_file)
routes.add_get("/plucker/metadata", get_metadata)

print("‼️ ComfyUI-Output-Plucker Loaded with Input Support!")
