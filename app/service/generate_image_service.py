from typing import Literal
import bpy
import mathutils
import math

class GenerateImageService(object):
    _instance = None
    _material_property_paths = []

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance
    
    def generate_image(
            self, 
            input_glb_path: str, 
            output_image_path: str, 
            camera_lenses: int,
            camera_distance: float = 1.3, 
            horizontal_rotate_direction: Literal['cw', 'ccw'] = 'cw', 
            horizontal_rotate_degree: float = 0,
            vertical_rotate_direction: Literal['u', 'd'] = 'u', 
            vertical_rotate_degree: float = 0
        ):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=input_glb_path)

        scene = bpy.context.scene
        scene.render.engine = "CYCLES" #CYCLES # BLENDER_EEVEE
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = output_image_path
        scene.render.film_transparent = True
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100

        world = scene.world
        if not world:
            world = bpy.data.worlds.new("World")
            scene.world = world
        world.use_nodes = True
        bg = world.node_tree.nodes['Background']
        bg.inputs[0].default_value = (0.8, 0.8, 0.8, 1)
        bg.inputs[1].default_value = 1.0

        min_coords, max_coords = None, None
        for obj in scene.objects:
            if obj.type == 'MESH':
                for vertex in obj.data.vertices:
                    global_vertex = obj.matrix_world @ vertex.co
                    if min_coords is None:
                        min_coords = global_vertex.copy()
                        max_coords = global_vertex.copy()
                    else:
                        min_coords = mathutils.Vector((min(min_coords[i], global_vertex[i]) for i in range(3)))
                        max_coords = mathutils.Vector((max(max_coords[i], global_vertex[i]) for i in range(3)))

        center = (min_coords + max_coords) / 2
        size = max_coords - min_coords
        max_dimension = max(size)

        def look_at(obj, target):
            direction = target - obj.location
            horizontal_rotation = direction.to_track_quat('-Z', 'Y').to_euler()
            vertical_rotation = math.atan2(direction.y, math.sqrt(direction.x ** 2 + direction.z ** 2))
            obj.rotation_euler = horizontal_rotation
            obj.rotation_euler[0] = vertical_rotation
            
            current_horizontal_angle = math.atan2(camera.location.y, camera.location.x)
            current_vertical_angle = math.atan2(camera.location.z, math.sqrt(camera.location.x ** 2 + camera.location.y ** 2))
            horizontal_distance = math.sqrt(camera.location.x ** 2 + camera.location.y ** 2)
            vertical_distance = math.sqrt(camera.location.z ** 2 + horizontal_distance ** 2)

            # cw (+) ccw (-)
            horizontal_rotate_direction_factor = 1 if horizontal_rotate_direction == 'cw' else -1
            # upward (+) downward (-)
            vertical_rotate_direction_factor = 1 if vertical_rotate_direction == 'u' else -1
            new_horizontal_angle = current_horizontal_angle + (math.radians(horizontal_rotate_degree) * horizontal_rotate_direction_factor)
            new_vertical_angle = current_vertical_angle + (math.radians(vertical_rotate_degree) * vertical_rotate_direction_factor)
            new_x = horizontal_distance * math.cos(new_horizontal_angle)
            new_y = horizontal_distance * math.sin(new_horizontal_angle)
            new_z = vertical_distance * math.sin(new_vertical_angle)

            camera.location.x = new_x
            camera.location.y = new_y
            camera.location.z = new_z

            # horizontal rotation
            camera.rotation_euler[2] += (math.radians(horizontal_rotate_degree) * horizontal_rotate_direction_factor)
            # vertical rotation
            camera.rotation_euler[0] += (math.radians(vertical_rotate_degree) * vertical_rotate_direction_factor)
                       
        camera_data = bpy.data.cameras.new("Camera")
        camera = bpy.data.objects.new("Camera", camera_data)
        camera.data.clip_start = 0.1
        camera.data.clip_end = 3000

        scene.collection.objects.link(camera)
        scene.camera = camera

        distance = max_dimension * camera_distance
        camera_data.lens = camera_lenses # 클수록 확대
        camera.location = center + mathutils.Vector((0, -distance, size.z / 2))

        look_at(camera, center)

        bpy.ops.render.render(write_still=True)