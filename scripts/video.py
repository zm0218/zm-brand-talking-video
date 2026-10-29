#!/usr/bin/env python3
"""Reference-led talking-head editing. Python stdlib + full FFmpeg/libass."""
import argparse, json, math, os, re, shutil, subprocess, sys
from pathlib import Path

RESOLUTIONS = ([1080,1920],[1920,1080],[2160,3840],[3840,2160])
THEMES = {
    'warm': {'accent':'FFCC29','border':'A82920','size':66},
    'blue': {'accent':'3F8CFF','border':'FFFFFF','size':62},
    'meme': {'accent':'FFCC29','border':'9B2626','size':76},
    'natural': {'accent':'FFC42B','border':'702820','size':62},
}

def run(args, cwd=None):
    p=subprocess.run([str(x) for x in args],cwd=cwd,capture_output=True,text=True)
    if p.returncode: raise RuntimeError('Command failed: '+str(args[0])+'\n'+p.stderr[-4000:])
    return p.stdout

def tools():
    candidates=[os.getenv('ZM_VIDEO_FFMPEG'),shutil.which('ffmpeg')]
    for c in candidates:
        if not c: continue
        try:
            run([c,'-version']); filters=run([c,'-hide_banner','-filters'])
            if not all(re.search(r'\s'+x+r'\s',filters) for x in ['subtitles','overlay','pad','loudnorm']):continue
            probe=os.getenv('ZM_VIDEO_FFPROBE') or str(Path(c).parent/('ffprobe.exe' if os.name=='nt' else 'ffprobe'))
            if not Path(probe).is_file():probe=shutil.which('ffprobe') or probe
            run([probe,'-version'])
            return str(c),str(probe)
        except (OSError,RuntimeError):continue
    raise RuntimeError('没有可运行且含 subtitles/overlay/pad/loudnorm 的 FFmpeg 和 ffprobe。将其加入 PATH，或设置 ZM_VIDEO_FFMPEG 与 ZM_VIDEO_FFPROBE；不自动安装。')

def probe(p, fp): return json.loads(run([fp,'-v','error','-show_streams','-show_format','-of','json',p]))
def seconds(v): return float(v)
def file_path(s, root):
    p=Path(s).expanduser();p=p if p.is_absolute() else root/p
    if not p.is_file():raise ValueError('素材不存在: '+str(p))
    return p.resolve()

def ass_color(h): return '&H'+h[4:6]+h[2:4]+h[0:2]+'&'
def clean(s): return str(s).replace('\\','／').replace('{','（').replace('}','）').replace('\r','')
def timecode(t):
    cent=round(t*100);return f'{cent//360000}:{cent//6000%60:02}:{cent//100%60:02}.{cent%100:02}'

def rich(s,theme,size):
    def line(s):
        parts=re.split(r'(\[\[.*?\]\])',s)
        out=''
        for p in parts:
            if p.startswith('[[') and p.endswith(']]'):
                out+=('{\\c'+ass_color(theme['accent'])+'\\3c'+ass_color(theme['border'])+'\\bord4\\fs'+str(round(size*1.12))+'}'+clean(p[2:-2])+'{\\c&HFFFFFF&\\3c&H111111&\\bord3\\fs'+str(size)+'}')
            else:out+=clean(p)
        return out
    return '\\N'.join(line(x) for x in s.split('\n'))

def write_ass(job,duration,path):
    theme=THEMES[job.get('theme','warm')];font=job.get('font_family','Noto Sans CJK SC')
    landscape=job.get('resolution',[1080,1920])[0]>job.get('resolution',[1080,1920])[1]
    cw,ch=(1920,1080) if landscape else (1080,1920)
    size=54 if landscape else theme['size'];title_size=76 if landscape else 100
    caption_y=.86 if landscape else .77
    lines=[f'''[Script Info]
ScriptType: v4.00+
PlayResX: {cw}
PlayResY: {ch}
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00111111,&H66000000,-1,0,0,0,100,100,0,0,1,3,1,5,70,110,260,1
Style: Title,{font},100,&H00FFFFFF,&H00FFFFFF,&H00111111,&H66000000,-1,0,0,0,100,100,0,0,1,4,1,5,70,110,260,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text''']
    for kind in ['captions','titles']:
        for e in job.get(kind,[]):
            a=max(0,float(e['start']));b=min(duration,float(e['end']))
            if b<=a:continue
            title=kind=='titles';s=int(e.get('size',title_size if title else size))
            x=float(e.get('x',.5 if landscape else .48))*cw;y=float(e.get('y',.2 if title else caption_y))*ch
            tags=f'{{\\an5\\pos({x:.0f},{y:.0f})\\fs{s}}}'
            if title:tags+=r'{\fscx94\fscy94\t(0,100,\fscx100\fscy100)\fad(60,60)}'
            lines.append(f'Dialogue: {2 if title else 1},{timecode(a)},{timecode(b)},'+('Title' if title else 'Caption')+',,0,0,0,,'+tags+rich(e['text'],theme,s))
    path.write_text('\n'.join(lines),encoding='utf-8')

def validate(job,root,fp):
    w,h=job.get('resolution',[1080,1920]);fps=job.get('fps',30)
    if [w,h] not in RESOLUTIONS: raise ValueError('支持 1080p / 4K 的 9:16 竖屏或 16:9 横屏。')
    if fps!=30: raise ValueError('参考模板固定 30fps；其他帧率需明确改编。')
    if job.get('theme','warm') not in THEMES:raise ValueError('未知 theme')
    if not job.get('brief',{}).get('confirmed'): raise ValueError('brief.confirmed 尚未确认；先核对核心信息，不得擅自填写 true。')
    if not job.get('clips'):raise ValueError('至少一个片段')
    if any(x in str(job.get('font_family','')) for x in [',','\n','\r']):raise ValueError('无效 font_family')
    resolved=[];total=0
    for clip in job['clips']:
        c=dict(clip);c['source']=file_path(c['source'],root);m=probe(c['source'],fp)
        if not any(x['codec_type']=='video' for x in m['streams']):raise ValueError('source 必须是视频')
        a=float(c.get('in',0));b=float(c['out']);dur=float(m['format']['duration'])
        if not math.isfinite(a+b) or not 0<=a<b<=dur+0.01:raise ValueError('片段 in/out 超出源文件: '+str(c['source']))
        c['duration']=round((b-a)*fps)/fps
        if c['duration']<1/fps:raise ValueError('片段不足一帧')
        c['has_audio']=any(x['codec_type']=='audio' for x in m['streams'])
        c['in']=a;c['start']=total;total+=c['duration'];c['end']=total
        if c.get('layout','full') not in ['full','inset']:raise ValueError('layout 仅 full/inset')
        if c.get('fit','cover') not in ['cover','contain']:raise ValueError('fit 仅 cover/contain')
        zoom=float(c.get('zoom',1))
        if not 1<=zoom<=1.3:raise ValueError('zoom 须在 1–1.3')
        if c.get('fit')=='contain' and zoom!=1:raise ValueError('contain 保留完整画面时 zoom 必须为1')
        for k in ['focus_x','focus_y']:
            if not 0<=float(c.get(k,.5))<=1:raise ValueError('focus 范围 0–1')
        if c.get('visual'):
            c['visual']=file_path(c['visual'],root)
            if c.get('visual_type','image') not in ['image','video']:raise ValueError('visual_type 仅 image/video')
            if c.get('visual_type')=='video':
                vm=probe(c['visual'],fp);vin=float(c.get('visual_in',0))
                if not any(s['codec_type']=='video' for s in vm['streams']):raise ValueError('visual 必须包含视频画面')
                if not math.isfinite(vin) or vin<0 or vin+c['duration']>float(vm['format']['duration'])+.01:raise ValueError('B-roll 超出源时长')
        resolved.append(c)
    for kind in ['captions','titles']:
        previous_end=-1
        for e in sorted(job.get(kind,[]),key=lambda z:z['start']):
            a=float(e['start']);b=float(e['end'])
            if not math.isfinite(a+b) or not 0<=a<b<=total+.04:raise ValueError(kind+' 时间超界')
            if a<previous_end-.001:raise ValueError(kind+' 同轨重叠')
            previous_end=b
            plain=re.sub(r'\[\[|\]\]','',e['text'])
            limit=14 if kind=='captions' else 10
            if len(plain.splitlines())>2 or any(len(x)>limit for x in plain.splitlines()):raise ValueError(kind+' 文字过长，先按语义拆行/拆句')
            if not .08<=float(e.get('x',.48))<=.85 or not .08<=float(e.get('y',.2 if kind=='titles' else .77))<=.87:raise ValueError('文字锚点超出安全区')
            if not 28<=int(e.get('size',66 if kind=='captions' else 100))<=160:raise ValueError('文字字号超界')
            if kind=='captions' and any((c.get('source_has_captions',False) or c.get('visual_has_captions',False)) and max(a,c['start'])<min(b,c['end']) for c in resolved):raise ValueError('源片已有烧录字幕：禁止叠加第二套字幕；使用无字幕原素材或清空该段 captions')
    if job.get('bgm'):file_path(job['bgm']['path'],root)
    if job.get('font_file'):file_path(job['font_file'],root)
    if job.get('endcard'):raise ValueError('片尾请作为单独 clip 或已确认片尾视频追加，勿在本配置臆造账号头像。')
    return resolved,total

def render(args):
    ff,fp=tools();config=Path(args.job).resolve();root=config.parent;job=json.loads(config.read_text())
    clips,total=validate(job,root,fp)
    if args.check:print(json.dumps({'valid':True,'seconds':total,'clips':len(clips),'ffmpeg':ff},ensure_ascii=False));return
    out=Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('输出目录非空；请换版本目录，保护已有交付。')
    out.mkdir(parents=True,exist_ok=True);w,h=job.get('resolution',[1080,1920]);fps=30
    if args.preview is not None and args.preview<=0:raise ValueError('--preview 必须大于 0')
    duration=min(total,args.preview) if args.preview else total
    (out/'job.snapshot.json').write_text(json.dumps(job,ensure_ascii=False,indent=2))
    (out/'source-map.json').write_text(json.dumps(clips,ensure_ascii=False,indent=2,default=str))
    segments=[]
    for i,c in enumerate(clips):
        if c['start']>=duration:break
        d=min(c['duration'],duration-c['start']);dest=out/f'segment-{i:03}.mkv'
        cmd=[ff,'-hide_banner','-loglevel','error','-y']
        cmd+=['-ss',str(c['in']),'-i',c['source']];vi=0
        if c.get('visual'):
            if c.get('visual_type')=='video':cmd+=['-ss',str(c.get('visual_in',0)),'-i',c['visual']]
            else:cmd+=['-loop','1','-framerate','30','-i',c['visual']]
            vi=1
        ai=0
        if not c['has_audio']:
            ai=2 if c.get('visual') else 1;cmd+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
        inset=c.get('layout','full')=='inset';iw=round(w*.84/2)*2 if inset else w;ih=round(h*.84/2)*2 if inset else h
        z=float(c.get('zoom',1));sw=math.ceil(iw*z/2)*2;sh=math.ceil(ih*z/2)*2
        fx=float(c.get('focus_x',.5));fy=float(c.get('focus_y',.5))
        if c.get('fit','cover')=='contain':
            vf=f'scale={iw}:{ih}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={iw}:{ih}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30'
        else:vf=f'scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={iw}:{ih}:(iw-ow)*{fx}:(ih-oh)*{fy},setsar=1,fps=30'
        if inset:vf+=f',pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black'
        cmd+=['-map',f'{vi}:v:0','-map',f'{ai}:a:0','-vf',vf,'-af',f'aresample=48000,apad,atrim=duration={d},asetpts=PTS-STARTPTS','-t',str(d),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','pcm_s16le','-ar','48000','-ac','2',dest]
        run(cmd);segments.append(dest);print(f'clip {i+1}/{len(clips)}',flush=True)
    (out/'concat.txt').write_text(''.join(f"file '{p.name}'\n" for p in segments))
    run([ff,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i','concat.txt','-c','copy','base.mkv'],cwd=out)
    write_ass(job,duration,out/'captions.ass')
    vf='subtitles=captions.ass'
    if job.get('font_file'):
        fonts=out/'fonts';fonts.mkdir();shutil.copy2(file_path(job['font_file'],root),fonts/('font'+Path(job['font_file']).suffix));vf+=':fontsdir=fonts'
    cmd=[ff,'-hide_banner','-loglevel','error','-y','-i','base.mkv']
    norm='loudnorm=I=-16:TP=-1.5:LRA=11'
    if job.get('bgm'):
        music=file_path(job['bgm']['path'],root);gain=float(job['bgm'].get('gain_db',-20))
        if not -36<=gain<=-12:raise ValueError('BGM gain_db 建议范围 -36 到 -12')
        cmd+=['-stream_loop','-1','-i',music,'-filter_complex',f'[0:a]asplit[v][side];[1:a]volume={gain}dB[m];[m][side]sidechaincompress=threshold=0.04:ratio=8:attack=15:release=250[duck];[v][duck]amix=inputs=2:normalize=0:duration=first,{norm}[audio]','-map','0:v','-map','[audio]']
    else:cmd+=['-map','0:v','-map','0:a','-af',norm]
    cmd+=['-vf',vf,'-t',str(duration),'-c:v','libx264','-preset','medium','-crf','19','-maxrate',('28M' if max(w,h)==3840 else '12M'),'-bufsize',('56M' if max(w,h)==3840 else '24M'),'-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','review.mp4']
    run(cmd,cwd=out)
    run([ff,'-v','error','-i',out/'review.mp4','-f','null','-'])
    info=probe(out/'review.mp4',fp);info.update(status='有声审片版；已完整解码，连续观看和听感未验收',planned_duration=duration)
    (out/'qa.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    for t in sorted(set([0.2,min(duration/2,duration-.04),max(0,duration-.2)])):
        run([ff,'-hide_banner','-loglevel','error','-y','-ss',str(t),'-i',out/'review.mp4','-frames:v','1','-vf',('scale=960:540' if w>h else 'scale=540:960'),out/f'check-{t:.2f}.jpg'])
    print(out/'review.mp4')

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('inspect');a.add_argument('sources',nargs='+');a.add_argument('--out',required=True)
    a=sub.add_parser('render');a.add_argument('job');a.add_argument('--out');a.add_argument('--check',action='store_true');a.add_argument('--preview',type=float)
    args=p.parse_args()
    if args.action=='inspect':
        ff,fp=tools();items=[]
        for s in args.sources:
            f=Path(s).expanduser().resolve();d=probe(f,fp);d.update(path=str(f),bytes=f.stat().st_size);items.append(d)
        path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():raise ValueError('inspect 输出已存在；换新文件名。')
        path.write_text(json.dumps(items,ensure_ascii=False,indent=2));print(path)
    else:
        if not args.check and not args.out:p.error('render 需要 --out 或 --check')
        render(args)

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError,KeyError) as e:sys.exit(str(e))
