import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translate import pool_strings

def chunks(d):
    t,hs,size=struct.unpack('<HHI', d[:8])
    p=hs
    while p+8<=size:
        t2,hs2,sz=struct.unpack('<HHI', d[p:p+8])
        if sz==0: break
        yield p,t2,hs2,sz
        p+=sz

class Axml:
    def __init__(self, path):
        self.d=open(path,'rb').read()
        self.pool=None; self.resmap=[]
        self.nodes=[]
        d=self.d; stack=[]
        for p,t,hs,sz in chunks(d):
            if t==1:
                self._pooloff=p
                self._poolcache,_=pool_strings(d,p)
            elif t==0x180:
                n=struct.unpack('<I', d[p+8:p+12])[0]
                avail=(sz-hs)//4
                self.resmap=[struct.unpack('<I', d[p+hs+4*i:p+hs+4*i+4])[0] for i in range(min(n,avail))]
            elif t==0x102:
                ext=p+hs
                ns,name,astart,asize,acount = struct.unpack('<IIHHH', d[ext:ext+14])
                attrs=[]
                for i in range(acount):
                    a=ext+astart+i*asize
                    ans,an,araw=struct.unpack('<III', d[a:a+12])
                    vsize,res0,dt=struct.unpack('<HBB', d[a+12:a+16])
                    data=struct.unpack('<i', d[a+16:a+20])[0]
                    if dt==3: val=self.s(data)
                    elif dt==1: val='@0x%08x'%data
                    elif dt in (0x10,0x11): val=data
                    elif dt==0x12: val=bool(data)
                    elif dt==0x1c or dt==0x1d: val=data
                    else: val=data
                    attrs.append(dict(name=self.s(an), val=val, raw=self.s(araw) if araw!=0xffffffff else None,
                                      resid=(self.resmap[an] if an < len(self.resmap) else None), dtype=dt, data=data))
                self.nodes.append(dict(kind='start', name=self.s(name), attrs=attrs, depth=len(stack), off=p))
                stack.append(self.s(name))
            elif t==0x103:
                ext=p+hs
                ns,name=struct.unpack('<II', d[ext:ext+8])
                self.nodes.append(dict(kind='end', name=self.s(name), depth=len(stack)-1, off=p))
                if stack: stack.pop()
            elif t==0x104:
                ext=p+hs
                txt,=struct.unpack('<I', d[ext:ext+4])
                self.nodes.append(dict(kind='text', text=self.s(txt), depth=len(stack)))
    def s(self,i):
        if i==0xffffffff or getattr(self,'_poolcache',None) is None and not hasattr(self,'_poolcache'):
            return None
        strings=self._poolcache
        if i>=len(strings): return None
        return strings[i]
    def dump(self):
        for n in self.nodes:
            if n['kind']=='start':
                print('  '*n['depth']+'<'+n['name']+' '+' '.join(
                    '%s=%r%s'%(a['name'],a['val'],(' [res 0x%08x]'%a['resid'] if False else '')) for a in n['attrs'])+'>')
            elif n['kind']=='end':
                print('  '*n['depth']+'</'+n['name']+'>')
            else:
                print('  '*n['depth']+'TEXT: '+repr(n['text']))

if __name__=='__main__':
    a=Axml(sys.argv[1]); a.dump()
