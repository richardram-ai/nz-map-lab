import json,sys,urllib.request,concurrent.futures as cf
W,S,E,N=175.6131,-40.3547,175.6260,-40.3448
base=sys.argv[1]; items=open(sys.argv[2]).read().split()
def get(h):
    u=base+'/'+h.lstrip('./'); j=json.load(urllib.request.urlopen(u,timeout=60)); return u,j
hits=[]
with cf.ThreadPoolExecutor(16) as ex:
    for u,j in ex.map(get,items):
        b=j['bbox']
        if b[0]<E and b[2]>W and b[1]<N and b[3]>S:
            a=[v['href'] for k,v in j['assets'].items() if v['href'].endswith('.tiff')][0]
            hits.append(u.rsplit('/',1)[0]+'/'+a.lstrip('./'))
print('\n'.join(hits))
