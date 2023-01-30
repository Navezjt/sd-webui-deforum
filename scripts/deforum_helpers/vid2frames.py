import os
import cv2
import shutil
import math
import requests
from modules.shared import state

def get_frame_name(path):
    name = os.path.basename(path)
    name = os.path.splitext(name)[0]
    return name

def vid2frames(video_path, video_in_frame_path, n=1, overwrite=True, extract_from_frame=0, extract_to_frame=-1, only_get_fps=False): 
    # n = extract_nth_frame 
    #get the name of the video without the path and ext
    
    # TODO: add optional out file format (png or jpg?)
    img_format = 'png'
    
    if (extract_to_frame <= extract_from_frame) and extract_to_frame != -1:
        raise RuntimeError('extract_to_frame can not be highher than extract_from_frame')
    name = get_frame_name(video_path)
    if n < 1: n = 1 #HACK Gradio interface does not currently allow min/max in gr.Number(...) 

    if video_path.startswith('http://') or video_path.startswith('https://'):
        response = requests.head(video_path)
        if response.status_code == 404 or response.status_code != 200:
            raise ConnectionError("Init video url or mask video url is not valid")
    else:
        if not os.path.exists(video_path):
            raise RuntimeError("Init video path or mask video path is not valid")
            
    vidcap = cv2.VideoCapture(video_path)
    video_fps = vidcap.get(cv2.CAP_PROP_FPS)

    if only_get_fps is False:
        input_content = []
        if os.path.exists(video_in_frame_path) :
            input_content = os.listdir(video_in_frame_path)

        # check if existing frame is the same video, if not we need to erase it and repopulate
        if len(input_content) > 0:
            #get the name of the existing frame
            content_name = get_frame_name(input_content[0])
            if not content_name.startswith(name):
                overwrite = True

        # grab the frame count to check against existing directory len 
        frame_count = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT)) 
        
        print(f"Extracting {frame_count} frames from video... Please wait.")
        
        # raise error if the user wants to skip more frames than exist
        if n >= frame_count : 
            raise RuntimeError('Skipping more frames than input video contains. extract_nth_frames larger than input frames')
        
        expected_frame_count = math.ceil(frame_count / n) 
        # Check to see if the frame count is matches the number of files in path
        if overwrite or expected_frame_count != len(input_content):
            shutil.rmtree(video_in_frame_path)
            os.makedirs(video_in_frame_path, exist_ok=True) # just deleted the folder so we need to make it again
            input_content = os.listdir(video_in_frame_path)
        
        if len(input_content) == 0:
            vidcap.set(cv2.CAP_PROP_POS_FRAMES, extract_from_frame) # Set the starting frame
            success,image = vidcap.read()
            count = extract_from_frame
            t=1
            success = True
            while success:
                if state.interrupted:
                    return
                if (count <= extract_to_frame or extract_to_frame == -1) and count % n == 0:
                    cv2.imwrite(video_in_frame_path + os.path.sep + name + f"{t:05}." + img_format , image)     # save frame as JPEG file
                    t += 1
                success,image = vidcap.read()
                count += 1
            print("Extracted %d frames" % count)
        else:
            print("Frames already unpacked")
    vidcap.release()
    return video_fps


def get_next_frame(outdir, video_path, frame_idx, mask=False):
    frame_path = 'inputframes'
    if (mask): frame_path = 'maskframes'
    return os.path.join(outdir, frame_path, get_frame_name(video_path) + f"{frame_idx+1:05}" + img_format)
    
def ffmpegvid2frames(full_vid_path = None, full_out_imgs_path = None, out_img_format = 'jpg', ffmpeg_location = None):
    try:
        cmd = [
                ffmpeg_location,
                '-i', full_vid_path,
                os.path.join(full_out_imgs_path,'%08d')
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        # if process.returncode != 0:
            # raise RuntimeError(stderr)
    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg not found. Please make sure you have a working ffmpeg path under 'ffmpeg_location' parameter. \n*Interpolated frames were SAVED as backup!*")
    except Exception as e:
        raise Exception(f'Error stitching interpolation video. Actual runtime error:{e}\n*Interpolated frames were SAVED as backup!*')   
