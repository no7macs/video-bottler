import subprocess
import sys
import os
import time
import json
import shutil
import tempfile
import yt_dlp
import tkinter
import tkinter.ttk as ttk
from tkinter.filedialog import *
from typing import Optional, Tuple, Union
from contextlib import contextmanager
from tkinter import *
from tkinterdnd2 import DND_FILES, TkinterDnD
from threading import Thread

@contextmanager
def tempFileName() -> str:
    dir = tempfile.mkdtemp()
    yield dir
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
            self.tempFoldername = tempFoldername
            #  copy audio stream with same conatiner into temp folder
            self.tempFile = os.path.join(self.tempFoldername, ("audio"+os.path.basename(self.file)))
            self.audioSeperate = subprocess.run(["ffmpeg", "-y", "-i", file, "-vn", "-acodec", "copy", self.tempFile],
                                                stdout = subprocess.PIPE,
                                                stderr = subprocess.STDOUT)
            self.audioFileSize = os.path.getsize(self.tempFile)*8 #bytes to bits
            self.audioBitrate = float(self.audioFileSize/self.audioTime)/1000 # bits to kilobits (a second)
            os.remove(self.tempFile)
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
        #self.targetVideoWidth = a if (a if (a:=((targetVideoBitrate/100)*145)) > 280 else 280) < self.targetVideoWidth else self.targetVideoWidth
        return(self.targetVideoWidth, self.targetVideoHeight, self.bitrateDifference)

    def setAlteredAudioVideoBitrate(self, precentage) -> float:
        self.audioUsagePrecentage = precentage
        #whole numbers (too lazy to do math properly
        self.alteredAudioBitrate = int((self.targetAudioBitrate+self.targetVideoBitrate)*precentage)
        self.alteredVideoBitrate = int((self.targetAudioBitrate+self.targetVideoBitrate)-float(self.alteredAudioBitrate))
        #print("--alteredAudioBitrate--"+str(self.alteredAudioBitrate))
        #print("--alteredVideoBitrate--"+str(self.alteredVideoBitrate))
        return(self.alteredAudioBitrate, self.alteredVideoBitrate)

    def setAlteredVideoSize(self) -> float:
        print(self.targetVideoBitrate/self.alteredAudioBitrate)
        self.alteredVideoWidth = self.targetVideoWidth*(self.targetVideoBitrate/self.alteredVideoBitrate)
        #self.alteredVideoWidth = a if (a if (a:=((self.alteredVideoBitrate/100)*145)) > 280 else 280) < self.targetVideoWidth else self.targetVideoWidth
        self.alteredVideoHeight = self.alteredVideoWidth/self.videoXYRatio
        return(self.alteredVideoWidth, self.alteredVideoHeight, (self.alteredVideoWidth/self.alteredVideoHeight))

    def setNumberOfFrames(self) -> float:
        self.frameCount = float(json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                                                            "-show_entries", "stream=nb_read_packets", 
                                                            "-of", "csv=p=0", "-of", "json", self.file], 
                                                            stdout=subprocess.PIPE,
                                                            stderr = subprocess.STDOUT).stdout)['streams'][0]['nb_read_packets'])
        return(self.frameCount)

    def getTargetBitrates(self) -> float:
        return(self.targetAudioBitrate, self.targetVideoBitrate)
    
    def getAlteredBitrates(self) -> float:
        return(self.alteredAudioBitrate, self.alteredVideoBitrate)

    def getEncodeStatus(self) -> float:
        return(self.encodeStage, self.encodePecent)

    def encodeHandler(self, process):
        self.queue = [0]
        self.encodePassProcessReader = Thread(target=self.encodeProcessReader, args=(process,))
        self.encodePassProcessReader.start()
        while True:
            if process.poll() is not None:
                break
            self.encodePecent = (self.queue[0]/self.setNumberOfFrames())*100

        process.stdout.close()
        self.encodePassProcessReader.join()
        process.wait()

    def encodeProcessReader(self, process):
        while True:
            if process.poll() is not None:
                break
            progressText = process.stdout.readline()
            print(progressText)
            if progressText is None:
                break
            progressText = progressText.decode("utf-8")
            if progressText.startswith("frame="):
                self.queue[0] = int(progressText.partition('=')[-1])

    def encode(self):
        self.encodeStage = 0
        self.encodePecent = 0
        self.videoEncoder = "libvpx-vp9"
        self.audioCodec = "libopus"
        self.fileEnding = "webm"
        self.alteredAudioBitrate, self.alteredVideoBitrate = valueTings.getAlteredBitrates()
        self.videoX, self.videoY, self.bitDiff = valueTings.setAlteredVideoSize()

        newfile = tkinter.filedialog.asksaveasfilename(title="save as", initialdir=os.path.dirname(file), initialfile=f"{os.path.splitext(file)[0]}1.{self.fileEnding}", filetypes=[("webm","webm")], defaultextension=".webm")
        self.encodeStage = 1
        self.videoPass1 = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-i", file, "-b:v", f"{self.alteredVideoBitrate}k",
                                    "-c:v",  self.videoEncoder,  "-maxrate", f"{self.alteredVideoBitrate*0.8}k", 
                                    "-bufsize", f"{(self.alteredVideoBitrate*0.8)*2}k", "-minrate", "0k",
                                    "-vf", f"scale={self.videoX}:{self.videoY}",
                                    "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "24",
                                    "-threads", "0", "-row-mt", "1", "-progress", "pipe:1",
                                    "-pass", "1", "-an", "-f", "null", "NUL"], 
                                    stdout=subprocess.PIPE,
                                    stderr = subprocess.STDOUT)
        self.encodeHandler(self.videoPass1)

        self.encodeStage = 2
        self.videoPass2 = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-i", file, "-b:v", f"{self.alteredVideoBitrate}k",
                                    "-c:v", self.videoEncoder, "-maxrate", f"{self.alteredVideoBitrate*0.8}k",
                                    "-bufsize", f"{(self.alteredVideoBitrate*0.8)*2}k", "-minrate", "0k",
                                    "-vf", f"scale={self.videoX}:{self.videoY}",
                                    "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "24",
                                    "-threads", "0", "-row-mt", "1",
                                    "-map_metadata", "0", "-metadata:s:v:0", f"bit_rate={self.alteredVideoBitrate}",
                                    "-c:a", self.audioCodec, "-frame_duration", "20",
                                    "-b:a", f"{self.alteredAudioBitrate}k", "-progress", "pipe:1",
                                    f"{newfile}"], 
                                    stdout=subprocess.PIPE,
                                    stderr = subprocess.STDOUT)
        self.encodeHandler(self.videoPass2)
        self.encodeStage = 3

    def haltEncode(self):
        pass


class ytdlpDownloader:
    def __init__(self, url, folder):
        self.tempFolder = folder
        self.url = url

    class MyLogger:
        def debug(self, msg):
            # For compatibility with youtube-dl, both debug and info are passed into debug
            # You can distinguish them by the prefix '[debug] '
            if msg.startswith('[debug] '):
                pass
            else:
                self.info(msg)
        def info(self, msg):
            print(msg)
        def warning(self, msg):
            pass
        def error(self, msg):
            print(msg)

    def getFormat(self, ctx):
        formats = ctx.get("formats")[::-1]
        bestVideo = next(a for a in formats if a['vcodec'] != "none" and a["acodec"] == 'none')
        audioExt = {"mp4": "m4a", "webm": "webm"}[bestVideo['ext']]
        bestAudio = next(a for a in formats if (a["acodec"] != "none" and a["vcodec"] == "none" and a["ext"] == audioExt))
        yield {
            'format_id': f'{bestVideo["format_id"]}+{bestAudio["format_id"]}',
            'ext': bestVideo['ext'],
            'requested_formats': [bestVideo, bestAudio],
            # Must be + separated list of protocols
            'protocol': f'{bestVideo["protocol"]}+{bestAudio["protocol"]}'
        }

    def download(self):
        ydl_opts = {
            'outtmpl':f"""{self.tempFolder}/%(title)s-%(id)s.%(ext)s""",
            'cookiefile':'./youtube.com_cookies.txt',
            'logger': self.MyLogger()
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(self.url)
        return(os.path.join(self.tempFolder, os.listdir(self.tempFolder)[0]))


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
        #15 decimal places because i'm to lazy to do math properly
        self.bitrateRatioSlider = Scale(self.bitrateSliderFrame, orient=HORIZONTAL, from_=0, to=1, showvalue=0, length=500, resolution=0.000000000000001, command=self.bitrateRatioSliderUpdate)
        self.bitrateRatioSlider.pack(anchor = W)
        self.snapToCommonAudio = False
        self.setDefaults()

    def bitrateRatioSliderUpdate(self, bitrateRatio):
        # no it does not snap properly and gives wack numbers
        if self.snapToCommonAudio == True:
            self.snapedRatio = min([a/(self.targetAudioBitrate+self.targetVideoBitrate) for a in [0,1,6,8,14,16,22,24,32,40,48,64,96,112,160,192,510]],key=lambda x:abs(x-float(bitrateRatio)))
            self.bitrateRatioSlider.set(self.snapedRatio)
        testTest["text"] = str(bitrateRatio)
        self.audioBitrateLabel.place(x=(((self.bitrateRatioSlider.coords()[0])/2)))
        self.videoBitrateLabel.place(x=((self.bitrateRatioSlider.coords()[0]+self.bitrateRatioSlider.cget("length")-self.videoBitrateLabel.winfo_width())/2))
        self.alteredAudioBitrate, self.alteredVideoBitrate = valueTings.setAlteredAudioVideoBitrate(self.bitrateRatioSlider.get())
        self.audioBitrateLabel["text"] = str(int(self.alteredAudioBitrate))+"kb/s"
        self.videoBitrateLabel["text"] = str(int(self.alteredVideoBitrate))+"kb/s"

    def setDefaults(self) -> None:
        self.targetAudioBitrate, self.targetVideoBitrate = valueTings.getTargetBitrates()
        self.audioBitrateLabel["text"] = str(int(self.targetAudioBitrate))+"kb/s"
        self.videoBitrateLabel["text"] = str(int(self.targetVideoBitrate))+"kb/s"
        self.audioUsagePrecentage = self.targetAudioBitrate/(self.targetAudioBitrate+self.targetVideoBitrate)
        self.bitrateRatioSlider.set(self.audioUsagePrecentage)

    def snapToCommonAudioValues(self, state:bool) -> None:
        self.snapToCommonAudio = state


# drag and drop exists in here for now, should revisit later and cleaned up
class selectFileWindow(TkinterDnD.Tk):
    def __init__(self, *args, **kwargs):
        TkinterDnD.Tk.__init__(self, *args, **kwargs)
        #self.title("Video Bottler")
        #customtkinter.set_appearance_mode("system")
        self.file = ""
        #customtkinter.set_widget_scaling(1000)
        #customtkinter.set_window_scaling(1000)
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', lambda a:self.setFile(a.data))
        self.fileSelectFrame()
        self.fileDownloadFrame()

    def checkFile(self) -> None:
        print(self.file)
        if not self.file == "" and os.path.exists(self.file):
            self.destroy()

    def setFile(self, file):
        print(file)
        self.file=file.replace("{","").replace("}","")
        self.checkFile()

    def getFile(self) -> str:
        return(self.file)

    def fileSelectFrame(self):
        self.selectFileFrame = Frame(self)
        self.selectFileFrame.grid(row=0, column=0, padx=5, pady=5)
        self.selectInfoLabel = Label(self.selectFileFrame, text="Drag and Drop \n or")
        self.selectInfoLabel.grid(row=0, column=0)
        self.browseFileButton = Button(self.selectFileFrame, text="Browse", command=self.browseForFiles)
        self.browseFileButton.grid(row=1, column=0)

    def fileDownloadFrame(self):
        self.downloadFileFrame = Frame(self)
        self.downloadFileFrame.grid(row=0, column=1, padx=5, pady=5)
        self.downloadFileLabel = Label(self.downloadFileFrame, text="Download a link (yt-dlp)")
        self.downloadFileLabel.grid(row=0, column=0)
        self.downloadUrl = StringVar()
        self.downloadEntry = Entry(self.downloadFileFrame, textvariable=self.downloadUrl)
        self.downloadEntry.grid(row=1, column=0)
        self.downloadStatusLabel = Label(self.downloadFileFrame)
        self.browseFileButton.grid(row=2, column=0)
        self.browseFileButton = Button(self.downloadFileFrame, text="Download", command=self.downloadFromUrl)
        self.browseFileButton.grid(row=3, column=0)

    def browseForFiles(self):
        self.file = tkinter.filedialog.askopenfilename(initialdir = "/", title = "Select a File",
                                          filetypes = (("Video",["*.webm*","*.mp4*","*.mov*","*.m4a*"]), ("all files", "*.*")))
        self.after(1, self.checkFile)

    def downloadFromUrl(self):
        self.tempFoldername = tempFoldername
        ytdlp = ytdlpDownloader(self.downloadEntry.get(), self.tempFoldername)
        self.file = ytdlp.download()
        self.checkFile()


class encodeStatusWindow(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.encodeStatusMessage = Label(self, text="Status: ")
        self.encodeStatusMessage.pack(anchor=W)
        self.encodeProgressBar = ttk.Progressbar(self, orient=HORIZONTAL, length=500, mode='determinate')
        self.encodeProgressBar.pack(anchor=W)
        self.actionButtonsFrame = Frame(self)
        self.actionButtonsFrame.pack(anchor=W)
        self.after(1, self.updateProgressBar)

    def updateProgressBar(self):  
        self.encodeStage, self.encodePecent = valueTings.getEncodeStatus()
        if self.encodeStage == 1:
            self.encodeStatusMessage["text"] = "Status: Pass1"
            self.encodeProgressBar["value"] = self.encodePecent/2
        elif self.encodeStage == 2:
            self.encodeStatusMessage["text"] = "Status: Pass2"
            self.encodeProgressBar["value"] = (self.encodePecent/2)+50
        elif self.encodeStage == 3:
            self.encodeStatusMessage["text"] = "Status: Done"
        self.changeActionButtons()
        self.after(1, self.updateProgressBar)

    def changeActionButtons(self):
        self.encodeStage, self.encodePecent = valueTings.getEncodeStatus()
        #if self.encodeStage < 3:
        #    self.cancelButton = Button(self.actionButtonsFrame, text="Cancel", command=valueTings.haltEncode)
        #    self.cancelButton.pack(side=RIGHT)
        return


if __name__ == "__main__":
    with tempFileName() as tempFoldername:
        # file select
        if len(sys.argv) >= 2:
            file = sys.argv[1]
        else:
            selectFile = selectFileWindow()
            selectFile.mainloop()
            file = selectFile.getFile()
        # initialize first couple set of values
        valueTings = encodeAndValue(file)
        audioBitrate = valueTings.setSourceAudioBitrate()
        videoBitrate = valueTings.setSourceVideoBitrate()
        targetAudioBitrate = valueTings.setTargetAudioBitrate()
        targetVideoBitrate = valueTings.setTargetVideoBitrate()
        videoX, videoY, bitDiff = valueTings.setTargetVideoSize()
        # main window for setting values and stuff
        root = Tk()
        root.title("Video Bottler")
        snapToAudio = IntVar()
        snapToAudioValuesBox = Checkbutton(root, text="Snap to common audio bitrates", variable=snapToAudio, onvalue=1, offvalue=0, command=lambda:videoaudioBitrateSlider.snapToCommonAudioValues(state=bool(snapToAudio.get())))
        snapToAudioValuesBox.pack(anchor=W)
        videoaudioBitrateSlider = bitrateSlider(root)
        videoaudioBitrateSlider.pack(anchor=W)
        testTest = Label(root, text='0')
        testTest.pack(anchor=W)
        sliderResetDefaultsButton = Button(root, text = "Reset Bitrate", command=lambda:videoaudioBitrateSlider.setDefaults())
        sliderResetDefaultsButton.pack(anchor=W)
        statusLabel = Label(root, text="")
        statusLabel.pack(anchor=W)
        root.mainloop()
        # start encodes
        encodeThread = Thread(target=valueTings.encode)
        encodeThread.start()
        # encode status window
        encodeStatus = encodeStatusWindow()
        encodeStatus.after(1, encodeStatus.updateProgressBar)
        encodeStatus.mainloop()