This addon is a suite of tools to help in the creation and export of assets with unique visual requirements:
- export GLTF while supporting centroid-based shape keys AND custom normals (normally incompatible)
- compose vertex colors and uvs from shader graphs

# Getting Started #

## Installation ##
1. Download or clone this repository
2. Install the addon (https://docs.blender.org/manual/en/latest/editors/preferences/addons.html)
3. Enable the addon titled "Scene: Horizon Tools"


# development #

When making any changes to the python code, you must reload the addon by pressing F3, and running "Reload Scripts".
Alternatively you can run "bpy.ops.script.reload()" in the console, or (recommended) use the addon-reload-helper available here: https://github.com/horizon-games/blender-addon-reload-helper/