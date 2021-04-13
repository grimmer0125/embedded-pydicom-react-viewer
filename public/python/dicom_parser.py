import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut
from my_js_module import buffer
import numpy as np

print("get buffer from javascript")
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
# 2d -> 1d -> 1d *4 (each array value -copy-> R+G+B+255)
# NOTE: 1st memory copy/allocation
image = np.zeros(4*width*height)
value_range = max - min
for k in range(0, width*height):
    row: int = k // width
    column: int = k % width
    value = image2d[row][column]
    value = (value - min) * 255 / value_range
    i = k*4
    image[i] = value
    image[i + 1] = value
    image[i + 2] = value
    image[i + 3] = 255
print("flatten to 2d RGB array ok")
image, min, max, width, height
