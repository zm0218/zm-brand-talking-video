#!/usr/bin/env python3
"""Use installed macOS Chinese SpeechTranscriber; no upload or model installation."""
import argparse, platform, subprocess, sys
from pathlib import Path
from video import tools, run

def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--out',required=True);a=p.parse_args()
    if platform.system()!='Darwin':raise RuntimeError('本脚本仅供 macOS；其他系统读取现有字幕或已授权 ASR。')
    root=Path(a.out).resolve()
    if root.exists() and any(root.iterdir()):raise RuntimeError('转写输出目录非空，换新目录。')
    root.mkdir(parents=True,exist_ok=True);ff,_=tools()
    run([ff,'-hide_banner','-loglevel','error','-y','-i',Path(a.source).resolve(),'-vn','-ac','1','-ar','16000',root/'audio.wav'])
    run(['swiftc','-parse-as-library','-module-cache-path',root/'swift-cache',Path(__file__).with_suffix('.swift'),'-o',root/'transcribe'])
    run([root/'transcribe',root/'audio.wav',root/'transcript.jsonl'])
    print(root/'transcript.jsonl')

if __name__=='__main__':
    try:main()
    except Exception as e:sys.exit(str(e))
