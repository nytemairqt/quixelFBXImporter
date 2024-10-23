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
from bpy_extras.io_utils import ImportHelper

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

		# Get the imported object
		imported_object = context.selected_objects[0]

		if imported_object.data.materials:
			imported_object.data.materials.clear()

		# Create a material
		material = bpy.data.materials.new(name="quixelMat")
		material.use_nodes = True
		imported_object.data.materials.append(material)

		# Look for texture files
		texture_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
		if texture_files:
			bsdf = material.node_tree.nodes.get("Principled BSDF")
			tex_dir = folder_path

			for tex_file in texture_files:
				tex_file_path = os.path.join(tex_dir, tex_file)
				img = bpy.data.images.load(tex_file_path)
				tex_node = material.node_tree.nodes.new('ShaderNodeTexImage')
				tex_node.image = img
				material.node_tree.links.new(bsdf.inputs['Base Color'], tex_node.outputs['Color'])
                
                # Map roughness, normal, etc. (simple example)
				if 'roughness' in tex_file.lower():
					material.node_tree.links.new(bsdf.inputs['Roughness'], tex_node.outputs['Color'])
				if 'normal' in tex_file.lower():
					normal_map = material.node_tree.nodes.new('ShaderNodeNormalMap')
					material.node_tree.links.new(normal_map.inputs['Color'], tex_node.outputs['Color'])
					material.node_tree.links.new(bsdf.inputs['Normal'], normal_map.outputs['Normal'])
				if 'displacement' in tex_file.lower():
					displacement_node = material.node_tree.nodes.new('ShaderNodeDisplacement')
					material.node_tree.links.new(displacement_node.inputs['Height'], tex_node.outputs['Color'])
					material.node_tree.links.new(material.node_tree.nodes.get('Material Output').inputs['Displacement'], displacement_node.outputs['Displacement'])


		# Call NodeWrangler operator
		#print(f'FilePath = {texture_files[0]}, directory={folder_path}')

		#bpy.ops.node.nw_add_textures_for_principled(filepath=texture_files[0], directory=folder_path, files=[{"name":"cavefloor1_Ambient_Occlusion.png", "name":"cavefloor1_Ambient_Occlusion.png"}, {"name":"cavefloor1_Base_Color.png", "name":"cavefloor1_Base_Color.png"}, {"name":"cavefloor1_Height.png", "name":"cavefloor1_Height.png"}, {"name":"cavefloor1_Metallic.png", "name":"cavefloor1_Metallic.png"}, {"name":"cavefloor1_Normal.png", "name":"cavefloor1_Normal.png"}, {"name":"cavefloor1_Roughness.png", "name":"cavefloor1_Roughness.png"}], relative_path=True)
		#bpy.ops.node.nw_add_textures_for_principled(filepath="D:\\Pictures\\textures\\FreePBR\\cave_floor\\cavefloor1_Ambient_Occlusion.png", directory="D:\\Pictures\\textures\\FreePBR\\cave_floor\\", files=[{"name":"cavefloor1_Ambient_Occlusion.png", "name":"cavefloor1_Ambient_Occlusion.png"}, {"name":"cavefloor1_Base_Color.png", "name":"cavefloor1_Base_Color.png"}, {"name":"cavefloor1_Height.png", "name":"cavefloor1_Height.png"}, {"name":"cavefloor1_Metallic.png", "name":"cavefloor1_Metallic.png"}, {"name":"cavefloor1_Normal.png", "name":"cavefloor1_Normal.png"}, {"name":"cavefloor1_Roughness.png", "name":"cavefloor1_Roughness.png"}], relative_path=True)

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
		
#--------------------------------------------------------------
# Register 
#--------------------------------------------------------------

classes_interface = (QUIXELFBXIMPORTER_PT_panelMain,)
classes_functionality = (QUIXELFBXIMPORTER_OT_importFBX,)

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