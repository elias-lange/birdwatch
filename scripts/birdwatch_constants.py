# Constants for birdwatch camera and server service

DEFAULT_MQTT_HOST = "192.168.1.1"

DEFAULT_TOPIC = "birdwatch"
DEBUG_SUBTOPIC = "/debug"
VIDEO_SUBTOPIC = "/video"
IR_LEDS_SUBTOPIC = "/ir_leds"
IR_LED_PINS = [2, 3, 4, 17]

VIDEO_RECORDING_SECONDS = 30

LOGGING_PREFIX_CAMERA = "Camera"
LOGGING_PREFIX_SERVER = "Server"

DEFAULT_CAMERA_TMP_PATH = "/tmp"
DEFAULT_SERVER_STORAGE_PATH = "/samba/public"
