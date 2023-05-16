import subprocess
import sys
import os
import time
import json
import shutil
import tempfile
from contextlib import contextmanager

if len(sys.argv) >= 2:
    file = sys.argv[1]
else:
    file = "A:/Desktop/Bim8UCQkFCOlQ8aX.mp4"

@contextmanager
def tempFileName(file) -> str:
    dir = tempfile.mkdtemp()
    yield os.path.join(dir, os.path.basename(file))
    shutil.rmtree(dir)  

class encodeAndValue:
    def __init__(self) -> None:
        self.ffmpegInfoOut = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", 
                                        "-show_format", "-show_streams", file],
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT).stdout)
        self.mediaInfoOut = json.loads((subprocess.run(["MediaInfo", "--Output=JSON", file], 
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT).stdout))      
        self.audioBitrate = 0
        self.videoBitrate = 0
        self.videoLength = float(self.ffmpegInfoOut["format"]["duration"])
        print(self.videoLength)
        self.targetVideoBitrate = 0
        self.bitrateDifference = 0
        #  video size
        self.videoWidth = float(self.ffmpegInfoOut["streams"][0]["width"])
        self.videoHeight = float(self.ffmpegInfoOut["streams"][0]["height"])
        self.videoXYRatio = self.videoWidth/self.videoHeight
        self.targetVideoWidth = float(0)
        self.targetVideoHeight = float(0)

    def setSourceAudioBitrate(self) -> float:
        if "bit_rate" in self.ffmpegInfoOut["streams"][1]:
            self.audioBitrate = float(self.ffmpegInfoOut["streams"][1]["bit_rate"])/1000
        elif "BitRate" in self.mediaInfoOut["media"]["track"][2]:
            self.audioBitrate = float(self.mediaInfoOut["media"]["track"][2]["BitRate"])/1000
        else:
            #audioBitrate = float(mediaInfoOut["media"]["track"][2]["BitDepth"])
            with tempFileName(file) as self.tempFilename:
                #  copy audio stream with same conatiner into temp folder
                self.audioSeperate = subprocess.run(["ffmpeg", "-y", "-i", file, "-vn", "-acodec", "copy", self.tempFilename], 
                                                    stdout=subprocess.PIPE, 
                                                    stderr=subprocess.PIPE)
                #  with audio stream time and temp file size, get bitrate
                self.audioTime = float(self.ffmpegInfoOut["streams"][1]["duration"])
                self.audioFileSize = os.path.getsize(self.tempFilename)*8/1024
                self.audioBitrate = float(self.audioFileSize/self.audioTime)
        #audioBitrate = 60
        print("--audio bitrate--"+str(self.audioBitrate))
        return(self.audioBitrate)
    
    def setSourceVideoBitrate(self) -> float:
        if "bit_rate" in self.ffmpegInfoOut["streams"][1]:
            self.videoBitrate = float(self.ffmpegInfoOut["streams"][0]["bit_rate"])/1000
        #if ffmpeg couldn't find anything in the bitrate tag, subtract the audio bitrate from the overall bitrate from mediainfo
        else:
            self.videoBitrate = (float(self.mediaInfoOut["media"]["track"][0]["OverallBitRate"]) - (self.audioBitrate*1000))/1000
        #videoBitrate = 99999999 if b"N/A" in videoBitrate else float(videoBitrate)/1000
        print("--videoBitrate--"+str(self.videoBitrate))
        return(self.videoBitrate)

    def setTargetVideoBitrate(self) -> float:
        #min max the bitrate with the input video stream bitrate and the max size (minus audio stream)
        self.targetVideoBitrate = a if (a := ((5.8 * 8 * 1024 * 1024) / ((1000 * self.videoLength) - (self.audioBitrate)))) < self.videoBitrate else self.videoBitrate
        self.bitrateDifference = self.targetVideoBitrate/self.videoBitrate
        print("--targetVideoBitrate--"+str(self.targetVideoBitrate))
        return(self.targetVideoBitrate)

    def setTargetVideoSize(self) -> float:
        self.targetVideoWidth = self.videoWidth * self.bitrateDifference
        self.targetVideoHeight = self.targetVideoWidth / self.videoXYRatio
        #videoSize[0] = a if (a if (a:=((targetVideoBitrate/100)*145)) > 280 else 280) < videoSize[0] else videoSize[0]
        return(self.targetVideoWidth, self.targetVideoHeight)
    
valueTings = encodeAndValue()
audioBitrate = valueTings.setSourceAudioBitrate()
valueTings.setSourceVideoBitrate()
targetVideoBitrate = valueTings.setTargetVideoBitrate()
videoX, videoY = valueTings.setTargetVideoSize()

videoEncoder = "libvpx-vp9"
audioCodec = "libopus"
fileEnding = "webm"

videoPass1 = subprocess.run(["ffmpeg", "-y", "-i", file, "-b:v", f"{targetVideoBitrate}k",
                            "-c:v",  videoEncoder,  "-maxrate", f"{(targetVideoBitrate/100)*80}k", 
                            "-bufsize", f"{targetVideoBitrate*2}k", "-minrate", "0k",
                            "-vf", f"scale={videoX}:{videoY}",
                            "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "24",
                            "-threads", "0", "-row-mt", "1",
                            "-pass", "1", "-an", "-f", "null", "NUL"])

videoPass2 = subprocess.run(["ffmpeg", "-y", "-i", file, "-b:v", f"{targetVideoBitrate}k",
                            "-c:v", videoEncoder, "-maxrate", f"{(targetVideoBitrate/100)*80}k",
                            "-bufsize", f"{targetVideoBitrate*2}k", "-minrate", "0k",
                            "-vf", f"scale={videoX}:{videoY}",
                            "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "24",
                            "-threads", "0", "-row-mt", "1",
                            "-map_metadata", "0", "-metadata:s:v:0", f"bit_rate={targetVideoBitrate}",
                            "-pass", "2", "-c:a", audioCodec, "-frame_duration", "20",
                            "-b:a", f"{audioBitrate}k",
                            f"{os.path.splitext(file)[0]}1.{fileEnding}"])