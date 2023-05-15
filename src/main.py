import subprocess
import sys
import os
import time
import json

#file = sys.argv[1]
file = "A:/Desktop/Sewerslvt - Ecifircas (Moral Orel Music Video) [2EXiI5ez7nk].webm"

videoLength = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                    "format=duration", "-of",
                                    "default=noprint_wrappers=1:nokey=1", file],
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT).stdout)
print(videoLength)

mediaInfoOut = json.loads((subprocess.run(["MediaInfo", "--Output=JSON", file], 
                                stdout = subprocess.PIPE,
                                stderr = subprocess.STDOUT).stdout))

audioBitrate = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
                                "a:0", "-show_entries", "stream=bit_rate",
                                "-of", "compact=p=0:nk=1", file], 
                                stdout = subprocess.PIPE,
                                stderr = subprocess.STDOUT).stdout)

if not b"N/A" in audioBitrate: 
    audioBitrate = float(audioBitrate)/1000

else:
    audioSampleRate = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
                                        "a:0", "-show_entries", "stream=sample_rate",
                                        "-of", "compact=p=0:nk=1", file], 
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT).stdout)
    audioChannels = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
                                        "a:0", "-show_entries", "stream=channels",
                                        "-of", "compact=p=0:nk=1", file], 
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT).stdout)
    audioBitDepth = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
                                        "a:0", "-show_entries", "stream=bits_per_raw_sample",
                                        "-of", "compact=p=0:nk=1", file], 
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT).stdout)
    if b"N/A" in audioBitDepth:
        if "BitRate" in mediaInfoOut["media"]["track"][2]:
            audioBitrate = float(mediaInfoOut["media"]["track"][2]["BitRate"])/1000
        else:
            audioBitrate = float(mediaInfoOut["media"]["track"][2]["BitDepth"])
            audioBitrate = 96

print("--audio bitrate--"+str(audioBitrate))

videoBitrate = (subprocess.run(["ffprobe", "-v", "quiet", "-select_streams",
                                    "v:0", "-show_entries", "stream=bit_rate", 
                                    "-of", "default=noprint_wrappers=1:nokey=1", file],
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT).stdout)
videoBitrate = (float(mediaInfoOut["media"]["track"][0]["OverallBitRate"])- (audioBitrate*1000))/1000
#videoBitrate = 99999999 if b"N/A" in videoBitrate else float(videoBitrate)/1000

videoSize = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
                                  "v:0", "-show_entries", "stream=width,height",
                                  "-of", "csv=s=x:p=0", file],
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.STDOUT).stdout).decode('utf-8').split('x')
videoSize[0], videoSize[1] = float(videoSize[0]), float(videoSize[1])
videoXYRatio = videoSize[0]/videoSize[1]

targetVideoBitrate = a if (a := ((24 * 8 * 1024 * 1024) / ((1000 * videoLength) - (audioBitrate)))) < videoBitrate else videoBitrate

print("--videoBitrate--"+str(videoBitrate))
print("--targetVideoBitrate--"+str(targetVideoBitrate))

videoSize[0] = a if (a if (a:=((targetVideoBitrate/100)*145)) > 280 else 280) < videoSize[0] else videoSize[0]
videoSize[1] = videoSize[0] / videoXYRatio

videoEncoder = "libvpx-vp9"
audioCodec = "libopus"
fileEnding = "webm"

videoPass1 = subprocess.run(["ffmpeg", "-y", "-i", file, "-b:v", f"{targetVideoBitrate}k",
                            "-c:v",  videoEncoder,  "-maxrate", f"{targetVideoBitrate}k", 
                            "-bufsize", f"{targetVideoBitrate/2}k", "-minrate", "0k",
                            "-vf", f"scale={videoSize[0]}:{videoSize[1]}",
                            "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "12",
                            "-threads", "0", "-row-mt", "1",
                            "-pass", "1", "-an", "-f", "null", "NUL"])

videoPass2 = subprocess.run(["ffmpeg", "-y", "-i", file, "-b:v", f"{targetVideoBitrate}k",
                            "-c:v", videoEncoder, "-maxrate", f"{targetVideoBitrate}k",
                            "-bufsize", f"{targetVideoBitrate/2}k", "-minrate", "0k",
                            "-vf", f"scale={videoSize[0]}:{videoSize[1]}",
                            "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "12",
                            "-threads", "0", "-row-mt", "1",
                            "-map_metadata", "0", "-metadata:s:v:0", f"bit_rate={targetVideoBitrate}",
                            "-pass", "2", "-c:a", audioCodec, "-frame_duration", "20",
                            "-b:a", f"{audioBitrate}k",
                            f"{os.path.splitext(file)[0]}1.{fileEnding}"])