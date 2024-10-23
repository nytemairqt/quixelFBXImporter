'''
    Copyright 2024 SceneFiller

    This file is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This file is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with This file. If not, see <http://www.gnu.org/licenses/>.
'''

#--------------------------------------------------------------
# Meta Dictionary
#--------------------------------------------------------------

bl_info = {
	"name" : "Grainy",
	"author" : "SceneFiller",
	"version" : (1, 0, 1),
	"blender" : (4, 0, 2),
	"location" : "View3d > Tool",
	"warning" : "",
	"wiki_url" : "",
	"category" : "3D View",
}

#--------------------------------------------------------------
# Import
#--------------------------------------------------------------

import os
import platform
import bpy
import numpy as np

#--------------------------------------------------------------
# Miscellaneous Functions
#--------------------------------------------------------------

def _convert_pixel_buffer_to_matrix(buffer, width, height, channels):
	# Converts a 1-D pixel buffer into an xy grid with n Colour channels
	buffer = buffer.reshape(height, width, channels)
	return buffer

def _convert_matrix_to_pixel_buffer(buffer):
	# Converts back to 1-D pixel buffer
	buffer = buffer.flatten()
	return buffer		

def _filter_gaussian(k=3, sig=1.0):
	# Apply a simple gaussian blur filter
	ax = np.linspace(-(k-1) / 2.0, (k-1) /2.0, k)
	gaussian = np.exp(-0.5 * np.square(ax) / np.square(sig))
	kernel = np.outer(gaussian, gaussian)
	return kernel / np.sum(kernel)

def GRAINCREATOR_FN_generateGrain(name, clip_min=.4, clip_max=.7, k=3, sigma=1.0, oversampling=False, monochromatic=True):	
	w = bpy.data.scenes[0].render.resolution_x if not oversampling else (bpy.data.scenes[0].render.resolution_x * 2)
	h = bpy.data.scenes[0].render.resolution_y if not oversampling else (bpy.data.scenes[0].render.resolution_y * 2)
	buffer_size = (4 * w * h)

	# Create Blank Image
	grain = bpy.data.images.new(name=name, width=w, height=h)
	
	# Convert Pixel Buffer to Matrix
	pixels_to_paint = np.ones(buffer_size, dtype=np.float32)	
	pixels_to_paint = _convert_pixel_buffer_to_matrix(pixels_to_paint, w, h, 4)	

	# Generate Grain
	r = np.random.rand(*pixels_to_paint.shape)

	pixels_to_paint[:, :, 0:3] = r[:, :, 0:3]	
			
	# Clip Values
	pixels_to_paint = np.clip(pixels_to_paint, clip_min, clip_max)

	# Apply Gaussian Blur
	kernel = _filter_gaussian(k=k, sig=sigma)
	blur_result = np.convolve(pixels_to_paint.flatten(), kernel.flatten())
	pixels = blur_result[:buffer_size].reshape(pixels_to_paint.shape)
	
	# Monochromatic
	if monochromatic:
		pixels[:, :, 0:3] = pixels[:, :, 0:1]	

	# Conver to float 32
	pixels_f32 = pixels.astype(np.float32)

	# Fix Alpha to 1.0
	pixels_f32[:, :, 3] = 1.0
	
	# Propagate Grain to Empty Image
	output = _convert_matrix_to_pixel_buffer(pixels_f32)
	grain.pixels.foreach_set(output)	
	grain.update()	

	# Show Result in Image Editor 
	for area in bpy.context.screen.areas:
		if area.type == 'IMAGE_EDITOR':
			area.spaces.active.image = grain

	return grain

def GRAINCREATOR_FN_exportFrame(self, image, idx, folder):
	name = idx
	if idx < 10:
		name = f'000{idx}'
	if idx >= 10 and idx < 100:
		name = f'00{idx}'
	if idx >= 100 and idx < 1000:
		name = f'0{idx}'
	try:
		image.filepath_raw = f'{folder}{name}.png'
		image.save()
	except:
		self.report({'WARNING'}, 'Invalid folder or file.')
		return{'CANCELLED'}


def GRAINCREATOR_FN_compositeGrain(self, folder):
	if folder is None:
		self.report({'WARNING'}, 'Grain folder not set.')
		return{'CANCELLED'}

	bpy.context.scene.use_nodes = True 
	tree = bpy.context.scene.node_tree 
	nodes = tree.nodes

	frames = list()

	try:
		for file_name in os.listdir(folder):
			if file_name.endswith('.png'):
				frames.append(file_name)
	except:
		self.report({'WARNING'}, 'Invalid folder or file.')
		return{'CANCELLED'}

	num_frames = len(frames)

	if num_frames < 1:
		self.report({'WARNING'}, 'No viable frames found.')
		return{'CANCELLED'}

	path = f'{folder}0001.png'
	grain_image = bpy.data.images.load(path)
	grain_image.source = 'SEQUENCE'

	composite_tree = bpy.data.node_groups.new('GrainComposite', 'CompositorNodeTree')
	tree = composite_tree
	nodes = composite_tree.nodes
	links = tree.links

	# Create Nodes
	comp_input = nodes.new('NodeGroupInput')	
	comp_input.location = (-500, 0)	
	
	comp_output = nodes.new('NodeGroupOutput')
	comp_output.location = (500, 0)
	
	grain = nodes.new(type='CompositorNodeImage')
	grain.label = 'Grain'
	grain.location = (-700, -150)
	grain.image = grain_image
	grain.frame_duration = num_frames
	grain.use_cyclic = True

	grain_scale = nodes.new(type='CompositorNodeScale')
	grain_scale.location = (-500, -200)

	mix_grain = nodes.new(type='CompositorNodeMixRGB')
	mix_grain.name = 'Overlay'
	mix_grain.label = 'Grain Blend'
	mix_grain.blend_type = 'OVERLAY'
	mix_grain.location = (-150, 0)

	mix_superimpose = nodes.new(type='CompositorNodeMixRGB')
	mix_superimpose.name = 'SuperImposeGrain'
	mix_superimpose.label = 'Super-Impose'
	mix_superimpose.blend_type = 'ADD'
	mix_superimpose.location = (-500, -400)

	exposure = nodes.new(type='CompositorNodeExposure')
	exposure.location = (150, 0)
	exp_math = nodes.new(type='CompositorNodeMath')
	exp_math.label = 'Exposure Mul'
	exp_math.location = (-150, -300)
	exp_math.operation = 'MULTIPLY'

	# Create Group Inputs & Outputs
	if bpy.app.version > (3, 99, 99):
		tree.interface.new_socket(name='Image', in_out='INPUT', socket_type='NodeSocketColor')
		tree.interface.new_socket(name='Mix', in_out='INPUT', socket_type='NodeSocketFloat')
		tree.interface.new_socket(name='Grain Scale', in_out='INPUT', socket_type='NodeSocketFloat')
		tree.interface.new_socket(name='Super Impose', in_out='INPUT', socket_type='NodeSocketFloat')
		tree.interface.new_socket(name='Exposure Compensation', in_out='INPUT', socket_type='NodeSocketFloat')
		tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
	else:
		tree.inputs.new('NodeSocketImage','Image')
		tree.inputs.new('NodeSocketFloat', 'Mix')
		tree.inputs.new('NodeSocketFloat', 'Grain Scale')
		tree.inputs.new('NodeSocketFloat', 'Super Impose')
		tree.inputs.new('NodeSocketFloat', 'Exposure Compensation')
		tree.outputs.new('NodeSocketImage', 'Image')

	# Connect Everything

	links.new(comp_input.outputs[0], mix_grain.inputs[1]) # Input Image -> Mix 
	links.new(comp_input.outputs[1], mix_grain.inputs[0]) # Input Mix -> Mix Factor
	links.new(comp_input.outputs[1], exp_math.inputs[0]) # Input Mix -> Exposure Compensation
	links.new(comp_input.outputs[4], exp_math.inputs[1]) # Input Exp Comp -> Exposure Compensation
	links.new(comp_input.outputs[2], grain_scale.inputs[1]) # Input Scale -> Scale X
	links.new(comp_input.outputs[2], grain_scale.inputs[2]) # Input Scale -> Scale Y
	links.new(grain.outputs[0], grain_scale.inputs[0]) # Grain -> Scale Image
	links.new(exp_math.outputs[0], exposure.inputs[1]) # Exposure Compensation -> Exposure Node
	links.new(grain_scale.outputs[0], mix_superimpose.inputs[1]) # Scale -> SuperImpose
	links.new(comp_input.outputs[0], mix_superimpose.inputs[2]) # Input Image -> SuperImpose
	links.new(comp_input.outputs[3], mix_superimpose.inputs[0]) # Input SI -> SuperImpose
	links.new(mix_superimpose.outputs[0], mix_grain.inputs[2]) # SuperImpose -> Mix
	links.new(mix_grain.outputs[0], exposure.inputs[0]) # Mix -> Exposure Node
	links.new(exposure.outputs[0], comp_output.inputs[0]) # Exposure Node -> Output

	# Build Group Node & Set Defaults
	group = bpy.context.scene.node_tree.nodes.new(type='CompositorNodeGroup')
	group.name = 'Grain Composite'
	group.node_tree = bpy.data.node_groups['GrainComposite']

	group.inputs[1].default_value = 0.5 
	group.inputs[2].default_value = 1.0 
	group.inputs[3].default_value = 0.0 
	group.inputs[4].default_value = 1.0
	return 

def GRAINCREATOR_FN_compositeHalation(self):
	bpy.context.scene.use_nodes = True 
	tree = bpy.context.scene.node_tree 
	nodes = tree.nodes

	composite_tree = bpy.data.node_groups.new('HalationComposite', 'CompositorNodeTree')
	tree = composite_tree
	nodes = composite_tree.nodes
	links = tree.links

	# Create Nodes
	comp_input = nodes.new('NodeGroupInput')	
	comp_input.location = (-500, 0)	
	
	split_rgb = nodes.new(type='CompositorNodeSeparateColor')
	split_rgb.location = (-500, -200)

	blur = nodes.new(type='CompositorNodeBlur')
	blur.location = (-200, -200)

	map_range = nodes.new(type='CompositorNodeMapRange')
	map_range.location = (-400, -400)

	combine_rgb = nodes.new(type='CompositorNodeCombineColor')
	combine_rgb.location = (500, -200)

	comp_output = nodes.new('NodeGroupOutput')
	comp_output.location = (500, 0)

	color_balance = nodes.new(type="CompositorNodeColorBalance")
	color_balance.location = (700, -200)

	# Create Group Inputs & Outputs
	if bpy.app.version > (3, 99, 99):
		tree.interface.new_socket(name='Image', in_out='INPUT', socket_type='NodeSocketColor')
		tree.interface.new_socket(name='Strength', in_out='INPUT', socket_type='NodeSocketFloat')
		tree.interface.new_socket(name='Warmth', in_out='INPUT', socket_type='NodeSocketFloat')
		tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
	else:
		tree.inputs.new('NodeSocketImage','Image')
		tree.inputs.new('NodeSocketFloat', 'Strength')
		tree.inputs.new('NodeSocketFloat', 'Warmth')
		tree.outputs.new('NodeSocketImage', 'Image')

	# Connect Everything
	links.new(comp_input.outputs[0], split_rgb.inputs[0]) # Input Image -> Separate Color 
	links.new(split_rgb.outputs[0], blur.inputs[0]) # Red Channel -> Blur
	links.new(split_rgb.outputs[0], map_range.inputs[0]) # Red Channel -> Map Range
	links.new(map_range.outputs[0], blur.inputs[1]) # Map Range -> Blur Size
	links.new(comp_input.outputs[1], map_range.inputs[3]) # Strength -> Map Range To Min
	links.new(blur.outputs[0], combine_rgb.inputs[0]) # Blur -> Red Channel
	links.new(split_rgb.outputs[1], combine_rgb.inputs[1]) # Green Channel -> Green Channel
	links.new(split_rgb.outputs[2], combine_rgb.inputs[2]) # Blue Channel -> Blue Channel
	links.new(split_rgb.outputs[3], combine_rgb.inputs[3]) # Alpha Channel -> Alpha Channel
	links.new(comp_input.outputs[2], color_balance.inputs[0]) # Warmth -> Color Balance
	links.new(combine_rgb.outputs[0], color_balance.inputs[1]) # Combine -> Color Balance
	links.new(color_balance.outputs[0], comp_output.inputs[0]) # Color Balance -> Output

	# Build Group Node & Set Defaults
	group = bpy.context.scene.node_tree.nodes.new(type='CompositorNodeGroup')
	group.name = 'Halation'
	group.node_tree = bpy.data.node_groups['HalationComposite']

	color_balance.gamma = (1.05042, 0.982923, 0.964609)
	blur.use_variable_size = True
	blur.size_x = 10
	blur.size_y = 10
	group.inputs[1].default_value = 0.25 # Strength
	group.inputs[2].default_value = 0.25 # Warmth
	return

def GRAINCREATOR_FN_compositeSCurve(self):
	bpy.context.scene.use_nodes = True 
	tree = bpy.context.scene.node_tree 
	nodes = tree.nodes

	# Create Nodes
	s_curve = nodes.new(type='CompositorNodeCurveRGB')
	s_curve.label = 'Film S Curve'

	rgb = s_curve.mapping.curves[3]

	# Clip Endpoints
	rgb.points[0].location = (0.0, 0.03)
	rgb.points[1].location = (1.0, 0.97)
	
	# Add Shoulders
	rgb.points.new(0.05, 0.1)
	rgb.points.new(0.95, 0.9)

	# Add S Curve
	rgb.points.new(0.388, 0.358)
	rgb.points.new(0.636, 0.741)

	# Update Final Curve
	s_curve.mapping.update()
	return


#--------------------------------------------------------------
# Operators
#--------------------------------------------------------------	

class GRAINCREATOR_OT_generateGrain(bpy.types.Operator):	
	bl_idname = "graincreator.generate_grain"
	bl_label = "Generates custom film grain image or sequence."
	bl_options = {"REGISTER", "UNDO"}
	bl_description = "Generates custom film grain image or sequence."

	clip_min: bpy.props.FloatProperty(name='clip_min', default=.5)
	clip_max: bpy.props.FloatProperty(name='clip_max', default=.6)
	kernel_size: bpy.props.IntProperty(name='kernel_size', default=3)
	sigma: bpy.props.FloatProperty(name='sigma', default=1.0)
	oversampling: bpy.props.BoolProperty(name='oversampling', default=False)
	monochromatic: bpy.props.BoolProperty(name='monochromatic', default=False)

	def execute(self, context):
		# Assert valid Clipping
		if self.clip_max < self.clip_min:
			self.report({"WARNING"}, "Invalid clip range.")
			return{'CANCELLED'}

		# Generate single frame for previewing.
		grain = GRAINCREATOR_FN_generateGrain(
			name=f"grainSingleFrame", 
			clip_min=self.clip_min, 
			clip_max=self.clip_max, 
			k=self.kernel_size, 
			sigma=self.sigma,
			oversampling=self.oversampling,
			monochromatic=self.monochromatic)			
		return {'FINISHED'}

class GRAINCREATOR_OT_exportGrainFrames(bpy.types.Operator):	
	bl_idname = "graincreator.export_grain_frames"
	bl_label = "Exports grain sequence to output folder."
	bl_options = {"REGISTER", "UNDO"}
	bl_description = "Exports grain sequence to output folder."

	clip_min: bpy.props.FloatProperty(name='clip_min', default=.5)
	clip_max: bpy.props.FloatProperty(name='clip_max', default=.6)
	kernel_size: bpy.props.IntProperty(name='kernel_size', default=3)
	sigma: bpy.props.FloatProperty(name='sigma', default=1.0)
	oversampling: bpy.props.BoolProperty(name='oversampling', default=False)
	monochromatic: bpy.props.BoolProperty(name='monochromatic', default=False)
	frames: bpy.props.IntProperty(name='frames', default=1)

	def execute(self, context):
		# Assert valid Clipping
		if self.clip_max < self.clip_min:
			self.report({"WARNING"}, "Invalid clip range.")
			return{'CANCELLED'}		

		# Export grain frames.		
		if platform.system() != "Linux":
			bpy.ops.wm.console_toggle()
		print('Writing Frames...')
		for i in range(self.frames):
			print(f'{i}/{self.frames}')
			grain = GRAINCREATOR_FN_generateGrain(
				name=f"{i+1}",
				clip_min=self.clip_min, 
				clip_max=self.clip_max, 
				k=self.kernel_size, 
				sigma=self.sigma,
				oversampling=self.oversampling,
				monochromatic=self.monochromatic)	
			GRAINCREATOR_FN_exportFrame(self, grain, i+1, folder=bpy.path.abspath(bpy.context.scene.GRAINCREATOR_VAR_output_dir))
		print('Finishing up...')
		if platform.system() != "Linux":
			bpy.ops.wm.console_toggle()
		return {'FINISHED'}		

class GRAINCREATOR_OT_compositeGrain(bpy.types.Operator):
	bl_idname = 'graincreator.composite_grain'
	bl_label = 'Composite Grain'
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = 'Composite Grain'

	def execute(self, context):
		GRAINCREATOR_FN_compositeGrain(self=self, folder=bpy.path.abspath(bpy.context.scene.GRAINCREATOR_VAR_output_dir))
		return{'FINISHED'}

class GRAINCREATOR_OT_compositeHalation(bpy.types.Operator):
	bl_idname = 'graincreator.composite_halation'
	bl_label = 'Composite Halation'
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = 'Composite Halation'

	def execute(self, context):
		GRAINCREATOR_FN_compositeHalation(self=self)		
		return{'FINISHED'}

class GRAINCREATOR_OT_compositeSCurve(bpy.types.Operator):
	bl_idname = 'graincreator.composite_s_curve'
	bl_label = 'Composite S Curve'
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = 'Composite S Curve'

	def execute(self, context):
		GRAINCREATOR_FN_compositeSCurve(self=self)		
		return{'FINISHED'}
	

#--------------------------------------------------------------
# Interface
#--------------------------------------------------------------

class GRAINCREATOR_PT_panelMain(bpy.types.Panel):
	bl_label = "Grainy"
	bl_idname = "GRAINCREATOR_PT_panelMain"
	bl_space_type = 'NODE_EDITOR'
	bl_region_type = 'UI'
	bl_category = 'Grainy'

	@classmethod 
	def poll(cls, context):
		snode = context.space_data
		return snode.tree_type == 'CompositorNodeTree'

	def draw(self, context):
		layout = self.layout		
		view = context.space_data
		scene = context.scene

		# Generate
		row = layout.row()
		row.label(text='Grain Designer: ')

		# Grain Settings
		row = layout.row()
		row.prop(context.scene, 'GRAINCREATOR_VAR_clip_min', text='Clip Min')
		row.prop(context.scene, 'GRAINCREATOR_VAR_clip_max', text='Clip Max')
		row = layout.row()
		row.prop(context.scene, 'GRAINCREATOR_VAR_kernel', text='Kernel')
		row.prop(context.scene, 'GRAINCREATOR_VAR_sigma', text='Sigma')
		row = layout.row()
		row.prop(context.scene, 'GRAINCREATOR_VAR_oversampling', text='Oversampling')
		row.prop(context.scene, 'GRAINCREATOR_VAR_monochromatic', text='Monochromatic')
		
		# Create Grain
		row = layout.row()
		button_create_grain = row.operator(GRAINCREATOR_OT_generateGrain.bl_idname, text="Create Test Frame", icon="FILE_IMAGE")

		# Output Directory
		row = layout.row()
		row.label(text='Grain Folder: ')
		row = layout.row()
		row.prop(scene, 'GRAINCREATOR_VAR_output_dir')

		# Frame Count
		row = layout.row()
		row.prop(scene, 'GRAINCREATOR_VAR_frames', text='Frames')

		# Save Grain 
		row = layout.row()
		button_export_grain = row.operator(GRAINCREATOR_OT_exportGrainFrames.bl_idname, text='Export Frames', icon_value=727)	

		# Composite Grain
		row = layout.row()
		button_composite_grain = row.operator(GRAINCREATOR_OT_compositeGrain.bl_idname, text='Composite Grain', icon="FILE_IMAGE")

		# Extras
		row = layout.row()
		row.label(text='Extras: ')

		row = layout.row()
		button_composite_halation = row.operator(GRAINCREATOR_OT_compositeHalation.bl_idname, text='Add Halation Node', icon='OUTLINER_OB_LIGHT')

		row = layout.row()
		button_composite_s_curve = row.operator(GRAINCREATOR_OT_compositeSCurve.bl_idname, text='Add Film S Curve', icon='FCURVE')


		# Assign Variables
		button_create_grain.clip_min = context.scene.GRAINCREATOR_VAR_clip_min
		button_create_grain.clip_max = context.scene.GRAINCREATOR_VAR_clip_max
		button_create_grain.kernel_size = context.scene.GRAINCREATOR_VAR_kernel
		button_create_grain.sigma = context.scene.GRAINCREATOR_VAR_sigma		
		button_create_grain.oversampling = context.scene.GRAINCREATOR_VAR_oversampling
		button_create_grain.monochromatic = context.scene.GRAINCREATOR_VAR_monochromatic

		button_export_grain.clip_min = context.scene.GRAINCREATOR_VAR_clip_min
		button_export_grain.clip_max = context.scene.GRAINCREATOR_VAR_clip_max
		button_export_grain.kernel_size = context.scene.GRAINCREATOR_VAR_kernel
		button_export_grain.sigma = context.scene.GRAINCREATOR_VAR_sigma		
		button_export_grain.oversampling = context.scene.GRAINCREATOR_VAR_oversampling
		button_export_grain.monochromatic = context.scene.GRAINCREATOR_VAR_monochromatic
		button_export_grain.frames = context.scene.GRAINCREATOR_VAR_frames


#--------------------------------------------------------------
# Register 
#--------------------------------------------------------------

classes_interface = (GRAINCREATOR_PT_panelMain,)
classes_functionality = (GRAINCREATOR_OT_generateGrain, GRAINCREATOR_OT_exportGrainFrames, GRAINCREATOR_OT_compositeGrain, GRAINCREATOR_OT_compositeHalation, GRAINCREATOR_OT_compositeSCurve)

bpy.types.Scene.GRAINCREATOR_VAR_clip_min = bpy.props.FloatProperty(name='GRAINCREATOR_VAR_clip_min', default=.5, soft_min=0.0, soft_max=1.0, description='Squash Black Values in Generated Grain.')
bpy.types.Scene.GRAINCREATOR_VAR_clip_max = bpy.props.FloatProperty(name='GRAINCREATOR_VAR_clip_max', default=.6, soft_min=0.0, soft_max=1.0, description='Squash White Values in Generated Grain.')
bpy.types.Scene.GRAINCREATOR_VAR_kernel = bpy.props.IntProperty(name='GRAINCREATOR_VAR_kernel', default=3, soft_min=1, soft_max=8, description='Set Kernel Size for Gaussian Blur.')
bpy.types.Scene.GRAINCREATOR_VAR_sigma = bpy.props.FloatProperty(name='GRAINCREATOR_VAR_sigma', default=1.0, soft_min=0.01, soft_max=5.0, description='Set Sigma for Gaussian Blur.')
bpy.types.Scene.GRAINCREATOR_VAR_oversampling = bpy.props.BoolProperty(name='GRAINCREATOR_VAR_oversampling', default=False)
bpy.types.Scene.GRAINCREATOR_VAR_monochromatic = bpy.props.BoolProperty(name='GRAINCREATOR_VAR_monochromatic', default=True)
bpy.types.Scene.GRAINCREATOR_VAR_frames = bpy.props.IntProperty(name='GRAINCREATOR_VAR_frames', default=1, soft_min=1, description='Number of frames to export.')
bpy.types.Scene.GRAINCREATOR_VAR_output_dir = bpy.props.StringProperty(name='', default='', subtype='DIR_PATH')

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

	del bpy.types.Scene.GRAINCREATOR_VAR_clip_min
	del bpy.types.Scene.GRAINCREATOR_VAR_clip_max
	del bpy.types.Scene.GRAINCREATOR_VAR_kernel
	del bpy.types.Scene.GRAINCREATOR_VAR_sigma	
	del bpy.types.Scene.GRAINCREATOR_VAR_oversampling 
	del bpy.types.Scene.GRAINCREATOR_VAR_monochromatic	
	del bpy.types.Scene.GRAINCREATOR_VAR_frames
	del bpy.types.Scene.GRAINCREATOR_VAR_output_dir

if __name__ == "__main__":
	register()