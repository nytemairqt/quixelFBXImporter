#--------------------------------------------------------------
# Meta Dictionary
#--------------------------------------------------------------

bl_info = {
	"name" : "QuixelFBXImporter",
	"author" : "SceneFiller",
	"version" : (1, 0, 0),
	"blender" : (4, 2, 0),
	"location" : "View3d > Tool",
	"warning" : "",
	"wiki_url" : "",
	"category" : "3D View",
}

#--------------------------------------------------------------
# Import
#--------------------------------------------------------------

import os
import bpy
from mathutils import Vector

#--------------------------------------------------------------
# Functions
#--------------------------------------------------------------	

def _importMesh(filepath):
	# Imports FBX file and makes it the active object
	bpy.ops.import_scene.fbx(filepath=filepath)		
	mesh = bpy.context.selected_objects[0]		
	bpy.context.view_layer.objects.active = mesh
	mesh.select_set(True)
	return mesh

def _setupMaterial(mesh, folder_path):
	if mesh.data.materials:
			mesh.data.materials.clear()

	material = bpy.data.materials.new(name=mesh.name)
	material.use_nodes = True
	mesh.data.materials.append(material)
	bsdf = material.node_tree.nodes.get("Principled BSDF")
	material_output = material.node_tree.nodes.get("Material Output")
	bump_node = material.node_tree.nodes.new("ShaderNodeBump")
	bump_node.inputs['Strength'].default_value = 0.1
	bump_node.location = Vector((-300.0, 0.0))
	bump_node.hide = True
	material.node_tree.links.new(bump_node.outputs['Normal'], bsdf.inputs['Normal'])

	# Look for texture files
	texture_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]	

	if not texture_files:
		self.report({'WARNING'}, 'Unable to find texture files, skipping.')
		return{"FINISHED"}	

	# Drop unneeded files
	for tex in texture_files:
		if 'roughness' in tex.lower():
			texture_files.remove(tex)
		if 'ao' in tex.lower():
			texture_files.remove(tex)
		if 'fuzz' in tex.lower():
			texture_files.remove(tex)
		if 'cavity' in tex.lower():
			texture_files.remove(tex)

	for tex in texture_files:
		tex_file_path = os.path.join(folder_path, tex)
		img = bpy.data.images.load(tex_file_path)
		tex_node = material.node_tree.nodes.new('ShaderNodeTexImage')
		tex_node.image = img
		tex_node.hide = True 

		if 'basecolor' in tex.lower():
			material.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
			tex_node.location = Vector((-300.0, 300.0))
		if 'specular' in tex.lower():
			img.colorspace_settings.name = 'Non-Color' # might be node-based instead...
			material.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Specular IOR Level'])
			tex_node.location = Vector((-300.0, 100.0))
		if 'gloss' in tex.lower():
			img.colorspace_settings.name = 'Non-Color'
			invert = material.node_tree.nodes.new('ShaderNodeInvert')
			invert.hide = True 
			material.node_tree.links.new(tex_node.outputs['Color'], invert.inputs['Color'])
			material.node_tree.links.new(invert.outputs['Color'], bsdf.inputs['Roughness'])
			invert.location = Vector((-300.0, 250.0))
			tex_node.location = Vector((-600.0, 250.0))
		if 'displacement' in tex.lower():
			img.colorspace_settings.name = 'Non-Color'
			displacement = material.node_tree.nodes.new('ShaderNodeDisplacement')
			displacement.hide = True
			material.node_tree.links.new(tex_node.outputs['Color'], displacement.inputs['Height'])
			material.node_tree.links.new(displacement.outputs['Displacement'], material_output.inputs['Displacement'])
			displacement.location = Vector((0.0, -400.0))
			tex_node.location = Vector((-300.0, -400.0))
		if 'normal' in tex.lower():
			img.colorspace_settings.name = 'Non-Color'
			normal_map = material.node_tree.nodes.new('ShaderNodeNormalMap')
			normal_map.hide = True 
			material.node_tree.links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
			material.node_tree.links.new(normal_map.outputs['Normal'], bump_node.inputs['Normal'])
			normal_map.location = Vector((-300.0, -200.0))
			tex_node.location = Vector((-600.0, -200.0))
		if 'bump' in tex.lower():
			img.colorspace_settings.name = 'Non-Color'
			material.node_tree.links.new(tex_node.outputs['Color'], bump_node.inputs['Height'])
			tex_node.location = Vector((-600.0, 0.0))

#--------------------------------------------------------------
# Operators
#--------------------------------------------------------------	

class QUIXELFBXIMPORTER_OT_importFBX(bpy.types.Operator):
	bl_idname = 'quixelfbximporter.import_fbx'
	bl_label = 'Import FBX'
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = 'Import FBX'

	filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="")

	def execute(self, context):
		folder_path = os.path.dirname(self.filepath)

		if not folder_path:
			self.report({'WARNING'}, "No folder selected")
			return {'CANCELLED'}

		file_name = os.path.splitext(os.path.basename(folder_path))[0]
		mesh = _importMesh(self.filepath)
		mesh.name = file_name
		_setupMaterial(mesh, folder_path)

		return{'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		bpy.app.timers.register(self.clear_filename, first_interval=0.1)
		return {'RUNNING_MODAL'}

	def clear_filename(self):
	# Ensure filename field is cleared after the file browser is open
		try:
			bpy.data.screens['temp'].areas[0].spaces.active.params.filename = ""
			return None  # Stop the timer
		except Exception as e:
			# Retry clearing the filename field if the file browser isn't fully ready
			return 0.1  # Retry after 0.1 seconds

class QUIXELFBXIMPORTER_OT_batchImportFBX(bpy.types.Operator):
	bl_idname = 'quixelfbximporter.batch_import_fbx'
	bl_label = 'Batch Import FBX'
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = 'Batch Import FBX'

	filepath: bpy.props.StringProperty(subtype="DIR_PATH", default="")

	def execute(self, context):
		subfolders = [f.path for f in os.scandir(self.filepath) if f.is_dir()]
		for folder in subfolders:
			with os.scandir(folder) as entries:
				for entry in entries:
					if entry.is_file() and entry.name.endswith('.fbx'):
						file_name = os.path.splitext(os.path.basename(entry))[0]
						mesh = _importMesh(entry.path)
						mesh.name = file_name
						_setupMaterial(mesh, folder)
		return{'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		bpy.app.timers.register(self.clear_filename, first_interval=0.1)
		return {'RUNNING_MODAL'}

	def clear_filename(self):
	# Ensure filename field is cleared after the file browser is open
		try:
			bpy.data.screens['temp'].areas[0].spaces.active.params.filename = ""
			return None  # Stop the timer
		except Exception as e:
			# Retry clearing the filename field if the file browser isn't fully ready
			return 0.1  # Retry after 0.1 seconds		

class QUIXELFBXIMPORTER_OT_applyRotationAndScale(bpy.types.Operator):
	bl_idname = 'quixelfbximporter.apply_rotation_and_scale'
	bl_label = 'Apply Rotation & Scale'
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = 'Apply Rotation & Scale'

	def execute(self, context):
		bpy.ops.object.select_all(action='DESELECT')
		bpy.ops.object.select_all(action='SELECT')
		bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
		self.report({'WARNING'}, "Applied rotation & scale to all scene objects.")
		return{'FINISHED'}
	

#--------------------------------------------------------------
# Interface
#--------------------------------------------------------------

class QUIXELFBXIMPORTER_PT_panelMain(bpy.types.Panel):
	bl_label = 'QuixelFBXImporter'
	bl_idname = 'QUIXELFBXIMPORTER_PT_panelMain'
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'QUIXELFBXImporter'

	def draw(self, context):
		layout = self.layout
		view = context.space_data 
		scene = context.scene 
		
		# Generate
		row = layout.row()
		row.label(text='Import Quixel FBX: ')

		row = layout.row()
		button_import_fbx = row.operator(QUIXELFBXIMPORTER_OT_importFBX.bl_idname, text="Import FBX", icon="FILE_FOLDER")

		row = layout.row()
		button_batch_import_fbx = row.operator(QUIXELFBXIMPORTER_OT_batchImportFBX.bl_idname, text="Batch Import FBX", icon="FILE_FOLDER")

		row = layout.row()
		button_apply_rotation_and_scale = row.operator(QUIXELFBXIMPORTER_OT_applyRotationAndScale.bl_idname, text='Apply Rotation & Scale', icon='DUPLICATE')
		
#--------------------------------------------------------------
# Register 
#--------------------------------------------------------------

classes_interface = (QUIXELFBXIMPORTER_PT_panelMain,)
classes_functionality = (QUIXELFBXIMPORTER_OT_importFBX, QUIXELFBXIMPORTER_OT_batchImportFBX, QUIXELFBXIMPORTER_OT_applyRotationAndScale)

def register():

	# Register Classes
	for c in classes_interface:
		bpy.utils.register_class(c)
	for c in classes_functionality:
		bpy.utils.register_class(c)	
			
def unregister():

	# Unregister
	for c in reversed(classes_interface):
		bpy.utils.unregister_class(c)
	for c in reversed(classes_functionality):
		bpy.utils.unregister_class(c)

if __name__ == "__main__":
	register()