import subprocess ## for calling gdal functions
import numpy as np ## for processing the images
import cv2 ## for creating the circular fields
from shutil import copyfile ## for copying the worldfile
from osgeo import gdal  ### used for relcass
from osgeo import osr
import urllib
import os
import time

start_time = time.time()


def map_circles(fileout, threshold_val):
### code taken from here http://docs.opencv.org/trunk/d3/db4/tutorial_py_watershed.html
	img = cv2.imread(fileout)
	# perform the actual resizing of the image and show it
	#img = cv2.resize(image, dim, interpolation = cv2.INTER_AREA)
	cv2.imwrite('image3.png', img)

	gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
	ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

	# noise removal
	kernel = np.ones((3,3),np.uint8)
	opening = cv2.morphologyEx(thresh,cv2.MORPH_OPEN,kernel, iterations = 1)
	# sure background area
	sure_bg = cv2.dilate(opening,kernel,iterations=3)
	# Finding sure foreground area
	dist_transform = cv2.distanceTransform(opening,cv2.DIST_L2,5)
	ret, sure_fg = cv2.threshold(dist_transform,0.1*dist_transform.max(),255,0)
	# Finding unknown region
	sure_fg = np.uint8(sure_fg)
	unknown = cv2.subtract(sure_bg,sure_fg)

	# Marker labelling
	ret, markers = cv2.connectedComponents(sure_fg)
	# Add one to all labels so that sure background is not 0, but 1
	markers = markers+1
	# Now, mark the region of unknown with zero
	markers[unknown==255] = 0


	markers = cv2.watershed(img,markers)
	img[markers == -1] = [0,0,255]


	cv2.imwrite(threshold_img,thresh)
	cv2.imwrite(mapped_img, img)

def copyworldfile(fileout, mapped_img, threshold_img):
### helper method to copy the world file
	worldfile_name = fileout[:-4] + ".wld"
	mapped_img_worldfile = mapped_img [:-4] + ".wld"
	threshold_img_worldfile = threshold_img [:-4] + ".wld"

	copyfile(worldfile_name, mapped_img_worldfile)
	copyfile(worldfile_name, threshold_img_worldfile)
	
def reclass(threshold_img, relcassed_img):
## from https://github.com/acgeospatial/Planet_API_Edge/blob/master/reclass_image.py
	### open the raster
	gdalData = gdal.Open(threshold_img)
	### read into array
	raster = gdalData.ReadAsArray()
	#reclassify raster values using Numpy! in this case less and greater functions
	temp = np.less(raster, 10)
	np.putmask(raster, temp, 0)
	temp = np.greater_equal(raster, 10)
	np.putmask(raster, temp, 1)

	# write results to file (lets set it to tif)
	format = "GTiff"
	driver = gdal.GetDriverByName(format)
	
	# CreateCopy() method instead of Create() to save our time as the raster is the same only the extension is changing
	outDataRaster = driver.CreateCopy(reclassed_img, gdalData, 0)
	proj = osr.SpatialReference()
	proj.SetWellKnownGeogCS( "EPSG:32639" )
	outDataRaster.SetProjection(proj.ExportToWkt())
	outDataRaster.GetRasterBand(1).WriteArray(raster)
	outDataRaster = None
	
def projection(EPSG, outprj):

	testfile = urllib.URLopener()
	testfile.retrieve(EPSG, outprj)

#### You can pass these values in as system arguments if needed	
os.chdir("...workingdirectory/")
threshold_val = 0.1
filein = "out_clip.tif"
fileout = "out_image1.jpg"
mapped_img = "out_image4.jpg"
threshold_img = "out_image3.jpg"
reclassed_img = "reclassed_image1.tif"
outshp = "mapped_field.shp"
outprj = "mapped_field.prj"

### Convert tif file to jpg
subprocess.call('gdal_translate -b 1 -b 2 -b 3 -of JPEG -scale -co worldfile=yes ' + filein + " " + fileout)
## threhold the circles
map_circles(fileout, threshold_val)
## copy the worldfile
copyworldfile(fileout, mapped_img, threshold_img)
### reclass helper function
reclass(threshold_img, reclassed_img)
### convert to polygons
subprocess.call('gdal_polygonize.bat -f "ESRI Shapefile" ' + reclassed_img + " " + outshp)

EPSG = "http://spatialreference.org/ref/epsg/32639/prj/"
## set shp projection
projection(EPSG, outprj)

print "Mapping circular fields took: ", time.time()-start_time
