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

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
SELECTIONS_FILE = os.path.join(NODE_DIR, "selections.json")

def load_selections():
    if not os.path.exists(SELECTIONS_FILE): return {}
    try:
        with open(SELECTIONS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_selections(data):
    try:
        with open(SELECTIONS_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"CivitaiGallery: Error saving selections: {e}")


class CivitaiGalleryNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if os.path.exists(SELECTIONS_FILE):
            return os.path.getmtime(SELECTIONS_FILE)
        return float("inf")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "hidden": { "unique_id": "UNIQUE_ID" },
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "STRING",)
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "image", "info",)
    
    FUNCTION = "get_selected_data"
    CATEGORY = "📜Asset Gallery/Civitai"

    def get_selected_data(self, unique_id):
        selections = load_selections()

        node_selection = selections.get(str(unique_id), {})

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

        tensor = None
        if should_download:
            print("CivitaiGalleryNode: Frontend reports image output is connected. Starting download.")
            if not image_url: raise ValueError("Image output connected, but no URL was selected.")
            img_data = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as response:
                        img_data = response.read()
                    break
                except Exception as e:
                    if attempt < max_retries - 1: time.sleep(1)
                    else: raise RuntimeError(f"Failed to download image from URL: {image_url}")
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            img_array = np.array(img).astype(np.float32) / 255.0
            tensor = torch.from_numpy(img_array)[None,]
        else:
            print("CivitaiGalleryNode: Frontend reports image output is not connected. Skipping download.")
            tensor = torch.zeros(1, 1, 1, 3)

        return (pos_prompt, neg_prompt, tensor, info_string,)

prompt_server = server.PromptServer.instance

@prompt_server.routes.post("/civitai_gallery/set_prompts")
async def set_civitai_prompts(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))
        if not node_id:
            return web.json_response({"status": "error", "message": "Missing node_id"}, status=400)

        selections = load_selections()

        selections[node_id] = {
            "item": data.get("item"),
            "download_image": data.get("download_image")
        }
        save_selections(selections)
        return web.json_response({"status": "ok", "message": "Selection saved"})
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

NODE_CLASS_MAPPINGS = { "CivitaiGalleryNode": CivitaiGalleryNode }
NODE_DISPLAY_NAME_MAPPINGS = { "CivitaiGalleryNode": "Civitai Gallery" }