# -*- coding: utf-8 -*-
"""
Created on Fri Dec 29 22:31:57 2017

@author: vikto
"""

import numpy as np
from skimage import io
import matplotlib.pyplot as plt
import time
#%% setting global variables
intensity_black = 455
intensity_white = 0
feedrate_white = 2000
feedrate_black = 850
#%%
def weight_distance (m1,m2,n1,n2):
    return max(abs(m1-m2),abs(n1-n2))
#%%
def get_feedrate(brightness):
    return  brightness/255.0 * (feedrate_white - feedrate_black) + feedrate_black
#%%
def get_intensity(brightness):
    return (1.0 - brightness/255.0) * (intensity_black - intensity_white) + intensity_white
#%% import image
filename = 'hello'
fileextension = '.png'
img = io.imread('images' + '\\' + filename + fileextension) 
gcodefile = filename + ".gco"
#%% normalize
image = np.zeros((img.shape[0], img.shape[1]))
image = (img[:,:,0] + img[:,:,1] + img[:,:,2] ) / 3
image = image/np.max(image)
image_tmp = np.copy(image)
plt.figure()
plt.imshow(image)
#%%
#factor = 5
#image_copy = np.copy(image)
#image_pom = np.zeros((ceil(image.shape[0]/factor), ceil(image.shape[1]/factor)))
#for i in range(image_pom.shape[0]):
#    for j in range(image_pom.shape[1]):
#        image_pom[i,j] = np.mean(image_copy[factor*i:factor*(i+1),factor*j:factor*(j+1)])
#plt.figure()
#plt.imshow(image_pom)
#image_pom_save = np.copy(image_pom)
#%% distance
starting_row = 0
starting_col = 0
first_row = 0
first_col = 0
last_row = 0
last_col = 0
min_dist = image.size
max_dist = 0
distances = np.zeros_like(image)
white_thresh = 0.9
i_max = image.shape[0]
j_max = image.shape[1]
for i in range(image.shape[0]):
    for j in range(image.shape[1]):
        if image[i,j] <= white_thresh:
            distances[i,j] = weight_distance(starting_row,i,starting_col,j) 
            if distances[i,j] < min_dist:
                first_row,first_col = (i,j)
                min_dist = distances[i,j]
            if distances[i,j] > max_dist:
                last_row,last_col = (i,j)
                max_dist = distances[i,j]
plt.imshow(distances)
#%% изминување на матрицата
file = open(gcodefile,'w')
image_copy = np.copy(image)
#i,j=(first_row,first_col)
i,j = (0,0)
count = 0;
max_count = image_copy.size
change_made = 0
i_remember = first_row
j_remember = first_col
i_last = 0
j_last = 0
direction_remember = 1
remember = 0
direction_up_down = 1
"""
direction_up_down = 1 == up ----> down
direction_up_down = -1 == up <---- down 
"""
direction_left_right = 1
"""
direction_left_right = 1 == left ----> right
direction_left_right = -1 == left <---- right 
"""
end_reached = -1 # 1 = end reached ; -1 = end not reached
just_to_save_some_time = 0
# -------------------------------------------
# setting gcode
# -------------------------------------------
gcode = "" 
gcode += '%\n'
gcode += "O testing enhanced engraving \n" # do I need this at all?
gcode += "F1000 \n" # setting initial value to the laser
gcode += "M3S0 \n" # set the laser on
gcode += "G0" + "X" + str(first_row/200) + "Y" + str(first_col/200) + "Z0\n" 

# starting the loop
#while (np.mean(image_copy)<0.999):
while (np.mean(image_copy) != 1):

#    count = count + 1
#    if count > max_count:
#        print("Ja pretera malku")
#        break
#    print(i,j)
#    time.sleep(0.01)
    
    # checking if i and j are out of boundaries 
    if i >= i_max: # I was going down, but I reached the end, so I start going up
        i = i_max - 1
        direction_up_down = -1
    if i < 0: # I was going up, but I reached the bottom, so I start going down
        i = 1
        direction_up_down = -1        
    if j >= j_max:
        direction_left_right = -1
        i = i+1
    if j < 0:
        direction_left_right = 1
        j = j+1
        
    # if i and j are changed, give new commands to gcode     
    if change_made:
        # for right gcode here will come: if image_copy[i,j] <= white_thresh:
        change_made = 0
        # now setting the gcode parameters 
        y_gcode = "Y"+str(j/200) if j != j_last else ""
        x_gcode = "X"+str(i/200) if i != i_last else ""
        gcode += "G1" if j != j_last or i != i_last else "G0"
        gcode += x_gcode + y_gcode
        gcode += ("F" + str(get_feedrate(image_copy[i,j])) + "S" + str(get_intensity(image_copy[i,j]))) if j==j_last or i==i_last else ""
        gcode += '\n'
        image_copy[i,j] = 1
        i_last = i
        j_last = j
        
    # find next pixel
    if direction_left_right == 1: # moving left ----> right
        for factor in range (1,5):
            if j+factor<=j_max:
                if image_copy[i,j+factor] <= white_thresh:
                    j = j + factor
                    change_made = 1
                    end_reached = -1
    #                print ("move to the positive direction with factor: ", factor)
                    break
            
        if change_made != 1:
            for factor in range (5,-5,-1):
                if j+factor<=j_max and j+factor>=0 and i+direction_up_down<i_max and i+direction_up_down>0:
                    if image_copy[i+direction_up_down,j+factor] <= white_thresh:
                        i = i + direction_up_down
                        j = j + factor
                        direction_left_right *= -1 
                        change_made = 1
                        end_reached = -1
                        break
    else: # moving left <---- right
        for factor in range (1,5):
            if j-factor>=0:
                if image_copy[i,j-factor] <= white_thresh:
                    j = j - factor
    #                i = i+1
                    change_made = 1
                    end_reached = -1
    #                print ("move to the negative direction with factor: ", factor)
                    break
        if change_made != 1:
            for factor in range (-5,5):
                if j+factor<=j_max and j+factor>=0 and i+direction_up_down<i_max and i+direction_up_down>0:
                    if image_copy[i+direction_up_down,j+factor] <= white_thresh:
                        i = i + direction_up_down
                        j = j + factor
                        direction_left_right *= -1 
                        change_made = 1
                        end_reached = -1
                        break
    
    # find a possible position that could have been skipped
    if remember == 1 and (i_remember != i or j_remember != j): # TODO: some error might occur here
#        print ("I already remember something, I don't need a new value")
        just_to_save_some_time = 1
    else:
        if direction_left_right == 1:
            for j_next in range (j+5,j_max):
                if image_copy[i,j_next] <= white_thresh and j_next <= j_max:
#                    print("entered here, just for debugging")
                    j_remember = j_next
                    i_remember = i
                    if change_made != 1:
                        i = i+1
                        j = 0
                        change_made = 1
                    remember = 1
                    direction_remember = 1
#                    print ("I have future value in the positive direction", i_remember, j_remember)
                    break
        else:
            for j_next in range (j-5,-1,-1):
                if image_copy[i,j_next] <= white_thresh and j_next >= 0:
                    j_remember = j_next
                    i_remember = i
                    if change_made != 1:
                        i = i+1
                        j = 0
                        change_made = 1
                    remember = 1
                    direction_remember = -1
#                    print ("I have future value in the negative direction",  i_remember, j_remember)
                    break

    # if a new value is set to i or j continue                
    if change_made == 1:
        continue
    # if there is no new pixel in close surrounding, move to the pixels that are remembered
    if remember == 1:
        i = i_remember
        j = j_remember
        remember = 0
        end_reached = -1
#        print ("now use the remembered value")
        continue
    
#    print ("the direction now is: ", direction_left_right)
    if end_reached == -1:
        i = i + direction_up_down
        direction_left_right = direction_left_right * (-1)
        change_made = 1
        end_reached = 1
#        print ("I am at the end, the direction is: ", direction_left_right)
    else:
        direction_left_right = direction_left_right * (-1)
        change_made = 1
        end_reached = -1
#        print ("I was once at the end, the direction is: ", direction_left_right)
gcode += ";EndImage\nM5\n"
plt.imshow(image_copy+image)
file.write(gcode)
file.close
#%%
br = 0
for ii in range (image.shape[0]):
    for jj in range(image.shape[1]):
        if image[ii,jj] <= white_thresh:
            br = br + 1
print (br)            
#%%
            
        





















#%% gcode generator
def generate_gcode(self, img, x,y,w,h, file_id):
	settings_comment = self.get_settings_as_comment(x,y,w,h, "")
	self._log.info("img2gcode conversion started:\n%s" % settings_comment)
	x += self.beam/2.0
	y -= self.beam/2.0
	direction_positive = True
	self._append_gcode(self.get_settings_as_comment(x,y,w,h, file_id))
	self._append_gcode('F' + str(self.feedrate_white) + '\n') # set an initial feedrate
	self._append_gcode('M3S0\n') # enable laser
	last_y = -1

	(width, height) = img.size

	# iterate line by line
	pix = img.load()
	for row in range(height-1,-1,-1):
		row_pos_y = y + (height - row) * self.beam # inverse y-coordinate as images have 0x0 at left top, mr beam at left bottom
		# back and forth
		pixelrange = range(0, width) if(direction_positive) else range(width-1, -1, -1)

		lastBrightness = self.ignore_brighter_than + 1
		for i in pixelrange:
			px = pix[i, row]
			#brightness = self.get_alpha_composition(px)
			brightness = px
			if(brightness != lastBrightness ):
				if(i != pixelrange[0]): # don't move after new line
					xpos = x + self.beam * (i-1 if (direction_positive) else (i)) # calculate position; backward lines need to be shifted by +1 beam diameter
					self._append_gcode(self.get_gcode_for_equal_pixels(lastBrightness, xpos, row_pos_y, last_y))
					last_y = row_pos_y
			else:
				pass # combine equal intensity values to one move
            
			lastBrightness = brightness

		if(not self._ignore_pixel_brightness(brightness) and self.get_intensity(brightness) > 0): # finish non-white line
			end_of_line = x + pixelrange[-1] * self.beam
			self._append_gcode(self.get_gcode_for_equal_pixels(brightness, end_of_line, row_pos_y, last_y))
			last_y = row_pos_y

		# flip direction after each line to go back and forth
		direction_positive = not direction_positive

	self._append_gcode(";EndImage\nM5\n") # important for gcode preview!
	return self._output_gcode