import server
from aiohttp import web
import aiohttp
import os
import json
import folder_paths
import asyncio
from datetime import datetime, timedelta
import dateutil.parser

from .Civitai_Gallery import (
    load_config, save_config,
    get_full_filename_list
)

MODELS_UI_STATE_FILE = os.path.join(os.path.dirname(__file__), "civitai_models_ui_state.json")
MODELS_FAVORITES_FILE = os.path.join(os.path.dirname(__file__), "civitai_models_favorites.json")

def load_models_favorites():
    if not os.path.exists(MODELS_FAVORITES_FILE): return {}
    try:
        with open(MODELS_FAVORITES_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_models_favorites(data):
    try:
        with open(MODELS_FAVORITES_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"CivitaiModelsGallery: Error saving favorites: {e}")

def load_models_ui_state():
    if not os.path.exists(MODELS_UI_STATE_FILE): return {}
    try:
        with open(MODELS_UI_STATE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_models_ui_state(data):
    try:
        with open(MODELS_UI_STATE_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e: print(f"CivitaiModelsGallery: Error saving UI state: {e}")


class CivitaiModelsGalleryNode:
    @classmethod
    def IS_CHANGED(cls, selection_data, **kwargs):
        return selection_data

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "selection_data": ("STRING", {"default": "{}", "multiline": True, "forceInput": True}),
                "civitai_models_gallery_unique_id_widget": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("model_info",)
    FUNCTION = "get_selected_model_data"
    CATEGORY = "📜Asset Gallery/Civitai"

    def get_selected_model_data(self, unique_id, civitai_models_gallery_unique_id_widget="", selection_data="{}"):
        try:
            node_selection = json.loads(selection_data)
        except:
            node_selection = {}

        item_data = node_selection.get("item", {})
        
        info_string = json.dumps(item_data, indent=4, ensure_ascii=False)
        
        return (info_string,)

prompt_server = server.PromptServer.instance

@prompt_server.routes.post("/civitai_models_gallery/set_ui_state")
async def set_civitai_models_ui_state(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))
        gallery_id = data.get("gallery_id")
        state = data.get("state")
        if not node_id or not gallery_id or state is None:
            return web.json_response({"status": "error", "message": "Missing required data"}, status=400)
        
        node_key = f"{gallery_id}_{node_id}"
        ui_states = load_models_ui_state()
        ui_states[node_key] = state
        save_models_ui_state(ui_states)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_models_gallery/get_ui_state")
async def get_civitai_models_ui_state(request):
    try:
        node_id = request.query.get('node_id')
        gallery_id = request.query.get('gallery_id')
        if not node_id or not gallery_id:
            return web.json_response({})
        
        node_key = f"{gallery_id}_{node_id}"
        ui_states = load_models_ui_state()
        return web.json_response(ui_states.get(node_key, {}))
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_models_gallery/models")
async def get_civitai_models(request):
    params = dict(request.query)
    params.setdefault('limit', '50')
    
    international_version = params.pop('international_version', 'false').lower() in ['true', '1']
    base_domain = "civitai.com" if international_version else "civitai.work"
    api_url = f"https://{base_domain}/api/v1/models"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return web.json_response(data)
    except aiohttp.ClientError as e:
        return web.json_response({"error": str(e)}, status=500)

@prompt_server.routes.post("/civitai_models_gallery/check_files_exist")
async def check_files_exist(request):
    try:
        data = await request.json()
        files_to_check = data.get("files", [])
        if not files_to_check:
            return web.json_response({})

        type_mapping = {
            "checkpoint": "checkpoints", "lora": "loras", "locon": "loras", "dora": "loras",
            "lycoris": "loras", "textualinversion": "embeddings", "hypernetwork": "hypernetworks",
            "aestheticgradient": "embeddings", "controlnet": "controlnet", "motionmodule": "motion_modules",
            "vae": "vae", "upscaler": "upscale_models",
        }
        custom_folder_types = ["workflows", "wildcards", "poses", "detection"]
        existing_files_cache = {}
        results = {}

        for file_info in files_to_check:
            filename = file_info.get("name")
            model_type = file_info.get("type", "").lower()
            if not filename or not model_type:
                continue

            save_folder_key = type_mapping.get(model_type)
            target_path = None

            if save_folder_key:
                if save_folder_key not in existing_files_cache:
                    try:
                        existing_files_cache[save_folder_key] = get_full_filename_list(save_folder_key)
                    except:
                        existing_files_cache[save_folder_key] = []
                results[filename] = filename in existing_files_cache[save_folder_key]
            
            elif model_type in custom_folder_types:
                models_dir = os.path.dirname(folder_paths.get_folder_paths('checkpoints')[0])
                target_dir_name = model_type.capitalize()
                target_path = os.path.join(models_dir, target_dir_name, filename)
                results[filename] = os.path.exists(target_path)

            elif model_type == "motionmodule":
                motion_module_path = os.path.join(folder_paths.get_folder_paths("custom_nodes")[0], "ComfyUI-AnimateDiff-Evolved", "models")
                target_path = os.path.join(motion_module_path, filename)
                results[filename] = os.path.exists(target_path)
                
            else:
                results[filename] = False

        return web.json_response(results)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@prompt_server.routes.get("/civitai_models_gallery/get_favorites_list")
async def get_models_favorites_list(request):
    favorites = load_models_favorites()
    return web.json_response(list(favorites.keys()))

@prompt_server.routes.post("/civitai_models_gallery/toggle_favorite")
async def toggle_model_favorite(request):
    try:
        data = await request.json()
        item = data.get("item")
        if not item or 'id' not in item:
            return web.json_response({"status": "error", "message": "Invalid item data"}, status=400)

        item_id = str(item['id'])
        favorites = load_models_favorites()

        if item_id in favorites:
            del favorites[item_id]
            status = "removed"
        else:
            favorites[item_id] = item
            status = "added"

        save_models_favorites(favorites)
        return web.json_response({"status": status})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@prompt_server.routes.get("/civitai_models_gallery/get_favorites_models")
async def get_favorites_models(request):
    try:
        page = int(request.query.get('page', '1'))
        limit = int(request.query.get('limit', '50'))

        favorites = load_models_favorites()
        items = list(favorites.values())

        query = request.query.get('tag', '').lower()
        sort = request.query.get('sort', 'Newest')
        period = request.query.get('period', 'AllTime')
        types = request.query.get('types', None)
        base_models = request.query.get('baseModels', None)

        filtered_items = []
        for item in items:
            if types and item.get('type') != types:
                continue
            if base_models:
                if not any(v.get('baseModel') == base_models for v in item.get('modelVersions', [])):
                    continue
            if query:
                matches_query = False
                if query in item.get('name', '').lower():
                    matches_query = True
                if not matches_query and 'creator' in item and query in item['creator'].get('username', '').lower():
                    matches_query = True
                if not matches_query and any(query in t.lower() for t in item.get('tags', [])):
                    matches_query = True
                if not matches_query:
                    continue
            if period != 'AllTime':
                if not item.get('modelVersions'):
                    continue
                try:
                    published_at_str = item['modelVersions'][0].get('publishedAt')
                    if not published_at_str:
                        continue
                    published_date = dateutil.parser.isoparse(published_at_str)
                    now = datetime.now(published_date.tzinfo)
                    delta = now - published_date
                    if period == 'Day' and delta > timedelta(days=1): continue
                    if period == 'Week' and delta > timedelta(weeks=1): continue
                    if period == 'Month' and delta > timedelta(days=30): continue
                    if period == 'Year' and delta > timedelta(days=365): continue
                except Exception as e:
                    print(f"CivitaiModelsGallery: 解析日期时出错: {e}")
                    continue
            filtered_items.append(item)

        if sort == 'Highest Rated':
            filtered_items.sort(key=lambda x: x.get('stats', {}).get('rating', 0), reverse=True)
        elif sort == 'Most Downloaded':
            filtered_items.sort(key=lambda x: x.get('stats', {}).get('downloadCount', 0), reverse=True)
        elif sort == 'Newest':
            filtered_items.sort(key=lambda x: dateutil.parser.isoparse(x['modelVersions'][0]['publishedAt']) if x.get('modelVersions') and x['modelVersions'][0].get('publishedAt') else datetime.min.replace(tzinfo=dateutil.tz.UTC), reverse=True)

        total_items = len(filtered_items)
        start_index = (page - 1) * limit
        end_index = start_index + limit

        paginated_items = filtered_items[start_index:end_index]

        response_data = {
            "items": paginated_items,
            "metadata": {
                "totalItems": total_items,
                "currentPage": page,
                "pageSize": limit,
                "totalPages": (total_items + limit - 1) // limit
            }
        }

        return web.json_response(response_data)
    except Exception as e:
        print(f"CivitaiModelsGallery: get_favorites_models 出错: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

NODE_CLASS_MAPPINGS = {
    "CivitaiModelsGalleryNode": CivitaiModelsGalleryNode
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "CivitaiModelsGalleryNode": "Civitai Models Gallery"
}