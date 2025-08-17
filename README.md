<div align="center">
![comfyui_civitai_gallery_001](https://github.com/user-attachments/assets/8bb7bf47-633a-41e0-ac75-473813c33434)

# ComfyUI Civitai Gallery<br><sub><sup>-=SFW-Friendly=-</sup></sub>

</div>

## Overview

**ComfyUI Civitai Gallery** is a powerful custom node for ComfyUI that integrates a seamless image browser for the Civitai website directly into your workflow. This node allows you to browse, search, and select images from Civitai and instantly import their prompts, negative prompts, and full-resolution images into your workflow. It is designed to significantly speed up your creative process by eliminating the need to switch between your browser and ComfyUI.

The gallery features a fluid, responsive waterfall (masonry) layout that intelligently fills the available space, ensuring a beautiful and efficient browsing experience.

## Features

  - **Direct Civitai Browsing**: Browse images from Civitai without leaving the ComfyUI interface.
  - **Advanced Filtering**: Filter images by NSFW level, sort order (Most Reactions, Newest, etc.), time period (Day, Week, etc.), specific tags, and username.
  - **One-Click Import**: Simply click on an image to select it. When you run the workflow, the node will output:
      - `positive_prompt`: The positive prompt used to generate the image.
      - `negative_prompt`: The negative prompt.
      - `image`: The original, full-resolution image.
      - `info`: A detailed JSON string containing all other available metadata (sampler, steps, seed, model hash, etc.).
  - **Intelligent Image Loading**: The original image is only downloaded if its `image` output is connected to another node, saving bandwidth and time.
  - **Stable Waterfall Layout**: A fluid, responsive masonry layout that keeps existing images in place when new ones are loaded via infinite scroll.
  - **Custom UI**: Features a custom-styled, permanently visible scrollbar for easy navigation.

## How to Use

1.  **Add the Node**: Press `Tab` or double-click in your ComfyUI workspace, search for `Civitai Gallery`, and add the node to your graph.
2.  **Browse and Filter**:
      - Use the dropdown menus and text fields at the top of the node to filter the images according to your needs.
      - Check the "International" box to use, If you are an international network user.
      - Click the "Refresh" button to apply new filters.
      - Scroll down within the gallery to automatically load more images (infinite scroll).
3.  **Select an Image**: Click on any image card in the gallery. A colored border will appear around your selection.
4.  **Connect the Outputs**:
      - Connect the `positive_prompt` and `negative_prompt` outputs to the corresponding inputs on your KSampler node or a text display node.
      - Connect the `image` output to a `Preview Image` or `Save Image` node if you need the original image. **(Note: The image will only be downloaded if this output is connected)**.
      - Connect the `info` output to a `Show Text` node to view all other generation parameters.
5.  **Queue Prompt**: Run your workflow. The selected image's data will be fed into the connected nodes.

## Installation

1.  Navigate to your ComfyUI installation directory.
2.  Go to the `custom_nodes` folder.
3.  Clone or download this repository into the `custom_nodes` folder. The final folder structure should be `ComfyUI/custom_nodes/ComfyUI_Civitai_Gallery/`.
4.  Restart ComfyUI.

-----

## 概述

**ComfyUI Civitai Gallery** 是一个功能强大的 ComfyUI 自定义节点，它将一个为 Civitai 网站打造的无缝图片浏览器直接集成到了您的工作流中。该节点允许您直接浏览、搜索和选择来自 Civitai 的图片，并能一键将其提示词、负向提示词和原始高分辨率图片导入到您的工作流中。它旨在通过消除在浏览器和 ComfyUI 之间来回切换的需要，从而极大地加速您的创作流程。

本插件的图库拥有一个流畅且响应式的瀑布流（砌体）布局，能够智能地填充所有可用空间，确保了美观高效的浏览体验。

## 功能特性

  - **直连 Civitai 浏览**：无需离开 ComfyUI 界面即可浏览来自 Civitai 的图片。
  - **高级筛选**：可以根据 NSFW 等级、排序方式（最多反应、最新等）、时间范围（天、周等）、特定标签和作者用户名来筛选图片。
  - **一键导入**：只需单击一张图片即可选中它。当您运行工作流时，该节点将输出：
      - `positive_prompt`：用于生成该图片的正向提示词。
      - `negative_prompt`：负向提示词。
      - `image`：原始的、未经压缩的高分辨率图片。
      - `info`：一个包含所有其他可用元数据（如采样器、步数、种子、模型哈希等）的详细 JSON 字符串。
  - **智能图片加载**：只有当 `image` 输出端口连接到其他节点时，插件才会下载原始图片，从而节省您的时间和带宽。
  - **稳定瀑布流布局**：一个流畅的、响应式的瀑布流布局，当通过无限滚动加载新图片时，已加载的图片会保持在原位不动。
  - **自定义界面**：拥有一个自定义样式的、永久可见的滚动条，方便您进行导航。

## 使用方法

1.  **添加节点**：在您的 ComfyUI 工作区中按 `Tab` 键或双击鼠标，搜索 `Civitai Gallery`，然后将该节点添加到您的图中。
2.  **浏览与筛选**：
      - 使用节点顶部的下拉菜单和输入框，根据您的需求筛选图片。
      - 如果你是国际用户，可以勾选 "International" 复选框，能得到更好的图片浏览体验。
      - 可以点击 "Refresh" 按钮来应用新的筛选条件，当然一般情况下不需要用到。
      - 在图库区域内向下滚动，即可自动加载更多图片（无限滚动）。
3.  **选择图片**：在图库中单击任意一张图片卡片。您选中的图片周围会出现一个彩色的边框。
4.  **连接输出端口**：
      - 将 `positive_prompt` 和 `negative_prompt` 输出连接到您的 KSampler 节点或文本显示节点的相应输入上。
      - 如果您需要使用原始图片，请将 `image` 输出连接到 `Preview Image`（预览图像）或 `Save Image`（保存图像）等节点。**（请注意：只有当此端口被连接时，插件才会执行下载操作）**。
      - 将 `info` 输出连接到 `Show Text`（显示文本）节点，以查看所有其他的生成参数。
5.  **运行工作流**：点击 "Queue Prompt" 执行您的工作流。所选图片的数据将被送入已连接的节点中。

## 安装说明

1.  导航至您的 ComfyUI 安装目录。
2.  进入 `custom_nodes` 文件夹。
3.  将此插件的仓库克隆或下载到 `custom_nodes` 文件夹中。最终的文件夹结构应为 `ComfyUI/custom_nodes/ComfyUI_Civitai_Gallery/`。
4.  重启 ComfyUI。
