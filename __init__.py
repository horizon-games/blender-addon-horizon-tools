bl_info = {
    "name": "Horizon Games Toolkit",
    "author": "Tomasz Dysinski",
    "version": (1, 0, 1),
    "blender": (2, 91, 0),
    "location": "Properties > Scene > Horizon Tools",
    "description": "Manages custom geometry for centroid based vertex effects during GLTF Export",
    "warning": "",
    "doc_url": "",
    "category": "Scene",
}


import importlib
if "bpy" in locals():
    importlib.reload(sceneTools)
    importlib.reload(customExport)
else:
    from . import sceneTools
    from . import customExport

import bpy


# ### REGISTER ###



def register():
    sceneTools.register()
    customExport.register()



def unregister():
    sceneTools.unregister()
    customExport.unregister()


if __name__ == "__main__":
    register()
