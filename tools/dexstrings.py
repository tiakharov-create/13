import struct, sys

class Dex:
    def __init__(self, path):
        self.d=open(path,'rb').read()
        d=self.d

        # layout is R8
        map_off,=struct.unpack('<I', d[52:56])
        n,=struct.unpack('<I', d[map_off:map_off+4])
        p=map_off+4; items={}
        for _ in range(n):
            typ,=struct.unpack('<H', d[p:p+2])
            size,off=struct.unpack('<II', d[p+4:p+12])
            items[typ]=(size,off)
            p+=12
        (string_count,string_off)=items[0x0001]
        string_data_off=items[0x2002][1]
        self.string_ids_size=string_count
        self.string_ids_off=string_off
        self.soffs=[string_data_off+struct.unpack('<I', d[string_off+4*i:string_off+4*i+4])[0] for i in range(string_count)]
        for i,o in enumerate(self.soffs):
            if o > len(d): self.soffs[i]=o-string_data_off
        self.map_items=items
        self.class_defs_size,self.class_defs_off=items[0x0006]
        self._strcache={}
    def uleb(self,p):
        d=self.d; r=0;s=0
        while True:
            x=d[p];p+=1; r|=(x&0x7f)<<s
            if not x&0x80: return r,p
            s+=7
    def s(self,i):
        if i in self._strcache: return self._strcache[i]
        p=self.soffs[i]; _,p=self.uleb(p); e=self.d.index(b'\x00',p)
        v=self.d[p:e].decode('utf-8','replace')
        self._strcache[i]=v
        return v
    def types(self):
        size,off=self.map_items[0x0002]
        return [self.s(struct.unpack('<I', self.d[off+4*i:off+4*i+4])[0]) for i in range(size)]
    def method(self,i):
        size,off=self.map_items[0x0005]
        o=off+8*i
        c,p,n=struct.unpack('<HHI', self.d[o:o+8])
        return c, self.types()[c], self.s(n)
    def skip_value(self,p):
        """p -> after encoded_value (header byte + value_arg+1 bytes)."""
        b=self.d[p]; p+=1
        arg=(b>>5); t=b&0x1f
        if t==0x1c:  # array: uleb count then values
            n,p=self.uleb(p)
            for _ in range(n): p=self.skip_value(p)
        elif t==0x1d:  # annotation
            _,p=self.uleb(p)
            n,p=self.uleb(p)
            for _ in range(n):
                _,p=self.uleb(p)
                p=self.skip_value(p)
        elif t==0x1e:
            pass
        elif t==0x1f:
            p+=arg   # boolean
        else:
            p+=arg+1
        return p
    def class_def_for_type(self, type_idx):
        d=self.d
        for i in range(self.class_defs_size):
            c=struct.unpack('<I', d[self.class_defs_off+i*32:self.class_defs_off+i*32+4])[0]
            if c==type_idx: return i
        return None

    def class_code(self,cidx):
        self._cdix=cidx
        d=self.d
        o=self.class_defs_off+self._cdix*32
        _c,acc,sup,ifoff,src,ann,clsdata,static=struct.unpack('<8I', d[o:o+32])
        p=clsdata
        sf,p=self.uleb(p); inf,p=self.uleb(p); dm,p=self.uleb(p); vm,p=self.uleb(p)
        res=[]
        for cnt,is_field in ((sf,True),(inf,True),(dm,False),(vm,False)):
            idx=0
            for _ in range(cnt):
                diff,p=self.uleb(p)
                accf,p=self.uleb(p)
                idx+=diff
                if is_field:
                    if accf & 0x10000:
                        p=self.skip_value(p)
                else:
                    co,p=self.uleb(p)
                    if co: res.append((idx,co))
        return res

def strings_in_code(d, code_off, dex):
    regs,ins,outs,tries,dbg,size=struct.unpack('<HHHHII', d[code_off:code_off+16])
    p=code_off+16
    units=struct.unpack('<%dH'%size, d[p:p+2*size])
    out=[]
    i=0
    while i < size:
        u=units[i]; op=u&0xff
        if op==0x1a and i+1<size and units[i+1] < dex.string_ids_size:
            out.append(dex.s(units[i+1])); i+=2; continue
        if op==0x1b and i+2<size and (units[i+1]|(units[i+2]<<16)) < dex.string_ids_size:
            out.append(dex.s(units[i+1]|(units[i+2]<<16))); i+=3; continue
        i+=1
    return out

if __name__=='__main__':
    dex=Dex(sys.argv[1])
    t=dex.types()
    want=sys.argv[2:] or None
    for ci,nm in enumerate(t):
        if not isinstance(nm,str): continue
        if not (nm.startswith('Lorg/godotengine') or nm.startswith('Lcom/godot')): continue
        if want and nm not in want: continue
        try:
            codes=dex.class_code(ci)
        except Exception as e:
            continue
        for mi,co in codes:
            try:
                c,cn,mn=dex.method(mi)
            except Exception:
                print('BAD mi',mi,'class',nm); continue
            ss=strings_in_code(dex.d,co,dex)
            if ss: print(cn, '\t', mn, '\t', ss)
