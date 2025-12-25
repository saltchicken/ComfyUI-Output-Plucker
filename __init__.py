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



async def serve_mobile(request):
    file_path = os.path.join(os.path.dirname(__file__), "web/mobile.html")
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

        return web.json_response({"total": 0, "items": items, "current_path": ""})

    root_name, target_dir = parse_virtual_path(subdir)

    if not target_dir:
        return web.json_response({"error": "Invalid path"}, status=400)

    if not os.path.exists(target_dir):
        return web.json_response({"error": "Directory not found"}, status=404)

    try:
        items = []
        all_entries = []

        with os.scandir(target_dir) as entries:
            for entry in entries:
                all_entries.append(entry)

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
                items.append(
                    {
                        "type": "file",
                        "name": entry.name,
                        "path": virtual_path,
                        "fullpath": entry.path,
                    }
                )

        dirs = [x for x in items if x["type"] == "dir"]
        files = [x for x in items if x["type"] != "dir"]

        # Sort independently
        dirs.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())  # Default sort by name

        total_files = len(files)

        paginated_files = files[offset : offset + limit]

        # This ensures the sidebar always has folders, and the grid has exactly 'limit' images
        result_items = dirs + paginated_files

        return web.json_response(
            {"total": total_files, "items": result_items, "current_path": subdir}
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

            # Check for potential paired files (e.g. .png + .json or .png + .txt)
            # Simple heuristic for ComfyUI: delete matching .json metadata if it exists
            # (Though often metadata is embedded, sidecars exist)
            base, ext = os.path.splitext(safe_path)
            if ext.lower() == ".png":
                # Maybe there is a .gif preview?
                gif_path = base + ".gif"
                if os.path.exists(gif_path):
                    os.remove(gif_path)

        return web.json_response({"message": f"{filename} deleted"})
    except FileNotFoundError:
        return web.json_response({"error": "File not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


def get_saved_root():
    return os.path.join(OUTPUT_DIR, SAVED_FOLDER_NAME)


async def get_collections(request):
    saved_root = get_saved_root()
    collections = []

    if os.path.exists(saved_root):
        try:
            with os.scandir(saved_root) as entries:
                for entry in entries:
                    if entry.is_dir():
                        collections.append(entry.name)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    collections.sort()
    return web.json_response({"collections": collections})


async def create_collection(request):
    try:
        data = await request.json()
        name = data.get("name")

        if not name:
            return web.json_response({"error": "No name provided"}, status=400)

        # Simple sanitation
        safe_name = "".join(
            [c for c in name if c.isalnum() or c in (" ", "-", "_")]
        ).strip()

        if not safe_name:
            return web.json_response({"error": "Invalid collection name"}, status=400)

        saved_root = get_saved_root()
        new_dir = os.path.join(saved_root, safe_name)

        os.makedirs(new_dir, exist_ok=True)
        return web.json_response({"message": "Created", "name": safe_name})

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def save_file(request):
    filename = request.rel_url.query.get("filename")

    collection = request.rel_url.query.get("collection", "")

    root_name, source_path = parse_virtual_path(filename)

    if not source_path:
        return web.json_response({"error": "Invalid file path"}, status=400)

    if not os.path.exists(source_path):
        return web.json_response({"error": "File not found"}, status=404)

    # regardless of whether source came from Input or Output

    saved_root = get_saved_root()
    saved_root_abs = os.path.abspath(saved_root)

    dest_dir = saved_root

    if collection:
        # Basic directory traversal protection for collection name
        safe_collection = os.path.basename(collection)
        dest_dir = os.path.join(dest_dir, safe_collection)

    os.makedirs(dest_dir, exist_ok=True)

    base_name = os.path.basename(filename)
    dest_path = os.path.join(dest_dir, base_name)

    counter = 1
    name, ext = os.path.splitext(base_name)
    while os.path.exists(dest_path):
        dest_path = os.path.join(dest_dir, f"{name}_{counter}{ext}")
        counter += 1

    try:
        shutil.move(source_path, dest_path)

        if ext.lower() == ".png":
            source_gif = os.path.splitext(source_path)[0] + ".gif"
            if os.path.exists(source_gif):
                dest_gif = os.path.splitext(dest_path)[0] + ".gif"
                shutil.move(source_gif, dest_gif)

        action = "Moved"

        return web.json_response(
            {"message": f"{action} to {os.path.relpath(dest_path, OUTPUT_DIR)}"}
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


routes.add_get("/plucker/mobile", serve_mobile)


# Frontend requests /plucker/files/Output/... or /plucker/files/Input/...
routes.add_static("/plucker/files/Output", OUTPUT_DIR)
routes.add_static("/plucker/files/Input", INPUT_DIR)

routes.add_get("/plucker/media-list", media_list)
routes.add_delete("/plucker/delete", delete_file)
routes.add_post("/plucker/save", save_file)
routes.add_get("/plucker/metadata", get_metadata)


routes.add_get("/plucker/collections", get_collections)
routes.add_post("/plucker/collections", create_collection)

print("‼️ ComfyUI-Output-Plucker Loaded with Input Support!")