import Speech
import AVFoundation
import Foundation

@main struct Main {
    static func main() async throws {
        guard CommandLine.arguments.count == 3 else {
            throw NSError(domain:"Usage: transcribe audio.wav output.jsonl",code:2)
        }
        let installed = await SpeechTranscriber.installedLocales
        guard installed.contains(where: {$0.identifier.replacingOccurrences(of:"_",with:"-").lowercased() == "zh-cn"}) else {
            throw NSError(domain:"未检测到已安装中文模型；也可能是沙箱不可见。先诊断权限，不自动下载安装。",code:3)
        }
        let input = CommandLine.arguments[1], output = CommandLine.arguments[2]
        guard !FileManager.default.fileExists(atPath: output) else {
            throw NSError(domain:"输出已存在，拒绝覆盖",code:4)
        }
        let transcriber = SpeechTranscriber(locale:Locale(identifier:"zh-CN"),preset:.timeIndexedTranscriptionWithAlternatives)
        let analyzer = SpeechAnalyzer(modules:[transcriber])
        FileManager.default.createFile(atPath:output,contents:nil)
        let fh=try FileHandle(forWritingTo:URL(fileURLWithPath:output))
        let task=Task {
            for try await result in transcriber.results where result.isFinal {
                var words:[[String:Any]]=[]
                for run in result.text.runs {
                    if let range=run.audioTimeRange {
                        words.append(["start":range.start.seconds,"end":range.end.seconds,"text":String(result.text[run.range].characters)])
                    }
                }
                let row:[String:Any]=["start":result.range.start.seconds,"end":result.range.end.seconds,"text":String(result.text.characters),"words":words]
                let data=try JSONSerialization.data(withJSONObject:row,options:[.sortedKeys,.withoutEscapingSlashes])
                try fh.write(contentsOf:data);try fh.write(contentsOf:Data([10]))
            }
        }
        let file=try AVAudioFile(forReading:URL(fileURLWithPath:input))
        if let last=try await analyzer.analyzeSequence(from:file) {
            try await analyzer.finalizeAndFinish(through:last)
        } else {try await analyzer.finalizeAndFinishThroughEndOfInput()}
        try await task.value;try fh.close()
    }
}
