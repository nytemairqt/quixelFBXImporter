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
# Operators
#--------------------------------------------------------------	

class QUIXELFBXIMPORTER_OT_importFBX(bpy.types.Operator):
	bl_idname = 'quixelfbximporter.import_fbx'
	bl_label = 'Import FBX'
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = 'Import FBX'

	filepath: bpy.props.StringProperty(subtype="FILE_PATH")

	def execute(self, context):
		folder_path = os.path.dirname(self.filepath)

		if not folder_path:
			self.report({'WARNING'}, "No folder selected")
			return {'CANCELLED'}

		# Import FBX
		bpy.ops.import_scene.fbx(filepath=self.filepath)		
		mesh = bpy.context.selected_objects[-1]		
		bpy.context.view_layer.objects.active = mesh
		mesh.select_set(True)

		# Get the imported object
		imported_object = context.selected_objects[0]

		if imported_object.data.materials:
			imported_object.data.materials.clear()

		# Create a material
		material = bpy.data.materials.new(name=mesh.name)
		material.use_nodes = True
		imported_object.data.materials.append(material)
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

		return{'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

class QUIXELFBXIMPORTER_OT_batchImportFBX(bpy.types.Operator):
	bl_idname = 'quixelfbximporter.batch_import_fbx'
	bl_label = 'Batch Import FBX'
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = 'Batch Import FBX'

	filepath: bpy.props.StringProperty(subtype="DIR_PATH")

	def execute(self, context):

		subfolders = [f.path for f in os.scandir(self.filepath) if f.is_dir()]

		print(subfolders)

		return{'FINISHED'}

		folder_path = os.path.dirname(self.filepath)

		if not folder_path:
			self.report({'WARNING'}, "No folder selected")
			return {'CANCELLED'}

		# Import FBX
		bpy.ops.import_scene.fbx(filepath=self.filepath)

		# Get the imported object
		imported_object = context.selected_objects[0]

		if imported_object.data.materials:
			imported_object.data.materials.clear()

		# Create a material
		material = bpy.data.materials.new(name="quixelMat")
		material.use_nodes = True
		imported_object.data.materials.append(material)
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

		return{'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}		
	

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
		
#--------------------------------------------------------------
# Register 
#--------------------------------------------------------------

classes_interface = (QUIXELFBXIMPORTER_PT_panelMain,)
classes_functionality = (QUIXELFBXIMPORTER_OT_importFBX, QUIXELFBXIMPORTER_OT_batchImportFBX)

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