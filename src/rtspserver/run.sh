/home/danalyst/projects/www.github.com/tcsatheesh/rtsp/src/rtspserver/test-launch "nvarguscamerasrc !
            video/x-raw(memory:NVMM),width=(int)1920,height=(int)1080,format=(string)NV12,framerate=(fraction)28/1 !
            nvv4l2h264enc bitrate=40000000 !
            rtph264pay mtu=1400 name=pay0"
