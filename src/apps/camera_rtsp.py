#!/usr/bin/env python3

################################################################################
# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
################################################################################

import argparse
import sys
sys.path.append('../')

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import GObject, Gst, GstRtspServer
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call

import pyds

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3

def osd_sink_pad_buffer_probe(pad,info,u_data):
    frame_number=0
    #Intiallizing object counter with 0.
    obj_counter = {
        PGIE_CLASS_ID_VEHICLE:0,
        PGIE_CLASS_ID_PERSON:0,
        PGIE_CLASS_ID_BICYCLE:0,
        PGIE_CLASS_ID_ROADSIGN:0
    }
    num_rects=0

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting is done by pyds.NvDsFrameMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number=frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj=frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            obj_counter[obj_meta.class_id] += 1
            try: 
                l_obj=l_obj.next
            except StopIteration:
                break

        # Acquiring a display meta object. The memory ownership remains in
        # the C code so downstream plugins can still access it. Otherwise
        # the garbage collector will claim it when this probe function exits.
        display_meta=pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]
        # Setting display text to be shown on screen
        # Note that the pyds module allocates a buffer for the string, and the
        # memory will not be claimed by the garbage collector.
        # Reading the display_text field here will return the C address of the
        # allocated string. Use pyds.get_string() to get the string content.
        #TCS Changed this: py_nvosd_text_params.display_text = "Frame Number={} Number of Objects={} Vehicle_count={} Person_count={}".format(frame_number, num_rects, obj_counter[PGIE_CLASS_ID_VEHICLE], obj_counter[PGIE_CLASS_ID_PERSON])

        # Now set the offsets where the string should appear
        py_nvosd_text_params.x_offset = 10
        py_nvosd_text_params.y_offset = 12

        # Font , font-color and font-size
        py_nvosd_text_params.font_params.font_name = "Serif"
        py_nvosd_text_params.font_params.font_size = 10
        # set(red, green, blue, alpha); set to White
        py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)

        # Text background color
        py_nvosd_text_params.set_bg_clr = 1
        # set(red, green, blue, alpha); set to Black
        py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        # Using pyds.get_string() to get display_text as string
        # print(pyds.get_string(py_nvosd_text_params.display_text))
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
        try:
            l_frame=l_frame.next
        except StopIteration:
            break
			
    return Gst.PadProbeReturn.OK	


def main(args):
    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements
    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")
    
    # Source element for reading from the file
    print("Creating Source \n ")
    source = Gst.ElementFactory.make("nvarguscamerasrc", "camera-source")
    if not source:
        sys.stderr.write(" Unable to create Source \n")

   # Create a caps filter
    caps0 = Gst.ElementFactory.make("capsfilter", "filter0")
    caps0_string = "video/x-raw(memory:NVMM),width=%d, height=%d, framerate=%d/1, format=NV12" % (args.width, args.height, args.framerate)
    caps0.set_property("caps", Gst.Caps.from_string(caps0_string))
        
    # Create nvstreammux instance to form batches from one or more sources.
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    if not streammux:
        sys.stderr.write(" Unable to create NvStreamMux \n")
    
    if args.with_dl:
        # Use nvinfer to run inferencing on decoder's output,
        # behaviour of inferencing is set through config file
        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
        if not pgie:
            sys.stderr.write(" Unable to create pgie \n")
        pgie.set_property('config-file-path', "dstest1_pgie_config.txt")
    
    # Use convertor to convert from NV12 to RGBA as required by nvosd
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        sys.stderr.write(" Unable to create nvvidconv \n")
    
    # Create OSD to draw on the converted RGBA buffer
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    if not nvosd:
        sys.stderr.write(" Unable to create nvosd \n")
    nvvidconv_postosd = Gst.ElementFactory.make("nvvideoconvert", "convertor_postosd")
    if not nvvidconv_postosd:
        sys.stderr.write(" Unable to create nvvidconv_postosd \n")
    
    # Create a caps filter
    caps = Gst.ElementFactory.make("capsfilter", "filter")
    caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=I420"))
    
    # Make the encoder
    if args.codec == "H264":
        encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
        print("Creating H264 Encoder")
    elif args.codec == "H265":
        encoder = Gst.ElementFactory.make("nvv4l2h265enc", "encoder")
        print("Creating H265 Encoder")
    if not encoder:
        sys.stderr.write(" Unable to create encoder")
    encoder.set_property('bitrate', args.bitrate)
    if is_aarch64():
        encoder.set_property('preset-level', 1)
        encoder.set_property('insert-sps-pps', 1)
        encoder.set_property('bufapi-version', 1)
    
    # Make the payload-encode video into RTP packets
    if args.codec == "H264":
        rtppay = Gst.ElementFactory.make("rtph264pay", "rtppay")
        print("Creating H264 rtppay")
    elif args.codec == "H265":
        rtppay = Gst.ElementFactory.make("rtph265pay", "rtppay")
        print("Creating H265 rtppay")
    if not rtppay:
        sys.stderr.write(" Unable to create rtppay")
    
    # Make the UDP sink
    updsink_port_num = 5400
    sink = Gst.ElementFactory.make("udpsink", "udpsink")
    if not sink:
        sys.stderr.write(" Unable to create udpsink")
    
    sink.set_property('host', '224.224.255.255')
    sink.set_property('port', updsink_port_num)
    sink.set_property('async', False)
    sink.set_property('sync', 1)
    
    source.set_property('sensor_id', 0)
    source.set_property('bufapi-version', 1)
    streammux.set_property('width', args.width)
    streammux.set_property('height', args.height)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', args.bitrate)
        
    print("Adding elements to Pipeline \n")
    pipeline.add(source)
    pipeline.add(caps0)
    pipeline.add(streammux)
    if args.with_dl:
        pipeline.add(pgie)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(nvvidconv_postosd)
    pipeline.add(caps)
    pipeline.add(encoder)
    pipeline.add(rtppay)
    pipeline.add(sink)

    # Link the elements together:
    # file-source -> caps0 ->
    # nvinfer -> nvvidconv -> nvosd -> nvvidconv_postosd -> 
    # caps -> encoder -> rtppay -> udpsink
    
    print("Linking elements in the Pipeline \n")
    source.link(caps0)    
    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux \n")
    
    srcpad = caps0.get_static_pad("src")
    if not srcpad:
        sys.stderr.write(" Unable to get source pad of decoder \n")
    
    srcpad.link(sinkpad)
    if args.with_dl:
        streammux.link(pgie)    
        pgie.link(nvvidconv)
    else:
        streammux.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(nvvidconv_postosd)
    nvvidconv_postosd.link(caps)
    caps.link(encoder)
    encoder.link(rtppay)
    rtppay.link(sink)
    
    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)
    
    # Start streaming
    rtsp_port_num = 8554
    
    server = GstRtspServer.RTSPServer.new()
    server.props.service = "%d" % rtsp_port_num
    server.attach(None)
    
    factory = GstRtspServer.RTSPMediaFactory.new()
    factory.set_launch( "( udpsrc name=pay0 port=%d buffer-size=524288 caps=\"application/x-rtp, media=video, clock-rate=90000, encoding-name=(string)%s, payload=96 \" )" % (updsink_port_num, args.codec))
    factory.set_shared(True)
    factory_endpoint = "/test"
    server.get_mount_points().add_factory(factory_endpoint, factory)
    
    print("\n *** DeepStream: Launched RTSP Streaming at rtsp://localhost:%d%s ***\n\n" % (rtsp_port_num, factory_endpoint))
    
    # Lets add probe to get informed of the meta data generated, we add probe to
    # the sink pad of the osd element, since by that time, the buffer would have
    # had got all the metadata.
    osdsinkpad = nvosd.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write(" Unable to get sink pad of nvosd \n")
    
    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)
    
    # start play back and listen to events
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    # cleanup
    pipeline.set_state(Gst.State.NULL)

def parse_args():
    parser = argparse.ArgumentParser(description='RTSP Output Sample Application Help ')
    parser.add_argument("--with-dl",
                  dest="with_dl",
                  action="store_true",
                  help="With deep learning")
    parser.add_argument("-c", "--codec", default="H264",
                  help="RTSP Streaming Codec H264/H265 , default=H264", choices=['H264','H265'])
    parser.add_argument("-b", "--bitrate", default=4000000,
                  help="Set the encoding bitrate ", type=int)
    parser.add_argument("-t", "--height", default=720, 
		  help="Set the height of the video.", type=int)
    parser.add_argument("-w", "--width", default=1280, 
		  help="Set the width of the video.", type=int)
    parser.add_argument("-f", "--framerate", default=28, 
		  help="Set the framerate of the video.", type=int)
    parser.set_defaults(with_dl=False)
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()
    sys.exit(main(args))

