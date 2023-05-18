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
        print("--videoLength--"+str(self.videoLength))
        self.upperVideoSize = (5.8*8*1024*1024) #megabits
        #self.preferedUpperVideoSize = self.upperVideoSize if self.upperVideoSize < (a:=os.path.getsize(self.file)*8) else a
        self.commonAudioValues = [0,1,6,8,14,16,22,24,32,40,48,64,96,112,160,192,510]
        #  video size
        self.videoWidth = float(self.ffmpegInfoOut["streams"][0]["width"])
        self.videoHeight = float(self.ffmpegInfoOut["streams"][0]["height"])
        self.videoXYRatio = self.videoWidth/self.videoHeight
        self.targetVideoWidth = float(0)
        self.targetVideoHeight = float(0)

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

    #this one NEEDS to be changed and made to actually do something (its very cringe)
    def setTargetAudioBitrate(self) -> float:
        self.targetAudioBitrate = self.audioBitrate
        #if (self.targetAudioBitrate*self.audioTime)*1024 > self.upperVideoSize:
        #    for a,b in enumerate(self.commonAudioValues):
        #        if b > self.targetAudioBitrate:
        #            self.targetAudioBitrate = self.commonAudioValues[a-1]
        #            break
        print("--targetAudioBitrate--"+str(self.targetAudioBitrate))
        self.targetAudioBitrate = 60
        return(self.targetAudioBitrate)

    def setTargetVideoBitrate(self) -> float:
        #min max the bitrate with the input video stream bitrate and the max size (minus audio stream)
        self.targetVideoBitrate = a if (a := (self.upperVideoSize / (1000 * self.videoLength)) - self.targetAudioBitrate) < self.videoBitrate else self.videoBitrate
        #self.targetVideoBitrate = (self.preferedUpperVideoSize / ((1000 * self.videoLength)- self.audioBitrate))
        self.bitrateDifference = self.targetVideoBitrate/self.videoBitrate
        print("--targetVideoBitrate--"+str(self.targetVideoBitrate))
        return(self.targetVideoBitrate)

    def setTargetVideoSize(self) -> float:
        self.targetVideoWidth = self.videoWidth * self.bitrateDifference
        self.targetVideoHeight = self.targetVideoWidth / self.videoXYRatio
        #videoSize[0] = a if (a if (a:=((targetVideoBitrate/100)*145)) > 280 else 280) < videoSize[0] else videoSize[0]
        return(self.targetVideoWidth, self.targetVideoHeight, self.bitrateDifference)


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
        self.bitrateRatioSlider = Scale(self.bitrateSliderFrame, orient=HORIZONTAL, from_=0, to=1, showvalue=0, variable=self.bitrateRatio, length=500, resolution=0.001, command=self.bitrateRatioSliderUpdate)
        self.bitrateRatioSlider.pack(anchor = W)
        self.audioBitrateLabel["text"] = str(round(targetAudioBitrate, 2))
        self.videoBitrateLabel["text"] = str(round(targetVideoBitrate, 2))
        self.bitrateRatioSlider.set(targetAudioBitrate/(targetAudioBitrate+targetVideoBitrate))

    def bitrateRatioSliderUpdate(self, bitrateRatio):
        #snapedRatio = min([a/(targetAudioBitrate+targetVideoBitrate) for a in [0,1,6,8,14,16,22,24,32,40,48,64,96,112,160,192,510]],key=lambda x:abs(x-float(bitrateRatio)))
        #self.bitrateRatioSlider.set(snapedRatio)
        testTest["text"] = str(bitrateRatio)
        self.audioBitrateLabel.place(x=(((self.bitrateRatioSlider.coords()[0])/2)))
        self.videoBitrateLabel.place(x=((self.bitrateRatioSlider.coords()[0]+self.bitrateRatioSlider.cget("length")-self.videoBitrateLabel.winfo_width())/2))
        self.alteredAudioBitrate = (targetAudioBitrate+targetVideoBitrate)*self.bitrateRatioSlider.get()
        self.alteredVideoBitrate = (targetAudioBitrate+targetVideoBitrate)-float(self.alteredAudioBitrate)
        self.audioBitrateLabel["text"] = str(round(self.alteredAudioBitrate,3))
        self.videoBitrateLabel["text"] = str(round(self.alteredVideoBitrate,3))
       
if __name__ == "__main__":

    if len(sys.argv) >= 2:
        file = sys.argv[1]
    else:
        file = "A:/Desktop/Vessel - Red Sex (Official Video) [8iPoS9zqmoQ].webm"

    valueTings = encodeAndValue(file)
    audioBitrate = valueTings.setSourceAudioBitrate()
    videoBitrate = valueTings.setSourceVideoBitrate()
    targetAudioBitrate = valueTings.setTargetAudioBitrate()
    targetVideoBitrate = valueTings.setTargetVideoBitrate()
    videoX, videoY, bitDiff = valueTings.setTargetVideoSize()

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
                                "-b:a", f"{targetAudioBitrate}k",
                                f"{os.path.splitext(file)[0]}1.{fileEnding}"])