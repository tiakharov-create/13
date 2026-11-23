import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translate import pool_strings

def load(path):
    d=open(path,'rb').read()
    total=struct.unpack('<I', d[4:8])[0]
    hs=struct.unpack('<H',d[2:4])[0]
    pk=None; p=hs
    while p<total:
        t,ch_hs,sz=struct.unpack('<HHI', d[p:p+8])
        if sz==0: break
        if t==0x200: pk=p
        p+=sz
    pid,=struct.unpack('<I', d[pk+8:pk+12])
    name=d[pk+12:pk+268].decode('utf-16-le').split('\x00')[0]
    pkgsize=struct.unpack('<I', d[pk+4:pk+8])[0]
    # type/key string pools are the first two string pool chunks inside the package
    pools=[]
    q=pk+288
    while q < pk+pkgsize and len(pools)<2:
        t,ch_hs,sz=struct.unpack('<HHI', d[q:q+8])
        if sz==0: break
        if t==1: pools.append(q)
        q+=sz
    types,_=pool_strings(d,pools[0])
    keys,_=pool_strings(d,pools[1])
    return d,dict(pk=pk,pid=pid,name=name,pool_offs=pools,types=types,keys=keys,total=total,hs=hs,pkgsize=pkgsize)

DEFAULT_CFG = b'\x40\x00\x00\x00' + b'\x00'*(0x40-4)

def entry_index(d,pk, type_id, entry_id, pkgsize=None):
    if pkgsize is None:
        pkgsize=struct.unpack('<I', d[pk+4:pk+8])[0]
    p=pk+288
    while p < pk+pkgsize:
        t,ch_hs,sz=struct.unpack('<HHI', d[p:p+8])
        if sz==0: break
        if t==0x201 and d[p+8]==type_id:
            cfg=d[p+20:p+ch_hs]
            if cfg == b'\x40\x00\x00\x00' + b'\x00'*(len(cfg)-4):
                cnt=struct.unpack('<I', d[p+12:p+16])[0]
                start=struct.unpack('<I', d[p+16:p+20])[0]
                if entry_id < cnt:
                    eo=struct.unpack('<I', d[p+ch_hs+4*entry_id:p+ch_hs+4*entry_id+4])[0]
                    if eo!=0xffffffff:
                        return p, p+start+eo, ch_hs
        p+=sz
    return None,None,None

def find_key_entry(d,pk,type_id,key_idx,pkgsize=None):
    """Find the default-config entry whose key string index == key_idx."""
    if pkgsize is None:
        pkgsize=struct.unpack('<I', d[pk+4:pk+8])[0]
    p=pk+288
    while p < pk+pkgsize:
        t,ch_hs,sz=struct.unpack('<HHI', d[p:p+8])
        if sz==0: break
        if t==0x201 and d[p+8]==type_id:
            cfg=d[p+20:p+ch_hs]
            if cfg == b'\x40\x00\x00\x00' + b'\x00'*(len(cfg)-4):
                cnt=struct.unpack('<I', d[p+12:p+16])[0]
                start=struct.unpack('<I', d[p+16:p+20])[0]
                for i in range(cnt):
                    eo=struct.unpack('<I', d[p+ch_hs+4*i:p+ch_hs+4*i+4])[0]
                    if eo==0xffffffff: continue
                    ep=p+start+eo
                    ki=struct.unpack('<I', d[ep+4:ep+8])[0]
                    if ki==key_idx: return p, ep, ch_hs, i
        p+=sz
    return None,None,None,None

def value_at(d, entry_off):
    esize,eflags=struct.unpack('<HH', d[entry_off:entry_off+4])
    keyidx,=struct.unpack('<I', d[entry_off+4:entry_off+8])
    vsize,res0,dt=struct.unpack('<HBB', d[entry_off+esize:entry_off+esize+4])
    vdata,=struct.unpack('<I', d[entry_off+esize+4:entry_off+esize+8])
    return keyidx,esize,eflags,dt,vdata
