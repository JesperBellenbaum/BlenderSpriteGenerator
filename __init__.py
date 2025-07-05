bl_info = {
    "name": "2D/2.5D Sprite Renderer",
    "description": "Renders multi-angle sprites with roll control for 2D/2.5D game development",
    "author": "Rubiel + enhanced",
    "version": (1, 3, 0),
    "blender": (3, 4, 0),
    "location": "View3D > Sidebar > Sprite Renderer Panel",
    "category": "Object",
}

import bpy
import os
import math
from math import cos, sin, tan
from mathutils import Vector


def bbox_center_and_size(obj):
    """Return (world-space centre, height) of obj's bounding box."""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    bb_min = Vector((min(c.x for c in corners),
                     min(c.y for c in corners),
                     min(c.z for c in corners)))
    bb_max = Vector((max(c.x for c in corners),
                     max(c.y for c in corners),
                     max(c.z for c in corners)))
    centre = (bb_min + bb_max) * 0.5
    height = bb_max.z - bb_min.z
    return centre, height


def ensure_output_nodes(scene, outdir, basename):
    """Create or reuse File Output nodes for N(ormal) and Z(depth)."""
    if not scene.node_tree:
        scene.use_nodes = True
    nt = scene.node_tree

    # Idempotent: only add once
    if "SPRITE_OUT_NORMAL" not in nt.nodes:
        rl = nt.nodes.new("CompositorNodeRLayers")
        rl.name = "SPRITE_RLAYERS"

        for tag, label, depth in (("N", "Normal", 8), ("Z", "Depth", 16)):
            out = nt.nodes.new("CompositorNodeOutputFile")
            out.name = f"SPRITE_OUT_{label.upper()}"
            out.base_path = outdir
            out.format.file_format = 'PNG'          # PNG for both normal and depth
            out.format.color_depth = str(depth)     # 8-bit for normals, 16-bit for depth
            nt.links.new(rl.outputs[label], out.inputs[0])
    return nt


def update_output_node_paths(nt, base, yaw_i, roll_i, frame):
    """Update File Output node paths for each pass."""
    tag = f"{yaw_i:02d}_{roll_i:02d}"
    if frame is not None:
        tag += f"_F{frame:03d}"
    nt.nodes["SPRITE_OUT_NORMAL"].file_slots[0].path = f"{base}_N_{tag}"
    nt.nodes["SPRITE_OUT_DEPTH"].file_slots[0].path = f"{base}_Z_{tag}"


class CharacterSpriteRenderer(bpy.types.Operator):
    """2D/2.5D Sprite Renderer"""      # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.sprite_renderer"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Render Sprites"   # Display name in the interface.

    def execute(self, context): 

        # Check if the camera path is valid
        camera_path = context.scene.sprite_renderer.camera_path
        output_folder = bpy.path.abspath(context.scene.sprite_renderer.output_folder)
        os.makedirs(output_folder, exist_ok=True)
        basename = context.scene.sprite_renderer.basename
        scene = bpy.context.scene
        include_animation = context.scene.sprite_renderer.include_animation
        frame_step = context.scene.sprite_renderer.frame_step
        # Get the frame range of the animation
        frame_start = scene.frame_start
        frame_end = scene.frame_end

        # Enable normal and depth passes
        view_layer = scene.view_layers[0]
        view_layer.use_pass_normal = True     # surface normals
        view_layer.use_pass_z = True          # linear depth

        # Set up compositor nodes for multi-pass rendering
        nt = ensure_output_nodes(scene, output_folder, basename)

        if camera_path == "":
            # Get the selected object (sprite root) and calculate its center
            if context.selected_objects:
                subject = context.selected_objects[0]
                pivot, character_height = bbox_center_and_size(subject)
                bb_size = subject.dimensions  # world-space size vec
                largest = max(bb_size.x, bb_size.y, bb_size.z)
                orig_rot = subject.rotation_euler.copy()
            else:
                self.report({'ERROR'}, "Select the object to render first.")
                return {'CANCELLED'}
            
            # Getting properties from the scene
            number_of_angles = context.scene.sprite_renderer.number_of_angles
            
            # Get roll properties
            roll_steps = context.scene.sprite_renderer.roll_steps
            roll_min_deg = context.scene.sprite_renderer.roll_min
            roll_max_deg = context.scene.sprite_renderer.roll_max

            scene.render.resolution_x = int(context.scene.sprite_renderer.resolution)
            scene.render.resolution_y = int(context.scene.sprite_renderer.resolution)
            scene.render.film_transparent = True

            perspective = context.scene.sprite_renderer.perspective
            camera_type = context.scene.sprite_renderer.camera_type

            # Check if the camera already exists in the scene
            camera_name = '2DSpriteCamera'
            if camera_name in bpy.data.objects:
                camera = bpy.data.objects[camera_name]
            else:
                # Add a new camera to the scene
                bpy.ops.object.camera_add(location=pivot)
                camera = bpy.context.object  # the newly added camera becomes the active object
                camera.name = camera_name  # set the camera name
            scene.camera = camera

            if camera_type == 'ORTHO':
                margin = context.scene.sprite_renderer.distance_factor  # reuse the knob
                camera.data.type = 'ORTHO'
                camera.data.ortho_scale = largest * margin  # uses largest dimension
            else:
                camera.data.type = 'PERSP'

            # Apply camera shift if specified
            camera.data.shift_y = context.scene.sprite_renderer.camera_shift_y

            if perspective == '2D':
                distance = 10 * context.scene.sprite_renderer.distance_factor
                z_distance = 0
            else:
                # Proper fit-to-height formula for perspective mode
                sensor_h = camera.data.sensor_height
                focal = camera.data.lens
                fov = 2 * math.atan((sensor_h * 0.5) / focal)  # radians
                base_distance = (character_height * 0.5) / math.tan(fov * 0.5)
                distance = base_distance * context.scene.sprite_renderer.distance_factor
                camera_angle_rad = context.scene.sprite_renderer.camera_angle * 3.14159 / 180  # converting to radians
                z_distance = distance * tan(camera_angle_rad)

            # Nested rendering loops: roll × yaw × frame
            for ri in range(roll_steps):
                # compute roll (pitch) in radians; -ve = downhill
                roll_deg = roll_min_deg + (roll_max_deg - roll_min_deg) * ri / (roll_steps - 1)
                roll_rad = roll_deg * 3.14159 / 180.0

                # tilt the model, *not* the camera, so shadows etc. follow the mesh
                subject.rotation_euler[0] = orig_rot[0] + roll_rad

                for yi in range(number_of_angles):
                    angle = yi * (2.0 * 3.14159 / number_of_angles)  # calculate angle

                    # Set the camera's position relative to the object's center
                    camera.location.x = pivot.x + distance * cos(angle)
                    camera.location.y = pivot.y + distance * sin(angle)
                    camera.location.z = pivot.z + z_distance

                    # Point the camera to the object's center
                    direction = pivot - camera.location
                    camera.rotation_mode = 'QUATERNION'
                    camera.rotation_quaternion = direction.to_track_quat('-Z', 'Y')  # camera looks towards the object center

                    # Check if there is animation
                    if include_animation and frame_start != frame_end:
                        # Loop through every frame of the animation
                        for frame in range(frame_start, frame_end + 1, frame_step):
                            scene.frame_set(frame)
                            # Set output path
                            col_path = os.path.join(
                                output_folder,
                                f"{basename}_C_{yi:02d}_{ri:02d}_F{frame:03}.png"
                            )
                            scene.render.filepath = col_path
                            update_output_node_paths(nt, basename, yi, ri, frame)
                            # Render the scene
                            bpy.ops.render.render(write_still=True)
                    else:
                        # Handle static scene (no animation)
                        col_path = os.path.join(
                            output_folder,
                            f"{basename}_C_{yi:02d}_{ri:02d}.png"
                        )
                        scene.render.filepath = col_path
                        update_output_node_paths(nt, basename, yi, ri, None)
                        # Render the scene
                        bpy.ops.render.render(write_still=True)

            # Restore original rotation
            subject.rotation_euler = orig_rot

            bpy.data.objects.remove(camera, do_unlink=True)
        else:
            scene.camera = bpy.data.objects[camera_path]
            if include_animation and frame_start != frame_end:
                # Loop through every frame of the animation
                for frame in range(frame_start, frame_end + 1, frame_step):
                    scene.frame_set(frame)
                    scene.render.filepath = os.path.join(output_folder, '{}_frame{:03}.png'.format(basename, frame))
                    bpy.ops.render.render(write_still = True)
            else:
                # Handle static scene (no animation)
                scene.render.filepath = os.path.join(output_folder, '{}.png'.format(basename))
                # Render the scene
                bpy.ops.render.render(write_still = True)

        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


# This is the Panel where you set the properties
class SpriteRendererPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Sprite Renderer"
    bl_idname = "OBJECT_PT_sprite_renderer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Sprite Renderer"

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        renderer = scene.sprite_renderer

        layout.prop(renderer, "camera_path")
        # draw the properties
        layout.prop(renderer, "output_folder")
        layout.prop(renderer, "basename")

        layout.prop(renderer, "include_animation")
        # Only enable frame_step if include_animation is True
        row = layout.row()
        row.enabled = renderer.include_animation
        row.prop(renderer, "frame_step")

        # Camera settings subsection
        camera_box = layout.box()
        # Disable the entire camera settings box if camera_path is not empty
        camera_box.enabled = (renderer.camera_path == "")

        # Adding a label for the subsection
        camera_box.label(text="Camera Settings")

        camera_box.prop(renderer, "number_of_angles")
        camera_box.prop(renderer, "distance_factor")
        
        row = camera_box.row(align=True)
        row.enabled = (renderer.perspective == '2.5D')
        row.prop(renderer, "roll_steps")
        row = camera_box.row(align=True)
        row.enabled = (renderer.perspective == '2.5D')
        row.prop(renderer, "roll_min")
        row.prop(renderer, "roll_max")

        camera_box.prop(renderer, "perspective")

        row = camera_box.row()
        row.enabled = (renderer.perspective == '2.5D')
        row.prop(renderer, "camera_angle")
        
        row = camera_box.row()
        row.enabled = (renderer.perspective == '2.5D')
        row.prop(renderer, "camera_shift_y")

        camera_box.prop(renderer, "camera_type")
        camera_box.prop(renderer, "resolution")

        # draw the operator
        layout.operator("object.sprite_renderer")


# This is the property group where you store your variables
class SpriteRendererProperties(bpy.types.PropertyGroup):

    camera_path: bpy.props.StringProperty(name="Camera", description="Path to an existing camera, if none is provided a new one will be created", default="")
    output_folder: bpy.props.StringProperty(name="Output Folder", default="//", subtype='DIR_PATH')
    basename: bpy.props.StringProperty(name="Basename", default="render")

    include_animation: bpy.props.BoolProperty(
        name="Include Animation",
        default=False,
        description="Whether to render all frames of the animation for each angle.",
    )
    frame_step: bpy.props.IntProperty(
        name="Frame Step",
        default=1,
        min=1,
        description="Render every n-th frame of the animation. For example, if set to 3, only every third frame will be rendered.",
    )

    number_of_angles: bpy.props.IntProperty(name="Number of Angles", default=8)
    distance_factor: bpy.props.FloatProperty(
        name="Distance Factor", 
        default=1.2, 
        min=0.1, 
        max=20.0,
        description="Camera distance multiplier - higher values move camera further away (1.2 = 20% margin)"
    )
    
    roll_steps: bpy.props.IntProperty(
        name="Roll Slices",
        default=5, min=2,
        description="How many tilt angles (top-to-bottom) to render"
    )
    roll_min: bpy.props.FloatProperty(
        name="Roll Min °",
        default=-15.0, min=-89.0, max=0.0,
        description="Lowest tilt (downhill)"
    )
    roll_max: bpy.props.FloatProperty(
        name="Roll Max °",
        default=15.0, min=0.0, max=89.0,
        description="Highest tilt (uphill)"
    )
    
    perspective: bpy.props.EnumProperty(
        name="Perspective",
        description="Select Perspective type",
        items=[
            ('2D', "2D", ""),
            ('2.5D', "2.5D", "")
        ],
        default='2.5D',
    )
    camera_angle: bpy.props.FloatProperty(name="Camera Angle", default=30.0, min=0.0, max=89.0)
    camera_shift_y: bpy.props.FloatProperty(
        name="Cam Shift Y", 
        default=0.0, 
        min=-2.0, 
        max=2.0,
        description="Vertical camera shift - positive moves view down"
    )
    camera_type: bpy.props.EnumProperty(
        name="Camera Type",
        description="Select Camera type",
        items=[
            ('ORTHO', "Orthographic", ""),
            ('PERSP', "Perspective", "")
        ],
        default='ORTHO',
    )
    resolution: bpy.props.EnumProperty(
        name="Resolution",
        description="Select the resolution",
        items=[
            ('32', "32x32", ""),
            ('64', "64x64", ""),
            ('128', "128x128", ""),
            ('256', "256x256", ""),
            ('512', "512x512", "")
        ],
        default='512',
    )


# Registration
def register():
    bpy.utils.register_class(CharacterSpriteRenderer)
    bpy.utils.register_class(SpriteRendererPanel)
    bpy.utils.register_class(SpriteRendererProperties)
    bpy.types.Scene.sprite_renderer = bpy.props.PointerProperty(type=SpriteRendererProperties)


def unregister():
    bpy.utils.unregister_class(CharacterSpriteRenderer)
    bpy.utils.unregister_class(SpriteRendererPanel)
    bpy.utils.unregister_class(SpriteRendererProperties)
    del bpy.types.Scene.sprite_renderer

if __name__ == "__main__":
    register()