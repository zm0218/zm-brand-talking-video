#!/usr/bin/env python3
"""Append supplied visual bookends to a rendered body without changing originals."""
import argparse, hashlib, json, math, sys
from pathlib import Path
from video import tools, probe, run, RESOLUTIONS

def duration(m):
    v=next(s for s in m['streams'] if s['codec_type']=='video')
    return float(v.get('duration') or m['format']['duration'])

def file(s):
    p=Path(s).expanduser().resolve()
    if not p.is_file():raise ValueError('文件不存在：'+str(p))
    return p

def main():
    p=argparse.ArgumentParser(description='首帧封面＋已剪正文＋原版片尾；hold=0仅导出独立封面，不插入时间轴。')
    p.add_argument('body');p.add_argument('--out',required=True)
    p.add_argument('--cover',required=True,help='本次获准使用的PNG/JPEG/WebP封面')
    p.add_argument('--tail',required=True,help='本次获准使用的片尾视频')
    p.add_argument('--hold',type=float,default=1.2)
    p.add_argument('--body-contains-tail',action='store_true')
    p.add_argument('--check',action='store_true')
    a=p.parse_args()
    if not math.isfinite(a.hold) or not 0<=a.hold<=5:raise ValueError('hold范围0–5秒；建议0.8–1.5秒，0表示仅独立封面。')
    if a.body_contains_tail:raise ValueError('正文已包含片尾；先使用去除旧片尾的正文，避免双片尾。')
    body,cover,tail=map(file,[a.body,a.cover,a.tail]);out=Path(a.out).expanduser().resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('输出目录非空，拒绝覆盖；换新版本目录。')
    ff,fp=tools();bm,cm,tm=[probe(f,fp) for f in [body,cover,tail]]
    if cm['streams'][0].get('codec_name') not in ['png','mjpeg','webp']:raise ValueError('cover需要PNG/JPEG/WebP静态图。')
    bv=next(s for s in bm['streams'] if s['codec_type']=='video');w,h=bv['width'],bv['height']
    if [w,h] not in RESOLUTIONS:raise ValueError('正文请先按1080p或4K横屏/竖屏渲染。')
    hold=round(a.hold*30)/30;bd=round(duration(bm)*30)/30;td=round(duration(tm)*30)/30
    manifest={'cover':str(cover),'tail':str(tail),'body':str(body),'cover_hold':hold,'body_offset':hold,'body_duration':bd,'tail_start':hold+bd,'tail_duration':td,'duration':hold+bd+td,'resolution':[w,h],'fps':30,'subtitle_time_rule':'正文字幕已烧录，保持同步；外部正文时码加body_offset才是完整成片时码。','sources':{str(f):hashlib.file_digest(f.open('rb'),'sha256').hexdigest() for f in [body,cover,tail]}}
    if a.check:print(json.dumps(manifest,ensure_ascii=False,indent=2));return
    out.mkdir(parents=True,exist_ok=True)
    fit=f'scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:white,setsar=1'
    run([ff,'-v','error','-y','-i',cover,'-frames:v','1','-vf',fit,out/'cover.png'])
    cmd=[ff,'-hide_banner','-loglevel','error','-y'];parts=[]
    if hold:
        cmd+=['-loop','1','-framerate','30','-i',cover];parts.append((hold,False,True))
    cmd+=['-i',body,'-i',tail]
    parts += [(bd,any(s['codec_type']=='audio' for s in bm['streams']),False),(td,any(s['codec_type']=='audio' for s in tm['streams']),False)]
    filters=[];labels=[]
    for i,(d,audio,still) in enumerate(parts):
        bg='white' if still else 'black'
        vf=fit.replace('/2:white','/2:'+bg)
        filters.append(f'[{i}:v]{vf},fps=30,tpad=stop_mode=clone:stop_duration=1,trim=duration={d},setpts=PTS-STARTPTS[v{i}]')
        af=f'aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={d},asetpts=PTS-STARTPTS'
        filters.append((f'[{i}:a]' if audio else 'anullsrc=r=48000:cl=stereo,')+af+f'[a{i}]')
        labels.append(f'[v{i}][a{i}]')
    filters.append(''.join(labels)+f'concat=n={len(parts)}:v=1:a=1[v][a]')
    cmd+=['-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(manifest['duration']),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r','30','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',out/'review-with-bookends.mp4']
    run(cmd);video=out/'review-with-bookends.mp4'
    run([ff,'-v','error','-i',video,'-f','null','-'])
    run([ff,'-v','error','-y','-sseof','-0.1','-i',tail,'-frames:v','1',out/'end-frame.png'])
    (out/'bookends.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    qa=probe(video,fp);qa['status']='有声审片版；完整解码通过，连续观看与听感另验收。'
    (out/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    print(video)

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError,KeyError,StopIteration) as e:sys.exit(str(e))
