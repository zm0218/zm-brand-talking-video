# 自备封面与片尾

开源版不捆绑人物头像、商业封面或品牌片尾。使用者需要提供本次有权使用的文件，并确认其标题、姓名、身份和品牌写法。

- 封面：PNG／JPEG／WebP，尽量与正文同画幅。默认视频内停留1.2秒，可设0.8–1.5秒；`--hold 0` 仅导出独立封面，不插入时间轴。
- 片尾：使用自备视频全长，保留其音轨；不再额外叠加旁白、音乐或正文字幕。
- 正文：必须是不含旧片尾的已剪正文。新人物／新账号不能套用其他人的身份和头像。
- 合并后的位图不是分层模板，替换文字或人物需适当编辑工具或原始工程，不用覆盖旧字的粗糙补丁。

```bash
python3 scripts/bookends.py /path/to/body/review.mp4 \
  --cover /path/to/approved-cover.png \
  --tail /path/to/approved-tail.mp4 \
  --out /path/to/work/with-bookends-v01 \
  --hold 1.2
```

加 `--check` 只预检。`--cover` 与 `--tail` 必须显式传入，不存在默认人物素材。工具将封面及片尾等比留边匹配正文的1080p／4K横竖屏，输出30fps。

输出 `review-with-bookends.mp4`、`cover.png`、`end-frame.png`、`bookends.json` 和 `qa.json`。`bookends.json` 记录正文时码偏移：`完整成片时码 = 正文时码 + cover_hold`。正文字幕已烧录，接入首尾后保持同步；首尾不显示正文字幕。

接入首尾后，以最终文件重新检查时长、响度、完整解码和全程看听。尾帧静图仅作预览，不代表动态片尾本身。
