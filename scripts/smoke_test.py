#!/usr/bin/env python3
"""Offline integration checks using generated patterns, never real people."""
import argparse, array, json, math, subprocess, sys
from pathlib import Path
from video import tools, run, probe, validate

HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('测试输出目录非空，请选新目录')
    out.mkdir(parents=True,exist_ok=True);ff,fp=tools()
    source=out/'source.mp4';visual=out/'visual.mp4';silent=out/'silent.mp4';cover=out/'cover.png'
    for path,color,freq in [(source,'red',440),(visual,'blue',880)]:
        run([ff,'-v','error','-y','-f','lavfi','-i',f'color=c={color}:s=640x360:r=30',
             '-f','lavfi','-i',f'sine=frequency={freq}:sample_rate=48000','-t','3',
             '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',path])
    run([ff,'-v','error','-y','-i',visual,'-an','-c:v','copy',silent])
    run([ff,'-v','error','-y','-f','lavfi','-i','color=c=white:s=640x360','-frames:v','1',cover])
    base={'brief':{'confirmed':True,'topic':'合成素材技术测试'},'fps':30,'theme':'warm',
          'font_family':'Arial','captions':[{'start':.15,'end':1.3,'text':'[[SYNC]] TEST'}],
          'titles':[{'start':.1,'end':1.0,'text':'TEST','y':.2}]}
    cases={
      'landscape':dict(base,resolution=[1920,1080],clips=[{'source':str(source),'in':0,'out':3,
         'fit':'contain','visual':str(visual),'visual_type':'video','visual_in':0}]),
      'portrait':dict(base,resolution=[1080,1920],clips=[{'source':str(source),'in':0,'out':1.5,
         'fit':'contain'},{'source':str(silent),'in':0,'out':1.5,'layout':'inset'}])}
    results={}
    for name,job in cases.items():
        jp=out/(name+'.json');jp.write_text(json.dumps(job,ensure_ascii=False,indent=2))
        run([sys.executable,HERE/'video.py','render',jp,'--check'])
        run([sys.executable,HERE/'video.py','render',jp,'--out',out/name])
        meta=probe(out/name/'review.mp4',fp);v=next(s for s in meta['streams'] if s['codec_type']=='video')
        assert [v['width'],v['height']]==job['resolution'] and v['r_frame_rate']=='30/1'
        assert abs(float(meta['format']['duration'])-3)<.08
        assert any(s['codec_type']=='audio' for s in meta['streams'])
        results[name]='render and full decode passed';print(name,'passed',flush=True)
    # The blue B-roll has an 880 Hz tone; output must retain the 440 Hz source.
    raw=subprocess.run([ff,'-v','error','-ss','1.5','-i',str(out/'landscape/review.mp4'),
         '-t','0.5','-vn','-ac','1','-ar','48000','-f','f32le','-'],capture_output=True,check=True).stdout
    samples=array.array('f');samples.frombytes(raw)
    if sys.byteorder!='little':samples.byteswap()
    def magnitude(freq):
        re=sum(x*math.cos(2*math.pi*freq*i/48000) for i,x in enumerate(samples))
        im=sum(x*math.sin(2*math.pi*freq*i/48000) for i,x in enumerate(samples))
        return math.hypot(re,im)
    assert magnitude(440)>magnitude(880)*5,'B-roll unexpectedly replaced source audio'
    pixel=subprocess.run([ff,'-v','error','-ss','1.5','-i',str(out/'landscape/review.mp4'),
         '-vf','crop=2:2:100:100,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True).stdout
    assert len(pixel)>=3 and pixel[2]>pixel[0]+80,'B-roll picture missing'
    results['broll']='blue picture, original 440 Hz audio verified'
    for label,mutate in [
      ('unconfirmed',lambda j:j['brief'].update(confirmed=False)),
      ('burned_caption',lambda j:j['clips'][0].update(source_has_captions=True)),
      ('broll_out_of_range',lambda j:j['clips'][0].update(visual_in=2))]:
        job=json.loads(json.dumps(cases['landscape']));mutate(job)
        try:validate(job,out,fp)
        except ValueError:results[label]='rejected as expected'
        else:raise AssertionError('Expected rejection: '+label)
    run([sys.executable,HERE/'bookends.py',out/'landscape/review.mp4','--cover',cover,
         '--tail',visual,'--out',out/'bookends','--hold','.5'])
    meta=probe(out/'bookends/review-with-bookends.mp4',fp)
    assert abs(float(meta['format']['duration'])-6.5)<.08
    results['bookends']='6.5 seconds, supplied cover and tail, full decode passed'
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError as e:
        detail=e.stderr.decode(errors='replace') if isinstance(e.stderr,bytes) else e.stderr
        sys.exit(detail or str(e))
    except (ValueError,RuntimeError,AssertionError) as e:sys.exit(str(e))
