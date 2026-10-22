"""Headless Cycles rendering with isolated linear-HDR OIDN filtering.
blender -b output/CCTV_Headquarters.blend -P output/render_views.py -- --mode final
"""
import bpy,os,sys,argparse,tempfile,subprocess,shutil,json,time
sys.path.insert(0,os.environ.get('CCTV_GEOMETRY_PATH','/workspace/cctv-blender-python'))
import numpy as np
p=argparse.ArgumentParser(); p.add_argument('--mode',default='final',choices=['preview','sample','final','test']); p.add_argument('--only',choices=['render_01','render_02','render_03','render_04']); a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
s=bpy.context.scene; out=os.path.dirname(os.path.abspath(__file__)); s.render.engine='CYCLES'; s.cycles.use_denoising=False; s.render.threads_mode='FIXED'; s.render.threads=5
s.cycles.samples={'preview':24,'sample':32,'test':16,'final':96}[a.mode]
s.cycles.use_adaptive_sampling=True; s.cycles.adaptive_threshold=.025; s.cycles.adaptive_min_samples=12 if a.mode in ['preview','test'] else 24
if a.mode=='preview':views=[('Progress south','progress_south',1000),('Progress west','progress_west',1000),('Progress plan','progress_plan',1000),('01 Southwest city','progress_perspective',1000)]
elif a.mode=='sample':views=[('Recess %dmm'%d,'sample_recess_%dmm'%d,1200) for d in [20,30,40]]+[('Macro %dmm'%d,'sample_macro_%dmm'%d,1200) for d in [20,30,40]]
elif a.mode=='test':views=[('Macro 30mm','sample_pipeline_test',600)]
else:views=[('01 Southwest city','render_01',2000),('02 Aerial closed loop','render_02',2000),('03 Cantilever upward','render_03',2000),('04 Southeast city','render_04',2000)]
if a.only:views=[v for v in views if v[1]==a.only]
assert views,'No views selected'
record=[]
for camera,name,size in views:
 if a.mode in ['sample','test']:
  depth=camera.split()[-1]
  for ob in bpy.data.collections['Recess samples'].objects:ob.hide_render=not ob.name.startswith('Sample '+depth+' ')
 start=time.time(); s.camera=bpy.data.objects[camera]; s.render.resolution_x=size; s.render.resolution_y=size; s.render.resolution_percentage=100
 with tempfile.TemporaryDirectory(prefix='cctv-render-') as temp:
  s.render.image_settings.file_format='OPEN_EXR'; s.render.image_settings.color_depth='32'; s.render.filepath=os.path.join(temp,'linear.exr'); bpy.ops.render.render(write_still=True)
  im=bpy.data.images.load(s.render.filepath,check_existing=False); w,h=im.size; px=np.empty(w*h*4,dtype=np.float32); im.pixels.foreach_get(px); color=np.ascontiguousarray(px.reshape(h,w,4)[:,:,:3]); np.save(os.path.join(temp,'color.npy'),color)
  s.render.image_settings.file_format='PNG'; s.render.image_settings.color_depth='8'
  if a.mode=='test':im.save_render(os.path.join(out,'sample_pipeline_raw.png'),scene=s)
  subprocess.run([os.environ.get('CCTV_DENOISE_PYTHON',shutil.which('python')),os.path.join(out,'denoise_linear.py'),os.path.join(temp,'color.npy'),os.path.join(temp,'filtered.npy')],check=True)
  filtered=np.load(os.path.join(temp,'filtered.npy')); assert filtered.shape==(h,w,3)
  rgba=np.ones((h,w,4),dtype=np.float32); rgba[:,:,:3]=filtered
  result=bpy.data.images.new('Denoised linear HDR',width=w,height=h,alpha=True,float_buffer=True); result.pixels.foreach_set(rgba.ravel()); result.update(); result.save_render(os.path.join(out,name+'.png'),scene=s)
  bpy.data.images.remove(im); bpy.data.images.remove(result)
 record.append(dict(file=name+'.png',camera=camera,width=w,height=h,sample_limit=s.cycles.samples,adaptive_threshold=s.cycles.adaptive_threshold,filter='OIDN 1.4.3 HDR; isolated process',seconds=round(time.time()-start,2)))
 print('RENDER_VIEW_COMPLETE',name,flush=True)
manifest_path=os.path.join(out,'render_manifest_'+a.mode+'.json')
if a.only and os.path.exists(manifest_path):
 previous=json.load(open(manifest_path)); current={r['file'] for r in record}; record=sorted([r for r in previous if r['file'] not in current]+record,key=lambda r:r['file'])
json.dump(record,open(manifest_path,'w'),indent=2)
print('RENDER_BATCH_COMPLETE',a.mode,flush=True)
