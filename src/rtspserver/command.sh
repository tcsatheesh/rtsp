# not working
./test-launch "videotestsrc is-live=true ! video/x-raw, width=1920, height=1080, framerate=20/1 ! nvvidconv ! video/x-raw(memory:NVMM), width=1920, height=1080, framerate=20/1, format=UYVY8 ! omxh264enc insert-vui=true insert-sps-pps=1 ! video/x-h264, stream-format=byte-stream, alignment=au ! h264parse ! rtph264pay name=pay0 pt=96 ! "

./test-launch "nvarguscamerasrc ! 
            video/x-raw(memory:NVMM),width=(int)3264,height=(int)1848,format=(string)NV12,framerate=(fraction)28/1 ! 
            omxh265enc name=omxh265enc control-rate=1 ! 
            video/x-h265,profile=baseline,stream-format=(string)byte-stream ! 
            h265parse ! 
            rtph265pay name=pay0"

# working 
./test-launch "nvarguscamerasrc ! 
            video/x-raw(memory:NVMM),width=(int)1280,height=(int)720,format=(string)NV12,framerate=(fraction)120/1 ! 
            omxh264enc name=omxh264enc control-rate=1 ! 
            video/x-h264,profile=baseline,stream-format=(string)byte-stream ! 
            h264parse ! 
            rtph264pay name=pay0"

./test-launch "nvarguscamerasrc ! 
            video/x-raw(memory:NVMM),width=(int)1920,height=(int)1080,format=(string)NV12,framerate=(fraction)29/1 ! 
            omxh264enc name=omxh264enc control-rate=1 ! 
            video/x-h264,profile=baseline,stream-format=(string)byte-stream ! 
            h264parse ! 
            rtph264pay name=pay0"

./test-launch "nvarguscamerasrc ! 
            video/x-raw(memory:NVMM),width=(int)3264,height=(int)1848,format=(string)NV12,framerate=(fraction)28/1 ! 
            omxh264enc name=omxh264enc control-rate=1 ! 
            video/x-h264,profile=baseline,stream-format=(string)byte-stream ! 
            h264parse ! 
            rtph264pay name=pay0"


