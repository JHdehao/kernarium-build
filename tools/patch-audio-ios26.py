#!/usr/bin/env python3
"""让音频设备代码在 Xcode 26 的 SDK 上编译：两条 iOS 27 才有的
AVFoundation 调用退回旧签名，两个 iOS 27 才有的通知观察者禁用
（成员保留为 nil，析构里的 removeObserver 对 nil 无害）。"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1]) / "darwin" / "device" / "audio"


def patch(name, old, new):
    path = root / name
    text = path.read_text()
    assert text.count(old) == 1, (name, text.count(old))
    path.write_text(text.replace(old, new))
    print(f"{name}: 替换 1 处")


def wrap_off(name, start_marker, occurrences):
    path = root / name
    text = path.read_text()
    start = text.index(start_marker)
    # 从 start 往后找 occurrences 个块结束标记
    pos = start
    for _ in range(occurrences):
        end = text.index("                    }];", pos)
        pos = end + len("                    }];")
    indent = "        "
    tail = text[pos:]
    assert tail.startswith("\n"), tail[:40]
    text = (
        text[:start]
        + "#if 0  /* iOS 27 的通知，Xcode 26 SDK 没有 */\n"
        + text[start:pos]
        + "\n#endif"
        + text[pos:]
    )
    path.write_text(text)
    print(f"{name}: 禁用 {occurrences} 段 iOS 27 通知观察者")


patch(
    "apple_microphone_input.mm",
    """            NSError* tapError = nil;
            const BOOL tapped = [input
                installTapOnBus:0
                     bufferSize:static_cast<AVAudioFrameCount>(
                                    inputFormat.sampleRate * tapSeconds)
                         format:inputFormat
                          error:&tapError
                          block:^(AVAudioPCMBuffer* buffer, AVAudioTime* when) {
                              tap->receive(buffer, when);
                          }];""",
    """            /* Xcode 26 的 installTapOnBus 没有 error 参数，也没有返回值。 */
            [input
                installTapOnBus:0
                     bufferSize:static_cast<AVAudioFrameCount>(
                                    inputFormat.sampleRate * tapSeconds)
                         format:inputFormat
                          block:^(AVAudioPCMBuffer* buffer, AVAudioTime* when) {
                              tap->receive(buffer, when);
                          }];
            const BOOL tapped = YES;""",
)

patch(
    "apple_playback_sink.mm",
    """        NSError* error = nil;
        if ([output.engine connect:output.player
                                to:output.engine.mainMixerNode
                            format:format
                             error:&error]) {
            [output.engine prepare];
            output.connected = true;
        }""",
    """        /* Xcode 26 的 connect:to:format: 没有 error 参数。 */
        [output.engine connect:output.player
                            to:output.engine.mainMixerNode
                        format:format];
        [output.engine prepare];
        output.connected = true;""",
)

wrap_off(
    "apple_microphone_input.mm",
    "        deactivationObserver_ = [NSNotificationCenter.defaultCenter",
    2,
)
wrap_off(
    "apple_playback_sink.mm",
    "        deactivationObserver_ = [[NSNotificationCenter defaultCenter]",
    2,
)
print("完成")

# 第二批：Xcode 26 SDK 的其余音频 API 差异。
patch(
    "apple_playback_sink.mm",
    """                NSError* connectError = nil;
                if (![engine_ connect:player_
                                   to:engine_.mainMixerNode
                               format:format_
                                error:&connectError]) {
                    configured_ = false;
                    prepared_ = false;
                    running_ = false;
                    fault("the engine would not connect");
                    return false;
                }""",
    """                /* Xcode 26 的 connect:to:format: 不返回错误。 */
                [engine_ connect:player_
                             to:engine_.mainMixerNode
                         format:format_];""",
)
patch(
    "apple_playback_sink.mm",
    "                          (void)[player playAndReturnError:&error];",
    "                          [player play];",
)
patch(
    "apple_playback_sink.mm",
    "            playing = [player_ playAndReturnError:&error];",
    "            [player_ play];\n            playing = true;",
)
patch(
    "apple_playback_sink.mm",
    """            if ([player_ playAndReturnError:&error])
                return OutputStart::running;""",
    """            [player_ play];
            return OutputStart::running;""",
)
print("第二批完成")
