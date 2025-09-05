import server
from aiohttp import web
import aiohttp
import os
import json
import torch
import numpy as np
from PIL import Image
import io
import urllib.request
import time
import folder_paths
import asyncio

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
SELECTIONS_FILE = os.path.join(NODE_DIR, "selections.json")
UI_STATE_FILE = os.path.join(NODE_DIR, "civitai_ui_state.json")
FAVORITES_FILE = os.path.join(NODE_DIR, "civitai_favorites.json")
CONFIG_FILE = os.path.join(NODE_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE): return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"CivitaiGallery: Error saving config: {e}")

def load_selections():
    if not os.path.exists(SELECTIONS_FILE): return {}
    try:
        with open(SELECTIONS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_selections(data):
    try:
        with open(SELECTIONS_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"CivitaiGallery: Error saving selections: {e}")

def load_ui_state():
    if not os.path.exists(UI_STATE_FILE): return {}
    try:
        with open(UI_STATE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_ui_state(data):
    try:
        with open(UI_STATE_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"CivitaiGallery: Error saving UI state: {e}")

def load_favorites():
    if not os.path.exists(FAVORITES_FILE): return {}
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_favorites(data):
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"CivitaiGallery: Error saving favorites: {e}")

def get_full_filename_list(folder_key):
    file_list = []
    for folder_path in folder_paths.get_folder_paths(folder_key):
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path, followlinks=True):
                for file in files:
                    file_list.append(file)
    return list(set(file_list))

class CivitaiGalleryNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if os.path.exists(SELECTIONS_FILE):
            return os.path.getmtime(SELECTIONS_FILE)
        return float("inf")

    @classmethod
    def INPUT_TYPES(cls):
        return { "required": {}, "hidden": { "unique_id": "UNIQUE_ID", "civitai_gallery_unique_id_widget": ("STRING", {"default": "", "multiline": False}), }, }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "STRING",)
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "image", "info",)
    FUNCTION = "get_selected_data"
    CATEGORY = "📜Asset Gallery/Civitai"

    def get_selected_data(self, unique_id, civitai_gallery_unique_id_widget=""):
        gallery_id = civitai_gallery_unique_id_widget
        node_id_str = str(unique_id)
        node_key = f"{gallery_id}_{node_id_str}"
        selections = load_selections()
        node_selection = selections.get(node_key, {})
        item_data = node_selection.get("item", {})
        should_download = node_selection.get("download_image", False)
        meta = item_data.get("meta", {}) if item_data else {}
        pos_prompt = meta.get("prompt", "") if meta else ""
        neg_prompt = meta.get("negativePrompt", "") if meta else ""
        image_url = item_data.get("url", "") if item_data else ""
        info_dict = meta.copy() if meta else {}
        info_dict.pop("prompt", None)
        info_dict.pop("negativePrompt", None)
        info_string = json.dumps(info_dict, indent=4, ensure_ascii=False)
        tensor = torch.zeros(1, 1, 1, 3)
        if should_download and image_url:
            print("CivitaiGalleryNode: Frontend reports image output is connected. Starting download.")
            try:
                req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    img_data = response.read()
                img = Image.open(io.BytesIO(img_data)).convert("RGB")
                img_array = np.array(img).astype(np.float32) / 255.0
                tensor = torch.from_numpy(img_array)[None,]
            except Exception as e:
                print(f"CivitaiGallery: Failed to download or process image from {image_url}. Error: {e}")
        elif should_download:
            print("CivitaiGalleryNode: Image output connected, but no URL was selected or found.")
        return (pos_prompt, neg_prompt, tensor, info_string,)

prompt_server = server.PromptServer.instance

@prompt_server.routes.post("/civitai_gallery/set_prompts")
async def set_civitai_prompts(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))
        gallery_id = data.get("gallery_id")
        if not node_id or not gallery_id:
            return web.json_response({"status": "error", "message": "Missing node_id or gallery_id"}, status=400)
        node_key = f"{gallery_id}_{node_id}"
        selections = load_selections()
        selections[node_key] = { "item": data.get("item"), "download_image": data.get("download_image") }
        save_selections(selections)
        return web.json_response({"status": "ok", "message": "Selection saved"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_gallery/get_selection")
async def get_civitai_selection(request):
    try:
        node_id = request.query.get('node_id')
        gallery_id = request.query.get('gallery_id')
        if not node_id or not gallery_id:
            return web.json_response({})
        node_key = f"{gallery_id}_{node_id}"
        selections = load_selections()
        return web.json_response(selections.get(node_key, {}))
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_gallery/images")
async def get_civitai_images(request):
    nsfw = request.query.get('nsfw', 'None')
    sort = request.query.get('sort', 'Most Reactions')
    period = request.query.get('period', 'Day')
    username = request.query.get('username', '')
    international_version = request.query.get('international_version', 'false').lower() in ['true', '1']
    cursor = request.query.get('cursor', None)
    tags_query = request.query.get('tags', None)
    base_domain = "civitai.com" if international_version else "civitai.work"
    api_url = f"https://{base_domain}/api/v1/images"
    params = {'limit': 50, 'nsfw': nsfw, 'sort': sort, 'period': period, 'username': username}
    if cursor: params['cursor'] = cursor
    if tags_query: params['tags'] = tags_query
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return web.json_response(data)
    except aiohttp.ClientError as e:
        return web.json_response({"error": str(e)}, status=500)

@prompt_server.routes.post("/civitai_gallery/set_ui_state")
async def set_civitai_ui_state(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))
        gallery_id = data.get("gallery_id")
        state = data.get("state")
        if not node_id or not gallery_id or state is None:
            return web.json_response({"status": "error", "message": "Missing required data"}, status=400)
        node_key = f"{gallery_id}_{node_id}"
        ui_states = load_ui_state()
        ui_states[node_key] = state
        save_ui_state(ui_states)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_gallery/get_ui_state")
async def get_civitai_ui_state(request):
    try:
        node_id = request.query.get('node_id')
        gallery_id = request.query.get('gallery_id')
        if not node_id or not gallery_id:
            return web.json_response({})
        node_key = f"{gallery_id}_{node_id}"
        ui_states = load_ui_state()
        return web.json_response(ui_states.get(node_key, {}))
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_gallery/get_favorites_list")
async def get_favorites_list(request):
    favorites = load_favorites()
    return web.json_response(list(favorites.keys()))

@prompt_server.routes.post("/civitai_gallery/toggle_favorite")
async def toggle_favorite(request):
    try:
        data = await request.json()
        item = data.get("item")
        if not item or 'id' not in item:
            return web.json_response({"status": "error", "message": "Invalid item data"}, status=400)
        item_id = str(item['id'])
        favorites = load_favorites()
        if item_id in favorites:
            del favorites[item_id]
            status = "removed"
        else:
            item['tags'] = []
            favorites[item_id] = item
            status = "added"
        save_favorites(favorites)
        return web.json_response({"status": status})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_gallery/get_favorites_images")
async def get_favorites_images(request):
    favorites = load_favorites()
    items = list(favorites.values())
    
    filter_tags_str = request.query.get('fav_tags', '').strip().lower()
    filter_mode = request.query.get('fav_tag_mode', 'OR').upper()

    if filter_tags_str:
        filter_tags = {tag.strip() for tag in filter_tags_str.split(',') if tag.strip()}
        
        filtered_items = []
        for item in items:
            item_tags = {str(t).lower() for t in item.get('tags', [])}
            if filter_mode == 'AND':
                if filter_tags.issubset(item_tags):
                    filtered_items.append(item)
            else:
                if any(ft in item_tags for ft in filter_tags):
                    filtered_items.append(item)
        items = filtered_items

    response_data = { "items": items, "metadata": {} }
    return web.json_response(response_data)
    
@prompt_server.routes.post("/civitai_gallery/download_model")
async def download_model(request):
    try:
        config = load_config()
        api_key = config.get("civitai_api_key")
        if not api_key:
            return web.json_response({"status": "error", "message": "Civitai API Key not found in config.json.", "reason": "API_KEY_MISSING"}, status=401)
        
        headers = { "Authorization": f"Bearer {api_key}" }
        data = await request.json()
        model_version_id = data.get("version_id")
        model_type = data.get("type", "").lower()
        if not model_version_id:
            return web.json_response({"status": "error", "message": "Missing model_version_id"}, status=400)
        
        version_info_url = f"https://civitai.com/api/v1/model-versions/{model_version_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(version_info_url, headers=headers) as response:
                if response.status != 200:
                    return web.json_response({"status": "error", "message": f"Failed to fetch model version info from Civitai. Status: {response.status}"}, status=500)
                version_data = await response.json()
        
        if not version_data or not version_data.get("files"):
            return web.json_response({"status": "error", "message": "No files found in model version info"}, status=404)

        model_file = version_data.get("files", [])[0]
        download_url = model_file.get("downloadUrl")
        filename = model_file.get("name")
        if not download_url or not filename:
             return web.json_response({"status": "error", "message": "Could not find a valid file or download URL in the model version info."}, status=404)

        type_mapping = {
            "checkpoint": "checkpoints", "lora": "loras", "locon": "loras", "dora": "loras",
            "lycoris": "loras", "textualinversion": "embeddings", "hypernetwork": "hypernetworks",
            "aestheticgradient": "embeddings", "controlnet": "controlnet", "motionmodule": "motion_modules",
            "vae": "vae", "upscaler": "upscale_models",
        }
        custom_folder_types = ["workflows", "wildcards", "poses", "detection"]
        primary_folder_path = None

        save_folder_key = type_mapping.get(model_type)

        if save_folder_key:
            primary_folder_path = folder_paths.get_folder_paths(save_folder_key)[0]
            if not os.path.exists(primary_folder_path): os.makedirs(primary_folder_path)
            existing_files = get_full_filename_list(save_folder_key)
            if filename in existing_files:
                return web.json_response({"status": "already_exists", "message": f"File already exists: {filename}"})
        
        elif model_type in custom_folder_types:
            models_dir = os.path.dirname(folder_paths.get_folder_paths('checkpoints')[0])
            target_dir_name = model_type.capitalize()
            primary_folder_path = os.path.join(models_dir, target_dir_name)
            
            if not os.path.exists(primary_folder_path):
                os.makedirs(primary_folder_path)
            
            if os.path.exists(os.path.join(primary_folder_path, filename)):
                 return web.json_response({"status": "already_exists", "message": f"File already exists: {filename}"})
        
        elif model_type == "motionmodule":
            motion_module_path = os.path.join(folder_paths.get_folder_paths("custom_nodes")[0], "ComfyUI-AnimateDiff-Evolved", "models")
            if not os.path.exists(motion_module_path): os.makedirs(motion_module_path)
            if filename in os.listdir(motion_module_path):
                return web.json_response({"status": "already_exists", "message": f"File already exists: {filename}"})
            primary_folder_path = motion_module_path

        else:
            return web.json_response({"status": "error", "message": f"Unknown or unsupported model type for download: {model_type}"}, status=400)
        
        file_path = os.path.join(primary_folder_path, filename)
        
        print(f"CivitaiGallery: Starting download of '{filename}' from {download_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, headers=headers) as response:
                if response.status != 200:
                    return web.json_response({"status": "error", "message": f"Download failed. Status: {response.status}. Check your API Key."}, status=response.status)
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk: break
                        f.write(chunk)
        
        print(f"CivitaiGallery: Successfully downloaded '{filename}' to '{primary_folder_path}'")
        return web.json_response({"status": "success", "message": "Download complete."})
    except Exception as e:
        print(f"CivitaiGallery: Error in download_model: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.post("/civitai_gallery/get_resource_info")
async def get_resource_info(request):
    try:
        data = await request.json()
        resources = data.get("resources", [])
        
        type_mapping = {
            "checkpoint": "checkpoints", "lora": "loras", "locon": "loras", "dora": "loras",
            "lycoris": "loras", "textualinversion": "embeddings", "hypernetwork": "hypernetworks",
            "aestheticgradient": "embeddings", "controlnet": "controlnet", "motionmodule": "motion_modules",
            "vae": "vae", "upscaler": "upscale_models",
        }
        custom_folder_types = ["workflows", "wildcards", "poses", "detection"]
        
        async def fetch_info(session, resource):
            version_id = resource.get("modelVersionId")
            if version_id:
                url = f"https://civitai.com/api/v1/model-versions/{version_id}"
            elif resource.get("hash"):
                url = f"https://civitai.com/api/v1/model-versions/by-hash/{resource.get('hash')}"
            else:
                return resource

            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        version_data = await response.json()
                        model = version_data.get("model", {})
                        resource["modelName"] = model.get("name")
                        
                        model_type = model.get("type", "").lower()
                        resource["modelType"] = model_type
                        
                        if not resource.get("modelVersionId"):
                            resource["modelVersionId"] = version_data.get("id")
                        
                        if version_data.get("files"):
                            filename = version_data["files"][0].get("name")
                            resource["fileName"] = filename
                            resource["publishedAt"] = version_data.get("publishedAt")
                            resource["fileSizeKB"] = version_data["files"][0].get("sizeKB")
                            
                            save_folder_key = type_mapping.get(model_type)
                            if save_folder_key:
                                try:
                                    existing_files = get_full_filename_list(save_folder_key)
                                    resource["exists"] = filename in existing_files
                                except:
                                    resource["exists"] = False
                            
                            elif model_type in custom_folder_types:
                                models_dir = os.path.dirname(folder_paths.get_folder_paths('checkpoints')[0])
                                target_dir_name = model_type.capitalize()
                                target_path = os.path.join(models_dir, target_dir_name, filename)
                                resource["exists"] = os.path.exists(target_path)

                            elif model_type == "motionmodule":
                                motion_module_path = os.path.join(folder_paths.get_folder_paths("custom_nodes")[0], "ComfyUI-AnimateDiff-Evolved", "models")
                                resource["exists"] = os.path.exists(os.path.join(motion_module_path, filename))
                                
                            else:
                                resource["exists"] = False
                        else:
                            resource["fileName"] = None
                            resource["exists"] = False
                    else:
                        resource["exists"] = False
                    return resource
            except Exception:
                resource["exists"] = False
                return resource

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_info(session, res) for res in resources]
            augmented_resources = await asyncio.gather(*tasks)
            return web.json_response(augmented_resources)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@prompt_server.routes.post("/civitai_gallery/save_api_key")
async def save_api_key(request):
    try:
        data = await request.json()
        api_key = data.get("api_key")
        if not api_key:
            return web.json_response({"status": "error", "message": "No API key provided"}, status=400)
        config = load_config()
        config["civitai_api_key"] = api_key
        save_config(config)
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.post("/civitai_gallery/update_favorite_tags")
async def update_favorite_tags(request):
    try:
        data = await request.json()
        item_id = str(data.get("id"))
        tags = data.get("tags", [])
        if not item_id:
            return web.json_response({"status": "error", "message": "Missing item id"}, status=400)
            
        favorites = load_favorites()
        if item_id in favorites:
            favorites[item_id]['tags'] = tags
            save_favorites(favorites)
            return web.json_response({"status": "success"})
        else:
            return web.json_response({"status": "error", "message": "Item not in favorites"}, status=404)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_gallery/get_all_favorite_tags")
async def get_all_favorite_tags(request):
    try:
        favorites = load_favorites()
        all_tags = set()
        for item in favorites.values():
            tags = item.get("tags")
            if isinstance(tags, list):
                for tag in tags:
                    all_tags.add(tag)
        
        sorted_tags = sorted(list(all_tags), key=lambda s: s.lower())
        return web.json_response({"tags": sorted_tags})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

NODE_CLASS_MAPPINGS = { "CivitaiGalleryNode": CivitaiGalleryNode }
NODE_DISPLAY_NAME_MAPPINGS = { "CivitaiGalleryNode": "Civitai Images Gallery" }