#!/usr/bin/python3

import datetime
import os
import shlex
import threading
import time
from subprocess import Popen, DEVNULL
import paho.mqtt.client as mqtt


loggingHost = "undefined"
loggingPrefix = "undefined"
loggingLock = threading.Lock()
loggingTopic = "undefined"


def configureLogging(host, prefix, topic):
  global loggingHost
  global loggingPrefix
  global loggingLock
  global loggingTopic
  loggingHost = host
  loggingPrefix = prefix
  loggingTopic = topic


def log(msg):
  msg = "[" + loggingPrefix + "] " + msg
  with loggingLock:
    print(msg)
    mqttClient = mqtt.Client()
    mqttClient.connect(loggingHost, 1883, 10)
    mqttClient.publish(loggingTopic, msg)
    mqttClient.loop(0.1)


def getSecondsSinceBoot():
  handle = open("/proc/uptime", "r")
  content = handle.read()
  t = float(shlex.split(content)[0])
  return t


def switchRasPiLedsOff():
  cmd = shlex.split("./switch_raspi_leds_off.bash")
  process = Popen(cmd, stdout=DEVNULL)
  process.communicate()
  process.wait()


def normalizePath(path):
  if (path.endswith(os.path.sep)):
    path = path[0:-1]
  return path


def renameFileIfExisting(sourcePath, targetPath, autofillDateTime=True):
  if autofillDateTime:
    now = datetime.datetime.today()
    nowDateString = "{:>04d}-{:>02d}-{:>02d}".format(now.year, now.month, now.day)
    nowTimeString = "{:>02d}-{:>02d}-{:>02d}".format(now.hour, now.minute, now.second)
    targetPath = targetPath.replace("YYYY-MM-DD", nowDateString)
    targetPath = targetPath.replace("HH-MM-SS", nowTimeString)
  if os.path.isfile(sourcePath):
    os.rename(sourcePath, targetPath)


def removeFileIfExisting(filePath):
  if os.path.isfile(filePath):
    os.remove(filePath)


def sendFileViaMQTTIfExisting(host, filePath, topic):
  if os.path.isfile(filePath):
    log("Sending file " + filePath + " on topic " + topic + " ...")
    startTime = time.time()
    cmd = shlex.split("mosquitto_pub -h " + host + " -t " + topic + " -f " + filePath)
    process = Popen(cmd)
    process.communicate()
    process.wait()
    endTime = time.time()
    duration = endTime - startTime
    rate_kBs = os.path.getsize(filePath) / 1024.0 / duration
    log("Sent file {} on topic {} in {:3.1f}s at {:3.1f}kB/s.".format(filePath, topic,
                                                                      duration, rate_kBs))


def receiveFileViaMQTT(host, topic, outputPath, timeout_s=240):
  if os.path.isfile(outputPath):
    os.remove(outputPath)
  outputHandle = open(outputPath, "w")
  cmd = "mosquitto_sub -h " + host + " -t " + topic + " -C 1 -W " + str(timeout_s)
  cmd = shlex.split(cmd)
  log("Waiting for message on topic " + topic + " for " + str(timeout_s) + "s ...")
  process = Popen(cmd, stdout=outputHandle)
  process.communicate()
  process.wait()
  outputHandle.close()
  hasReceivedFile = True
  if os.path.isfile(outputPath):
    if os.path.getsize(outputPath) == 0:
      os.remove(outputPath)
      hasReceivedFile = False
  if hasReceivedFile:
    log("Stored message from topic " + topic + " to file " + outputPath + ".")
  else:
    log("Nothing received on topic " + topic + " within " + str(timeout_s) + "s.")


def convertH264ToMP4IfExisting(inputPath, outputPath):
  if os.path.isfile(inputPath):
    log("Converting H.264 file " + inputPath + " to MP4 file ...")
    cmd = "ffmpeg -i " + inputPath + " -vcodec copy " + outputPath
    cmd = shlex.split(cmd)
    process = Popen(cmd, stdout=DEVNULL)
    process.communicate()
    process.wait()
    log("Converted H.264 file to MP4 file " + outputPath + ".")


def recordRasPiCamVideo(duration_s, outputPath):
  log("Recording video for " + str(duration_s) + "s ...")
  if os.path.isfile(outputPath):
    os.remove(outputPath)
  duration_ms = duration_s * 1000
  cmd = shlex.split("raspivid -o " + outputPath + " -t " + str(duration_ms)
                    + " -w 960 -h 720 -fps 30 -b 2000000 --profile baseline --level 4")
  process = Popen(cmd)
  process.communicate()
  process.wait()
  log("Recorded video to file " + outputPath + ".")


def recordRasPiCamImage(outputPath):
  log("Taking image now ...")
  if os.path.isfile(outputPath):
    os.remove(outputPath)
  cmd = shlex.split("raspistill -o " + outputPath + " -w 1640 -h 1232 -t 100 -q 95")
  process = Popen(cmd)
  process.communicate()
  process.wait()
  log("Stored image in file " + outputPath + ".")
