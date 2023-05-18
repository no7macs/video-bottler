import subprocess
import sys
import os
import time
import json
import shutil
import tempfile
from contextlib import contextmanager
from tkinter import * 

@contextmanager
def tempFileName(file) -> str:
    dir = tempfile.mkdtemp()
    yield os.path.join(dir, os.path.basename(file))
    shutil.rmtree(dir)  


class encodeAndValue:
    def __init__(self, file) -> None:
        self.file = file
        self.ffmpegInfoOut = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", 
                                        "-show_format", "-show_streams", self.file],
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT).stdout)
        self.mediaInfoOut = json.loads((subprocess.run(["MediaInfo", "--Output=JSON", self.file], 
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT).stdout))  
        self.videoLength = float(self.ffmpegInfoOut["format"]["duration"])
        print(self.videoLength)
        self.upperVideoSize = (5.8*8*1024*1024)
        #  video size
        self.videoWidth = float(self.ffmpegInfoOut["streams"][0]["width"])
        self.videoHeight = float(self.ffmpegInfoOut["streams"][0]["height"])
        self.videoXYRatio = self.videoWidth/self.videoHeight
        self.targetVideoWidth = float(0)
        self.targetVideoHeight = float(0)

    def getMaxTargetSize(self) -> int:
        return(self.maxTargetSize)

    def setSourceAudioBitrate(self) -> float:
        if "duration" in self.ffmpegInfoOut["streams"][1]:
                    self.audioTime = float(self.ffmpegInfoOut["streams"][1]["duration"])
        else:
            self.audioTime = float(self.mediaInfoOut["media"]["track"][2]["Duration"])

        if "bit_rate" in self.ffmpegInfoOut["streams"][1]:
            self.audioBitrate = float(self.ffmpegInfoOut["streams"][1]["bit_rate"])/1000
        elif "BitRate" in self.mediaInfoOut["media"]["track"][2]:
            self.audioBitrate = float(self.mediaInfoOut["media"]["track"][2]["BitRate"])/1000
        else:
            with tempFileName(file) as self.tempFilename:
                #  copy audio stream with same conatiner into temp folder
                self.audioSeperate = subprocess.run(["ffmpeg", "-y", "-i", file, "-vn", "-acodec", "copy", self.tempFilename], 
                                                    stdout=subprocess.PIPE, 
                                                    stderr=subprocess.PIPE)
                self.audioFileSize = os.path.getsize(self.tempFilename)*8/1024
                self.audioBitrate = float(self.audioFileSize/self.audioTime)
        print("--audio bitrate--"+str(self.audioBitrate))
        return(self.audioBitrate)
    
    def setSourceVideoBitrate(self) -> float:
        if "bit_rate" in self.ffmpegInfoOut["streams"][1]:
            self.videoBitrate = float(self.ffmpegInfoOut["streams"][0]["bit_rate"])/1000
        else:
            self.videoBitrate = (float(self.mediaInfoOut["media"]["track"][0]["OverallBitRate"]) - (self.audioBitrate*1000))/1000
        #videoBitrate = 99999999 if b"N/A" in videoBitrate else float(videoBitrate)/1000
        print("--videoBitrate--"+str(self.videoBitrate))
        return(self.videoBitrate)

    def setTargetVideoBitrate(self) -> float:
        #min max the bitrate with the input video stream bitrate and the max size (minus audio stream)
        self.calculatedUpperVideoSize = (self.upperVideoSize if self.upperVideoSize < (a:=os.path.getsize(self.file)*8) else a)
        print(self.calculatedUpperVideoSize)
        print(os.path.getsize(self.file)*8)
        self.targetVideoBitrate = ((self.calculatedUpperVideoSize - self.audioBitrate) / (1000 * self.videoLength))
        self.bitrateDifference = self.targetVideoBitrate/self.videoBitrate
        print("--targetVideoBitrate--"+str(self.targetVideoBitrate))
        return(self.targetVideoBitrate)

    def setTargetVideoSize(self) -> float:
        self.targetVideoWidth = self.videoWidth * self.bitrateDifference
        self.targetVideoHeight = self.targetVideoWidth / self.videoXYRatio
        #videoSize[0] = a if (a if (a:=((targetVideoBitrate/100)*145)) > 280 else 280) < videoSize[0] else videoSize[0]
        return(self.targetVideoWidth, self.targetVideoHeight)


class bitrateSlider(Frame):
    def __init__(self, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)
        self.bitrateSliderFrame = Frame(self)
        self.bitrateSliderFrame.pack(anchor = W, expand=True, fill='both')
        self.sliderValuesFrame = Frame(self.bitrateSliderFrame)
        self.sliderValuesFrame.pack(anchor = W, expand=True, fill='both')
        self.audioBitrateLabel = Label(self.sliderValuesFrame, text='0kb/s')
        self.audioBitrateLabel.pack(side=LEFT)
        self.videoBitrateLabel = Label(self.sliderValuesFrame, text='0kb/s')
        self.videoBitrateLabel.pack(side=RIGHT)
        self.bitrateRatio = DoubleVar()
        self.bitrateRatioSlider = Scale(self.bitrateSliderFrame, orient=HORIZONTAL, from_=0, to=1, showvalue=0, variable=self.bitrateRatio, length=500, resolution=0.01, command=self.bitrateRatioSliderUpdate)
        self.bitrateRatioSlider.pack(anchor = W)
        self.audioBitrateLabel["text"] = str(round(audioBitrate, 2))
        self.videoBitrateLabel["text"] = str(round(targetVideoBitrate, 2))
        self.bitrateRatioSlider.set(audioBitrate/targetVideoBitrate)

    def bitrateRatioSliderUpdate(self, bitrateRatio):
        #snapedRatio = min([0.1, 0.5, 0.6, 0.9],key=lambda x:abs(x-float(bitrateRatio)))
        #bitrateRatioSlider.set(bitrateRatio)
        testTest["text"] = str(bitrateRatio)
        self.audioBitrateLabel.place(x=(((self.bitrateRatioSlider.coords()[0])/2)))
        self.videoBitrateLabel.place(x=((self.bitrateRatioSlider.coords()[0]+self.bitrateRatioSlider.cget("length")-self.videoBitrateLabel.winfo_width())/2))
        self.audioBitrateLabel["text"] = str(round((valueTings.getMaxTargetSize()/8/1024/1024)/float(bitrateRatio),3))+"kb/s"

if __name__ == "__main__":

    if len(sys.argv) >= 2:
        file = sys.argv[1]
    else:
        file = "A:/Desktop/rhu4pIjQxF9emfnP.mp4"

    valueTings = encodeAndValue(file)
    audioBitrate = valueTings.setSourceAudioBitrate()
    videoBitrate = valueTings.setSourceVideoBitrate()
    targetVideoBitrate = valueTings.setTargetVideoBitrate()
    videoX, videoY = valueTings.setTargetVideoSize()

    root = Tk()
    root.title("Video Bottler")
    slider = bitrateSlider(root).pack(anchor=W)
    testTest = Label(root, text='0')
    testTest.pack(anchor = W)
    root.mainloop()

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