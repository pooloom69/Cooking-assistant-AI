import os
#import sys
#import pathlib
import argparse
import math
import subprocess
import logging
import time
from picamera2 import Picamera2, Preview
from picamera2.encoders import Encoder
from time import sleep
#from libcamera import Transform
from datetime import datetime
from picamera2.encoders import H264Encoder


# define global parameters
# date will be utilized to catalog directories
video_length = 60  # length of each video segment in seconds
run_date = datetime.today().strftime('%Y%m%d')
run_time = datetime.now().strftime('%H:%M:%S')
CURRENT_DIR = os.getcwd() + "/"
OUTPUT_VID_DIR = os.path.join(CURRENT_DIR, run_date, "videos/")
OUTPUT_VID_COMP_DIR = os.path.join(CURRENT_DIR, run_date, "compressed_videos/")
OUTPUT_STILL_DIR = os.path.join(CURRENT_DIR, run_date, "stills/")
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
	logger = logging.getLogger('dataGather')
	logger.setLevel(logging.DEBUG)

	return logger

# initiate logger
logger = logger()
logger.info("Initiating program ...")

# make output directories if they doesn't exist
try:
	os.makedirs(os.path.dirname(OUTPUT_VID_DIR), exist_ok=True)
	os.makedirs(os.path.dirname(OUTPUT_VID_COMP_DIR), exist_ok=True)
	os.makedirs(os.path.dirname(OUTPUT_STILL_DIR), exist_ok=True)
except Exception as e:
	logger.exception("An error occurred: {}".format(e))

# parse out argument list
try:
	msg = "Help message"
	parser = argparse.ArgumentParser(
			prog = "Cooking Video Recorder",
			description = msg,
			usage = "%(prog)s [options]")
	parser.add_argument("-r", "--r", "-recipe", "--recipe", nargs = "?", type = str, help = "select one of: " + str(RECIPE_LIST), choices = RECIPE_LIST)
	parser.add_argument("-m", "--m", "-minutes", "--minutes", nargs = "?", type = int, help = "define number of minutes you would like the camera to record for")
	parser.add_argument("-d", "--d", "-debug", "--debug", help = "set this to True if you'd like to run the program in debug mode")
	parser.add_argument("-f", "--f", "-format", "--format", nargs = "?", help = "select v for video or s for stills", choices = ['s','v'])
	args = parser.parse_args()

	if args.d:
		print("Arguments captured:",args)
	logger.info("Arguments captured: {}".format(args))
except Exception as e:
	logger.exception("An error occurred: {}".format(e))
	
# store and format args
try:
	debug = True if args.d else False
	recipe = "chicken_teriyaki" if args.r is None else args.r
	rec_secs = 60 if args.m is None else args.m * 60
	rec_format = 'v' if args.f is None else args.f

	if debug:
		print("Arguments formatted: debug={}, recipe={}, rec_secs={}, rec_format={}".format(debug,recipe,rec_secs,rec_format))
		print("Video output directory: {}".format(OUTPUT_VID_DIR))
		print("Stills output directory: {}".format(OUTPUT_STILL_DIR))
	logger.info("Arguments formatted: debug={}, recipe={}, rec_secs={}, rec_format={}".format(debug,recipe,rec_secs,rec_format))
	logger.info("Video output directory: {}".format(OUTPUT_VID_DIR))
	logger.info("Stills output directory: {}".format(OUTPUT_STILL_DIR))
except Exception as e:
	logger.exception("An error occurred: {}".format(e))

# function to compress video
def compress_video(debug):
	# make sure to only compress files that have not been compressed already
	already_compressed_files = [f for f in os.listdir(OUTPUT_VID_COMP_DIR) if os.path.isfile(os.path.join(OUTPUT_VID_COMP_DIR,f))]
	for filename in os.listdir(OUTPUT_VID_DIR):
		if filename.endswith(".h264") and filename.replace(".h264",".mp4") not in already_compressed_files:
			input_file = os.path.join(OUTPUT_VID_DIR,filename)
			output_file = os.path.join(OUTPUT_VID_COMP_DIR,filename.replace(".h264",".mp4"))
			if debug:
				print("Compressing {} ...".format(filename))
			logger.info("Compressing {} ...".format(filename))
			ffmpeg_cmd = "ffmpeg -i " + input_file + " -c:v libx264 -c:a copy -crf 20 " + output_file
			subprocess.run(ffmpeg_cmd, shell=True)

# function to record video and take stills simultaneously
def record_video(debug,recipe,rec_secs):
	# grab list of file names in output directory
	# I am going to use ints to name the files so that way it is easy for me to name each file
	files = [f for f in os.listdir(OUTPUT_VID_DIR) if os.path.isfile(os.path.join(OUTPUT_VID_DIR,f))]
	if debug:
		print("Files captured:",files)

	# figure out the new starting int
	i = 0
	new_start = 0
	new_file_name = recipe + "_" + run_date + "_" + str(i) + ".h264"
	while i < len(files) and new_file_name in files:
		i += 1
		new_start = i

	if debug:
		print("New batch videos starting integer: {}".format(new_start))
	logger.info("New batch videos starting integer: {}".format(new_start))
	
	# as a safety precaution, create a loop to take and store a video every 60 seconds
	for video_mins in range(math.floor(rec_secs/video_length)):
		new_file_name = recipe + "_" + run_date + "_" + str(new_start) + ".h264"
		new_start += 1
		if debug:
			print("Video file name that will be written to disk: {}".format(new_file_name))
		logger.info("Video file name that will be written to disk: {}".format(new_file_name))

		# initiate the camera and take a video
		picam = Picamera2()
		video_config = picam.create_video_configuration(controls={"FrameRate":25.0})
		picam.configure(video_config)
		encoder = H264Encoder(10000000)
		picam.start_recording(encoder, OUTPUT_VID_DIR + new_file_name)

		# while the video is recording, take stills
		still_sec = 0
		while still_sec < rec_secs:
			request = picam.capture_request()
			request.save("main",OUTPUT_STILL_DIR + new_file_name.replace(".h264", "_" + str(still_sec) + ".jpg"))
			request.release()
			time.sleep(1)
			still_sec += 1
		
		picam.stop_recording()
		picam.close()

# function to record stills
def record_stills(debug,recipe,rec_secs):
	# grab list of file names in output directory
	# I am going to use ints to name the files so that way it is easy for me to name each file
	files = [f for f in os.listdir(OUTPUT_STILL_DIR) if os.path.isfile(os.path.join(OUTPUT_STILL_DIR,f))]
	if debug:
		print("Files captured:",files)

	# figure out the new starting int
	i = 0
	new_start = 0
	new_file_name = recipe + "_" + run_date + "_" + str(i) + ".jpg"
	while i < len(files) and new_file_name in files:
		i += 1
		new_start = i

	if debug:
		print("New batch pictures starting integer: {}".format(new_start))
	logger.info("New batch pictures starting integer: {}".format(new_start))
	
	# create a loop to take and store a picture every n seconds
	for still_num in range(rec_secs):
		new_file_name = recipe + "_" + run_date + "_" + str(new_start) + ".jpg"
		new_start += 1
		if debug:
			print("Picture file name that will be written to disk: {}".format(new_file_name))
		logger.info("Picture file name that will be written to disk: {}".format(new_file_name))

		# initiate the camera and take a picture
		picam = Picamera2()
		picam.start()
		picam.capture_file(OUTPUT_STILL_DIR + new_file_name)
		if debug:
			print("Camera has captured picture: {}".format(new_file_name))
		logger.info("Camera has captured picture: {}".format(new_file_name))
		picam.close()
		sleep(1)

# call function(s)
if __name__ == '__main__':
	try:
		if rec_format == 's':
			record_stills(debug,recipe,rec_secs)
		elif rec_format == 'v':
			record_video(debug,recipe,rec_secs)
			compress_video(debug)
	except Exception as e:
		logger.exception("An error occurred: {}".format(e))


