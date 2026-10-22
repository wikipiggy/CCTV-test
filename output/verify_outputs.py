"""Verify completed deliverables and write SHA-256 manifest. Run after rendering."""
import pathlib,struct,zlib,hashlib,json
root=pathlib.Path(__file__).resolve().parent
expected={**{'render_%02d.png'%i:(2000,2000) for i in range(1,5)},**{'progress_'+n+'.png':(1000,1000) for n in ['south','west','plan','perspective']},**{'sample_'+kind+'_%dmm.png'%d:(1200,1200) for kind in ['recess','macro'] for d in [20,30,40]}}
for name,dims in expected.items():
 data=(root/name).read_bytes(); assert data[:8]==b'\x89PNG\r\n\x1a\n',name
 assert struct.unpack('>II',data[16:24])==dims,(name,'dimensions')
 pos=8; ended=False
 while pos<len(data):
  size=struct.unpack('>I',data[pos:pos+4])[0]; typ=data[pos+4:pos+8]; chunk=data[pos+8:pos+8+size]; crc=struct.unpack('>I',data[pos+8+size:pos+12+size])[0]
  assert zlib.crc32(typ+chunk)&0xffffffff==crc,(name,'CRC')
  pos+=size+12
  if typ==b'IEND':ended=True;break
 assert ended and pos==len(data),(name,'incomplete PNG')
assert json.loads((root/'scene_validation.json').read_text())['status']=='passed'
final=json.loads((root/'render_manifest_final.json').read_text()); assert len(final)==4
assert {i['file'] for i in final}=={'render_%02d.png'%i for i in range(1,5)}
manifest=[]
for p in sorted(root.iterdir()):
 if p.is_file() and p.suffix in ['.py','.sh','.md','.png','.json','.blend'] and p.name!='delivery_manifest.json':
  data=p.read_bytes(); assert len(data)<100*1024*1024,(p.name,'GitHub file size')
  manifest.append({'file':p.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(root/'delivery_manifest.json').write_text(json.dumps({'status':'passed','verified_png_count':len(expected),'files':manifest},indent=2)+'\n')
print('DELIVERY_VERIFIED',len(expected),'complete PNGs,',len(manifest),'files hashed')
