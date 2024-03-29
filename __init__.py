bl_info = {
    "name": "Horizon Games Toolkit",
    "author": "Tomasz Dysinski",
    "version": (1, 1, 1),
    "blender": (2, 91, 0),
    "location": "Properties > Scene > Horizon Tools",
    "description": "Manages custom geometry for centroid based vertex effects during GLTF Export",
    "warning": "",
    "doc_url": "",
    "category": "Scene",
}


import importlib
if "bpy" in locals():
    importlib.reload(customExport)
    importlib.reload(bakeAmbientOcclusionToVertexColor)
    importlib.reload(squashAttributes)
    importlib.reload(copyVertexColorChannels)
    importlib.reload(applyModifiers)
    importlib.reload(generateCentroidShapeKeys)
    importlib.reload(sceneTools)
    importlib.reload(objectDataTools)
else:
    from . import customExport
    from . import bakeAmbientOcclusionToVertexColor
    from . import squashAttributes
    from . import copyVertexColorChannels
    from . import applyModifiers
    from . import generateCentroidShapeKeys
    from . import sceneTools
    from . import objectDataTools

import bpy

def register():
    customExport.register()
    bakeAmbientOcclusionToVertexColor.register()
    squashAttributes.register()
    copyVertexColorChannels.register()
    applyModifiers.register()
    generateCentroidShapeKeys.register()
    sceneTools.register()
    objectDataTools.register()

def unregister():
    customExport.unregister()
    bakeAmbientOcclusionToVertexColor.unregister()
    squashAttributes.unregister()
    copyVertexColorChannels.unregister()
    applyModifiers.unregister()
    generateCentroidShapeKeys.unregister()
    sceneTools.unregister()
    objectDataTools.unregister()

if __name__ == "__main__":
    register()
