#!/usr/bin/env python3
"""Compare consecutive Dr. Park CSV and our ROS2 bag (NOT the same events).
Runs on PC or robot, Python 3.8+, stdlib only. Never accesses USB itself.
"""
import argparse,csv,json,math,pathlib,sqlite3,statistics
from validate_kromek_bag import parse_measurement,parse_spectrum

EDGES=[0,64,128,256,512,1024,2048,4095,4096]

def park_data(directory):
    summary=directory/'interval_summary.csv'
    if not summary.is_file():
        possibilities=list(directory.glob('measurement_*/interval_summary.csv'))
        if len(possibilities)!=1:raise ValueError('Specify the measurement_<timestamp> folder containing interval_summary.csv')
        summary=possibilities[0]
    rows=list(csv.DictReader(summary.open(newline='')))
    if not rows:raise ValueError('Park acquisition has no intervals')
    counts=[0]*4096;elapsed_live=0.0;total=0
    for row in rows:
        live=float(row['interval_live_s']);n=int(row['interval_counts'])
        if live<=0 or n<0:raise ValueError('Bad Park interval')
        file=summary.parent/row['filename']
        with file.open(newline='') as f:spec=list(csv.DictReader(f))
        if len(spec)!=4096:raise ValueError('Expected 4096 Park channels in '+str(file))
        current=[int(x['counts']) for x in spec]
        if any(int(x['channel'])!=i for i,x in enumerate(spec)) or sum(current)!=n:
            raise ValueError('Park spectrum mismatch: '+str(file))
        counts=[a+b for a,b in zip(counts,current)]
        total+=n;elapsed_live+=live
    return dict(name='Dr. Park original',channels=counts,count=total,live_s=elapsed_live,intervals=len(rows),rate=total/elapsed_live)

def ros_data(db):
    if db.is_dir():
        matches=list(db.glob('*.db3'))
        if len(matches)!=1:raise ValueError('Expected exactly one .db3 in ROS2 bag')
        db=matches[0]
    with sqlite3.connect(str(db)) as con:
        topics={i:n for i,n in con.execute('SELECT id,name FROM topics')}
        ms={};ss={}
        for id,stamp,blob in con.execute('SELECT topic_id,timestamp,data FROM messages ORDER BY timestamp'):
            if topics[id]=='/kromek/measurement':
                v=parse_measurement(blob)
                if v['stamp_ns'] in ms:raise ValueError('Duplicate ROS timestamp')
                ms[v['stamp_ns']]=v
            elif topics[id]=='/kromek/spectrum':
                v=parse_spectrum(blob)
                if v['stamp_ns'] in ss:raise ValueError('Duplicate spectrum timestamp')
                ss[v['stamp_ns']]=v
    if not ms or set(ms)!=set(ss):raise ValueError('Missing ROS measurement/spectrum pairs')
    counts=[0]*4096;duration=0.0;total=0
    for stamp in sorted(ms):
        m,s=ms[stamp],ss[stamp]
        if m['device_id']!=s['device_id'] or m['frame_id']!=s['frame_id']:raise ValueError('ROS metadata mismatch')
        if len(s['channels'])!=4096 or sum(s['channels'])!=m['counts']:raise ValueError('ROS count mismatch')
        if not 0<m['live_ms']<=m['real_ms']:raise ValueError('ROS time mismatch')
        counts=[a+b for a,b in zip(counts,s['channels'])]
        total+=m['counts'];duration+=m['live_ms']/1000
    return dict(name='ROS 2 Kromek',channels=counts,count=total,live_s=duration,intervals=len(ms),rate=total/duration)

def compare(park,ros):
    r1,r2=park['rate'],ros['rate'];n1,n2=park['count'],ros['count'];t1,t2=park['live_s'],ros['live_s']
    se=math.sqrt(n1/t1**2+n2/t2**2) if n1+n2 else 0.0
    z=(r1-r2)/se if se else 0.0
    grouped=[]
    total_variation=0.0
    for lo,hi in zip(EDGES[:-1],EDGES[1:]):
        p=sum(park['channels'][lo:hi])/max(1,n1)
        q=sum(ros['channels'][lo:hi])/max(1,n2)
        total_variation+=abs(p-q)/2
        grouped.append({'channels':'{}–{}'.format(lo,hi-1),'park_fraction':p,'ros_fraction':q,'absolute_diff':abs(p-q)})
    return {'park':{k:v for k,v in park.items() if k!='channels'},
            'ros':{k:v for k,v in ros.items() if k!='channels'},
            'rate_difference_cps':r1-r2,'rate_difference_z':z,
            'rate_95pct_approx_compatible':abs(z)<1.96,
            'grouped_spectral_total_variation':total_variation,
            'spectrum_groups':grouped,
            'caution':'Sequential independent Poisson-like counts: no event-by-event equality expected. Rate z assumes stable exposure/geometry; <1.96 not proof of equivalence.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--park',type=pathlib.Path,required=True,help='Park measurement directory')
    parser.add_argument('--rosbag',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,default=pathlib.Path('comparison.json'))
    a=parser.parse_args()
    report=compare(park_data(a.park),ros_data(a.rosbag))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('Original Park: {count} counts / {live_s:.2f} live seconds = {rate:.3f} CPS'.format(**report['park']))
    print('ROS driver:   {count} counts / {live_s:.2f} live seconds = {rate:.3f} CPS'.format(**report['ros']))
    print('Rate difference: {:.3f} CPS; approximate z = {:.3f}'.format(report['rate_difference_cps'],report['rate_difference_z']))
    print('Grouped spectral TV distance: {:.4f}'.format(report['grouped_spectral_total_variation']))
    print('See',a.output,'for spectral groups and important cautions.')

if __name__=='__main__':main()
