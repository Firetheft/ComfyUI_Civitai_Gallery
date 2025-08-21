import server
from aiohttp import web
import aiohttp
import os
import json
import random
import torch
import numpy as np
from PIL import Image
import io
import urllib.request
import time

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(NODE_DIR, "selected_prompt.json")

class CivitaiGalleryNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if os.path.exists(PROMPT_FILE):
            return os.path.getmtime(PROMPT_FILE)
        else:
            return 0.0

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "STRING",)
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "image", "info",)
    
    FUNCTION = "get_selected_data"
    CATEGORY = "📜Asset Gallery/Civitai"

    def get_selected_data(self):
        item_data = {}
        should_download = False
        
        try:
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
                item_data = full_data.get("item", {})
                should_download = full_data.get("download_image", False)
        except (FileNotFoundError, json.JSONDecodeError):
            if not os.path.exists(PROMPT_FILE):
                with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"item": {}, "download_image": False}, f)

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


@server.PromptServer.instance.routes.post("/civitai_gallery/set_prompts")
async def set_civitai_prompts(request):
    try:
        data = await request.json()
        with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return web.json_response({"status": "ok", "message": "Data saved"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@server.PromptServer.instance.routes.get("/civitai_gallery/images")
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