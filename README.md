# rtsp


This will run only on a jetson nano

        cd src\apps
        python3 camera_rtsp.py [--with-dl]

Don't use the --with-dl if you only want an rtsp stream.        

This is copy from the Deepstream-SDK. Simply takes the camera and outputs an RTSP stream.