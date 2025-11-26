# Unused Nodes Finder for Blender

## A Blender add-on designed to find unused nodes in the scene

![Image alt](https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmp5aGJ3cmZ2NXl0Ync2ZnBkdTRpbGNsMm50N3gwNnJtZmlwbjhhYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/ziAj9OON3tCc4cWLmR/giphy.gif)

- Search for unused nodes in materials.
- Output a list of found unused nodes to the Blender console.
- Add an Attribute node to each unused node.
- Organize unused nodes in a separate frame in the Shader Editor.

## Requirements

- Blender version 3.6 or higher
- Python 3.7+

## Installation

1. Download the ZIP archive with the add-on.
2. In Blender, go to Edit > Preferences > Add-ons.
3. Click "Install" and select the downloaded ZIP file.
4. Find "Unused Nodes Finder" in the add-on list and activate it.

## Usage

1. Open the 3D Viewport in Blender.
2. Find the "Unused Nodes Finder" panel in the sidebar (N-panel) in the "Tool" tab.
3. Click the "Find and Organize Unused Nodes" button.
4. If materials used in the scene contain unused nodes, a list of unused nodes will be output to the console, and the materials will be updated.
