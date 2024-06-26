from pydantic import BaseModel
from pygltflib import (
    Scene,
    Buffer,
    Mesh,
    BufferView,
    Accessor,
    Node,
    Image,
    Material,
    Sampler,
    Texture,
    Animation,
    Skin,
)

class CollectedInfo(BaseModel):
    nodes: list[Node]
    meshes: list[Mesh]
    materials: list[Material]
    textures: list[Texture]
    images: list[Image]
    accessors: list[Accessor]
    buffers: list[Buffer]
    bufferViews: list[BufferView]
    animations: list[Animation]
    scenes: list[Scene]
    samplers: list[Sampler]
    skins: list[Skin]
    scene_node_indices: list[list[int]]
    skins_indices: dict[int, int]
    meshes_indices: dict[int, int]
    material_indices: dict[int, int]
    samplers_indices: dict[int, int]
    images_indices: dict[int, int]
    textures_indices: dict[int, int]
    accessor_indices: dict[int, int]
    bufferView_indices: dict[int, int]
    node_indices: set[int]
    batch_table: dict[str, list]
    batch_table_mapping: dict

    class Config:
        arbitrary_types_allowed = True