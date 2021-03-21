#!/usr/bin/python3

import argparse
import threading
import time

import RPi.GPIO
import paho.mqtt.client as mqtt

import birdwatch_constants as bwc
import birdwatch as bw


class BirdwatchCamera:

  mqttClient = None
  host = "undefined"
  topic = "undefined"
  tmpPath = "undefined"

  fileExchangeLock = threading.Lock()

  def __init__(self, host, topic, tmpPath):
    self.host = host
    self.topic = topic
    self.tmpPath = bw.normalizePath(tmpPath)
    bw.configureLogging(self.host, bwc.LOGGING_PREFIX_CAMERA,
                        self.topic + bwc.DEBUG_SUBTOPIC)
    self.mqttClient = mqtt.Client()
    self.mqttClient.connect(self.host, port=1883, keepalive=10)
    self.mqttClient.subscribe(self.topic + bwc.IR_LEDS_SUBTOPIC, qos=1)
    self.mqttClient.on_message = self.onMqttMessage

  def onMqttMessage(self, client, userdata, message):
    assert(client == self.mqttClient)
    payload = str(message.payload.decode("utf-8"))
    if (payload == "0"):
      self.setIRLedPins(RPi.GPIO.LOW)
    elif (payload == "1"):
      self.setIRLedPins(RPi.GPIO.HIGH)
    else:
      bw.log("Ignoring message '" + payload + "' on topic " + (self.topic + bwc.IR_LEDS_SUBTOPIC))

  def recordVideosAndImages(self):
    imageRecordingPath = self.tmpPath + "/image_recording.jpg"
    imageReadyPath = self.tmpPath + "/image_ready.jpg"
    videoRecordingPath = self.tmpPath + "/video_recording.h264"
    videoReadyPath = self.tmpPath + "/video_ready.h264"
    while(True):
      bw.recordRasPiCamImage(imageRecordingPath)
      with self.fileExchangeLock:
        bw.removeFileIfExisting(imageReadyPath)
        bw.renameFileIfExisting(imageRecordingPath, imageReadyPath)
      bw.recordRasPiCamVideo(bwc.VIDEO_RECORDING_SECONDS, videoRecordingPath)
      with self.fileExchangeLock:
        bw.removeFileIfExisting(videoReadyPath)
        bw.renameFileIfExisting(videoRecordingPath, videoReadyPath)

  def myMQTTLoop(self):
    imageReadyPath = self.tmpPath + "/image_ready.jpg"
    imageSendingPath = self.tmpPath + "/image_sending.jpg"
    videoReadyPath = self.tmpPath + "/video_ready.h264"
    videoSendingPath = self.tmpPath + "/video_sending.h264"
    bw.removeFileIfExisting(self.tmpPath + "/image_sending.jpg")
    bw.removeFileIfExisting(self.tmpPath + "/video_sending.h264")
    while(True):
      time.sleep(1.0)
      with self.fileExchangeLock:
        bw.renameFileIfExisting(imageReadyPath, imageSendingPath)
      bw.sendFileViaMQTTIfExisting(self.host, imageSendingPath, self.topic)
      bw.removeFileIfExisting(imageSendingPath)
      with self.fileExchangeLock:
        bw.renameFileIfExisting(videoReadyPath, videoSendingPath)
      bw.sendFileViaMQTTIfExisting(self.host, videoSendingPath, self.topic + bwc.VIDEO_SUBTOPIC)
      bw.removeFileIfExisting(videoSendingPath)

  def configureIRLedPins(self):
    RPi.GPIO.setwarnings(False)
    RPi.GPIO.setmode(RPi.GPIO.BCM)
    for pin in bwc.IR_LED_PINS:
      RPi.GPIO.setup(pin, RPi.GPIO.OUT)

  def setIRLedPins(self, state):
    assert(state == RPi.GPIO.LOW or state == RPi.GPIO.HIGH)
    bw.log("Setting IR LEDs to " + str(state))
    for pin in bwc.IR_LED_PINS:
      RPi.GPIO.output(pin, state)

  def run(self):
    bw.log("Starting birdwatch_camera program.")
    timeSinceBoot = bw.getSecondsSinceBoot()
    bw.log("This computer has been booted {:3.1f}s ago.".format(timeSinceBoot))
    if (timeSinceBoot < 45.0):
      timeToSleep = 45.0 - timeSinceBoot
      bw.log("Will wait {:3.1f}s until the computer has booted completely.".format(timeToSleep))
      time.sleep(timeToSleep)
    bw.switchRasPiLedsOff()
    self.configureIRLedPins()
    t1 = threading.Thread(target=self.recordVideosAndImages)
    t2 = threading.Thread(target=self.myMQTTLoop)
    t1.start()
    t2.start()
    self.mqttClient.loop_start()
    t1.join()
    t2.join()
    self.mqttClient.loop_stop()


def main():
  parser = argparse.ArgumentParser(description='Birdwatch camera service.')
  parser.add_argument("--host", default=bwc.DEFAULT_MQTT_HOST,
                      help="MQTT host name or IP (default=" + bwc.DEFAULT_MQTT_HOST + ")")
  parser.add_argument("--topic", default=bwc.DEFAULT_TOPIC,
                      help="topic name (default=" + bwc.DEFAULT_TOPIC + ")")
  parser.add_argument("--tmp", default=bwc.DEFAULT_CAMERA_TMP_PATH,
                      help="path for temporary storage of video/photo (default="
                      + bwc.DEFAULT_CAMERA_TMP_PATH + ")")
  args = parser.parse_args()

  service = BirdwatchCamera(args.host, args.topic, args.tmp)
  service.run()


if __name__ == "__main__":
    main()
