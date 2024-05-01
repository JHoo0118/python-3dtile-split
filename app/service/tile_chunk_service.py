import os
import copy

from typing import Any
from pygltflib import (
    GLTF2,
    Scene,
    Buffer,
    Mesh,
    BufferView,
    Accessor,
    Node,
    Image,
    Material,
    Primitive,
    Sampler,
    Texture,
    Animation,
    Attributes,
    Skin,
)

from model.collected_info_model import CollectedInfo

class TileChunkService(object):
    _instance = None
    _material_property_paths = []

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self) -> None:
        
        self._material_property_paths = [
            "pbrMetallicRoughness.baseColorTexture",
            "pbrMetallicRoughness.metallicRoughnessTexture",
            "normalTexture",
            "occlusionTexture",
            "emissiveTexture",
        ]

    def __init_collected_info(self) -> CollectedInfo:
        return CollectedInfo(
            nodes=[],
            meshes=[],
            materials=[],
            textures=[],
            images=[],
            accessors=[],
            buffers=[],
            bufferViews=[],
            animations=[],
            scenes=[],
            samplers=[],
            skins=[],
            scene_node_indices=[],
            skins_indices=dict(),
            meshes_indices=dict(),
            material_indices=dict(),
            samplers_indices=dict(),
            images_indices=dict(),
            textures_indices=dict(),
            accessor_indices=dict(),
            bufferView_indices=dict(),
            node_indices=set(),
        )
    
    def __collect_mesh_material_texture_info(
        self,
        gltf: GLTF2,
        texture_index: int,
        collected_info: CollectedInfo,
    ) -> None:
        texture = self.__get_validated_texture(gltf, texture_index, collected_info)

        if texture.sampler is not None:
            self.__update_sampler_for_texture(gltf, texture, collected_info)

        if texture.source is not None:
            self.__handle_texture_image(gltf, texture, collected_info)


    def __get_validated_texture(
        self,
        gltf: GLTF2,
        texture_index: int,
        collected_info: CollectedInfo,
    ) -> Texture:
        texture = gltf.textures[texture_index]
        if collected_info.textures_indices.get(texture_index) is None:
            new_texture_index = len(collected_info.textures)
            collected_info.textures.append(texture)
            collected_info.textures_indices[texture_index] = new_texture_index
        return texture

    def __update_sampler_for_texture(
        self,
        gltf: GLTF2,
        texture: Texture,
        collected_info: CollectedInfo,
    ) -> None:
        if gltf.samplers is not None and len(gltf.samplers) > 0:
            sampler = gltf.samplers[texture.sampler]
            origin_sampler_index = texture.sampler

            if collected_info.samplers_indices.get(texture.sampler) is None:
                new_texture_index = len(collected_info.samplers)
                texture.sampler = new_texture_index
                collected_info.samplers.append(sampler)
                collected_info.samplers_indices[origin_sampler_index] = new_texture_index

            else:
                texture.sampler = collected_info.samplers_indices.get(texture.sampler)


    def __handle_texture_image(
        self,
        gltf: GLTF2,
        texture: Texture,
        collected_info: CollectedInfo,
    ) -> None:
        if gltf.images is not None and len(gltf.images) > 0:
            image: Image = gltf.images[texture.source]
            origin_image_index = texture.source
            if collected_info.images_indices.get(origin_image_index) is None:
                if image.bufferView is not None:
                    self.__handle_image_buffer_view(gltf, image, collected_info, origin_image_index)
                else:
                    new_image_index = len(collected_info.images)
                    collected_info.images.append(image)
                    collected_info.images_indices[origin_image_index] = new_image_index


    def __handle_image_buffer_view(
        self,
        gltf: GLTF2,
        image: Image,
        collected_info: CollectedInfo,
        source_index: int,
    ) -> None:
        bufferView = gltf.bufferViews[image.bufferView]
        if collected_info.bufferView_indices.get(image.bufferView) is None:
            new_bufferView_index = len(collected_info.bufferViews)
            collected_info.bufferViews.append(bufferView)
            collected_info.bufferView_indices[image.bufferView] = new_bufferView_index

            new_image_index = len(collected_info.images)
            collected_info.images.append(image)
            collected_info.images_indices[source_index] = new_image_index

            buffer = gltf.buffers[bufferView.buffer]
            if buffer not in collected_info.buffers:
                collected_info.buffers.append(buffer)

    def __collect_mesh_material_texture_info_helper(
        self,
        gltf: GLTF2,
        material: Material,
        collected_info: CollectedInfo,
        texture_type: str, 
        ) -> None:
        texture_type = texture_type.split(".")[-1]
        texture_attribute = getattr(material.pbrMetallicRoughness if texture_type in ['baseColorTexture', 'metallicRoughnessTexture'] else material, texture_type, None)
        if texture_attribute is not None:
            texture_index = texture_attribute.index
            self.__collect_mesh_material_texture_info(
                gltf=gltf,
                texture_index=texture_index,
                collected_info=collected_info,
            )
    def __collect_mesh_material_info(
        self,
        gltf: GLTF2,
        primitive: Primitive,
        collected_info: CollectedInfo,
      ) -> None:
        if primitive.material is not None:
            material = gltf.materials[primitive.material]

            if collected_info.material_indices.get(primitive.material) is None:
                new_material_index = len(collected_info.materials)
                collected_info.material_indices[primitive.material] = new_material_index
                collected_info.materials.append(material)
            
            for texture_type in self._material_property_paths:
                self.__collect_mesh_material_texture_info_helper(
                    gltf=gltf,
                    material=material,
                    collected_info=collected_info,
                    texture_type=texture_type,
                )
    def __collect_mesh_attributes_info(
        self,
        gltf: GLTF2,
        primitive: Primitive,
        collected_info: CollectedInfo,
    ) -> dict:
        attributes_dict = self.__extract_attributes(primitive)

        if primitive.targets is not None and len(primitive.targets) > 0:
            for target_index, target in enumerate(primitive.targets):
                attributes_dict = self.__extract_targets(
                    target_index=target_index,
                    target=target,
                    attributes_dict=attributes_dict,
                )
        self.__process_indices_and_accessors(gltf, attributes_dict, collected_info)


    def __extract_attributes(self, primitive: Primitive) -> dict:
        if isinstance(primitive.attributes, dict):
            attributes_dict = {
                k: v for k, v in primitive.attributes.items() if v is not None
            }
        else:
            attributes_dict = {
                k: v for k, v in vars(primitive.attributes).items() if v is not None
            }
        if primitive.indices is not None:
            attributes_dict["PRIMITIVE_INDICES"] = primitive.indices
        return dict(sorted(attributes_dict.items(), key=lambda x: x[1]))


    def __extract_targets(
        self,
        target_index: int,
        target: Attributes,
        attributes_dict: dict,
    ) -> dict:
        if isinstance(target, dict):
            attributes_dict.update(
                {f"{k}#{target_index}": v for k, v in target.items() if v is not None}
            )
        else:
            attributes_dict.update(
                {f"{k}#{target_index}": v for k, v in vars(target).items() if v is not None}
            )

        return dict(sorted(attributes_dict.items(), key=lambda x: x[1]))


    def __process_indices_and_accessors(
        self,
        gltf: GLTF2,
        attributes_dict: dict,
        collected_info: CollectedInfo,
    ) -> None:
        for _, accessor_index in attributes_dict.items():
            if (
                accessor_index is not None
                and collected_info.accessor_indices.get(accessor_index) is None
            ):
                accessor = gltf.accessors[accessor_index]
                new_accessor_index = len(collected_info.accessors)
                collected_info.accessors.append(accessor)
                collected_info.accessor_indices[accessor_index] = new_accessor_index
                self.__collect_buffer_view_and_buffer(
                    gltf=gltf,
                    accessor=accessor,
                    collected_info=collected_info,
                )


    def __collect_buffer_view_and_buffer(
        self,
        gltf: GLTF2,
        accessor: Accessor,
        collected_info: CollectedInfo,
    ) -> None:
        if collected_info.bufferView_indices.get(accessor.bufferView) is None:
            bufferView: BufferView = gltf.bufferViews[accessor.bufferView]

            new_bufferView_index = len(collected_info.bufferViews)
            collected_info.bufferViews.append(bufferView)
            collected_info.bufferView_indices[accessor.bufferView] = new_bufferView_index

            buffer = gltf.buffers[bufferView.buffer]
            if buffer not in collected_info.buffers:
                collected_info.buffers.append(buffer)

    def __collect_mesh_info(
        self,
        current_node: Node,
        gltf: GLTF2,
        collected_info: CollectedInfo,
    ) -> None:
        if current_node.mesh is not None:
            mesh = gltf.meshes[current_node.mesh]

            if collected_info.meshes_indices.get(current_node.mesh) is None:
                new_mesh_index = len(collected_info.meshes)
                collected_info.meshes_indices[current_node.mesh] = new_mesh_index

                for primitive in mesh.primitives:
                    self.__collect_mesh_material_info(
                        gltf=gltf,
                        primitive=primitive,
                        collected_info=collected_info,
                    )
                
                    self.__collect_mesh_attributes_info(
                        gltf=gltf,
                        primitive=primitive,
                        collected_info=collected_info,
                    )
                collected_info.meshes.append(mesh)

    def __collect_skin_info(
        self,
        gltf: GLTF2,
        current_node: Node,
        collected_info: CollectedInfo,
    ):
        # TEST
        target_skin: Skin = gltf.skins[current_node.skin]
        copied_target_skin = copy.deepcopy(target_skin)
        
        if copied_target_skin.inverseBindMatrices is None:
            return
        
        original_accessor_index = copied_target_skin.inverseBindMatrices
        if collected_info.accessor_indices.get(original_accessor_index) is None:
            skin_accessor: Accessor = gltf.accessors[original_accessor_index]

            original_bufferView_index = skin_accessor.bufferView
            origin_bufferView: BufferView = gltf.bufferViews[original_bufferView_index]

            new_accessor_index = len(collected_info.accessors)

            if collected_info.bufferView_indices.get(original_bufferView_index) is None:
                new_bufferView_index = len(collected_info.bufferViews)
                collected_info.bufferViews.append(origin_bufferView)
                collected_info.bufferView_indices[original_bufferView_index] = (
                    new_bufferView_index
                )
                buffer = gltf.buffers[origin_bufferView.buffer]
                if buffer not in collected_info.buffers:
                    collected_info.buffers.append(buffer)

            collected_info.accessors.append(skin_accessor)
            collected_info.accessor_indices[original_accessor_index] = (
                new_accessor_index
            )

            collected_info.skins_indices[original_accessor_index] = (
                new_accessor_index
            )
            collected_info.skins.append(copied_target_skin)

    def __collect_info(
        self,
        gltf: GLTF2,
        node_index: int,
        split_size: int,
        collected_info: CollectedInfo = None,
        parent_scene_indices: list = None,
    ) -> CollectedInfo:
        if collected_info is None:
            collected_info = self.__init_collected_info()
            parent_scene_indices = []

        if parent_scene_indices is None:
            parent_scene_indices = []

        if len(collected_info.nodes) >= split_size:
            return collected_info

        if node_index in collected_info.node_indices:
            return collected_info

        current_node = gltf.nodes[node_index]
        collected_info.node_indices.add(node_index)
        collected_info.nodes.append(current_node)

        if current_node.skin is not None:
            self.__collect_skin_info(
                gltf=gltf,
                current_node=current_node,
                collected_info=collected_info,
            )

        self.__collect_mesh_info(
            current_node=current_node,
            gltf=gltf,
            collected_info=collected_info,
        )

        current_node_scene_indices = []
        for i, scene in enumerate(gltf.scenes):
            if node_index in scene.nodes:
                current_node_scene_indices.append(i)
                if scene not in collected_info.scenes:
                    collected_info.scenes.append(scene)

        combined_scene_indices = list(
            set(parent_scene_indices + current_node_scene_indices)
        )

        for scene_index in combined_scene_indices:
            while len(collected_info.scene_node_indices) <= scene_index:
                collected_info.scene_node_indices.append([])
            collected_info.scene_node_indices[scene_index].append(node_index)

        if current_node.children is not None and len(current_node.children) > 0:
            for child_index in current_node.children:
                if child_index not in collected_info.node_indices:
                    self.__collect_info(
                        gltf=gltf,
                        node_index=child_index,
                        split_size=split_size,
                        collected_info=collected_info,
                    )

        return collected_info
    
    def __copy_texture_properties(
        self,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        texture_index: int,
        bufferView_index_map: dict[int, int],
        collected_info: CollectedInfo,
    ) -> int:
        
        original_texture = (
            original_gltf.textures[texture_index]
            if collected_info.textures_indices.get(texture_index) is None
            else collected_info.textures[collected_info.textures_indices.get(texture_index)]
        )
        original_sampler_index = original_texture.sampler
        original_image_index = original_texture.source

        new_sampler: Sampler = (
            Sampler()
            if original_gltf.samplers is None or len(original_gltf.samplers) == 0
            else copy.deepcopy(
                original_gltf.samplers[
                    collected_info.samplers_indices[original_sampler_index]
                ]
            )
        )
        new_image: Image = (
            Image()
            if original_gltf.images is None or len(original_gltf.images) == 0
            else copy.deepcopy(
                collected_info.images[collected_info.images_indices[original_image_index]]
            )
        )

        if new_image.bufferView is not None:
            new_image.bufferView = bufferView_index_map[new_image.bufferView]

        new_sampler_index = len(new_gltf.samplers)
        new_gltf.samplers.append(new_sampler)
        new_image_index = len(new_gltf.images)
        new_gltf.images.append(new_image)

        new_texture = copy.deepcopy(original_texture)
        new_texture.sampler = new_sampler_index
        new_texture.source = new_image_index
        new_texture_index = len(new_gltf.textures)
        new_gltf.textures.append(new_texture)

        return new_texture_index


    def __copy_texture_properties_and_update_material(
        self,
        original_material: Material,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        new_material_index: int,
        bufferView_index_map: dict[int, int],
        collected_info: CollectedInfo,
        texture_index_map: dict[int, int],
    ):
        for property_path in self._material_property_paths:
            property_value = original_material
            for part in property_path.split("."):
                if hasattr(property_value, part):
                    property_value = getattr(property_value, part)
                else:
                    property_value = None
                    break

            if property_value is not None and hasattr(property_value, "index"):
                origin_texture_index = property_value.index
                new_texture_index = -1
                if origin_texture_index in texture_index_map:
                    new_texture_index = texture_index_map[origin_texture_index]
                else:
                    new_texture_index = self.__copy_texture_properties(
                        original_gltf=original_gltf,
                        new_gltf=new_gltf,
                        texture_index=origin_texture_index,
                        bufferView_index_map=bufferView_index_map,
                        collected_info=collected_info,
                    )
                    texture_index_map[origin_texture_index] = new_texture_index
                self.__set_texture_index(
                    new_gltf.materials[new_material_index],
                    property_path,
                    new_texture_index,
                )


    def __set_texture_index(
        self,
        material: Material,
        property_path: str,
        new_texture_index: int,
    ):
        parts = property_path.split(".")
        for part in parts[:-1]:
            if hasattr(material, part):
                material = getattr(material, part)
            else:
                return

        if hasattr(material, parts[-1]):
            setattr(material, parts[-1], {"index": new_texture_index})


    def __copy_material_textures(
        self,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        original_material: Material,
        new_material_index: int,
        bufferView_index_map: dict[int, int],
        collected_info: CollectedInfo,
        texture_index_map: dict[int, int],
    ) -> None:
        # material_property_paths = [
        #     "pbrMetallicRoughness.baseColorTexture",
        #     "pbrMetallicRoughness.metallicRoughnessTexture",
        #     "normalTexture",
        #     "occlusionTexture",
        #     "emissiveTexture",
        # ]

        self.__copy_texture_properties_and_update_material(
            original_material=original_material,
            original_gltf=original_gltf,
            new_gltf=new_gltf,
            new_material_index=new_material_index,
            bufferView_index_map=bufferView_index_map,
            collected_info=collected_info,
            texture_index_map=texture_index_map,
        )


    def __update_primitive_attributes_and_indices(
        self,
        primitive: Primitive,
        accessor_index_map: dict[int, int],
    ) -> None:
        
        if hasattr(primitive, "attributes"):
            attributes_dict = (
                primitive.attributes
                if isinstance(primitive.attributes, dict)
                else vars(primitive.attributes)
            )
            attributes_dict = {
                k: accessor_index_map.get(v, v)
                for k, v in attributes_dict.items()
                if v is not None
            }
            primitive.attributes = Attributes(**attributes_dict)

        if primitive.indices is not None:
            primitive.indices = accessor_index_map.get(primitive.indices, primitive.indices)

        if primitive.targets is not None and len(primitive.targets) > 0:
            new_targets = []
            for target in primitive.targets:

                attributes_dict = target if isinstance(target, dict) else vars(target)
                attributes_dict = {
                    k: accessor_index_map.get(v, v)
                    for k, v in attributes_dict.items()
                    if v is not None
                }
                attributes_dict = dict(sorted(attributes_dict.items(), key=lambda x: x[1]))

                new_targets.append(attributes_dict)

            primitive.targets = new_targets
    def __reindex_node(
        self,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        collected_info: CollectedInfo,
        node_index_map: dict,
        mesh_index_map: dict[int, int],
    ) -> None:
        new_gltf.nodes = []
        node_children_temp = {}

        for old_index in collected_info.node_indices:
            
            node_copy: Node = copy.deepcopy(original_gltf.nodes[old_index])

            if node_copy.mesh is not None:
                origin_mesh_index = node_copy.mesh
                node_copy.mesh = mesh_index_map.get(origin_mesh_index, origin_mesh_index)
                # node_copy.mesh = collected_info.meshes_indices.get(
                #     node_copy.mesh, node_copy.mesh
                # )
            new_index = len(new_gltf.nodes)

            for children_idx in node_copy.children:
                child_node: Node = copy.deepcopy(original_gltf.nodes[children_idx])
                if child_node.mesh is not None:
                    origin_child_mesh_index = child_node.mesh
                    child_node.mesh = mesh_index_map.get(origin_child_mesh_index, origin_child_mesh_index)
                    # child_node.mesh = collected_info.meshes_indices.get(
                    #     child_node.mesh, child_node.mesh
                    # )

            node_children_temp[new_index] = node_copy.children
            node_copy.children = []
            new_gltf.nodes.append(node_copy)

        for node_index, old_children_indices in node_children_temp.items():
            new_children_indices = [
                node_index_map.get(child_index)
                for child_index in old_children_indices
                if child_index in node_index_map
            ]
            new_gltf.nodes[node_index].children = new_children_indices

    def __reindex_bufferViews(
        self,
        new_gltf: GLTF2,
        collected_info: CollectedInfo,
        bufferView_index_map: dict[int, int],
    ) -> None:
        new_gltf.bufferViews = []
        for i, bufferView in enumerate(collected_info.bufferViews):
            origin_bufferView_index = {
                key
                for key in collected_info.bufferView_indices
                if collected_info.bufferView_indices[key] == i
            }.pop()
            new_index = len(new_gltf.bufferViews)
            bufferView_copy = copy.deepcopy(bufferView)
            new_gltf.bufferViews.append(bufferView_copy)
            bufferView_index_map[origin_bufferView_index] = new_index
    
    def __reindex_accessors(
        self,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        collected_info: CollectedInfo,
        bufferView_index_map: dict[int, int],
        accessor_index_map: dict[int, int],
    ) -> None:
        new_gltf.accessors = []
        for i, accessor in enumerate(collected_info.accessors):
            new_index = len(new_gltf.accessors)
            origin_accessor_index = {
                key
                for key in collected_info.accessor_indices
                if collected_info.accessor_indices[key] == i
            }.pop()
            accessor_copy: Accessor = copy.deepcopy(accessor)

            if accessor.bufferView is not None:
                accessor_copy.bufferView = bufferView_index_map[accessor.bufferView]
            new_gltf.accessors.append(accessor_copy)
            accessor_index_map[origin_accessor_index] = new_index
    
    def __reindex_mesh(
        self,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        collected_info: CollectedInfo,
        bufferView_index_map: dict[int, int],
        accessor_index_map: dict[int, int],
        mesh_index_map: dict[int, int],
        texture_index_map: dict[int, int],
    ) -> None:
        new_gltf.meshes = []
        new_gltf.textures = []
        new_gltf.samplers = []
        new_gltf.images = []
        for mesh_index, mesh in enumerate(collected_info.meshes):
            mesh_copy: Mesh = copy.deepcopy(mesh)
            for primitive in mesh_copy.primitives:

                if "material" in primitive.__dict__:
                    material_index = primitive.material
                    original_material: Material = collected_info.materials[collected_info.material_indices.get(material_index, material_index)]

                    new_material_index = len(new_gltf.materials)
                    new_material = copy.deepcopy(original_material)
                    new_gltf.materials.append(new_material)
                    new_material.material = new_material_index

                    primitive.material = new_material_index

                    self.__copy_material_textures(
                        original_gltf=original_gltf,
                        new_gltf=new_gltf,
                        original_material=original_material,
                        new_material_index=new_material_index,
                        bufferView_index_map=bufferView_index_map,
                        collected_info=collected_info,
                        texture_index_map=texture_index_map,
                    )

                self.__update_primitive_attributes_and_indices(
                    primitive=primitive,
                    accessor_index_map=accessor_index_map,
                )
            origin_mesh_index = {key for key in collected_info.meshes_indices if collected_info.meshes_indices[key] == mesh_index}.pop()
            new_mesh_index = len(new_gltf.meshes)
            new_gltf.meshes.append(mesh_copy)
            mesh_index_map[origin_mesh_index] = new_mesh_index
    
    def __reindex_animations(
        self,
        new_gltf: GLTF2,
        collected_info: CollectedInfo,
        node_index_map: dict,
        accessor_index_map: dict[int, int],
    ) -> None:
        new_gltf.animations = []
        for animation in collected_info.animations:
            animation_copy: Animation = copy.deepcopy(animation)

            for channel in animation_copy.channels:
                if channel.target.node is not None:
                    channel.target.node = node_index_map.get(
                        channel.target.node, channel.target.node
                    )
                    
            for sampler in animation_copy.samplers:
                if collected_info.accessor_indices.get(sampler.input) is not None:
                    sampler.input = accessor_index_map.get(
                        collected_info.accessor_indices[sampler.input]
                    )
                if collected_info.accessor_indices.get(sampler.output) is not None:
                    sampler.output = accessor_index_map.get(
                        collected_info.accessor_indices[sampler.output]
                    )

            new_gltf.animations.append(animation_copy)

    def __reindex_cameras(
        self, original_gltf: GLTF2, new_gltf: GLTF2
    ) -> None:
        new_gltf.cameras = []
        for node in new_gltf.nodes:
            if node.camera is not None:
                camera_index = node.camera
                original_camera = original_gltf.cameras[camera_index]
                new_camera = copy.deepcopy(original_camera)
                node.camera = len(new_gltf.cameras)
                new_gltf.cameras.append(new_camera)

    def __reindex_scenes(
        self,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        collected_info: CollectedInfo,
        node_index_map: dict,
    ) -> None:
        new_gltf.scenes = []
        for scene_index, scene in enumerate(collected_info.scenes):
            scene_copy: Scene = copy.deepcopy(scene)

            updated_node_indices = []
            for old_node_index in collected_info.scene_node_indices[scene_index]:
                new_node_index = node_index_map.get(old_node_index)
                if new_node_index is not None:
                    updated_node_indices.append(new_node_index)

            scene_copy.nodes = updated_node_indices

            new_gltf.scenes.append(scene_copy)

        root_nodes_indexes = [node_index for scene in original_gltf.scenes for node_index in scene.nodes]

        if new_gltf.scenes is None or len(new_gltf.scenes) == 0:
            new_gltf.scenes = []
            new_scene = Scene(
                nodes=[
                    i
                    for i in range(len(new_gltf.nodes))
                    if new_gltf.nodes[i].mesh is not None
                ]
            )
            new_gltf.scenes.append(new_scene)

        if new_gltf.scene is None:
            new_gltf.scene = 0

    def __reindex_skin(
        self,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        collected_info: CollectedInfo,
        accessor_index_map: dict[int, int],
        bufferView_index_map: dict[int, int]
    ):
        new_gltf.skins = []
        for index, skin in enumerate(collected_info.skins):
            new_index = len(new_gltf.skins)
            # origin_accessor_index = {
            #     key
            #     for key in collected_info.skins_indices
            #     if collected_info.skins_indices[key] == index
            # }.pop()
            # accessor_copy: Accessor = copy.deepcopy(original_gltf.accessors[origin_accessor_index])
            skin_copy = copy.deepcopy(skin)
            # if accessor_copy.bufferView is not None:
            #     accessor_copy.bufferView = bufferView_index_map[accessor_copy.bufferView]
            skin_copy.inverseBindMatrices = new_index
            # accessor_index_map[origin_accessor_index] = new_index
            # new_gltf.accessors.append(accessor_copy)
            new_gltf.skins.append(skin_copy)

    from typing import Tuple


    def __reindex_entities(
        self,
        original_gltf: GLTF2,
        new_gltf: GLTF2,
        collected_info: CollectedInfo,
        bufferView_index_map: dict,
        accessor_index_map: dict,
        mesh_index_map: dict,
        texture_index_map: dict,
    ) -> Tuple[int, int, int]:
        new_gltf.buffers = collected_info.buffers

        node_index_map = {
            old_index: new_index
            for new_index, old_index in enumerate(collected_info.node_indices)
        }

        prev_buffer_views_index = self.__reindex_bufferViews(
            new_gltf=new_gltf,
            collected_info=collected_info,
            bufferView_index_map=bufferView_index_map,
        )

        self.__reindex_skin(
            original_gltf=original_gltf,
            new_gltf=new_gltf,
            collected_info=collected_info,
            accessor_index_map=accessor_index_map,
            bufferView_index_map=bufferView_index_map,
        )

        self.__reindex_accessors(
            original_gltf=original_gltf,
            new_gltf=new_gltf,
            collected_info=collected_info,
            bufferView_index_map=bufferView_index_map,
            accessor_index_map=accessor_index_map,
        )

        self.__reindex_mesh(
            original_gltf=original_gltf,
            new_gltf=new_gltf,
            collected_info=collected_info,
            bufferView_index_map=bufferView_index_map,
            accessor_index_map=accessor_index_map,
            mesh_index_map=mesh_index_map,
            texture_index_map=texture_index_map,
        )

        self.__reindex_node(
            original_gltf=original_gltf,
            new_gltf=new_gltf,
            collected_info=collected_info,
            node_index_map=node_index_map,
            mesh_index_map=mesh_index_map,
        )

        self.__reindex_animations(
            new_gltf=new_gltf,
            collected_info=collected_info,
            node_index_map=node_index_map,
            accessor_index_map=accessor_index_map,
        )

        self.__reindex_cameras(
            original_gltf=original_gltf,
            new_gltf=new_gltf,
        )

        self.__reindex_scenes(
            original_gltf=original_gltf,
            new_gltf=new_gltf,
            collected_info=collected_info,
            node_index_map=node_index_map,
        )

    def __recalculate_buffers_and_save_bin(
        self,
        new_gltf: GLTF2,
        binary_data: Any,
        output_directory: str,
        bin_filename: str,
    ) -> None:
        new_buffers_data = []
        new_buffer_view_offsets = []

        for bufferView in new_gltf.bufferViews:
            start = bufferView.byteOffset
            end = start + bufferView.byteLength
            data_segment = binary_data[start:end]

            new_byteOffset = (
                sum(len(data) for data in new_buffers_data) if new_buffers_data else 0
            )
            new_buffers_data.append(data_segment)
            new_buffer_view_offsets.append(new_byteOffset)

        combined_data = b"".join(new_buffers_data)

        new_buffers = []
        new_gltf.buffers = new_buffers

        # for glb
        new_gltf.set_binary_blob(combined_data)

        new_buffer = Buffer()
        new_buffer.byteLength = len(combined_data)

        # for gltf
        # bin_file_path = os.path.join(output_directory, bin_filename)
        # with open(bin_file_path, "wb") as bin_file:
        #     bin_file.write(combined_data)
        # new_buffer.uri = bin_filename

        new_buffers.append(new_buffer)

        for i, bufferView in enumerate(new_gltf.bufferViews):
            bufferView.buffer = 0
            bufferView.byteOffset = new_buffer_view_offsets[i]

    def __copy_extensions(self, original_gltf: GLTF2, new_gltf: GLTF2) -> None:
      if original_gltf.extensionsRequired is not None:
        new_gltf.extensionsRequired = copy.deepcopy(original_gltf.extensionsRequired)
      if original_gltf.extensionsUsed is not None:
        new_gltf.extensionsUsed = copy.deepcopy(original_gltf.extensionsUsed)
      if original_gltf.extensions is not None:
        new_gltf.extensions = copy.deepcopy(original_gltf.extensions)

    def __set_animations(
        self,
        original_gltf: GLTF2,
        node_index: int,
        collected_info: CollectedInfo,
    ) -> None:
        for animation in original_gltf.animations:
            self.__process_animation_if_relevant(
                animation, node_index, original_gltf, collected_info
            )


    def __process_animation_if_relevant(
        self,
        animation: Animation,
        node_index: int,
        gltf: GLTF2,
        collected_info: CollectedInfo,
    ) -> None:
        for channel in animation.channels:
            if channel.target.node == node_index:
                self.__add_animation_and_its_dependencies(animation, gltf, collected_info)
                break


    def __add_animation_and_its_dependencies(
        self,
        animation: Animation,
        gltf: GLTF2,
        collected_info: CollectedInfo,
    ) -> None:
        if animation not in collected_info.animations:
            for sampler in animation.samplers:
                self.__process_sampler_for_animation(
                    sampler=sampler,
                    gltf=gltf,
                    collected_info=collected_info,
                )
            
            collected_info.animations.append(animation)


    def __process_sampler_for_animation(
        self,
        sampler: Sampler,
        gltf: GLTF2,
        collected_info: CollectedInfo,
    ) -> None:
        if sampler.input is not None:
            if collected_info.accessor_indices.get(sampler.input) is None:
                new_accessor_index = self.__add_accessor_and_its_dependencies(
                    sampler.input, gltf, collected_info
                )
                sampler.input = new_accessor_index
            else:
                sampler.input = collected_info.accessor_indices.get(sampler.input)
        if sampler.output is not None:
            if collected_info.accessor_indices.get(sampler.output) is None:
                new_accessor_index = self.__add_accessor_and_its_dependencies(
                    sampler.output, gltf, collected_info
                )
                sampler.output = new_accessor_index
            else:
                sampler.output = collected_info.accessor_indices.get(sampler.output)


    def __add_accessor_and_its_dependencies(
        self,
        accessor_index: int,
        gltf: GLTF2,
        collected_info: CollectedInfo,
    ) -> int:
        accessor = gltf.accessors[accessor_index]
        new_accessor_index = len(collected_info.accessors)
        collected_info.accessors.append(accessor)
        collected_info.accessor_indices[accessor_index] = new_accessor_index

        bufferView_index = accessor.bufferView
        if collected_info.bufferView_indices.get(bufferView_index) is None:
            bufferView = gltf.bufferViews[bufferView_index]
            new_bufferView_index = len(collected_info.bufferViews)
            collected_info.bufferViews.append(bufferView)
            collected_info.bufferView_indices[bufferView_index] = new_bufferView_index

            self.__add_buffer_for_bufferView(bufferView, gltf, collected_info)

        return new_accessor_index


    def __add_buffer_for_bufferView(
        self,
        bufferView: BufferView,
        gltf: GLTF2,
        collected_info: CollectedInfo,
    ) -> None:
        buffer = gltf.buffers[bufferView.buffer]
        if buffer not in collected_info.buffers:
            collected_info.buffers.append(buffer)

    def __build_parent_map(self, gltf: GLTF2) -> dict[int, int]:
        parent_map = {}

        def visit_node(node_index, parent_index=-1):
            parent_map[node_index] = parent_index
            for child_index in gltf.nodes[node_index].children or []:
                visit_node(child_index, node_index)

        for scene in gltf.scenes:
            for node_index in scene.nodes:
                visit_node(node_index)

        return parent_map

    def split_model_by_nodes(self, input_glb_path: str, split_size: int = 100, output_dir: str = "./outputs") -> None:
        base_name = os.path.splitext(os.path.basename(input_glb_path))[0]
        os.makedirs(output_dir, exist_ok=True)

        original_gltf = GLTF2().load(input_glb_path)
        binary_data = original_gltf.binary_blob()

        copied_original_gltf = copy.deepcopy(original_gltf)

        parent_map = self.__build_parent_map(original_gltf)

        root_nodes = [
            node_index
            for node_index, parent_index in parent_map.items()
            if parent_index == -1
        ]

        total_nodes = len(original_gltf.nodes)
        total_files = (total_nodes + split_size - 1) // split_size
        bufferView_index_map = {}
        accessor_index_map = {}
        mesh_index_map = {}
        texture_index_map = {}

        if total_nodes <= 400:
            gltf_filename = f"{base_name}_{1}.glb"
            output_file_path = os.path.join(output_dir, gltf_filename)
            original_gltf.save(output_file_path)
            print(f"Saved: {output_file_path}")
            return

        for file_index in range(total_files):
            new_gltf = GLTF2()

            self.__copy_extensions(
                original_gltf=copied_original_gltf,
                new_gltf=new_gltf,
            )

            collected_info = self.__init_collected_info()

            start_node_index = file_index * split_size
            end_node_index = min(start_node_index + split_size, total_nodes)

            for node_index in range(start_node_index, end_node_index):
                # if parent_map[node_index] in collected_info.node_indices:
                #     continue
                self.__collect_info(
                    gltf=copied_original_gltf,
                    node_index=node_index,
                    split_size=split_size,
                    collected_info=collected_info,
                )
                self.__set_animations(
                    original_gltf=copied_original_gltf,
                    node_index=node_index,
                    collected_info=collected_info,
                )

            gltf_filename = f"{base_name}_{file_index + 1}.glb"
            bin_filename = f"{base_name}_{file_index + 1}.bin"

            self.__reindex_entities(
                original_gltf=original_gltf,
                new_gltf=new_gltf,
                collected_info=collected_info,
                bufferView_index_map=bufferView_index_map,
                accessor_index_map=accessor_index_map,
                mesh_index_map=mesh_index_map,
                texture_index_map=texture_index_map,
            )

            if (
                new_gltf.accessors is None
                or new_gltf.bufferViews is None
                or len(new_gltf.accessors) == 0
                or len(new_gltf.bufferViews) == 0
            ):
                continue

            self.__recalculate_buffers_and_save_bin(
                new_gltf=new_gltf,
                binary_data=binary_data,
                output_directory=output_dir,
                bin_filename=bin_filename,
            )

            output_file_path = os.path.join(output_dir, gltf_filename)
            new_gltf.save(output_file_path)
            # pathlib.Path(os.path.join(output_dir, bin_filename)).unlink(missing_ok=True)