import subprocess
import sys
import os
import time
import json
import shutil
import tempfile
from contextlib import contextmanager

@contextmanager
def tempFileName(file):
    dir = tempfile.mkdtemp()
    yield os.path.join(dir, os.path.basename(file))
    shutil.rmtree(dir)

if len(sys.argv) >= 2:
    file = sys.argv[1]
else:
    file = "A:/Desktop/Ordio - 3 in 1 [c76DZmiKhDI].mkv"

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
    audioChannels = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
                                        "a:0", "-show_entries", "stream=channels",
                                        "-of", "compact=p=0:nk=1", file], 
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT).stdout)
    if "BitRate" in mediaInfoOut["media"]["track"][2]:
        audioBitrate = float(mediaInfoOut["media"]["track"][2]["BitRate"])/1000
    else:
        #audioBitrate = float(mediaInfoOut["media"]["track"][2]["BitDepth"])
        with tempFileName(file) as tempFilename:
            #ffmpeg -i input-video.avi -vn -acodec copy output-audio.aac
            audioSeperate = subprocess.run(["ffmpeg", "-y", "-i", file, "-vn", "-acodec", "copy", tempFilename], 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE)
            audioTime = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", 
                                            "-show_entries", "format=duration", "-of",
                                            "default=noprint_wrappers=1:nokey=1", tempFilename],
                                            stdout = subprocess.PIPE,
                                            stderr = subprocess.STDOUT).stdout)
            audioFileSize = os.path.getsize(tempFilename)*8/1024
            audioBitrate = (audioFileSize/audioTime)
#audioBitrate = 60
print("--audio bitrate--"+str(audioBitrate))

videoBitrate = (subprocess.run(["ffprobe", "-v", "quiet", "-select_streams",
                                    "v:0", "-show_entries", "stream=bit_rate", 
                                    "-of", "default=noprint_wrappers=1:nokey=1", file],
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT).stdout)
#if ffmpeg couldn't find anything in the bitrate tag, subtract the audio bitrate from the overall bitrate from mediainfo
if b"N/A" in videoBitrate:
    videoBitrate = (float(mediaInfoOut["media"]["track"][0]["OverallBitRate"]) - (audioBitrate*1000))/1000
else:
    videoBitrate = float(videoBitrate)
#videoBitrate = 99999999 if b"N/A" in videoBitrate else float(videoBitrate)/1000

videoSize = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
                                  "v:0", "-show_entries", "stream=width,height",
                                  "-of", "csv=s=x:p=0", file],
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.STDOUT).stdout).decode('utf-8').split('x')
videoSize[0], videoSize[1] = float(videoSize[0]), float(videoSize[1])
videoXYRatio = videoSize[0]/videoSize[1]

#min max the bitrate with the input video stream bitrate and the max size (minus audio stream)
print((5.8 * 8 * 1024 * 1024))
time.sleep(30)
targetVideoBitrate = a if (a := ((5.8 * 8 * 1024 * 1024) / ((1000 * videoLength) - (audioBitrate)))) < videoBitrate else videoBitrate
bitrateDifference = targetVideoBitrate/videoBitrate

print("--videoBitrate--"+str(videoBitrate))
print("--targetVideoBitrate--"+str(targetVideoBitrate))

#videoSize[0] = a if (a if (a:=((targetVideoBitrate/100)*145)) > 280 else 280) < videoSize[0] else videoSize[0]
videoSize[0] = videoSize[0] * bitrateDifference
videoSize[1] = videoSize[0] / videoXYRatio

videoEncoder = "libvpx-vp9"
audioCodec = "libopus"
fileEnding = "webm"

videoPass1 = subprocess.run(["ffmpeg", "-y", "-i", file, "-b:v", f"{targetVideoBitrate}k",
                            "-c:v",  videoEncoder,  "-maxrate", f"{(targetVideoBitrate/100)*80}k", 
                            "-bufsize", f"{targetVideoBitrate*2}k", "-minrate", "0k",
                            "-vf", f"scale={videoSize[0]}:{videoSize[1]}",
                            "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "24",
                            "-threads", "0", "-row-mt", "1",
                            "-pass", "1", "-an", "-f", "null", "NUL"])

videoPass2 = subprocess.run(["ffmpeg", "-y", "-i", file, "-b:v", f"{targetVideoBitrate}k",
                            "-c:v", videoEncoder, "-maxrate", f"{(targetVideoBitrate/100)*80}k",
                            "-bufsize", f"{targetVideoBitrate*2}k", "-minrate", "0k",
                            "-vf", f"scale={videoSize[0]}:{videoSize[1]}",
                            "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "24",
                            "-threads", "0", "-row-mt", "1",
                            "-map_metadata", "0", "-metadata:s:v:0", f"bit_rate={targetVideoBitrate}",
                            "-pass", "2", "-c:a", audioCodec, "-frame_duration", "20",
                            "-b:a", f"{audioBitrate}k",
                            f"{os.path.splitext(file)[0]}1.{fileEnding}"])