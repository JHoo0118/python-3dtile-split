
from tqdm.auto import tqdm
from .tree_node_model import TreeNode
import numpy as np
from functools import partial

class IfcTreeStructure:
    def __init__(self, element, ifc_create_shape: partial, use_edge=False, include_space=False):
        self.num_meshes = 0
        self.num_nodes = 0
        self.use_edge = use_edge
        self.include_space = include_space
        self.material_dict = {}
        self.tree = self.create_node(element)
        self.ifc_create_shape = ifc_create_shape

        self.element_count = 0
        self.explore_element_count(element)

        self.bar = tqdm(total=self.element_count)
        self.explore_element(self.tree)
        self.bar.close()

    def __repr__(self):
        return repr(self.tree)

    def create_node(self, element, level=0):
        node = TreeNode(element, level, self.num_nodes)
        self.num_nodes += 1
        return node

    def get_child_elements(self, element):
        for relationship in getattr(element, "IsDecomposedBy", []):
            for related_element in relationship.RelatedObjects:
                yield related_element

        for relationship in getattr(element, "ContainsElements", []):
            for related_element in relationship.RelatedElements:
                yield related_element

    def explore_element_count(self, element):
        self.element_count += 1
        for child_element in self.get_child_elements(element):
            self.explore_element_count(child_element)

    def explore_element(self, node, level=0):
        self.bar.update(1)

        if node.has_geometry:
            geometry = self.get_geometry(node.element)
            if len(geometry) == 0:
                node.has_geometry = False
            elif len(geometry) == 1:
                node.geometry = geometry[0]
                node.mesh_index = self.num_meshes
                self.num_meshes += 1
            elif len(geometry) > 1:
                node.has_geometry = False
                for g in geometry:
                    child = self.create_node(node.element, level + 1)
                    node.children.append(child)
                    material_name = self.material_dict[g["material"]]["name"]
                    child.name = f"{node.name} | {material_name}"
                    child.geometry = g
                    child.mesh_index = self.num_meshes
                    self.num_meshes += 1
                return

        for child_element in self.get_child_elements(node.element):
            child = self.create_node(child_element, level + 1)
            node.children.append(child)
            self.explore_element(child, level + 1)

    def is_valid_material(self, diffuse_color, transparency):
        if all(c == 0.0 for c in diffuse_color) and transparency == 0.0:
            return False
        return True

    def get_geometry(self, element):
        if not self.include_space and element.is_a("IfcSpace"):
            return []

        try:
            shape = self.ifc_create_shape(inst=element)
        except Exception as e:
            print(element, e)
            return []

        matrix = shape.transformation.matrix.data
        faces = shape.geometry.faces
        edges = shape.geometry.edges
        verts = shape.geometry.verts
        materials = shape.geometry.materials
        material_ids = shape.geometry.material_ids
        edges = np.array(edges).reshape(-1, 2)

        if not self.use_edge and len(faces) == 0:
            return []

        vertices = np.array(verts).reshape(-1, 3)[:, [0, 2, 1]]
        vertices[:, 0] = -vertices[:, 0]
        triangles = np.array(faces).reshape(-1, 3)

        geometries = []
        material_ids = np.array(material_ids)
        for mat_id, material in enumerate(materials):
            diffuse_color = (
                np.array(material.diffuse) / 255.0
                if np.max(material.diffuse) > 1
                else np.array(material.diffuse)
            )
              
            color = *diffuse_color, 1 - material.transparency

            if not self.is_valid_material(diffuse_color, material.transparency):
                # color = (0.8, 0.8, 0.8, 1)
                color = (0.5, 0.5, 0.5, 1)

            self.material_dict[material.name] = dict(
                color=color, name=material.original_name()
            )

            mat_edges = edges[material_ids == mat_id] if len(triangles) == 0 else edges
            mat_triangles = (
                triangles[material_ids == mat_id] if len(triangles) > 0 else triangles
            )
            geometries.append(
                dict(
                    name=element.is_a(),
                    vertices=vertices,
                    triangles=mat_triangles,
                    material=material.name,
                    edges=mat_edges,
                )
            )

        return geometries