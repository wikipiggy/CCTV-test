"""Headless CCTV exterior reconstruction; dimensions metres, inferred from supplied images.
Blender 4.3.2 / Python 3.13; Shapely 2.1.2. No interior architecture.
"""
import bpy, math, random, sys, os, json, argparse
from mathutils import Vector
sys.path.insert(0,os.environ.get('CCTV_GEOMETRY_PATH','/workspace/cctv-blender-python'))
from shapely.geometry import Polygon,LineString,box,Point
from shapely.ops import unary_union,substring
from shapely import constrained_delaunay_triangles
def triangulate(p):return list(constrained_delaunay_triangles(p).geoms)
parser=argparse.ArgumentParser(); parser.add_argument('--stage',default='all'); parser.add_argument('--samples',type=int,default=192); parser.add_argument('--resolution',type=int,default=1600)
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=os.path.dirname(os.path.abspath(__file__)); random.seed(17)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
s=bpy.context.scene; s.unit_settings.system='METRIC'; s.render.engine='CYCLES'; s.cycles.samples=a.samples; s.cycles.use_denoising=False; s.cycles.use_adaptive_sampling=True; s.cycles.adaptive_threshold=.015; s.cycles.adaptive_min_samples=24; s.render.threads_mode='FIXED'; s.render.threads=5
s.render.image_settings.file_format='PNG'; s.view_settings.view_transform='AgX'
groups={}
def group(o,n):
 if n not in groups:
  c=bpy.data.collections.new(n); s.collection.children.link(c); groups[n]=c
 for c in list(o.users_collection):c.objects.unlink(o)
 groups[n].objects.link(o); return o
def material(n,c,m=0,r=.4):
 mat=bpy.data.materials.new(n); mat.diffuse_color=(*c,1); mat.use_nodes=True; p=mat.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*c,1); p.inputs['Metallic'].default_value=m; p.inputs['Roughness'].default_value=r; return mat
glass=[material('Silver blue glass %02d'%i,(.13+i*.006,.22+i*.006,.28+i*.006),.48,.16+i*.005) for i in range(9)]
for m in glass:
 nt=m.node_tree; bs=nt.nodes.get('Principled BSDF'); bs.inputs['Coat Weight'].default_value=.35
 geo=nt.nodes.new('ShaderNodeNewGeometry'); scale=nt.nodes.new('ShaderNodeVectorMath'); scale.operation='MULTIPLY'; scale.inputs[1].default_value=(1/1.45,1/1.45,1/3.85)
 floors=nt.nodes.new('ShaderNodeVectorMath'); floors.operation='FLOOR'; noise=nt.nodes.new('ShaderNodeTexWhiteNoise'); noise.noise_dimensions='3D'; ramp=nt.nodes.new('ShaderNodeValToRGB')
 ramp.color_ramp.elements[0].color=(.11,.19,.245,1); ramp.color_ramp.elements[1].color=(.19,.29,.35,1)
 nt.links.new(geo.outputs['Position'],scale.inputs[0]); nt.links.new(scale.outputs['Vector'],floors.inputs[0]); nt.links.new(floors.outputs['Vector'],noise.inputs['Vector']); nt.links.new(noise.outputs['Value'],ramp.inputs[0]); nt.links.new(ramp.outputs[0],bs.inputs['Base Color'])
sampleglass=material('Controlled sample glass',(.16,.26,.32),.48,.18)
slot=material('Recess graphite',(.025,.032,.039),.7,.3); frame=material('Fine aluminium divisions',(.32,.37,.39),.75,.3)
roofmat=material('Zinc roof',(.27,.3,.32),.65,.4); stone=material('Limestone paving',(.48,.48,.43),0,.85); road=material('Asphalt',(.065,.07,.075),0,.9)
lawn=material('Lawn',(.15,.25,.065),0,.9); foliage=material('Foliage',(.065,.16,.04),0,.85); bark=material('Bark',(.12,.08,.04),0,.9); white=material('Lane paint',(.78,.77,.7),0,.8); concrete=material('Context concrete',(.44,.45,.43),0,.85)
for m,sc in [(road,110),(stone,35)]:
 nt=m.node_tree; n=nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=sc; b=nt.nodes.new('ShaderNodeBump'); b.inputs['Strength'].default_value=.15; b.inputs['Distance'].default_value=.025; nt.links.new(n.outputs['Fac'],b.inputs['Height']); nt.links.new(b.outputs['Normal'],nt.nodes.get('Principled BSDF').inputs['Normal'])
def mesh(n,v,f,m,inds=None,g='Architecture'):
 me=bpy.data.meshes.new(n); me.from_pydata(v,[],f); me.update(); ob=bpy.data.objects.new(n,me); s.collection.objects.link(ob); group(ob,g)
 for mat in m:me.materials.append(mat)
 if inds:
  for p,i in zip(me.polygons,inds):p.material_index=i
 return ob
def cube(n,p,d,m,g='Site',bevel=0):
 v=[(x*d[0]/2,y*d[1]/2,z*d[2]/2) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 ob=mesh(n,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],[m],g=g); ob.location=p
 if bevel:b=ob.modifiers.new('Edge radius','BEVEL'); b.width=bevel; b.segments=2; ob.modifiers.new('Normals','WEIGHTED_NORMAL')
 return ob
def beam(n,p,q,w,m,g='Site'):
 d=Vector(q)-Vector(p); ob=cube(n,(Vector(p)+Vector(q))/2,(w,w,d.length),m,g); ob.rotation_euler=d.to_track_quat('Z','Y').to_euler(); return ob
def polygons(x):
 if x.is_empty:return []
 if x.geom_type=='Polygon':return [x]
 return [p for p in x.geoms if p.geom_type=='Polygon']
report={'units':'metres','body_max_height':234,'soffit_height':161,'survey_accuracy':False,'surfaces':[]}
def surface(n,pts,depth=.03,offset=0,g='Facade',station=0,spacing=16):
 print('BUILD_SURFACE',n,flush=True)
 p0,p1,p2,p3=map(Vector,pts); w=(p1-p0).length; h=((p3-p0).length+(p2-p1).length)/2; normal=(p1-p0).cross(p3-p0).normalized()
 def xyz(x,y,d=0):
  u=x/w; v=y/h; return tuple(p0*(1-u)*(1-v)+p1*u*(1-v)+p2*u*v+p3*(1-u)*v-normal*d)
 domain=box(0,0,w,h); lines=[]; main=[]; extra=[]
 for slope in [-1.28,1.28]:
  for k in range(-30,40):
   c=k*spacing+offset+slope*station
   line=LineString([(-2*h,-2*h*slope+c),(w+2*h,(w+2*h)*slope+c)])
   main.append(line); lines.append(line.buffer(.17,cap_style=2))
   if k%3==0:
    extra.append(LineString([(-2*h,-2*h*slope+c+5.3),(w+2*h,(w+2*h)*slope+c+5.3)]))
 base=unary_union(main); zones=unary_union([box(0,0,w,min(45,h)),box(w*.2,h*.55,w*.8,h*.90)])
 endpoint_errors=0; density_segments=0
 for line in extra:
  visible=line.intersection(domain)
  if visible.is_empty or visible.geom_type!='LineString':continue
  ends=[line.project(Point(p)) for p in [visible.coords[0],visible.coords[-1]]]
  crossings=line.intersection(base).intersection(domain)
  points=[crossings] if crossings.geom_type=='Point' else list(crossings.geoms) if hasattr(crossings,'geoms') else []
  nodes=sorted(ends+[line.project(p) for p in points if p.geom_type=='Point'])
  requested=visible.intersection(zones)
  pieces=[requested] if requested.geom_type=='LineString' else list(requested.geoms) if hasattr(requested,'geoms') else []
  for piece in pieces:
   if piece.is_empty or piece.geom_type!='LineString':continue
   lo,hi=sorted([line.project(Point(piece.coords[0])),line.project(Point(piece.coords[-1]))])
   d0=max([d for d in nodes if d<=lo+1e-7],default=ends[0]); d1=min([d for d in nodes if d>=hi-1e-7],default=ends[-1])
   if d1-d0<1e-6:continue
   segment=substring(line,d0,d1)
   start_on_edge=Point(segment.coords[0]).distance(domain.boundary)<1e-5; end_on_edge=Point(segment.coords[-1]).distance(domain.boundary)<1e-5
   paint=substring(line,d0-.5 if start_on_edge else d0,d1+.5 if end_on_edge else d1)
   lines.append(paint.buffer(.15,cap_style=2)); density_segments+=1
   for xy in [segment.coords[0],segment.coords[-1]]:
    point=Point(xy)
    if min(point.distance(base),point.distance(domain.boundary))>1e-5:endpoint_errors+=1
 assert endpoint_errors==0,(n,endpoint_errors)
 grooves=unary_union(lines).intersection(domain); glazing=domain.difference(grooves)
 verts=[]; faces=[]; inds=[]
 def add(poly,d,mi):
  for t in triangulate(poly):
   if not poly.covers(t.representative_point()):continue
   st=len(verts); verts.extend(xyz(x,y,d) for x,y in list(t.exterior.coords)[:3]); faces.append((st,st+1,st+2)); inds.append(mi)
 for p in polygons(glazing):add(p,0,random.randrange(9))
 for p in polygons(grooves):
  add(p,depth,9)
  for ring in [p.exterior,*p.interiors]:
   co=list(ring.coords)
   for (x,y),(xx,yy) in zip(co,co[1:]):
    st=len(verts); verts.extend([xyz(x,y),xyz(xx,yy),xyz(xx,yy,depth),xyz(x,y,depth)]); faces.append((st,st+1,st+2,st+3)); inds.append(9)
 ob=mesh(n,verts,faces,([sampleglass]*9 if g=='Recess samples' else glass)+[slot],inds,g); ob['recess_depth_m']=depth; ob['glass_removed_in_grooves']=True
 # Small bevel only; angle test excludes coplanar triangles.
 be=ob.modifiers.new('3mm groove edge bevel','BEVEL'); be.width=.003; be.segments=1; be.limit_method='ANGLE'; be.angle_limit=.6
 # Fine regular frame strips stop at the recessed structural bands.
 strips=[box(i*1.45-.013,0,i*1.45+.013,h) for i in range(1,math.ceil(w/1.45))]
 strips += [box(0,j*3.85-.018,w,j*3.85+.018) for j in range(1,math.ceil(h/3.85))]
 v=[]; f=[]
 for p in [piece for strip in strips for piece in polygons(strip.intersection(glazing))]:
  for t in triangulate(p):
   if p.covers(t.representative_point()):
    st=len(v); v.extend(xyz(x,y,-.004) for x,y in list(t.exterior.coords)[:3]); f.append((st,st+1,st+2))
 mesh(n+' fine mullions',v,f,[frame],g=g)
 report['surfaces'].append(dict(name=n,width=w,height=h,depth=depth,glass_area=glazing.area,groove_area=grooves.area,domain_area=domain.area,overlap=glazing.intersection(grooves).area,density_segments=density_segments,unconnected_density_endpoints=endpoint_errors))
def ring(cx,cy,wx,wy,z):return [(cx-wx/2,cy-wy/2,z),(cx+wx/2,cy-wy/2,z),(cx+wx/2,cy+wy/2,z),(cx-wx/2,cy+wy/2,z)]
for n,b,t,d in [('Tower 1',(-44,80),(-33,66),(48,60)),('Tower 2',(80,-44),(66,-33),(60,48))]:
 low=ring(*b,*d,0); high=ring(*t,*d,161)
 for i in range(4):j=(i+1)%4; surface(n+' face '+str(i),[low[i],low[j],high[j],high[i]],station=[0,d[0],sum(d),2*d[0]+d[1]][i],spacing=15.36)
bottom=[(-57,-57),(96,-57),(96,-9),(-9,-9),(-9,96),(-57,96)]
top=[(-52,-52),(90,-52),(90,-4),(-4,-4),(-4,90),(-52,90)]
def roofz(x,y):return 234-(x+52)*20.1/142
for i in range(6):
 j=(i+1)%6; p,q,r,t=bottom[i],bottom[j],top[j],top[i]
 surface('L overhang face '+str(i),[(*p,161),(*q,161),(*r,roofz(*r)),(*t,roofz(*t))],offset=i*3)
v=[]; f=[]; roofpoly=Polygon(top)
for t in triangulate(roofpoly):
 if roofpoly.covers(t.representative_point()):
  st=len(v); v.extend((x,y,roofz(x,y)) for x,y in list(t.exterior.coords)[:3]); f.append((st,st+1,st+2))
mesh('Continuous sloping L roof',v,f,[roofmat])
surface('Recessed west soffit',[(-57,36,161),(-9,36,161),(-9,-57,161),(-57,-57,161)],g='Soffit')
surface('Recessed south soffit',[(-9,-9,161),(36,-9,161),(36,-57,161),(-9,-57,161)],g='Soffit')
for x,y in [(-45,-43),(-26,-43),(-45,-20),(-26,-20)]:
 bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=2.1,depth=.05,location=(x,y,160.965)); ob=bpy.context.object; ob.name='Circular soffit inset'; ob.data.materials.append(slot); group(ob,'Soffit')
for n,cx,cy,wx,wy,h in [('North podium',33,93,162,34,42),('East podium',98,23,32,168,36)]:
 low=ring(cx,cy,wx,wy,0); high=ring(cx,cy,wx,wy,h)
 for i in range(4):j=(i+1)%4; surface(n+str(i),[low[i],low[j],high[j],high[i]])
 cube(n+' roof',(cx,cy,h+.1),(wx,wy,.2),roofmat,'Architecture')
for x in [-28,-12,4,20,36,52]:
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,radius=2.4,location=(x,93,43.7)); ob=bpy.context.object; ob.name='Roof dish'; ob.scale=(1,1,.25); ob.rotation_euler[0]=.3; ob.data.materials.append(white); group(ob,'Roof detail')
for x in [-44,-28,-12]:cube('Roof plant enclosure',(x,39,roofz(x,39)+1.2),(9,12,2.4),roofmat,'Roof detail')
cube('Flat urban ground',(0,0,-1.1),(2000,2000,2),concrete); cube('Site plinth',(0,0,-.1),(255,260,1),stone)
for x,y,wx,wy in [(-158,0,46,900),(0,-160,900,35),(0,164,900,23),(155,0,22,900)]:
 # Road surface is unioned below, preventing coplanar intersection overlap.
 if wy>wx:
  for yy in range(-400,401,12):
   for xx in ([-10,0,10] if wx>30 else [0]):cube('Lane dash',(x+xx,yy,.052),(.14,5,.012),white,'Road detail')
 else:
  for xx in range(-400,401,12):
   for yy in ([-8,0,8] if wy>30 else [0]):cube('Lane dash',(xx,y+yy,.052),(5,.14,.012),white,'Road detail')
road_union=unary_union([box(x-w/2,y-h/2,x+w/2,y+h/2) for x,y,w,h in [(-158,0,46,900),(0,-160,900,35),(0,164,900,23),(155,0,22,900)]])
rv=[]; rf=[]
for t in triangulate(road_union):
 st=len(rv); rv.extend((x,y,.04) for x,y in list(t.exterior.coords)[:3]); rf.append((st,st+1,st+2))
mesh('Unified city roads',rv,rf,[road],g='Site')
for cx,cy in [(-158,-160),(-158,164),(155,-160),(155,164)]:
 for dx in range(-16,17,3):cube('Crosswalk',(cx+dx,cy+22,.055),(1.3,6,.014),white,'Road detail')
cube('West arterial viaduct',(-181,0,5),(17,850,.9),road)
for y in range(-390,400,40):cube('Viaduct pier',(-181,y,2),(2,3,5),concrete)
for x in [-189.2,-172.8]:cube('Viaduct parapet',(x,0,5.7),(.35,850,.6),concrete)
for x,y,wx,wy in [(-88,-73,36,60),(27,-104,112,20),(-93,47,22,115),(48,120,116,12),(120,-8,10,170)]:cube('Lawn',(x,y,.46),(wx,wy,.12),lawn)
# Union coplanar landscape beds and walks before triangulation to prevent overlap artifacts.
beds=unary_union([Polygon(points) for points in [
 [(-110,-112),(-8,-112),(-70,-78)], [(-60,-76),(-5,-108),(35,-78)],
 [(-10,-74),(34,-108),(67,-78)], [(-112,-64),(-76,-86),(-77,14)],
 [(-112,-30),(-80,10),(-112,47)]]])
walks=unary_union([LineString([p,q]).buffer(1.6,cap_style=2) for p,q in [
 ((-113,-116),(60,-73)),((-110,-70),(-20,-115)),((-115,-30),(-75,25))]])
for name,shape,height,mat in [('Angular landscape beds',beds.difference(walks),.54,lawn),('Diagonal plaza walks',walks,.56,stone)]:
 v=[]; f=[]
 for poly in polygons(shape):
  for tri in triangulate(poly):
   st=len(v); v.extend((x,y,height) for x,y in list(tri.exterior.coords)[:3]); f.append((st,st+1,st+2))
 mesh(name,v,f,[mat],g='Site')
shared_tree=None
for i in range(115):
 if i<65:
  t=-118+(i//4)*15; x,y=[(-121,t),(120,t),(t,-122),(t,122)][i%4]
 else:x,y=random.uniform(-112,112),random.choice([-108,106])+random.uniform(-6,6)
 h=random.uniform(5,9); beam('Tree trunk',(x,y,.5),(x,y,h*.65),.3,bark,'Vegetation')
 if shared_tree is None:
  bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1); ob=bpy.context.object; shared_tree=ob.data; shared_tree.materials.append(foliage); group(ob,'Vegetation')
  for vert in shared_tree.vertices:vert.co*=random.uniform(.86,1.12)
  for face in shared_tree.polygons:face.use_smooth=True
 else:ob=bpy.data.objects.new('Canopy',shared_tree); groups['Vegetation'].objects.link(ob)
 ob.location=(x,y,h); ob.scale=(h*.42,h*.38,h*.5)
car_mats=[material('Vehicle '+str(i),c,.5,.27) for i,c in enumerate([(.12,.16,.2),(.6,.62,.61),(.035,.05,.065),(.56,.13,.07)])]
for i in range(48):
 x,y=(-158+random.choice([-14,-5,5,14]),random.uniform(-320,300)) if i<28 else (random.uniform(-310,300),-160+random.choice([-10,8]))
 body=cube('Vehicle',(x,y,.88),(1.9,4.5,1.1),random.choice(car_mats),'Street furniture',.18); cab=cube('Vehicle glazing',(x,y+.2,1.65),(1.65,2.4,.7),glass[0],'Street furniture',.15)
 if i>=28:body.rotation_euler.z=math.pi/2; cab.rotation_euler.z=math.pi/2
for y in range(-240,260,35):
 for x in [-132,139]:
  beam('Light pole',(x,y,0),(x,y,11),.16,frame,'Street furniture'); beam('Light arm',(x,y,11),(x+3,y,11),.16,frame,'Street furniture'); cube('Lamp',(x+3,y,10.9),(1.2,.6,.15),slot,'Street furniture')
cube('TVCC context base',(-24,250,13),(110,75,26),roofmat,'Context'); cube('TVCC context tower',(-35,257,77),(39,43,128),concrete,'Context',1); cube('TVCC dark inset',(-35,234.9,83),(30,.3,112),glass[0],'Context')
for x,y,w,d,h in [(-290,220,42,44,95),(270,260,50,50,130),(270,-250,45,60,75),(-280,-250,55,45,66),(70,370,70,45,98),(340,70,65,65,140)]:
 cube('City context',(x,y,h/2),(w,d,h),concrete,'Context',.4)
 for z in range(5,h,5):cube('Context windows',(x,y-d/2-.1,z),(w-.8,.2,2.8),glass[3],'Context')
for i,d in enumerate([.02,.03,.04]):
 x=1100+i*14; surface('Sample %dmm front'%round(d*1000),[(x,0,0),(x+10,0,0),(x+10,0,12),(x,0,12)],d,8,'Recess samples'); surface('Sample %dmm return'%round(d*1000),[(x+10,0,0),(x+10,8,0),(x+10,8,12),(x+10,0,12)],d,8,'Recess samples',station=10)
world=bpy.data.worlds.new('Beijing daylight'); s.world=world; world.use_nodes=True; nt=world.node_tree; nt.nodes.clear(); sky=nt.nodes.new('ShaderNodeTexSky'); sky.sky_type='NISHITA'; sky.sun_elevation=math.radians(34); sky.sun_rotation=math.radians(220); sky.air_density=.85; bg=nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value=.055; out=nt.nodes.new('ShaderNodeOutputWorld'); nt.links.new(sky.outputs['Color'],bg.inputs['Color']); nt.links.new(bg.outputs[0],out.inputs[0])
bpy.ops.object.light_add(type='SUN',location=(0,0,500)); sun=bpy.context.object; sun.name='Sun'; sun.rotation_euler=(.5,-.55,-.7); sun.data.energy=2.5; sun.data.angle=.035; group(sun,'Lighting')
def camera(n,p,t,lens=45,ortho=None):
 bpy.ops.object.camera_add(location=p); ob=bpy.context.object; ob.name=n; ob.rotation_euler=(Vector(t)-ob.location).to_track_quat('-Z','Y').to_euler(); ob.data.lens=lens; ob.data.clip_end=5000
 if ortho:ob.data.type='ORTHO'; ob.data.ortho_scale=ortho
 group(ob,'Cameras'); return ob
heroes=[camera('01 Southwest city',(-330,-430,90),(10,10,117),52),camera('02 Aerial closed loop',(-340,-400,400),(10,20,100),48),camera('03 Cantilever upward',(-123,-148,12),(-8,-4,168),23),camera('04 Southeast city',(380,-400,160),(0,0,111))]
progress=[camera('Progress south',(0,-650,118),(0,0,118),ortho=285),camera('Progress west',(-650,0,118),(0,0,118),ortho=285),camera('Progress plan',(0,0,700),(0,0,0),ortho=330)]
samples=[camera('Recess %dmm'%d,(1115+i*14,-15,9),(1106+i*14,0,6),55) for i,d in enumerate([20,30,40])]

for i,d in enumerate([20,30,40]):
 x=1100+i*14; camera('Macro %dmm'%d,(x+2.7,-1.7,11.1),(x+2.07,0,10.65),55)
s.camera=heroes[0]; s.render.resolution_x=a.resolution; s.render.resolution_y=a.resolution; s.render.resolution_percentage=100
with open(os.path.join(OUT,'geometry_validation.json'),'w') as f:json.dump(report,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'CCTV_Headquarters.blend'),compress=True)
def render(c,n,size):
 s.camera=c; s.render.resolution_x=size; s.render.resolution_y=size; s.render.filepath=os.path.join(OUT,n+'.png'); bpy.ops.render.render(write_still=True)
if a.stage in ['all','sample']:
 for i,c in enumerate(samples):render(c,'sample_recess_'+str([20,30,40][i])+'mm',1000)
if a.stage in ['all','render']:
 for i,c in enumerate(progress):render(c,'progress_'+['south','west','plan'][i],1000)
 for i,c in enumerate(heroes):render(c,'render_'+str(i+1).zfill(2),a.resolution)
print('CCTV_BUILD_COMPLETE',len(bpy.data.objects),'objects')
