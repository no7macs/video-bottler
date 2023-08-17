
#  standard library imports
import subprocess
import sys
import os
import re
import time
import json
import shutil
import tempfile
from threading import Thread
from datetime import datetime
from typing import Optional, Tuple, Union
from contextlib import contextmanager
from tkinter import *
from tkinter.ttk import Progressbar
from tkinter import filedialog, messagebox

#  third party imports
import yt_dlp
import keyboard
from tkinterdnd2 import DND_FILES, TkinterDnD

@contextmanager
def tempFileName() -> str:
    dir = tempfile.mkdtemp()
    yield dir
    shutil.rmtree(dir)


class encodeAndValue:
    def __init__(self) -> None:
        self.file = ""
        self.audioMute = False
        self.customResolutionFlag = False
        self.outFile = ""
        self.fileEnding = "webm"

    # this exists since everything needs the file but the file is set after the class is invoked in the select file window making it so everything has to run afterwards
    # for the love of god please find a better solution
    def setDefaults(self) -> None:
        self.ffmpegInfoOut = json.loads(subprocess.run(["ffprobe.exe", "-v", "error", "-print_format", "json", 
                                        "-show_format", "-show_streams", self.file],
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT,
                                        shell = True).stdout)
        self.mediaInfoOut = json.loads(subprocess.run(["MediaInfo.exe", "--Output=JSON", self.file], 
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT,
                                        shell = True).stdout)
        #  this is messy and should be rewrote cuz there better ways to do this
        if self.ffmpegInfoOut["streams"][0]["codec_type"] == 'video':
            self.ffmpegVidStrNum = 0
            self.ffmpegAudStrNum = 1
        elif self.ffmpegInfoOut["streams"][0]["codec_type"] == 'audio':
            self.ffmpegVidStrNum = 1
            self.ffmpegAudStrNum = 0
        
        self.upperVideoSizeMegabyte = 6
        self.upperVideoSize = (self.upperVideoSizeMegabyte*8*1024*1024) #megabits
        #self.preferedUpperVideoSize = self.upperVideoSize if self.upperVideoSize < (a:=os.path.getsize(self.file)*8) else a
        self.commonAudioValues = [0,1,6,8,14,16,22,24,32,40,48,64,96,112,160,192,510]
        #  video size
        self.videoWidth = float(self.ffmpegInfoOut["streams"][self.ffmpegVidStrNum]["width"])
        self.videoHeight = float(self.ffmpegInfoOut["streams"][self.ffmpegVidStrNum]["height"])
        self.videoXYRatio = self.videoWidth/self.videoHeight
        self.targetVideoWidth = float(0)
        self.targetVideoHeight = float(0)
        self.originalAudioCodec = str(self.ffmpegInfoOut["streams"][self.ffmpegAudStrNum]["codec_name"])

        # initialize first couple set of values
        self.setSourceTime()
        self.setSourceAudioBitrate()
        self.setSourceVideoBitrate()
        self.setUsedTime(self.startTime, self.endTime)
        self.setTargetAudioVideoBitrate()
        self.setAlteredAudioVideoBitrate(-1)
        self.setTargetVideoSize()
        self.setAlteredVideoSize(self.targetVideoWidth, self.targetVideoHeight)

    def setFile(self, file):
        self.file = file
        print(self.file)
        self.outFile = self.file+"-1" #also sets out file just in case

    def setUpperVideoSize(self, sizeMB:float) -> None:
        self.upperVideoSize = (sizeMB*8*1024*1024)
        return()

    def setSourceTime(self):
        self.startTime = float(self.ffmpegInfoOut["format"]["start_time"]) # sometimes things out a slightly higher number then 0
        self.startTime = float(0) # so correct them and use 0
        self.endTime = float(self.ffmpegInfoOut["format"]["duration"])
        self.duration = float(self.endTime-self.startTime)
        print("--duration--"+str(self.duration))
        return()

    def setSourceAudioBitrate(self) -> None:
        #if "duration" in self.ffmpegInfoOut["streams"][1]:
        #            self.audioTime = float(self.ffmpegInfoOut["streams"][1]["duration"])
        #else:
        #    self.audioTime = float(self.mediaInfoOut["media"]["track"][2]["Duration"])

        if "bit_rate" in self.ffmpegInfoOut["streams"][self.ffmpegAudStrNum]:
            self.audioBitrate = float(self.ffmpegInfoOut["streams"][self.ffmpegAudStrNum]["bit_rate"])/1000
        elif "BitRate" in self.mediaInfoOut["media"]["track"][2]:
            self.audioBitrate = float(self.mediaInfoOut["media"]["track"][2]["BitRate"])/1000
        else:
            self.tempFoldername = tempFoldername
            #  copy audio stream with same conatiner into temp folder
            self.tempFile = os.path.join(self.tempFoldername, ("audio"+os.path.basename(self.file)))
            self.audioSeperate = subprocess.run(["ffmpeg", "-y", "-i", self.file, "-vn", "-acodec", "copy", self.tempFile],
                                                stdout = subprocess.PIPE,
                                                stderr = subprocess.STDOUT)
            self.audioFileSize = os.path.getsize(self.tempFile)*8 #bytes to bits
            self.audioBitrate = float(self.audioFileSize/self.duration)/1000 # bits to kilobits (a second)
            os.remove(self.tempFile)
        print("--audio bitrate--"+str(self.audioBitrate))
        return()
    
    def setSourceVideoBitrate(self) -> None:
        if "bit_rate" in self.ffmpegInfoOut["streams"][self.ffmpegVidStrNum]:
            self.videoBitrate = float(self.ffmpegInfoOut["streams"][self.ffmpegVidStrNum]["bit_rate"])/1000
        else:
            self.videoBitrate = (float(self.mediaInfoOut["media"]["track"][0]["OverallBitRate"]) - (self.audioBitrate*1000))/1000
        #videoBitrate = 99999999 if b"N/A" in videoBitrate else float(videoBitrate)/1000
        print("--videoBitrate--"+str(self.videoBitrate))
        return()

    def setUsedTime(self, start, end) -> None:
        self.usedStartTime = min(max(start, self.startTime), end+1)
        self.usedEndTime = max(min(end, self.endTime), start+1, self.startTime)
        self.usedDuration = float(self.usedEndTime-self.usedStartTime)
        #print("--usedStartTime--"+str(self.usedStartTime))
        #print("--usedEndTime--"+str(self.usedEndTime))
        #print("--usedDuration--"+str(self.usedDuration))

    #this one NEEDS to be changed (its very cringe)
    def setTargetAudioVideoBitrate(self) -> None:
        self.targetAudioBitrate = self.audioBitrate
        if (self.targetAudioBitrate*self.usedDuration)*1024 > self.upperVideoSize:
            for a in self.commonAudioValues[::-1]:
                if a*self.usedDuration*1024 < self.upperVideoSize:
                    self.targetAudioBitrate = a
                    break
        print("--targetAudioBitrate--"+str(self.targetAudioBitrate))

        self.targetVideoBitrate = self.videoBitrate
        # try to make spookie bitrates not rattle everytthing else
        if 1.45 < (self.targetVideoBitrate/(self.videoHeight+self.videoWidth)):
            self.targetVideoBitrate = ((self.videoHeight+self.videoWidth)*1.45)

        #min max the bitrate with the input video stream bitrate and the max size (minus audio stream)
        self.targetVideoBitrate = a if (a := (self.upperVideoSize / (1000 * self.usedDuration)) - self.targetAudioBitrate) < self.targetVideoBitrate else self.targetVideoBitrate
        #self.targetVideoBitrate = (self.preferedUpperVideoSize / ((1000 * self.videoLength)- self.audioBitrate))
        #self.bitrateDifference = self.targetVideoBitrate/self.videoBitrate
        print("--targetVideoBitrate--"+str(self.targetVideoBitrate))
        return()

    def setAlteredAudioVideoBitrate(self, precentage) -> None:
        self.audioUsagePrecentage = precentage
        if not self.audioUsagePrecentage == -1:
            #whole numbers (too lazy to do math properly
            self.alteredAudioBitrate = int(float(self.targetAudioBitrate+self.targetVideoBitrate)*float(self.audioUsagePrecentage))
            self.alteredVideoBitrate = int((self.targetAudioBitrate+self.targetVideoBitrate)-float(self.alteredAudioBitrate))
            #print("--alteredAudioBitrate--"+str(self.alteredAudioBitrate))
            #print("--alteredVideoBitrate--"+str(self.alteredVideoBitrate))
        elif self.audioUsagePrecentage == -1:
            self.alteredAudioBitrate = self.targetAudioBitrate
            self.alteredVideoBitrate = self.targetVideoBitrate
        self.bitrateDifference = self.alteredVideoBitrate/self.videoBitrate
        return()

    def setTargetVideoSize(self) -> None:
        self.targetVideoWidth = (self.videoWidth * self.bitrateDifference) + 280
        self.targetVideoHeight = self.targetVideoWidth / self.videoXYRatio
        #self.targetVideoWidth = a if (a if (a:=((targetVideoBitrate/100)*145)) > 280 else 280) < self.targetVideoWidth else self.targetVideoWidth
        #if (self.targetVideoBitrate/(self.videoHeight+self.videoWidth)) > 1:
        print((self.targetVideoBitrate/(self.targetVideoHeight*self.targetVideoWidth*8)))
        print("--targetVideoSize--"+str(self.targetVideoWidth)+"x"+str(self.targetVideoHeight))
        return()
    
    def setAlteredVideoSize(self, videoX:int, videoY:int, maxAtSource:bool=True, maintainOriginalRatio:bool=True) -> None:
        #print((self.alteredVideoBitrate/self.targetVideoBitrate))
        self.alteredVideoWidth = videoX #*(self.alteredVideoBitrate/self.targetVideoBitrate)
        #print(self.alteredVideoWidth)
        if maxAtSource == True:
            self.alteredVideoWidth = min(self.alteredVideoWidth, self.videoWidth)

        if maintainOriginalRatio == True:
            self.alteredVideoHeight = self.alteredVideoWidth/self.videoXYRatio
        elif maintainOriginalRatio == False:
            self.alteredVideoHeight = videoY
        #self.alteredVideoWidth, self.alteredVideoHeight = round(self.alteredVideoWidth), round(self.alteredVideoHeight)
        print("--alteredVideoSize--"+str(self.alteredVideoWidth)+"x"+str(self.alteredVideoHeight))
        return()

    def setNumberOfFrames(self) -> None:
        self.frameCount = float(json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                                                            "-show_entries", "stream=nb_read_packets", 
                                                            "-of", "csv=p=0", "-of", "json", self.file], 
                                                            stdout=subprocess.PIPE,
                                                            stderr = subprocess.STDOUT).stdout)['streams'][0]['nb_read_packets'])
        return()

    def setAudioMuteFlag(self, mute:bool) -> None:
        self.audioMute = mute
        return()
    
    def setCustomResolutionFlag(self, resolutionFlag:bool) -> None:
        self.customResolutionFlag = resolutionFlag
        return()

    def setOutFile(self, outFile:str) -> None:
        self.outFile = outFile
        return()

    def setOutFileEndging(self, ending:str) -> None:
        self.fileEnding = ending
        return()

    def getFile(self) -> str:
        return(self.file)

    def getSourceTime(self) -> float:
        return(self.startTime, self.endTime, self.duration)

    def getSourceAudioBitrate(self) -> float:
        return(self.audioBitrate)

    def getSourceVideoBitrate(self) -> float:
        return(self.videoBitrate)

    def getUsedTime(self) -> float:
        return(self.usedStartTime, self.usedEndTime)

    def getTargetAudioVideoBitrate(self) -> float:
        return(self.targetAudioBitrate, self.targetVideoBitrate)

    def getTargetVideoSize(self) -> float:
        return(self.targetVideoWidth, self.targetVideoHeight, self.bitrateDifference)

    def getAlteredAudioVideoBitrate(self) -> float:
        return(self.alteredAudioBitrate, self.alteredVideoBitrate)

    def getAudioUsagePrecentage(self) -> float:
        return(self.audioUsagePrecentage)

    def getAlteredVideoSize(self) -> int:
        return(self.alteredVideoWidth, self.alteredVideoHeight, (self.alteredVideoWidth/self.alteredVideoHeight))

    def getNumberOfFrames(self) -> float:
        return(self.frameCount)

    def getOutFile(self) -> str:
        return(self.outFile)

    def getOutFileEndging(self) -> str:
        return(self.fileEnding)

    def getCustomResolutionFlag(self) -> bool:
        return(self.customResolutionFlag)

    #  --EVERYTHING FROM THIS POINT FORWARD IS FOR ENCODING ONLY--
    def getEncodeStatus(self) -> float:
        return(self.encodeStage, self.haltEncodeFlag, self.taskStats)

    def startEncode(self):
        encodeThread = Thread(target=valueTings.encode)
        encodeThread.start()

    def haltEncode(self):
        self.haltEncodeFlag = True

    def encodeHandler(self, process):
        if self.haltEncodeFlag == False:
            self.queue = [0]
            self.encodePassProcessReader = Thread(target=self.encodeProcessReader, args=(process,))
            self.encodePassProcessReader.start()
            self.setNumberOfFrames()
            self.totalFrames = self.getNumberOfFrames()
            while (process.poll() is None) and (self.haltEncodeFlag == False):
                self.taskStats["encodePrecent"] = (self.queue[0]/self.totalFrames)*100
            process.stdout.close()
            self.encodePassProcessReader.join()
            if self.haltEncodeFlag == False:
                process.wait()
        process.kill()

    def encodeProcessReader(self, process):
        while process.poll() is None and not self.haltEncodeFlag:
            progressText = process.stdout.readline()
            #print(progressText)
            if progressText is None:
                break
            # should be rewriten later to not be all if else (yanderedev level garbage)
            progressText = progressText.decode("utf-8").strip().replace(" ", "")
            try:
                if progressText.startswith("frame="):
                    self.queue[0] = int(progressText.partition('=')[-1])
                elif progressText.startswith("fps="):
                    self.taskStats["fps"] = float(progressText.partition('=')[-1])
                elif progressText.startswith("bitrate="):
                    self.taskStats["bitrate"] =  progressText.partition('=')[-1]
                elif progressText.startswith("total_size=") and (not "N/A" in progressText):
                    self.taskStats["totalSize"] = int(progressText.partition('=')[-1])
                elif progressText.startswith("out_time_ms="):
                    self.taskStats["outTime"] = int(progressText.partition('=')[-1])
                    if self.taskStats["outTime"] < 0:
                        self.taskStats["outTime"] = 0
                elif progressText.startswith("dup_frames="):
                    self.taskStats["dumpedFrames"] = int(progressText.partition('=')[-1])
                elif progressText.startswith("drop_frames="):
                    self.taskStats["dropedFrames"] = int(progressText.partition('=')[-1])
                elif progressText.startswith("speed=") and (not "N/A" in progressText):
                    self.taskStats["speed"] = progressText.partition('=')[-1]
            except ValueError as err:
                print(err)
                print("THREW ENCODE STATS FROM MALFORMED OUTPUT")

    def encode(self):
        self.haltEncodeFlag = False
        self.encodeStage = 0
        self.videoEncoder = "libvpx-vp9"
        self.audioCodec = "libopus"
        self.taskStats = {"encodePrecent":0, "fps":0, "bitrate":"", "totalSize":0, "outTime":0, "dumpedFrames":0, "dropedFrames":0, "speed":""}
        self.alteredAudioBitrate, self.alteredVideoBitrate = valueTings.getAlteredAudioVideoBitrate()
        #valueTings.setAlteredVideoSize(valueTings.getTargetVideoSize()[0:2])
        self.videoX, self.videoY, self.bitDiff = valueTings.getAlteredVideoSize()

        self.starterEncodeInfo = ["ffmpeg.exe", "-y", "-loglevel", "error", "-i", self.file]
        self.videoEncodeInfo = ["-b:v", f"{self.alteredVideoBitrate}k", "-pix_fmt", "yuv420p",
                                "-c:v",  self.videoEncoder, "-maxrate", f"{self.alteredVideoBitrate*0.8}k", 
                                "-bufsize", f"{self.alteredVideoBitrate*0.8*2}k", "-minrate", "0k",
                                "-vf", f"scale={self.videoX}:{self.videoY}:flags=lanczos", "-aspect", f"{self.videoX}:{self.videoY}", "-ss", f"{self.usedStartTime}", "-to", f"{self.usedEndTime}",
                                "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "24",
                                "-threads", "0", "-row-mt", "1"]
        self.audioEncodeInfo = ["-c:a", self.audioCodec, "-b:a", f"{self.alteredAudioBitrate}k", "-frame_duration", "20"]
        if self.audioMute == True:
            self.audioEncodeInfo = ["-an"] # I guess theres a way to do this better with -map but I can't be bothered for the time
        elif "opus" in self.originalAudioCodec and int(self.audioBitrate) == self.alteredAudioBitrate: #copy source audio track if same bitrate and codec
            self.audioEncodeInfo = ["-c:a", "copy"] #tags if coppied for no reason

        self.encodeStage = 1
        self.videoPass1 = subprocess.Popen(self.starterEncodeInfo+self.videoEncodeInfo+[
                                            "-pass", "1", "-progress", "pipe:1", "-an", "-f", "null", "NUL"], 
                                            stdout=subprocess.PIPE,
                                            stderr = subprocess.STDOUT,
                                            shell = True)
        self.encodeHandler(self.videoPass1)

        self.encodeStage = 2
        self.stage2EncodeFlags = self.starterEncodeInfo + self.videoEncodeInfo + self.audioEncodeInfo
        self.videoPass2 = subprocess.Popen(self.stage2EncodeFlags+[
                                            "-map_metadata", "0", "-metadata:s:v:0", f"BPS={self.alteredVideoBitrate}", # meaningless BPS tag that **might** work with matroska
                                            "-metadata:g", f"encoding_tool=no7macs video-bottler",
                                            "-pass", "2", "-progress", "pipe:1",
                                            f"{self.outFile}"], 
                                            stdout=subprocess.PIPE,
                                            stderr = subprocess.STDOUT,
                                            shell = True)
        self.encodeHandler(self.videoPass2)
        self.encodeStage = 3


class ytdlpDownloader:
    def __init__(self, url, folder):
        self.tempFolder = folder
        self.url = url
        self.debug = ""
        self.info = ""
        self.warning = ""
        self.err = ""

    class MyLogger:
        def debug(self, msg):
            if msg.startswith('[debug] '): # debug
                pass
            else: # info 
                self.info(msg)
        def info(self, msg):
            #print(msg)
            pass
        def warning(self, msg):
            pass
        def error(self, msg):
            self.err = msg
            print(msg)

    def ytdlpHandler(self):
        ydl_opts = {
            'outtmpl':f"""{self.tempFolder}/%(title)s-%(id)s.%(ext)s""",
            'cookiefile':'./cookies.txt',
            'logger': self.MyLogger(),
            'noplaylist': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            #  needs to check if it's none and raise some kind of error/ message (should be done after this bits threaded)
            #  also there are just errors and other things different places throw that should be handled
            ydl.download(self.url)

    def download(self):
        self.ytdlpHandler()
        return(os.path.join(self.tempFolder, os.listdir(self.tempFolder)[0]))


# drag and drop exists in here for now, should revisit later and cleaned up
class selectFileWindow(TkinterDnD.Tk):
    def __init__(self, *args, **kwargs):
        TkinterDnD.Tk.__init__(self, *args, **kwargs)
        self.title("Video Bottler")
        self.lift()
        #customtkinter.set_appearance_mode("system")
        self.file = ""
        #customtkinter.set_widget_scaling(1000)
        #customtkinter.set_window_scaling(1000)
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', lambda a:self.setFile(a.data))
        self.fileSelectFrame()
        self.fileDownloadFrame()
        self._job = self.after(100, self.fileSelectEverntLoop)
        self.mainloop()

    def fileSelectEverntLoop(self) -> None: #also checks if enter was pressed
        if keyboard.is_pressed("enter") and not self.downloadEntry.get() == "":
            self.downloadFromUrl()
        if not self.file == "" and os.path.exists(self.file):
            valueTings.setFile(self.file)
            valueTings.setDefaults()
            self.destroy()
            self.after_cancel(self._job)
            self._job = None
            mainWindow()
        self._job = self.after(1, self.fileSelectEverntLoop)

    def setFile(self, file): # drag and drop file set
        self.file=file.replace("{","").replace("}","")
        #self.checkFile()
        self.drop_target_unregister()
        self.drop_target_register(DND_FILES)

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
        self.downloadButton = Button(self.downloadFileFrame, text="Download", command=self.downloadFromUrl)
        self.downloadButton.grid(row=2, column=0)
        self.tk.call("focus", self.downloadEntry)

    def browseForFiles(self):
        self.file = filedialog.askopenfilename(initialdir = "/", title = "Select a File",
                                                filetypes = (("Video",["*.webm*","*.mp4*","*.mov*","*.m4a*"]), ("all files", "*.*")))
        self.fileSelectEverntLoop()

    def downloadFromUrl(self):
        self.tempFoldername = tempFoldername
        for a in os.listdir(self.tempFoldername): #clean temp dir because i'm too lazy to get a filename from ytdlp
            os.remove(os.path.join(self.tempFoldername, a))
        ytdlp = ytdlpDownloader(self.downloadEntry.get(), self.tempFoldername)
        self.file = ytdlp.download()
        self.fileSelectEverntLoop()


class upperSizeChanger(Frame):
    def __init__(self, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)
        self.customResolutionDropdownLabel = Label(self, text="File size:")
        self.customResolutionDropdownLabel.grid(row=0, column=0)
        self.dropdownOptions = ["6mb 4chan", "8mb Discord (old)", "25mb Discord", "50mb Discord premium", "500mb Discord nitro", "Custom"]
        self.optionSizes = [6, 8, 25, 50, 500]
        self.dropdownStringVar = StringVar()
        self.dropdownStringVar.set(self.dropdownOptions[0])
        self.fileSizeDropdown = OptionMenu(self, self.dropdownStringVar, *self.dropdownOptions, command=self.changeSize)
        self.fileSizeDropdown.grid(row=0, column=1)

    def changeSize(self, *args):
        self.chosenOptionListIndex = self.dropdownOptions.index(args[0])
        valueTings.setUpperVideoSize(sizeMB=self.optionSizes[self.chosenOptionListIndex])

        valueTings.setSourceTime()
        valueTings.setSourceAudioBitrate()
        valueTings.setSourceVideoBitrate()

        valueTings.setTargetAudioVideoBitrate()
        valueTings.setAlteredAudioVideoBitrate(-1)
        valueTings.setTargetVideoSize()
        

#  unused but should replace timeChangeEntries later
class timeEntry(Frame):
    def __init__(self, textvariable, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)
        self.textVariable = textvariable
        self.hourVar = StringVar()
        self.minVar = StringVar()
        self.secVar = StringVar()
        self.millisecVar = StringVar()
        self.hourEntry = Entry(self, textvariable=self.hourVar, border=0)
        self.hourEntry.grid(column=0, row=0)
        Label(self, text=":").grid(column=1, row=0)
        self.minEntry = Entry(self, textvariable=self.minVar, border=0)
        self.minEntry.grid(column=2, row=0)
        Label(self, text=":").grid(column=3, row=0)
        self.secEntry = Entry(self, textvariable=self.secVar, border=0)
        self.secEntry.grid(column=4, row=0)
        self.secVar.trace_add("write", self.secCheck)

    def secCheck(self, *args):
        if int(self.secVar.get()) >= 60:
            pass
    def set(self, time) -> None:
        return()

    def get(self) -> int:
        return()


class timeChangeEntries(Frame):
    def __init__(self, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)
        #timeEntry(self).grid(column=21,row=2)
        self.usedStartTime, self.usedEndTime = valueTings.getUsedTime()
        self.startTimeStringVar = StringVar()
        self.endTimeStringVar = StringVar()
        self.startTimeStringVar.set(self.usedStartTime)
        self.endTimeStringVar.set(self.usedEndTime)
        self.startTimeStringVar.trace_add("write", self.changeTime)
        self.endTimeStringVar.trace_add("write", self.changeTime)
        self.startTimeLabel = Label(self, text="Start:")
        self.startTimeLabel.grid(column=0, row=0)
        self.startTimeEntry = Entry(self, textvariable=self.startTimeStringVar)
        self.startTimeEntry.grid(column=1, row=0)
        self.endTimeLabel = Label(self, text="Stop:")
        self.endTimeLabel.grid(column=2, row=0)
        self.endTimeEntry = Entry(self, textvariable=self.endTimeStringVar)
        self.endTimeEntry.grid(column=3, row=0)
        self.startTimeEntry.bind("<FocusOut>", self.defocusInputs)
        self.endTimeEntry.bind("<FocusOut>", self.defocusInputs)
        #self.defaultTimeVar = IntVar()
        #self.useDefaultCheckBox = Checkbutton(self, text="Use default", variable=self.defaultTimeVar, onvalue=1, offvalue=0, command=self.toggleDefaultUsage)
        #self.useDefaultCheckBox.grid(column=4, row=0)

    def changeTime(self, *args):
        print(args)
        #self.startTimeStringVar.set(re.sub("^.*?\.[^.]*.", "", (self.startTimeStringVar.get())))
        print(self.startTimeStringVar.get())
        if (not self.startTimeStringVar.get() == '') and (not self.endTimeStringVar.get() == ''):
            valueTings.setUsedTime(float(self.startTimeStringVar.get()), float(self.endTimeStringVar.get()))
            valueTings.setTargetAudioVideoBitrate()
            valueTings.setTargetVideoSize()
            valueTings.setAlteredAudioVideoBitrate(valueTings.getAudioUsagePrecentage())
            videoX, videoY = valueTings.getTargetVideoSize()[0:2]
            if not valueTings.getCustomResolutionFlag():
                valueTings.setAlteredVideoSize(videoX, videoY)
            self.master.videoaudioBitrateSlider.setDefaults() #  namespace is a lie

    def defocusInputs(self, *args):
        self.changeTime()
        self.startTimeEntry.delete(0, END)
        self.startTimeEntry.insert(0, valueTings.getUsedTime()[0])
        self.endTimeEntry.delete(0, END)
        self.endTimeEntry.insert(0, valueTings.getUsedTime()[1])

    def resetToDefault(self):
        self.startTimeStringVar.set(self.usedStartTime)
        self.endTimeStringVar.set(self.usedEndTime)


class resolutionChangeEntries(Frame):
    def __init__(self, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)
        self.customResolutionCheckbuttonLabel = Label(self, text="Custom Resolution")
        self.customResolutionCheckbuttonLabel.grid(row=0, column=0)
        self.customResolution = IntVar()
        self.customSizeCheckbox = Checkbutton(self, variable=self.customResolution, onvalue=1, offvalue=0, command=self.customAudioToggle)
        self.customSizeCheckbox.grid(row=0, column=1)
        self.widthStringVar = StringVar()
        self.heightStringVar = StringVar()
        self.widthStringVar.trace_add("write", self.changeResolution)
        self.heightStringVar.trace_add("write", self.changeResolution)
        self.widthEntryLabel = Label(self, text="Width:")
        self.widthEntryLabel.grid(row=0, column=2)
        self.widthEntry = Entry(self, textvariable=self.widthStringVar, state="disabled")
        self.widthEntry.grid(row=0, column=3)
        self.heightEntryLabel = Label(self, text="Height:")
        self.heightEntryLabel.grid(row=0, column=4)
        self.heightEntry = Entry(self, textvariable=self.heightStringVar, state="disabled")
        self.heightEntry.grid(row=0, column=5)
        self.widthEntry.bind("<FocusOut>", self.defocusInputs)
        self.heightEntry.bind("<FocusOut>", self.defocusInputs)
        valueTings.setCustomResolutionFlag(False)

    def changeResolution(self, *args) -> None:
        print(args)
        self.widthStringVar.set(re.sub("[^0-9]", "", (self.widthStringVar.get())))
        self.heightStringVar.set(re.sub("[^0-9]", "", (self.heightStringVar.get())))
        if (not self.widthStringVar.get() == '') and (not self.heightStringVar.get() == ''):
            valueTings.setAlteredVideoSize(videoX=int(self.widthStringVar.get()), videoY=int(self.heightStringVar.get()), maintainOriginalRatio=False)

    def updateResolutionIfNotCustom(self, width, height) -> None:
        if self.customResolution.get() == 0:
            self.widthStringVar.set(str(round(width)))
            self.heightStringVar.set(str(round(height)))

    def customAudioToggle(self):
        if self.customResolution.get() == 0:
            self.widthEntry.config(state="disabled")
            self.heightEntry.config(state="disabled")
            valueTings.setCustomResolutionFlag(False)
        elif self.customResolution.get() == 1:
            self.widthEntry.config(state="normal")
            self.heightEntry.config(state="normal")
            valueTings.setCustomResolutionFlag(True)

    def defocusInputs(self, *args):
        self.changeResolution()
        self.widthEntry.delete(0, END)
        self.widthEntry.insert(0, valueTings.getAlteredVideoSize()[0])
        self.heightEntry.delete(0, END)
        self.heightEntry.insert(0, valueTings.getAlteredVideoSize()[1])


# needs to be redone to use ONLY altered variables and readjust on time change
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
        # no I will not fix it right now
        if self.snapToCommonAudio == True:
            self.snapedRatio = min([a/(self.alteredAudioBitrate+self.alteredVideoBitrate) for a in [0,1,6,8,14,16,22,24,32,40,48,64,96,112,160,192,510]],key=lambda x:abs(x-float(bitrateRatio)))
            self.bitrateRatioSlider.set(self.snapedRatio)
            bitrateRatio = self.bitrateRatioSlider.get()
        self.audioBitrateLabel.place(x=(((self.bitrateRatioSlider.coords()[0])/2)))
        self.videoBitrateLabel.place(x=((self.bitrateRatioSlider.coords()[0]+self.bitrateRatioSlider.cget("length")-self.videoBitrateLabel.winfo_width())/2))
        valueTings.setAlteredAudioVideoBitrate(bitrateRatio)
        valueTings.setTargetVideoSize()
        #  will have to change somewhere else, I don't want to break namespace again (I have enough nightmares as is)
        if not valueTings.getCustomResolutionFlag():
            videoX, videoY = valueTings.getTargetVideoSize()[0:2]
            valueTings.setAlteredVideoSize(videoX, videoY)
            videoX, videoY = valueTings.getAlteredVideoSize()[0:2]
            self.master.resolutionChangeFrame.updateResolutionIfNotCustom(videoX, videoY)
        #print(valueTings.getTargetVideoSize())
        self.alteredAudioBitrate, self.alteredVideoBitrate = valueTings.getAlteredAudioVideoBitrate()
        self.audioBitrateLabel["text"] = str(int(self.alteredAudioBitrate))+"kb/s"
        self.videoBitrateLabel["text"] = str(int(self.alteredVideoBitrate))+"kb/s"
        if self.alteredAudioBitrate <= 0:
            valueTings.setAudioMuteFlag(True)
        elif self.alteredAudioBitrate > 0:
            valueTings.setAudioMuteFlag(False)
        #self._job = self.after(1000, self.bitrateRatioSliderUpdate(bitrateRatio))

    def setDefaults(self) -> None:
        valueTings.setAlteredAudioVideoBitrate(-1)
        self.alteredAudioBitrate, self.alteredVideoBitrate = valueTings.getAlteredAudioVideoBitrate()
        #self.targetAudioBitrate, self.targetVideoBitrate = valueTings.getTargetAudioVideoBitrate()
        self.audioBitrateLabel["text"] = str(int(self.alteredAudioBitrate))+"kb/s"
        self.videoBitrateLabel["text"] = str(int(self.alteredVideoBitrate))+"kb/s"
        self.audioUsagePrecentage = self.alteredAudioBitrate/(self.alteredAudioBitrate+self.alteredVideoBitrate)
        valueTings.setAlteredAudioVideoBitrate(self.audioUsagePrecentage)
        self.bitrateRatioSlider.set(self.audioUsagePrecentage)

    def snapToCommonAudioValues(self, state:bool) -> None:
        self.snapToCommonAudio = state


class mainWindow(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.title("Video Bottler")
        self.lift()
        self.changeSizeFrame = upperSizeChanger(self)
        self.changeSizeFrame.grid(row=1, column=0, sticky=W)
        self.changeDurationFrame = timeChangeEntries(self)
        self.changeDurationFrame.grid(row=2, column=0, sticky=W)
        self.resolutionChangeFrame = resolutionChangeEntries(self)
        self.resolutionChangeFrame.grid(row=3, column=0, sticky=W)
        self.snapToAudio = IntVar()
        self.snapToAudioValuesBox = Checkbutton(self, text="Snap to common audio bitrates", variable=self.snapToAudio, onvalue=1, offvalue=0, command=lambda:self.videoaudioBitrateSlider.snapToCommonAudioValues(state=bool(self.snapToAudio.get())))
        self.snapToAudioValuesBox.grid(row=4, column=0, sticky=W)
        self.videoaudioBitrateSlider = bitrateSlider(self)
        self.videoaudioBitrateSlider.grid(row=5, column=0)
        self.sliderResetDefaultsButton = Button(self, text = "Reset", command=self.resetAll)
        self.sliderResetDefaultsButton.grid(row=6, column=0, sticky=W)
        #self.statusLabel = Label(self, text="")
        #self.statusLabel.pack(anchor=W)
        self.buttonFrame = Frame(self)
        self.buttonFrame.grid(row=7, column=0, sticky=E)
        self.encodeButton = Button(self.buttonFrame, text="encode", command=self.startEncode, width=25)
        self.encodeButton.grid(row=0, column=0)
        self.protocol("WM_DELETE_WINDOW", self.onClose)
        self.bind_all("<Button-1>", lambda event: (self.tk.call("focus", self) if not event.widget.winfo_class() == 'Entry' else event.widget.focus_set()))
        self.mainloop()

    def resetAll(self):
        self.videoaudioBitrateSlider.setDefaults()
        self.changeDurationFrame.resetToDefault()

    def onClose(self):
        #if tkinter.messagebox.askokcancel("Exit", "Do you want to quit?"):
        self.destroy()
        selectFileWindow()

    def startEncode(self):
        self.destroy()
        encodeStatusWindow()


class encodeStatusWindow(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.title("Video Bottler")
        self.lift()
        self.encodeStatFrame = Frame(self)
        self.encodeStatFrame.pack(anchor=W)

        self.fpsLabel = Label(self.encodeStatFrame, text="")
        self.fpsLabel.pack(anchor=W)
        self.bitrateLabel = Label(self.encodeStatFrame, text="")
        self.bitrateLabel.pack(anchor=W)
        self.totalSizeLabel = Label(self.encodeStatFrame, text="")
        self.totalSizeLabel.pack(anchor=W)
        self.outTimeLabel = Label(self.encodeStatFrame, text="")
        self.outTimeLabel.pack(anchor=W)
        #self.dumpedFramesLabel = Label(self.encodeStatFrame, text="")
        #self.dumpedFramesLabel.pack(anchor=W)
        #self.dropedFramesLabel = Label(self.encodeStatFrame, text="")
        #self.dropedFramesLabel.pack(anchor=W)
        self.speedLabel = Label(self.encodeStatFrame, text="")
        self.speedLabel.pack(anchor=W)

        self.encodeStatusMessage = Label(self, text="Status: ")
        self.encodeStatusMessage.pack(anchor=W)
        self.encodeProgressBar = Progressbar(self, orient=HORIZONTAL, length=500, mode='determinate')
        self.encodeProgressBar.pack(anchor=W)
        self.actionButtonsFrame = Frame(self)
        self.actionButtonsFrame.pack(anchor=W)
        self.cancelButton = Button(self, text="Cancel", command=valueTings.haltEncode)
        self.doneButton = Button(self, text="Done", command=self.done)
        self.exitButton = Button(self, text="Exit", command=self.exit)
        self.protocol("WM_DELETE_WINDOW", self.done)

        self.outFile = filedialog.asksaveasfilename(title="save as", initialdir=os.path.dirname(valueTings.getFile()), initialfile=f"{os.path.splitext(os.path.basename(valueTings.getFile()))[0]}-1.{valueTings.getOutFileEndging()}", filetypes=[("webm","webm")], defaultextension=".webm")
        if not self.outFile:
            self.done()
        elif self.outFile:
            valueTings.setOutFile(self.outFile)
            valueTings.startEncode()

        self._job = self.after(1, self.update)
        self.mainloop()

    def done(self):
        try:
            self.after_cancel(self._job)
        except AttributeError:
            print("no jobs to cancel")
        self._job = None
        self.destroy()
        mainWindow()

    def exit(self):
        self.destroy()

    def update(self):
        # {"encodePrecent":0, "fps":0, "bitrate":"", "totalSize":0, "outTime":0, "dumpedFrames":0, "dropedFrames":0, "speed":""}
        self.encodeStage, self.haltEncodeFlag, self.taskStatus = valueTings.getEncodeStatus()

        self.fpsLabel["text"] = "fps: "+str(self.taskStatus["fps"])
        self.bitrateLabel["text"] = "bitrate: "+self.taskStatus["bitrate"]
        self.totalSizeLabel["text"] = "file size: "+str(round(self.taskStatus["totalSize"]/1024/1024,3))+"mb"
        self.outTimeLabel["text"] = "video length: "+str(round(self.taskStatus["outTime"]/1000/1000,2))+"sec"
        #self.dumpedFramesLabel["text"] = "dumped frames: "+str(self.taskStatus["dumpedFrames"])
        #self.dropedFramesLabel["text"] = "droped frames: "+str(self.taskStatus["dropedFrames"])
        self.speedLabel["text"] = "speed: "+self.taskStatus["speed"]
        
        if self.haltEncodeFlag == True: #check if cancel flag has been set
            self.encodeStatusMessage["text"] = "Status: Canceling"
            if self.encodeStage == 3: # if it fully closed out of encoding, setting the status to 3 (final thing it does)
                self.encodeStatusMessage["text"] = "Status: Canceled"
                self.encodeProgressBar["value"] = 100
        elif self.encodeStage == 1:
            self.encodeStatusMessage["text"] = "Status: Pass 1 of 2"
            self.encodeProgressBar["value"] = self.taskStatus["encodePrecent"]
        elif self.encodeStage == 2:
            self.encodeStatusMessage["text"] = "Status: Pass 2 of 2"
            self.encodeProgressBar["value"] = self.taskStatus["encodePrecent"]
        elif self.encodeStage == 3:
            self.encodeStatusMessage["text"] = "Status: Done"
            self.encodeProgressBar["value"] = 100

        if self.encodeStage < 3 and self.cancelButton.winfo_ismapped() == 0:
            self.cancelButton.pack(side=RIGHT)
        elif self.encodeStage == 3:
            self.cancelButton.pack_forget()
        if self.encodeStage == 3 and self.exitButton.winfo_ismapped() == 0 and self.doneButton.winfo_ismapped() == 0:
            self.exitButton.pack(side=RIGHT)
            self.doneButton.pack(side=RIGHT)
        self._job = self.after(100, self.update)


def main():
    pass

if __name__ == "__main__":
    with tempFileName() as tempFoldername:
        meipass = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        sys.path.append(meipass) #pyinstaller tempdir
        os.chdir(meipass)

        print(meipass)
        valueTings = encodeAndValue()
        print(sys.path)
        # file select
        print(sys.argv)
        if len(sys.argv) >= 2:
            valueTings.setFile(sys.argv[1])
            valueTings.setDefaults()
            mainWindow()
        else:
            selectFileWindow()