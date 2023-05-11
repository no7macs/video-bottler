import subprocess
import sys
import os
import time
import json

#file = "./vidya/0op.mp4"
#file = sys.argv[1]
file = "./Season 5 Trailer [2327495449].mp4"
#file = "./Alberto Balsalm Cover With The Wrong Instruments [-Eq9cpb6-8I]-1.webm"

#Calculate the video bitrate to meet the file size ( megabyte-limit * 8 * 1024 * 1024 / (1000 * video-length-seconds) - audio-bitrate) )
# ( 6 * 8 * 1024 * 1024 / (1000 * videoLength) - audioBitrate) )
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
#  find sample rate from all frames and length from all frames, then devide both by each other
#----------------------------------------------------------------------------------------------------
#if b"N/A" not in audioBitrate:
#    print("using cunt hack")
#    manualRateList = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
#                                    "a:0", "-show_entries", "packet=size,duration",
#                                    "-of", "csv", file],
#                                    stdout = subprocess.PIPE,
#                                    stderr = subprocess.STDOUT).stdout.splitlines())
#    del manualRateList[1] 
#    print((((sum(list((float(b.split(b',')[1]) for b in manualRateList)))) / (sum(list((float(b.split(b',')[2]) for b in manualRateList)))))*1024*8)/1000)

# get audio only bitrate through the streams duration tag, devide by 1024, multiply by time, then devide by 10
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
        if "BitDepth" in mediaInfoOut["media"]["track"][2]:
            audioBitrate = float(mediaInfoOut["media"]["track"][2]["BitDepth"])
        else:
            audioBitrate = float(mediaInfoOut["media"]["track"][2]["BitRate"])/1000
    #take sample rate x nummber of channels (default 2) x 2 (bits to byts) / 100 to make kilobyte
    #audioBitrate = (4800*(float(audioChannels)if not b"N/A" in audioChannels else 2)*2)/100
    #audioBitrate = 96  
# audioBitrate = round((float(audioSampleRate)/1000)*videoLength, 3)
print("--audio bitrate--"+str(audioBitrate))

videoBitrate = (subprocess.run(["ffprobe", "-v", "quiet", "-select_streams",
                                    "v:0", "-show_entries", "stream=bit_rate", 
                                    "-of", "default=noprint_wrappers=1:nokey=1", file],
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT).stdout)
videoBitrate = (float(mediaInfoOut["media"]["track"][0]["OverallBitRate"])- (audioBitrate*1000))/1000
#videoBitrate = 99999999 if b"N/A" in videoBitrate else float(videoBitrate)/1000

#if b"N/A" in videoBitrate:
#    print("using cunt hack")
#    manualRateList = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
#                                    "v:0", "-show_entries", "packet=size,duration",
#                                    "-of", "csv", file],
#                                    stdout = subprocess.PIPE,
#                                    stderr = subprocess.STDOUT).stdout.splitlines())
#    del manualRateList[1] 
#    videoBitrate = (((sum(list((float(b.split(b',')[1]) for b in manualRateList)))) / (sum(list((float(b.split(b',')[2]) for b in manualRateList)))))*1000*8)
#else: videoBitrate = float(videoBitrate)/1000

videoSize = (subprocess.run(["ffprobe", "-v", "error", "-select_streams",
                                  "v:0", "-show_entries", "stream=width,height",
                                  "-of", "csv=s=x:p=0", file],
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.STDOUT).stdout).decode('utf-8').split('x')
videoSize[0], videoSize[1] = float(videoSize[0]), float(videoSize[1])
videoXYRatio = videoSize[0]/videoSize[1]

targetVideoBitrate = a if (a := ((20 * 8 * 1024 * 1024) / ((1000 * videoLength) - (audioBitrate)))) < videoBitrate else videoBitrate

print("--videoBitrate--"+str(videoBitrate))
print("--targetVideoBitrate--"+str(targetVideoBitrate))

#masterSizeCoor = 0 if videoXYRatio >= 1 else 0
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
                            "-threads", "8", "-row-mt", "1",
                            "-pass", "1", "-an", "-f", "null", "NUL"])

videoPass2 = subprocess.run(["ffmpeg", "-y", "-i", file, "-b:v", f"{targetVideoBitrate}k",
                            "-c:v", videoEncoder, "-maxrate", f"{targetVideoBitrate}k",
                            "-bufsize", f"{targetVideoBitrate/2}k", "-minrate", "0k",
                            "-vf", f"scale={videoSize[0]}:{videoSize[1]}",
                            "-deadline", "good", "-auto-alt-ref", "1", "-lag-in-frames", "12",
                            "-threads", "8", "-row-mt", "1",
                            "-map_metadata", "0", "-metadata:s:v:0", f"bit_rate={targetVideoBitrate}",
                            "-pass", "2", "-c:a", audioCodec, "-frame_duration", "20",
                            "-b:a", f"{audioBitrate}k",
                            f"{os.path.splitext(file)[0]}1.{fileEnding}"])