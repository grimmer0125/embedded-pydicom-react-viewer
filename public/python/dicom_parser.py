import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut
from my_js_module import buffer
import numpy as np

print("get buffer from javascript, copy memory to wasm heap")
# print(buffer) #  memoryview object.
ds = pydicom.dcmread(io.BytesIO(buffer))
# name = ds.PatientName
# print("family name:"+name.family_name)
arr = ds.pixel_array
image2d = apply_modality_lut(arr, ds)
min = image2d .min()
max = image2d .max()
print(f'pixel (after lut) min:{min}')
print(f'pixel (after lut) max:{max}')
width = len(image2d[0])
height = len(image2d)
print(f'width:{width};height:{height}')

# 2d -> 1d -> 1d *4 (each array value -copy-> R+G+B+A)
# NOTE: 1st memory copy/allocation
image = np.zeros(4*width*height, dtype="uint8")
print("allocate a 1d array")
value_range = max - min

# ISSUE: Below may takes 4s for a 512x512 image, even already use 2nd method: two loop. 
# still 3.5~4s
# Using JS is much faster: <0.5s 
for i_row in range(0, height):
    for j_col in range(0, width):
        store_value = image2d[i_row][j_col]
        value = (store_value - min) * 255 / value_range
        k =  4* (i_row*width + j_col) 
        image[k] = value
        image[k + 1] = value
        image[k + 2] = value
        image[k + 3] = 255
print("2d grey array flattens to 1d RGBA array ok")

# ISSUE: instead of v0.17.0a2, if using latest dev code, this numpy.uint16 value becomes empty in JS !!!
# so we need to use int(min), int(max)
print(f'min type is:{type(min)}')  # numpy.uint16
print(f'max type is:{type(width)}')

if __name__ == '__main__':
    # will not be executed
    print("it is main, for testing")

image, int(min), int(max), width, height
