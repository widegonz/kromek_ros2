#!/usr/bin/env python3
"""Run a TEMPORARY configuration-only copy of Dr. Park's *original* live-count script.
Does not change the SDK script in vendor/reference. NEVER run alongside ROS node.
"""
import argparse, pathlib,re,subprocess,datetime,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]

def replace_once(src,pattern,replacement):
    new,n=re.subn(pattern,lambda _m:replacement,src,count=1,flags=re.MULTILINE|re.DOTALL)
    if n!=1:raise RuntimeError('Unexpected vendor script format; cannot safely adapt: '+pattern)
    return new

def make_configured_copy(text,library,dest,seconds):
    text=replace_once(text,r'^LIB_PATH\s*=\s*\(.*?^\)', 'LIB_PATH = {!r}'.format(str(library)))
    text=replace_once(text,r'^OUTPUT_ROOT\s*=[^\n]*', 'OUTPUT_ROOT = Path({!r})'.format(str(dest)))
    text=replace_once(text,r'^MEASUREMENT_TIME_S\s*=[^\n]*', 'MEASUREMENT_TIME_S = {!r}'.format(float(seconds)))
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=float,default=60)
    p.add_argument('--out',type=pathlib.Path)
    a=p.parse_args()
    original=ROOT/'vendor/dr_park/reference/linux/kromek_live_count.py'
    library=ROOT/'vendor/dr_park/source/SpectrometerPackage/output/linux64/release/libSpectrometerDriver.so'
    if not original.is_file() or not library.is_file():p.error('Run prepare_vendor.sh and build_sdk.sh first')
    if a.seconds <= 1:p.error('Use --seconds > 1')
    out=(a.out or ROOT/'data'/'reference_runs'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')).resolve()
    out.mkdir(parents=True,exist_ok=False)
    adapted=make_configured_copy(original.read_text(),library,out,a.seconds)
    temp=out/'park_reference_configured.py'
    temp.write_text(adapted)
    print('Using original Park acquisition logic. Configuration-only copy:',temp,flush=True)
    print('DO NOT launch ROS driver concurrently.',flush=True)
    subprocess.run([sys.executable,'-u',str(temp)],check=True)
    print('Reference output:',out)

if __name__=='__main__':main()
