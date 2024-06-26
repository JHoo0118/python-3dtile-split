import os
import json
import ifcopenshell
import ifcopenshell.geom
import struct
import numpy as np
from ifcopenshell.entity_instance import entity_instance
from types import SimpleNamespace
from functools import partial
from pygltflib import (
    GLTF2,
    Buffer,
    BufferView,
    Mesh,
    UNSIGNED_INT,
    SCALAR,
    FLOAT,
    ELEMENT_ARRAY_BUFFER,
    ARRAY_BUFFER,
    VEC3,
    OPAQUE,
    BLEND,
    Material,
    PbrMetallicRoughness,
    Accessor,
    Attributes,
    Primitive,
    Node,
    Scene,
    LINES,
    TRIANGLES,
    UNSIGNED_BYTE,
    UNSIGNED_SHORT,
    UNSIGNED_INT,
)
from model.ifc_tree_structure_model import IfcTreeStructure
from utils import to_dict, extract_non_null_attributes
from service.batch_table_service import BatchTableService

settings = ifcopenshell.geom.settings()
settings.set(settings.USE_WORLD_COORDS, True)
# settings.set(settings.INCLUDE_CURVES, True)
settings.set(settings.STRICT_TOLERANCE, True)
settings.set(settings.USE_ELEMENT_GUIDS, True)
settings.set(settings.APPLY_DEFAULT_MATERIALS, True)


class IfcService(object):
    _instance = None
    _batch_table_service: BatchTableService
    _mesh_name_mapping: dict[str, str]
    _batch_table: dict[str, list]
    _batch_table_mapping: dict
    exclude_keys: list[str] = ["representation", "objectPlacement", "ownerHistory"]

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance
    
    def __init__(self):
        self._batch_table_service = BatchTableService()
        
    
    def __make_shape(self) -> partial:
        return partial(ifcopenshell.geom.create_shape, settings=settings)
                
    def ifc_to_glb(
      self,
      input_ifc_path: str, 
      output_dir: str,
      output_base_filename: str,
    ) -> tuple[dict[str, list], dict, dict[str, str]]:
        
      ifc_file = ifcopenshell.open(input_ifc_path)

      products = ifc_file.by_type("IfcProduct")

      project = products[0]

      self._mesh_name_mapping = {}
      batch_table, batch_table_mapping = self._batch_table_service.init_batch_table_keys(project)
      self._batch_table, self._batch_table_mapping = batch_table, batch_table_mapping

      ifc_create_shape = self.__make_shape()
      tree = IfcTreeStructure(project, ifc_create_shape) 
      gltf: GLTF2 = self.__to_glb(tree)

      gltf.save(f"{output_dir}/{output_base_filename}.glb")
      self._batch_table_service.save_batch_table(output_dir, output_base_filename, batch_table, batch_table_mapping)
      self.__save_mesh_name_mapping(output_dir, output_base_filename, self._mesh_name_mapping)
      return self._batch_table, self._batch_table_mapping, self._mesh_name_mapping
    
    def __save_mesh_name_mapping(self, output_dir: str, output_filename: str, mesh_name_mapping: dict[str, str]):
        with open(f'{output_dir}/{output_filename}_mesh_name_mapping.json', 'w') as f:
            json.dump(mesh_name_mapping, f, indent=2)

    def __to_glb(self, mesh_tree: IfcTreeStructure):
        materials = []
        for index, (_, material_data) in enumerate(mesh_tree.material_dict.items()):
            color = material_data["color"]
            name = material_data["name"]
            material_data["index"] = index
            alphaMode = OPAQUE if color[-1] == 1 else BLEND
            materials.append(
                Material(
                    pbrMetallicRoughness=PbrMetallicRoughness(
                        baseColorFactor=color,
                        metallicFactor=0,
                        roughnessFactor=0.5,
                    ),
                    alphaMode=alphaMode,
                    # alphaCutoff=0.5 if alphaMode == "MASK" else None,
                    doubleSided=False,
                    name=name,
                )
            )

        gltf_data = SimpleNamespace(
            nodes=[],
            meshes=[],
            bufferViews=[],
            accessors=[],
            byteOffset=0,
            binary_blobs=b"",
        )

        def __create_gltf_node_mesh(node):
            gltf_data.nodes.append(
                Node(
                    name=node.name,
                    mesh=node.mesh_index,
                    children=[child.node_index for child in node.children],
                )
            )

            if node.has_geometry:
                mesh, bufferView, accessor, binary_blob = self.__create_gltf_mesh(
                    node.geometry,
                    mesh_tree.material_dict,
                    node.mesh_index,
                    gltf_data.byteOffset,
                )
                if hasattr(node.element, "GlobalId"):
                    ifc_data = self.__extract_ifc_data(node.element)
                    self._batch_table_service.create_batch_table(self._batch_table, self._batch_table_mapping, node.mesh_index, ifc_data)
                    self._mesh_name_mapping[node.element.GlobalId] = (
                        mesh.name if mesh.name else "Mesh"
                    )
                    mesh.name = node.element.GlobalId
                gltf_data.meshes.append(mesh)
                gltf_data.bufferViews.extend(bufferView)
                gltf_data.accessors.extend(accessor)
                gltf_data.binary_blobs += binary_blob
                gltf_data.byteOffset += len(binary_blob)

            for child in node.children:
                __create_gltf_node_mesh(child)

        root_node = mesh_tree.tree
        __create_gltf_node_mesh(root_node)

        gltf = GLTF2(
            scene=0,
            scenes=[Scene(nodes=[0])],
            nodes=gltf_data.nodes,
            meshes=gltf_data.meshes,
            accessors=gltf_data.accessors,
            bufferViews=gltf_data.bufferViews,
            buffers=[Buffer(byteLength=len(gltf_data.binary_blobs))],
            materials=materials,
        )
        gltf.set_binary_blob(gltf_data.binary_blobs)
        return gltf
        
    def __create_gltf_mesh(self, geometry, material_dict: dict, index: int, byteOffset: int):
        points = geometry["vertices"]
        lines = geometry.get("edges", [])
        triangles = geometry["triangles"]
        material_name = geometry.get("material")
        material_index = material_dict[material_name]["index"]

        if len(triangles) == 0:
            indices = lines
            mode = LINES
        else:
            indices = triangles
            mode = TRIANGLES

        points = points.astype(np.float32)
        indices_max = indices.max()
        if indices_max <= np.iinfo(np.uint8).max:
            componentType = UNSIGNED_BYTE
            indices = indices.astype(np.uint8)
        elif indices_max <= np.iinfo(np.uint16).max:
            componentType = UNSIGNED_SHORT
            indices = indices.astype(np.uint16)
        else:
            componentType = UNSIGNED_INT
            indices = indices.astype(np.uint32)

        indices_binary_blob = indices.flatten().tobytes()
        points_binary_blob = points.tobytes()

        mesh = Mesh(
            primitives=[
                Primitive(
                    attributes=Attributes(POSITION=1 + index * 2),
                    indices=index * 2,
                    material=material_index,
                    mode=mode,
                )
            ]
        )

        # bufferViews
        byteLength = len(indices_binary_blob) + len(points_binary_blob)
        bufferViews = [
            BufferView(
                buffer=0,
                byteOffset=byteOffset,
                byteLength=len(indices_binary_blob),
                target=ELEMENT_ARRAY_BUFFER,
            ),
            BufferView(
                buffer=0,
                byteOffset=byteOffset + len(indices_binary_blob),
                byteLength=len(points_binary_blob),
                target=ARRAY_BUFFER,
            ),
        ]
        byteOffset += byteLength

        # accessors
        accessors = [
            Accessor(
                bufferView=index * 2,
                componentType=componentType,
                count=indices.size,
                type=SCALAR,
                max=[int(indices.max())],
                min=[int(indices.min())],
            ),
            Accessor(
                bufferView=index * 2 + 1,
                componentType=FLOAT,
                count=len(points),
                type=VEC3,
                max=points.max(axis=0).tolist(),
                min=points.min(axis=0).tolist(),
            ),
        ]

        binary_blobs = indices_binary_blob + points_binary_blob

        return mesh, bufferViews, accessors, binary_blobs
  
    def merge_metadata(self, output_dir:str, base_name: str):
        with open(f"{output_dir}/{base_name}_batch_table.json", "r") as f:
          batch_table = json.load(f)
        with open(f"{output_dir}/{base_name}_batch_table_mapping.json", "r") as f:
          batch_table_mapping = json.load(f)
        with open(f"{output_dir}/{base_name}_mesh_name_mapping.json", "r") as f:
          mesh_name_mapping = json.load(f)

        original_gltf = GLTF2().load(f"{output_dir}/{base_name}.glb")

        structural_metadata_output, structural_metadata_buffer_data_output = (
              self.create_structural_metadata(original_gltf, batch_table, True)
          )

        self.add_structural_metadata_to_gltf(
            gltf=original_gltf,
            bin_filename=f"{base_name}_feature_metadata_buffer.bin",
            output_dir=output_dir,
            structural_metadata=structural_metadata_output,
            structural_metadata_buffer_data=structural_metadata_buffer_data_output,
            save=True,
        )

        self.generate_feature_data(
            gltf=original_gltf,
            output_dir=output_dir,
            output_path=f"{base_name}_feature_ids_buffer.bin",
            batch_table=batch_table,
            batch_table_mapping=batch_table_mapping,
            mesh_name_mapping=mesh_name_mapping
        )
        
        gltf_filename = f"{base_name}_merged_with_metadata.glb"
        output_file_path = os.path.join(output_dir, gltf_filename)
        original_gltf.save(output_file_path)
        print(f"Saved: {output_file_path}")
        return True

    def __extract_height(self, ifc_element):
        try:
            settings = ifcopenshell.geom.settings()
            shape = ifcopenshell.geom.create_shape(settings, ifc_element)
            vertices = shape.geometry.verts
            if not vertices:
                return 0
            z_coords = [vertices[i+2] for i in range(0, len(vertices), 3)]
            height = max(z_coords) - min(z_coords)
            return height
        except Exception as e:
            print(f"Error extracting height for element {ifc_element.GlobalId}: {e}")
            return 0
        
    def __get_owner_history(self, owner_history):
        if not owner_history:
            return 'Unknown'
        
        owning_user = owner_history.OwningUser if hasattr(owner_history, 'OwningUser') else None
        if owning_user:
            person = owning_user.ThePerson if hasattr(owning_user, 'ThePerson') else None
            if person:
                return person.GivenName if person.GivenName else 'Unknown'
        
        return 'Unknown'

    def __get_building_address(self, building_address):
        if not building_address:
            return 'No Address'
        
        address_lines = building_address.AddressLines if hasattr(building_address, 'AddressLines') else []
        return ', '.join(address_lines)
    

    def __get_wbs_data(self, element: entity_instance) -> str:
        for rel in element.IsDefinedBy:
          if rel.is_a("IfcRelDefinesByProperties"):
              prop_set = rel.RelatingPropertyDefinition
              if prop_set.is_a("IfcPropertySet"):
                  for prop in prop_set.HasProperties:
                      if prop.is_a("IfcPropertySingleValue") and prop.Name == 'WBS':
                          wbs_value = prop.NominalValue.wrappedValue
                          return wbs_value
        return ""

    def __extract_ifc_data(self, element):
        if not hasattr(element, 'Representation') or not element.Representation:
          return None
        
        element_dict = to_dict(element, self._batch_table_service.exclude_keys)

        wbs = self.__get_wbs_data(element)
        element_dict["wbs"] = wbs
        element_data = {key: '' for key in self._batch_table}
        element_data.update(element_dict)

        return element_data
    
    def create_structural_metadata(self, gltf: GLTF2, batch_table: dict, save=True) -> tuple[dict, bytearray]:
      structural_metadata_buffer_data = bytearray()

      def add_string_buffer_view_and_accessor(strings) -> tuple[int, int]:
          offsets = []
          byte_offset = len(structural_metadata_buffer_data)
          current_offset = 0

          for string in strings:
              if not string:
                  string = ""
              elif isinstance(string, dict):
                  string = json.dumps(string)
              elif isinstance(string, int):
                  string = str(string)
              encoded_string = string.encode("utf-8")
              structural_metadata_buffer_data.extend(encoded_string)
              offsets.append(current_offset)
              current_offset += len(encoded_string)
          if current_offset == 0:
              return 0, 0
          offsets.append(current_offset)

          string_buffer_view = BufferView(
              buffer=len(gltf.buffers),
              byteOffset=byte_offset,
              byteLength=current_offset,
              target=None,
          )
          gltf.bufferViews.append(string_buffer_view)

          string_accessor = Accessor(
              bufferView=len(gltf.bufferViews) - 1,
              byteOffset=0,
              componentType=5121,  # UNSIGNED_BYTE
              count=current_offset,
              type=SCALAR,
              normalized=False,
          )
          gltf.accessors.append(string_accessor)

          offsets_data = struct.pack(f"<{len(offsets)}I", *offsets)
          offsets_byte_offset = len(structural_metadata_buffer_data)
          structural_metadata_buffer_data.extend(offsets_data)

          offsets_buffer_view = BufferView(
              buffer=len(gltf.buffers),
              byteOffset=offsets_byte_offset,
              byteLength=len(offsets_data),
              target=None,
          )
          gltf.bufferViews.append(offsets_buffer_view)

          offsets_accessor = Accessor(
              bufferView=len(gltf.bufferViews) - 1,
              byteOffset=0,
              componentType=5125,  # UNSIGNED_INT
              count=len(offsets),
              type=SCALAR,
              normalized=False,
          )
          gltf.accessors.append(offsets_accessor)

          return len(gltf.accessors) - 2, len(gltf.accessors) - 1

      property_tables = {
          "class": "class_batch_table",
          "count": len(batch_table["globalId"]),
          "properties": {},
      }

      structural_metadata = {
          "schema": {
              "id": "ID_batch_table",
              "name": "Generated from batch_table",
              "classes": {"class_batch_table": {"properties": {}}},
          },
      }
      for key in batch_table:
          if not batch_table[key]:
              continue

          if save:
              accessor, string_offset = add_string_buffer_view_and_accessor(
                  batch_table[key]
              )
              if accessor == 0 and string_offset == 0:
                  continue
              property_tables["properties"][key] = {
                  "values": accessor,
                  "stringOffsets": string_offset,
              }
          else:
              property_tables["properties"][key] = {}

          structural_metadata["schema"]["classes"]["class_batch_table"]["properties"][
              key
          ] = {
              "name": key,
              "type": "STRING",
              "description": f"Generated from {key}",
          }
      structural_metadata["propertyTables"] = [property_tables]

      return structural_metadata, structural_metadata_buffer_data
    
    def add_structural_metadata_to_gltf(
        self,
        gltf: GLTF2,
        bin_filename: str,
        output_dir: str,
        structural_metadata: dict,
        structural_metadata_buffer_data,
        save=True,
    ):
        if not gltf.extensionsUsed:
            gltf.extensionsUsed = []

        if "EXT_structural_metadata" not in gltf.extensionsUsed:
            gltf.extensionsUsed.append("EXT_structural_metadata")
        if "EXT_mesh_features" not in gltf.extensionsUsed:
            gltf.extensionsUsed.append("EXT_mesh_features")

        if not gltf.extensions:
            gltf.extensions = {}

        gltf.extensions["EXT_structural_metadata"] = structural_metadata

        if save:
            buffer = Buffer(
                uri=bin_filename, byteLength=len(structural_metadata_buffer_data)
            )
            gltf.buffers.append(buffer)

            with open(f"{output_dir}/{bin_filename}", "wb") as f:
                f.write(structural_metadata_buffer_data)

    def generate_feature_data_helper(
        self,
        gltf: GLTF2,
        feature_ids_buffer_data: bytearray,
        mesh_index: int,
        mesh: Mesh,
        batch_table: dict,
        batch_table_mapping: dict,
        mesh_name_mapping: dict[str, str]
    ):
        for primitive_index, primitive in enumerate(mesh.primitives):
            if not primitive.attributes:
                primitive.attributes = Attributes()

            attributes_dict = extract_non_null_attributes(primitive.attributes)

            position_accessor_index: int = primitive.attributes.POSITION
            position_accessor: Accessor = gltf.accessors[position_accessor_index]
            vertex_count: int = position_accessor.count

            mapping_key = mesh.name + str(mesh_index)
            batch_data = batch_table_mapping[mapping_key]
            feature_id = batch_data["batchId"]

            mesh.name = mesh_name_mapping[mesh.name]

            feature_ids_replicated = [feature_id] * vertex_count

            feature_ids_data = struct.pack(
                f"<{len(feature_ids_replicated)}f", *feature_ids_replicated
            )

            if len(feature_ids_data) == 0:
                print("no data")
                continue

            byte_offset = len(feature_ids_buffer_data)
            feature_ids_buffer_data.extend(feature_ids_data)

            feature_ids_buffer_view = BufferView(
                buffer=len(gltf.buffers),
                byteOffset=byte_offset,
                byteLength=len(feature_ids_data),
                target=34962,
            )
            gltf.bufferViews.append(feature_ids_buffer_view)

            feature_ids_accessor = Accessor(
                bufferView=len(gltf.bufferViews) - 1,
                byteOffset=0,
                componentType=5126,  # FLOAT
                count=vertex_count,
                type=SCALAR,
                normalized=False,
            )
            gltf.accessors.append(feature_ids_accessor)
            feature_ids_accessor_index = len(gltf.accessors) - 1

            attributes_dict["_FEATURE_ID_0"] = feature_ids_accessor_index

            # BATCHID START
            # batch_ids_replicated = [feature_id] * vertex_count
            # batch_ids_data = struct.pack(
            #     f"<{len(batch_ids_replicated)}f", *batch_ids_replicated
            # )

            # batch_byte_offset = len(feature_ids_buffer_data)
            # feature_ids_buffer_data.extend(batch_ids_data)

            # batch_ids_buffer_view = BufferView(
            #     buffer=len(gltf.buffers),
            #     byteOffset=batch_byte_offset,
            #     byteLength=len(batch_ids_data),
            #     target=34962
            # )
            # gltf.bufferViews.append(batch_ids_buffer_view)

            # batch_ids_accessor = Accessor(
            #     bufferView=len(gltf.bufferViews) - 1,
            #     byteOffset=0,
            #     componentType=5126,  # UNSIGNED_INT
            #     count=vertex_count,
            #     type="SCALAR",
            #     normalized=False
            # )
            # gltf.accessors.append(batch_ids_accessor)
            # batch_ids_accessor_index = len(gltf.accessors) - 1

            # attributes_dict["_BATCHID"] = batch_ids_accessor_index
            # BATCHID END

            primitive.attributes = Attributes(**attributes_dict)
            primitive = Primitive(
                attributes=primitive.attributes,
                extras=primitive.extras,
                indices=primitive.indices,
                material=primitive.material,
                mode=primitive.mode,
                targets=primitive.targets,
                extensions={
                    "EXT_mesh_features": {
                        "featureIds": [
                            {
                                "attribute": 0,
                                # "featureCount": vertex_count,
                                "featureCount": 1,
                                "propertyTable": 0,
                            }
                        ]
                    }
                },
            )
            mesh.primitives[primitive_index] = primitive


    def generate_feature_data(
            self,
            gltf: GLTF2,
            output_dir: str,
            output_path: str,
            batch_table: dict,
            batch_table_mapping: dict,
            mesh_name_mapping: dict[str, str]
        ):
        feature_ids_buffer_data = bytearray()
        for mesh_index, mesh in enumerate(gltf.meshes):
            self.generate_feature_data_helper(
                gltf=gltf,
                feature_ids_buffer_data=feature_ids_buffer_data,
                mesh_index=mesh_index,
                mesh=mesh,
                batch_table=batch_table,
                batch_table_mapping=batch_table_mapping,
                mesh_name_mapping=mesh_name_mapping,
            )

        feature_id_buffer = Buffer(uri=output_path, byteLength=len(feature_ids_buffer_data))
        gltf.buffers.append(feature_id_buffer)

        with open(f"{output_dir}/{output_path}", "wb") as f:
            f.write(feature_ids_buffer_data)