"""Validate actual saved Blender scene. blender -b output/CCTV_Headquarters.blend --python-exit-code 1 -P output/validate_scene.py"""
import bpy,math,json,os
s=bpy.context.scene; out=os.path.dirname(os.path.abspath(__file__))
facades=[o for o in s.objects if o.get('glass_removed_in_grooves')]
assert len(facades)==30, len(facades)
assert len([o for o in s.objects if o.type=='CAMERA'])==13
assert all(o.get('recess_depth_m') in [.02,.03,.04] for o in facades)
for o in s.objects:
 if o.type=='MESH':assert all(math.isfinite(c) for v in o.data.vertices for c in v.co)
body=[o for o in facades if o.name.startswith(('Tower','L overhang'))]
zmax=max((o.matrix_world@v.co).z for o in body for v in o.data.vertices)
assert abs(zmax-234)<1e-4,zmax
measured={}
for depth in [20,30,40]:
 ob=bpy.data.objects['Sample %dmm front'%depth]
 extent=max(v.co.y for v in ob.data.vertices)-min(v.co.y for v in ob.data.vertices)
 assert abs(extent-depth/1000)<1e-6,(depth,extent)
 measured[str(depth)+'mm']=extent
images=[i for i in bpy.data.images if i.source=='FILE' and i.filepath and not i.packed_file]
assert not images, [(i.name,i.filepath) for i in images]
areas=json.load(open(os.path.join(out,'geometry_validation.json')))
for f in areas['surfaces']:
 assert abs(f['glass_area']+f['groove_area']-f['domain_area'])<1e-5
 assert f['overlap']<1e-8
report={'status':'passed','object_count':len(s.objects),'camera_count':13,'recessed_surfaces':len(facades),'body_height_m':zmax,'actual_sample_recess_depth_m':measured,'mesh_vertices':sum(len(o.data.vertices) for o in s.objects if o.type=='MESH'),'mesh_polygons':sum(len(o.data.polygons) for o in s.objects if o.type=='MESH'),'external_image_dependencies':0,'render_engine':s.render.engine,'denoising':s.cycles.use_denoising,'checks':['finite mesh coordinates','expected facade/sample count','body maximum 234m','20/30/40mm recess metadata and measured mesh depths','glass and groove area partition','zero external image dependencies']}
json.dump(report,open(os.path.join(out,'scene_validation.json'),'w'),indent=2)
print(json.dumps(report))
