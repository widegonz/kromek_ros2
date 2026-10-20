#!/usr/bin/env python3
"""Read /proc per-thread CPU deltas, not lifetime-averaged ps %%CPU.
Python 3.8+, no ROS and no extra dependencies.
"""
import argparse,csv,os,time,pathlib

def read_stat(pid,tid):
    stat=(pathlib.Path('/proc')/str(pid)/'task'/str(tid)/'stat').read_text()
    rest=stat[stat.rfind(')')+2:].split()
    # fields 14 and 15 (utime, stime), after stripping pid/comm
    return (int(rest[11])+int(rest[12]))/os.sysconf('SC_CLK_TCK')

def samples(pid):
    tasks=pathlib.Path('/proc')/str(pid)/'task'
    values={}
    for p in tasks.iterdir():
        try:
            values[int(p.name)]=(read_stat(pid,p.name),(p/'comm').read_text().strip())
        except (FileNotFoundError,PermissionError,ValueError):continue
    return values

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--seconds',type=int,default=60)
    parser.add_argument('--out',default='cpu_threads.csv')
    a=parser.parse_args()
    before=samples(a.pid);t0=time.monotonic();started=t0
    with open(a.out,'w',newline='') as fh:
        w=csv.writer(fh);w.writerow(['time_since_start_s','pid','tid','thread','cpu_pct_one_core'])
        for _ in range(a.seconds):
            time.sleep(1)
            t1=time.monotonic()
            try:after=samples(a.pid)
            except FileNotFoundError:
                print('Process exited');break
            dt=t1-t0;rows=[]
            for tid,(cpu,label) in after.items():
                if tid not in before:continue
                pct=100*(cpu-before[tid][0])/dt
                w.writerow([round(t1-started,3),a.pid,tid,label,round(pct,3)])
                rows.append((pct,tid,label))
            fh.flush()
            total=sum(v[0] for v in rows)
            top=', '.join('{}(tid={}):{:.1f}%'.format(label,tid,pct) for pct,tid,label in sorted(rows,reverse=True)[:3])
            print('CPU instantánea {:.1f}% | {}'.format(total,top),flush=True)
            before,t0=after,t1
    print('CSV:',a.out)

if __name__=='__main__':main()
