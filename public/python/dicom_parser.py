import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut
from my_js_module import buffer
print("get buffer from javascript")
# print(buffer) #  memoryview object.
ds = pydicom.dcmread(io.BytesIO(buffer))
# name = ds.PatientName
# print("family name:"+name.family_name)
arr = ds.pixel_array
image = apply_modality_lut(arr, ds)
min = image.min()
max = image.max()
print(f'pixel (after lut) min:{min}')
print(f'pixel (after lut) max:{max}')
image, min, max
