#!/usr/bin/python3

import argparse
import threading

import birdwatch_constants as bwc
import birdwatch as bw


class BirdwatchServer:

  host = "undefined"
  topic = "undefined"
  storagePath = "undefined"

  def __init__(self, host, topic, storagePath):
    self.host = host
    self.topic = topic
    self.storagePath = bw.normalizePath(storagePath)
    bw.configureLogging(self.host, bwc.LOGGING_PREFIX_SERVER, self.topic + bwc.DEBUG_SUBTOPIC)

  def receiveImageFiles(self):
    imageReceivePath = self.storagePath + "/image_tmp.jpg"
    imageStoragePath = self.storagePath + "/YYYY-MM-DD/image_YYYY-MM-DD_HH-MM-SS.jpg"
    while(True):
      bw.receiveFileViaMQTT(self.host, self.topic, imageReceivePath)
      bw.renameFileIfExisting(imageReceivePath, imageStoragePath)

  def receiveAndProcessVideoFiles(self):
    videoReceivePath = self.storagePath + "/video_tmp.h264"
    videoMP4Path = self.storagePath + "/video_tmp.mp4"
    videoStoragePath = self.storagePath + "/YYYY-MM-DD/video_YYYY-MM-DD_HH-MM-SS.mp4"
    while(True):
      bw.receiveFileViaMQTT(self.host, self.topic + bwc.VIDEO_SUBTOPIC, videoReceivePath)
      bw.convertH264ToMP4IfExisting(videoReceivePath, videoMP4Path)
      bw.renameFileIfExisting(videoMP4Path, videoStoragePath)

  def run(self):
    t1 = threading.Thread(target=self.receiveImageFiles)
    t2 = threading.Thread(target=self.receiveAndProcessVideoFiles)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def main():
  parser = argparse.ArgumentParser(description='Birdwatch server service.')
  parser.add_argument("--host", default=bwc.DEFAULT_MQTT_HOST,
                      help="MQTT host name or IP (default=" + bwc.DEFAULT_MQTT_HOST + ")")
  parser.add_argument("--topic", default=bwc.DEFAULT_TOPIC,
                      help="topic name (default=" + bwc.DEFAULT_TOPIC + ")")
  parser.add_argument("--storage", default=bwc.DEFAULT_SERVER_STORAGE_PATH,
                      help="path for permanent storage of video/photo (default="
                      + bwc.DEFAULT_SERVER_STORAGE_PATH + ")")
  args = parser.parse_args()

  service = BirdwatchServer(args.host, args.topic, args.storage)
  service.run()


if __name__ == "__main__":
    main()
