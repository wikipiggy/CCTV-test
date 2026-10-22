"""Isolated OIDN 1.4.3 HDR filter; avoids Blender/system TBB ABI conflicts.
Input/output are linear float32 NumPy arrays. Called by render_views.py.
"""
import sys,os,ctypes
sys.path[:0]=[os.environ.get('CCTV_NUMPY_PATH','/workspace/cctv-denoise'),os.environ.get('CCTV_DENOISE_PATH','/workspace/cctv-denoise')]
import numpy as np
import oidn
color=np.ascontiguousarray(np.load(sys.argv[1]),dtype=np.float32)
h,w,_=color.shape; result=np.empty_like(color)
lib=oidn.__lib_oidn
setbool=lib.oidnSetFilter1b; setbool.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_bool]; setbool.restype=None
setint=lib.oidnSetDevice1i; setint.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int]; setint.restype=None
d=oidn.NewDevice(); setint(d,b'numThreads',4); oidn.CommitDevice(d)
assert oidn.GetDeviceError(d)==0
f=oidn.NewFilter(d,'RT'); oidn.SetSharedFilterImage(f,'color',color,oidn.FORMAT_FLOAT3,w,h); oidn.SetSharedFilterImage(f,'output',result,oidn.FORMAT_FLOAT3,w,h); setbool(f,b'hdr',True)
oidn.CommitFilter(f); oidn.ExecuteFilter(f); err=oidn.GetDeviceError(d)
assert err==0,('OIDN error',err)
assert np.isfinite(result).all()
np.save(sys.argv[2],result); oidn.ReleaseFilter(f); oidn.ReleaseDevice(d)
print('OIDN_HDR_COMPLETE',w,h)
