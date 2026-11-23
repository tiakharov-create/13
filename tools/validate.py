import os, struct, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translate import pool_strings

def walk(d, start, end, depth=0, out=None):
    if out is None: out=[]
    p=start
    while p+8<=end:
        t,hs,sz=struct.unpack('<HHI', d[p:p+8])
        if sz==0: break
        assert p+sz<=end, 'chunk overruns parent at 0x%x (sz %d, parent end 0x%x)'%(p,sz,end)
        assert hs<=sz, 'header size > chunk size at 0x%x'%p
        out.append((depth,p,t,hs,sz))
        if t==0x0001:
            cnt,sty,fl,ss,sts=struct.unpack('<IIIII', d[p+8:p+28])
            assert hs+4*cnt<=sz, 'string offsets overrun'
            # every string offset must be inside the chunk
            for i in range(cnt):
                o=struct.unpack('<I', d[p+hs+4*i:p+hs+4*i+4])[0]
                assert ss+o < sz, 'string %d offset %d beyond chunk (%d)'%(i,ss+o,sz)
        if t==0x0200:
            walk(d, p+hs, p+sz, depth+1, out)
        if t==0x0201:
            cnt=struct.unpack('<I', d[p+12:p+16])[0]
            st=struct.unpack('<I', d[p+16:p+20])[0]
            assert hs+4*cnt<=sz, 'entry offsets overrun'
        p+=sz
    return out

def check_arsc(path):
    d=open(path,'rb').read()
    total=struct.unpack('<I', d[4:8])[0]; hs=struct.unpack('<H', d[2:4])[0]
    assert d[:2]==b'\x02\x00'
    assert total==len(d), 'header size %d != file %d'%(total,len(d))
    out=walk(d, hs, total)
    # package sizes must match their content
    for depth,p,t,ch_hs,sz in out:
        if t==0x200:
            assert p+sz<=total, 'package overruns file'
            # last child must end exactly at package end
            kids=[o for o in out if o[1]>p and o[1]<p+sz and o[0]==depth+1]
            last=max(k[1]+k[4] for k in kids)
            assert last==p+sz, 'package 0x%x: children end 0x%x != 0x%x'%(p,last,p+sz)
    for depth,p,t,ch_hs,sz in out:
        if t==1:
            s,info=pool_strings(d,p)
            assert len(s)==info['count']
    return out

def check_axml(path):
    d=open(path,'rb').read()
    total=struct.unpack('<I', d[4:8])[0]; hs=struct.unpack('<H', d[2:4])[0]
    assert d[:2]==b'\x03\x00'
    assert total==len(d), '%s: header %d != file %d'%(path,total,len(d))
    out=walk(d, hs, total)
    for depth,p,t,ch_hs,sz in out:
        if t==1:
            s,info=pool_strings(d,p)
            assert len(s)==info['count']
    return out

if __name__=='__main__':
    o=check_arsc(sys.argv[1])
    print('resources.arsc OK — %d chunks, %d bytes'%(len(o), len(open(sys.argv[1],'rb').read())))
    bad=0
    for f in sorted(glob.glob('/home/user/13/res/**/*.xml', recursive=True)):
        try:
            check_axml(f)
        except AssertionError as e:
            print('FAIL', f, e); bad+=1
    print('all res/*.xml validated, failures:', bad)
