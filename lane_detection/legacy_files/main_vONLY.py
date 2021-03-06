import time
import glob
import numpy as np
import cv2
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from moviepy.editor import VideoFileClip

#do some camera undistortion

# Define perspective transform function
def warp(undistorted_image):
    # define calibration box in source (original) and
    # destination (destination or warped) coordinates
    image_size = undistorted_image.shape[1::-1]
    # Four source coordinates
    src = np.float32([[830,250],
                     [1010,530],
                     [180,530],
                     [360,250]])
    # Four desired coordinates
    dst = np.float32([[1000,155],
                     [1000,680],
                     [400,680],
                     [400,155]])
    # Compute the perspective transform M
    M = cv2.getPerspectiveTransform(src, dst)


    # Create the warped image - uses linear interpolation
    warped = cv2.warpPerspective(undistorted_image, M, image_size,flags = cv2.INTER_LINEAR)

    return warped

def unwarp(warped_image):
    # define calibration box in source (original) and
    # destination (destination or warped) coordinates
    image_size = warped_image.shape[1::-1]
    # Four source coordinates
    src = np.float32([[830,250],
                     [1010,530],
                     [180,530],
                     [360,250]])
    # Four desired coordinates
    dst = np.float32([[1000,155],
                     [1000,680],
                     [400,680],
                     [400,155]])
    #dst = np.float32([[1100,155],
    #                 [1100,680],
    #                 [290,680],
    #                 [300,155]])
    # Compute the inverse perspective transform
    Minv = cv2.getPerspectiveTransform(dst, src)

    # unwarp the warped image - uses linear interpolation
    unwarped = cv2.warpPerspective(warped_image, Minv, image_size,flags = cv2.INTER_LINEAR)

    return unwarped

# the function to take x and y gradient threshold
def abs_sobel_thresh(image, orient = 'x', thresh = (0,255)):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    if orient == 'x':
        sobel = cv2.Sobel(gray,cv2.CV_64F,1,0,)
    elif orient == 'y':
        sobel = cv2.Sobel(gray,cv2.CV_64F,0,1,)
    abs_sobel = np.absolute(sobel)
    scaled_sobel = np.uint8(255*abs_sobel/np.max(abs_sobel))
    binary_output = np.zeros_like(scaled_sobel)
    binary_output[(scaled_sobel >= thresh[0])&(scaled_sobel <= thresh[1])] = 1
    return binary_output

# applying both s thresholding and sobel magnitude thresholding
def process_image(image):
    # first let's get rid of camera distortion
    #TODO IMPLEMENT THIS
    undistorted_image = image
    
    
    # lets apply thresholding to S channel
    hls_image = cv2.cvtColor(undistorted_image,cv2.COLOR_RGB2HLS)
    s_channel_image = hls_image[:,:,2]
    thresh = (80,255)
    s_thresholded_image = np.zeros_like(s_channel_image)
    s_thresholded_image[(s_channel_image>thresh[0])&(s_channel_image < thresh[1])] = 1

    #invert image
    s_thresholded_image = cv2.bitwise_not(s_thresholded_image)
    
    #lets apply magnitude of sobel thresholding
    gray = cv2.cvtColor(undistorted_image,cv2.COLOR_RGB2GRAY)
    #gaussian blur
    kernel_size = 19 
    gray = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)

    sobelx = cv2.Sobel(gray,cv2.CV_64F,1,0)
    sobely = cv2.Sobel(gray,cv2.CV_64F,0,1)
    abs_sobelxy = np.sqrt(sobelx**2 + sobely**2)
    sobelxy_scaled = np.uint8(255 * abs_sobelxy / np.max(abs_sobelxy))
    thresh_min = 50
    thresh_max = 100
    sobel_thresholded_image = np.zeros_like(sobelxy_scaled)
    sobel_thresholded_image[(sobelxy_scaled >= thresh_min) & (sobelxy_scaled <= thresh_max)] = 1

    #cv2.imshow("cropped", sobel_thresholded_image)
    #cv2.waitKey(0)

    # combine two thresholds
    combined_binary = np.zeros_like(sobel_thresholded_image)
    combined_binary[(s_thresholded_image == 1)|(sobel_thresholded_image == 1)] = 1
    
    # let's change camera pespective into bird's eye view
    warped_image = warp(combined_binary)
    
    # creating a three channel  image from our 1 channel binary(B&W) Image
    three_channel_thresholded_image = np.dstack((warped_image,warped_image,warped_image))*255
    return three_channel_thresholded_image

def draw_sliding_window(image):
    #crop to bottom half of image
    crop_img = image[600:720,0:1280]
    histogram = np.sum(crop_img[:,:,0],axis = 0)

    #find peaks that are greater than the average and some standard deviation
    mean = np.mean(histogram, axis = 0)
    std = np.std(histogram, axis = 0)

    #min peak cutoff
    cutoff = mean+std*3

    plt.plot(histogram)
    plt.plot([0, len(histogram)], [mean+std*2, mean+std*2], color='k', linestyle='-', linewidth=2)
    plt.show()
    
    binsize = 10
    maxes = list() 
    #find peak in each bin
    for i in range(0,binsize):
        leftbound = int(i*1280/binsize)
        rightbound = int((i+1)*1280/binsize)
        midpoint = int((leftbound+rightbound)/2)
        binmax = np.amax(histogram[:][leftbound:rightbound],axis=0)
        if (binmax>cutoff):
            maxes.append([midpoint,binmax])
        
    # Hyperparameters
    # choose the number of sliding windows
    nwindows = 20 
    # Set the width of the windows +/- margin
    margin = 100 
    # Set the minimum number of the pixels to recenter the windows
    minpix = 50
    # Set height of the windows - based on nwindows above and image shape
    window_height = image.shape[0] // nwindows

    # Identify the x and y positions of all nonzero (i.e. activated) pixels in the image
    nonzero = image.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    # Current positions to be updated later for each window in nwindows
    for i in range(0,len(maxes)):
        leftx_current = maxes[i][0]

        # Create empty lists to receive left and right lane pixel indices
        left_lane_inds = []

        for window in range(nwindows):
            #Identify window boundaries in x and y
            win_y_low = image.shape[0] - (window+1)*window_height
            win_y_high = image.shape[0] - window*window_height
            win_xleft_low = leftx_current - margin
            win_xleft_high = leftx_current + margin

            # Draw the windows on the visualization image
            cv2.rectangle(image,(win_xleft_low,win_y_low),(win_xleft_high,win_y_high),(0,255,0), 2)

            # Identify the nonzero pixels in x and y within the window
            good_left_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xleft_low) &  (nonzerox < win_xleft_high)).nonzero()[0]
            # Append these indices to the lists
            left_lane_inds.append(good_left_inds)
            #if more than minpix pixels were found , recenter next window on their mean position
            if len(good_left_inds) > minpix:
                leftx_current = np.int(np.mean(nonzerox[good_left_inds]))
        # Concatenate the arrays of indices (previously was a list of lists of pixels)
        left_lane_inds = np.concatenate(left_lane_inds)

        # Extract left and right line pixel positions
        leftx = nonzerox[left_lane_inds]
        lefty = nonzeroy[left_lane_inds]

        # Generate x and y values for plotting
        ploty = np.linspace(0, image.shape[0]-1, image.shape[0])
        try:
            # Fit a second order polynomial to each set of lane points
            left_fit = np.polyfit(lefty, leftx, 2)
            left_fitx = left_fit[0]*ploty**2 + left_fit[1]*ploty + left_fit[2]
        except TypeError:
            # Avoids an error if `left` and `right_fit` are still none or incorrect
            left_fitx = 1*ploty**2 + 1*ploty

        # Highlightign the left and right lane regions
        image[lefty, leftx] = [255, 0, 0]

        # Draw the lane onto the warped blank image
        plt.plot(left_fitx,ploty, color='yellow')

    return image

# highlights the lane in the original video stream
def highlight_lane_original(image):

    # process the image to undistort, apply s and sobel thresholding
    # and warp it into the bird's eye view
    processed_image = process_image(image)

    #crop to bottom half of image
    crop_img = processed_image[600:720,0:1280]
    histogram = np.sum(crop_img[:,:,0],axis = 0)
    # find the peaks of the left and right halves of the histogram
    # as the starting point for the left and right lines
    midpoint = np.int(histogram.shape[0]//2)
    leftx_base = np.argmax(histogram[:midpoint])
    rightx_base = np.argmax(histogram[midpoint:])+midpoint
    # Hyperparameters
    # choose the number of sliding windows
    nwindows = 30
    # Set the width of the windows +/- margin
    margin = 50 
    # Set the minimum number of the pixels to recenter the windows
    minpix = 50
    # Set height of the windows - based on nwindows above and image shape
    window_height = processed_image.shape[0] // nwindows

    # Identify the x and y positions of all nonzero (i.e. activated) pixels in the image
    nonzero = processed_image.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    # Current positions to be updated later for each window in nwindows
    leftx_current = leftx_base
    rightx_current = rightx_base

    # Create empty lists to receive left and right lane pixel indices
    left_lane_inds = []
    right_lane_inds = []
    for window in range(nwindows):
        #Identify window boundaries in x and y
        win_y_low = processed_image.shape[0] - (window+1)*window_height
        win_y_high = processed_image.shape[0] - window*window_height
        win_xleft_low = leftx_current - margin
        win_xleft_high = leftx_current + margin
        win_xright_low = rightx_current - margin
        win_xright_high = rightx_current + margin


        # Identify the nonzero pixels in x and y within the window
        good_left_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xleft_low) &  (nonzerox < win_xleft_high)).nonzero()[0]
        good_right_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xright_low) &  (nonzerox < win_xright_high)).nonzero()[0]
        # Append these indices to the lists
        left_lane_inds.append(good_left_inds)
        right_lane_inds.append(good_right_inds)
        #if more than minpix pixels were found , recenter next window on their mean position
        if len(good_left_inds) > minpix:
            leftx_current = np.int(np.mean(nonzerox[good_left_inds]))
        if len(good_right_inds) > minpix:
            rightx_current = np.int(np.mean(nonzerox[good_right_inds]))
    # Concatenate the arrays of indices (previously was a list of lists of pixels)
    left_lane_inds = np.concatenate(left_lane_inds)
    right_lane_inds = np.concatenate(right_lane_inds)

    # Extract left and right line pixel positions
    leftx = nonzerox[left_lane_inds]
    lefty = nonzeroy[left_lane_inds]
    rightx = nonzerox[right_lane_inds]
    righty = nonzeroy[right_lane_inds]


    # Generate x and y values for plotting
    ploty = np.linspace(0, processed_image.shape[0]-1, processed_image.shape[0])
    try:
        # Fit a second order polynomial to each set of lane points
        left_fit = np.polyfit(lefty, leftx, 2)
        right_fit = np.polyfit(righty, rightx, 2)
        left_fitx = left_fit[0]*ploty**2 + left_fit[1]*ploty + left_fit[2]
        right_fitx = right_fit[0]*ploty**2 + right_fit[1]*ploty + right_fit[2]
    except TypeError:
        # Avoids an error if `left` and `right_fit` are still none or incorrect
        left_fitx = 1*ploty**2 + 1*ploty
        right_fitx = 1*ploty**2 + 1*ploty

    # Highlightign the left and right lane regions
    # drawing the left and right polynomials on the lane lines
    pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
    pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
    pts = np.hstack((pts_left, pts_right))

    blank_image = np.zeros_like(processed_image)
    # Draw the lane onto a blank warped image
    cv2.fillPoly(blank_image, np.int_([pts]), (0,255, 0))

    # change the perspective back into the original view
    unwarped_image = unwarp(blank_image)

    # add the unwarped processed image to the original image
    weighted_image = cv2.addWeighted(image, 1.0, unwarped_image, .7, 0)
    return weighted_image

#test stuff
for i in range(0,10):
    image_name = str(i) + '.jpg'
    image = cv2.imread('images/'+image_name)
# crop away the text on the bottom of the image
#ymax = 650
#xmax = 1280
#mask = np.zeros(image.shape[:2],np.uint8) #720x1280
#mask[0:ymax,0:xmax] = 255
#image = cv2.bitwise_and(image,image,mask = mask)
#crop_img = image[0:650, 0:1280]

#warped_image = warp(image)
#unwarped_image = unwarp(warped_image)

    test_image = process_image(image)
    sw = draw_sliding_window(test_image)
#un_sw = unwarp(sw)
    plt.imshow(sw)
    plt.show()


#out = highlight_lane_original(image)
    cv2.imwrite('output_images/'+image_name,sw)

#plt.imshow(un_sw)
#plt.show()
#plt.imshow(out)
#plt.show()

#video exporting stuff
    ##clip1 = VideoFileClip("test_videos/solidWhiteRight.mp4").subclip(0,5)
    #output_file_path = 'output_images/vid.mp4'
    #input_video = VideoFileClip("images/vid.mp4")
    #output_video = input_video.fl_image(highlight_lane_original) #NOTE: this function expects color images!!
    #output_video.write_videofile(output_file_path, audio=False)

#find reference points
    #plt.imshow(image)
    #plt.plot(1010,530,'.')
    #plt.plot(180,530,'.')
    #plt.plot(360,250, '.')
    #plt.plot(830,250,'.')
    #plt.show()
