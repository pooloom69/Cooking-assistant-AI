# script to take snapshots from videos
import os
import sys
import pathlib
import logging
import time
import cv2
import math
import subprocess
from datetime import datetime


run_date = datetime.today().strftime('%Y%m%d')
CURRENT_DIR = os.getcwd() + "/"
LOG_DIR = os.path.join(CURRENT_DIR, "logs/", run_date)
LOG_FILE_NAME = 'data_gather_' + run_date + '.log'
RECIPE_LIST = ['bean_soup','chicken_teriyaki']

# function to create logger
def logger():
	logger = None

	# set up logger dir
	log_file = LOG_DIR + '/' + LOG_FILE_NAME

	# logger directory and file creation
	os.makedirs(LOG_DIR, exist_ok = True)

	# initiate logger
	logging.basicConfig(
		filename = log_file,
		encoding = 'utf-8',
		filemode = 'a',
		datefmt = '%Y-%m-%d %H:%M',
		format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
	)
	logger = logging.getLogger('videoToStills')
	logger.setLevel(logging.DEBUG)

	return logger

# initiate logger
logger = logger()
logger.info("Initiating program ...")

def compress_h264_videos(input_dir):
    """
    Compress .h264 videos from the specified directory into .mp4 format
    Args:
        input_dir: Directory containing .h264 videos
    """
    try:
        # Create compressed_videos directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(input_dir), "compressed_videos")
        os.makedirs(output_dir, exist_ok=True)
        
        # Get list of already compressed files
        already_compressed = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
        
        # Process each .h264 file
        for filename in os.listdir(input_dir):
            if filename.endswith(".h264"):
                output_filename = filename.replace(".h264", ".mp4")
                # Skip if already compressed
                if output_filename in already_compressed:
                    logger.info(f"Skipping {filename} - already compressed")
                    continue
                    
                input_file = os.path.join(input_dir, filename)
                output_file = os.path.join(output_dir, output_filename)
                
                logger.info(f"Compressing {filename} to {output_filename}")
                print(f"Compressing {filename} ...")
                
                # Use ffmpeg to compress the video with good quality settings
                ffmpeg_cmd = f"ffmpeg -i {input_file} -c:v libx264 -c:a copy -crf 20 {output_file}"
                subprocess.run(ffmpeg_cmd, shell=True)
                logger.info(f"Finished compressing {filename}")
                
    except Exception as e:
        logger.exception(f"An error occurred during compression: {e}")

# find all video directories that have videos of specific format
def fast_scandir(dirname):
    try:
        vid_dir = []
        # loop through and recursively identify ALL directory paths
        subfolders = [f.path for f in os.scandir(dirname) if f.is_dir()]
        for dirname in list(subfolders):
            subfolders.extend(fast_scandir(dirname))
        # filter out the directories for compressed_videos
        for dir in subfolders:
            if "compressed_videos" in dir:
                in_scope_video_files = [vid_file for vid_file in os.listdir(dir) if vid_file.endswith(".mp4")]
                if len(in_scope_video_files) > 0:
                    vid_dir.append(dir)
        return vid_dir
    except Exception as e:
	    logger.exception("An error occurred: {}".format(e))

# create appropriate stills directories        
def stills_dir(vid_dirs):
    try:
        stills_dirs = []    
        for dir in vid_dirs:
            still_dir = dir.replace("compressed_videos","stills")
            print(still_dir)
            try:
                if os.path.exists(still_dir):
                    logger.info("Directory {} already exists for stills.".format(still_dir))
                else:
                    logger.info("Creating related stills directory {}".format(still_dir))
                    os.makedirs(still_dir, exist_ok=True)  # Create the actual stills directory
                    # for os to acknowledge existence of directory create a blank .DS_Store file in it
                    open(still_dir + "/.DS_Store", 'a').close()
                stills_dirs.append(still_dir)
            except Exception as e:
                logger.exception("An error occurred: {}".format(e))
        return stills_dirs
    except Exception as e:
	    logger.exception("An error occurred: {}".format(e))

# convert videos to stills
def video_to_stills(vid_dirs):
    try:
        for dir in vid_dirs:
            still_dir = dir.replace("compressed_videos","stills")
            try:
                # check whether there is images data in dir. already (jpg, jpeg, png)
                if os.listdir(still_dir):
                    stills_in_scope_format = [still_file for still_file in os.listdir(still_dir) if (still_file.endswith(".png") or still_file.endswith(".jpeg") or still_file.endswith(".jpg"))]
                    if len(stills_in_scope_format) > 0:
                        logger.warning("Stills directory {} is not empty".format(still_dir))
                        continue
                    else:
                        print("Ok to proceed parsing of videos to stills directory {}".format(still_dir))
                        video_files = [vid_file for vid_file in os.listdir(dir) if vid_file.endswith(".mp4")]
                        for video_name in video_files:
                            video_path = dir + "/" + video_name
                            logger.info("Processing video {}".format(video_path))
                            cam = cv2.VideoCapture(video_path)
                            interval = 1 # number of seconds interval
                            fps = int(cam.get(cv2.CAP_PROP_FPS))
                            logger.info("FPS for video {}: {}".format(video_path,fps))
                            current_frame = 0
                            while(True):
                                ret, frame = cam.read()
                                if ret:
                                    if (current_frame % (fps * interval) == 0):
                                        still_file_path = still_dir + "/" + video_name.replace(".mp4", "_" + str(math.floor(current_frame / fps)) + ".jpg")
                                        logger.info("Processing still {}".format(still_file_path))
                                        cv2.imwrite(still_file_path, frame)
                                    current_frame += 1
                                else:
                                    break
                else:
                    logger.error("Stills directory {} doesn't exist".format(still_dir))
            except Exception as e:
                logger.exception("An error occurred: {}".format(e))
    except Exception as e:
	    logger.exception("An error occurred: {}".format(e))

if __name__ == '__main__':
    print("Initiating program ...")
    
    # Compress .h264 videos from data_record directory first
    video_dir = "enter_your_directory_here/data_record/"  # specify your data_record directory here
    if os.path.exists(video_dir):
        print(f"Compressing videos in {video_dir}...")
        compress_h264_videos(video_dir)
    else:
        print(f"Directory {video_dir} not found!")

    # Continue with the regular video to stills processing
    vid_dirs = fast_scandir(CURRENT_DIR)
    logger.info("Videos directories identified: {}".format(vid_dirs))
    print("Videos directories identified: {}".format(vid_dirs))
    # if there are videos, then create directories for stills
    stills_dirs = stills_dir(vid_dirs)
    logger.info("Stills directories that we will work with: {}".format(stills_dirs))
    print("Stills directories that we will work with: {}".format(stills_dirs))
    # parse out the videos and create stills
    print("Processing data ...")
    video_to_stills(vid_dirs)
    print("Program has completed!")