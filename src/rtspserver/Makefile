CC=gcc
CFLAGS=`pkg-config --cflags --libs gstreamer-1.0 gstreamer-rtsp-server-1.0`
test-launch: test-launch.c
		$(CC) -o test-launch test-launch.c $(CFLAGS)