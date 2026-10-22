"""Render saved scene without rebuilding. blender -b output/CCTV_Headquarters.blend -P output/render_views.py -- --mode preview"""
import bpy,os,sys,argparse
from mathutils import Vector
p=argparse.ArgumentParser(); p.add_argument('--mode',default='final',choices=['preview','sample','final']); a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
s=bpy.context.scene; out=os.path.dirname(os.path.abspath(__file__)); s.render.engine='CYCLES'; s.cycles.use_denoising=False; s.render.threads_mode='FIXED'; s.render.threads=5
s.cycles.samples=24 if a.mode=='preview' else 192
s.cycles.use_adaptive_sampling=True; s.cycles.adaptive_threshold=.015; s.cycles.adaptive_min_samples=8 if a.mode=='preview' else 24
if a.mode=='preview':views=[('Progress south','progress_south',900),('Progress west','progress_west',900),('Progress plan','progress_plan',900),('01 Southwest city','progress_perspective',1000)]
elif a.mode=='sample':views=[('Recess 20mm','sample_recess_20mm',1200),('Recess 30mm','sample_recess_30mm',1200),('Recess 40mm','sample_recess_40mm',1200)]+[('Macro %dmm'%d,'sample_macro_%dmm'%d,1000) for d in [20,30,40]]
else:views=[('01 Southwest city','render_01',2000),('02 Aerial closed loop','render_02',2000),('03 Cantilever upward','render_03',2000),('04 Southeast city','render_04',2000)]
for camera,name,size in views:
 s.camera=bpy.data.objects[camera]; s.render.resolution_x=size; s.render.resolution_y=size; s.render.resolution_percentage=100; s.render.filepath=os.path.join(out,name+'.png'); bpy.ops.render.render(write_still=True)
print('RENDER_BATCH_COMPLETE',a.mode)
