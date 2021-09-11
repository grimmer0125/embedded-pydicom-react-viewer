from dataclasses import dataclass
import sys
import os
import pydicom
from pydicom import FileDataset
from pydicom.dicomdir import DicomDir
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_color_lut
import numpy as np
import time
from io import BytesIO
from typing import Any, Union

from pydicom.encaps import defragment_data, decode_data_sequence


compressed_list = ["1.2.840.10008.1.2.4.50", "1.2.840.10008.1.2.4.51", "1.2.840.10008.1.2.4.57", "1.2.840.10008.1.2.4.70",
                   "1.2.840.10008.1.2.4.80", "1.2.840.10008.1.2.4.81", "1.2.840.10008.1.2.4.90", "1.2.840.10008.1.2.4.91"]


handling_list = ["1.2.840.10008.1.2.4.57", "1.2.840.10008.1.2.4.70"]

#### Testing interaction between JS and Pyodide ####


@dataclass
class Test:
    a: int = 5

    def test_a(self):
        self.a += 100


try:
    bb
except NameError:
    print("well, it WASN'T defined after all!")
    bb = Test()
    x = []

####


@dataclass
class PyodideDicom:
    uncompressed_ndarray: np.ndarray = None
    width: int = None
    height: int = None
    max: int = None
    min: int = None
    photometric: str = None
    transferSyntaxUID: str = None
    allocated_bits: int = None
    ds: Union[FileDataset, DicomDir] = None
    compressed_pixel_bytes: bytes = None

    def get_pydicom_dataset_from_js_buffer(self, buffer_memory):
        print("get buffer from javascript, copied memory to wasm heap, start to read dicom")
        # file_name = "image-00000-ot.dcm"
        ds = pydicom.dcmread(BytesIO(buffer_memory), force=True)
        print("read dicom ok")
        # patient_name = ds.PatientName
        # print("patient family name:"+patient_name.family_name)
        return ds

    def get_pydicom_dataset_from_local_file(self, path):
        ds = pydicom.dcmread(path, force=True)
        print("read dicom ok")
        return ds

    def get_manufacturer_independent_pixel_image2d_array(self, ds, transferSyntaxUID: str, decoder: Any):

        # 8,8 or 16,12
        allocated_bits = ds[0x0028, 0x0100].value
        stored_bites = ds[0x0028, 0x0101].value
        pr = ds[0x0028, 0x0103].value
        print(f"pr:{pr}")
        print(f"allocated_bits:{allocated_bits}")
        print(f"stored_bites:{stored_bites}")

        # '1.2.840.10008.1.2.4.90'  #
        # ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.4.99'  # '1.2.840.10008.1.2.1.99'
        # has_TransferSyntax = True
        # print(f"syntax:{ds.file_meta.TransferSyntaxUID}")
        # RLE 1.2.840.10008.1.2.5:  US-PAL-8-10x-echo.dcm is automatically handled as uncompressed case
        if (transferSyntaxUID and transferSyntaxUID in compressed_list):
            print("compressed case !!!!!!!!!")

            # return None, ds.PixelData
        # ref: https://github.com/pydicom/pydicom/blob/master/pydicom/pixel_data_handlers/pillow_handler.py
            print("try to get compressed dicom's pixel data manually, can not handle by pydicom in pyodide, lack of some pyodide extension")
            try:
                print(f"pixeldata:{len(ds.PixelData)}")  # 2126020

                # TODO: only get 1st frame for multiple frame case and will improve later
                if getattr(ds, 'NumberOfFrames', 1) > 1:
                    print("multi frame")
                    j2k_precision, j2k_sign = None, None
                    # multiple compressed frames
                    # working case (50):
                    # 1. 0002.dcm, some are [-5], [-4], [-6]. 512x512
                    # 2. color3d_jpeg_baseline , some frames needs [-1] but some do not need. size unknown?
                    frame_count = 0
                    for frame in decode_data_sequence(ds.PixelData):
                        frame_count += 1
                        # print(f"frame i:{frame_count}, len:{len(frame)}")
                        # a = frame[0]
                        # b = frame[1]
                        # c = frame[len(frame)-2]
                        # d = frame[len(frame)-1]
                        # print(f"{a},{b},{c},{d}")
                        if frame_count == 1:
                            pixel_data = frame
                        # im = _decompress_single_frame(
                        #     frame,
                        #     transfer_syntax,
                        #     ds.PhotometricInterpretation
                        # )
                        # if 'YBR' in ds.PhotometricInterpretation:
                        #     im.draft('YCbCr', (ds.Rows, ds.Columns))
                        # pixel_bytes.extend(im.tobytes())

                        # if not j2k_precision:
                        #     params = get_j2k_parameters(frame)
                        #     j2k_precision = params.setdefault("precision", ds.BitsStored)
                        #     j2k_sign = params.setdefault("is_signed", None)
                    # TODO: what is the rule of -5/-1? But even not using pixel_data[:-1], pixel_data[:-5], still work
                    p2 = pixel_data
                else:
                    print("single frame")
                    # working case but browser can not render :
                    # - JPGLosslessP14SV1_1s_1f_8b.dcm,  DICOM made JPEG Lossless, 1.2.840.10008.1.2.4.70. 1024x768. local mac is able to view.
                    # - JPEG57-MR-MONO2-12-shoulder.dcm from https://barre.dev/medical/samples/, JPEG Lossless, 1.2.840.10008.1.2.4.57.
                    #   https://products.groupdocs.app/viewer/jpg can be used to view. local mac seeme not able to view (all black)
                    # - JPEG-lossy.dcm 1.2.840.10008.1.2.4.51 from https://github.com/pydicom/pydicom/blob/master/pydicom/data/test_files/JPEG-lossy.dcm,
                    #   https://products.groupdocs.app/viewer/jpg can be used to view, local mac seems not able to view (all black)

                    pixel_data = defragment_data(ds.PixelData)
                    p2 = pixel_data
                print(f"pixel_data:{len(p2)}, {type(p2)}")  # bytes
                # return None, pixel_data
                numpy_array = None
                if transferSyntaxUID in handling_list:

                    # try:
                    #     fio = BytesIO(ds.PixelData)  # pixel_data)
                    #     image = Image.open(fio)
                    # except Exception as e:
                    #     print(f"pillow error:{e}")

                    # print('pillow done')
                    # JPEG57-MR-MONO2-12-shoulder data:718940 -> data:718924
                    # python bytes -> unit8array -> arrayBuffer
                    # p2 is arrayBuffer?
                    # cols * rows * bytesPerComponent * numComponents
                    b = decoder.decompress(p2)  # ArrayBuffer
                    # print(type(b))  # <class 'pyodide.JsProxy'> #
                    # print(f"b:{b}")  # b:[object ArrayBuffer]
                    b2 = b.to_py()
                    print(f"b size:{len(b2)}")
                    # print(f"b2:{b2}")  # <memory at 0x20adfe8> memoryview

                    # numpy_array = np.asarray(b2, dtype=np.uint8)
                    # dt = np.dtype(np.uint16)
                    # https://numpy.org/doc/stable/reference/generated/numpy.frombuffer.html?highlight=frombuffer#numpy.frombuffer
                    # https://numpy.org/doc/stable/reference/generated/numpy.dtype.byteorder.html
                    # print(f"order:{dt.byteorder}") # native. guess probably is big endian
                    # todo: handle PR=1(signed number)
                    if allocated_bits == 16:
                        print("unit16")
                        numpy_array = np.frombuffer(b2, dtype=np.uint16)
                    else:
                        print("uint8")
                        numpy_array = np.frombuffer(b2, dtype=np.uint8)
                    # print(f"numpy:{numpy_array}")
                    # 1024*1024*2 or 1024*768
                    print(f"shape:{numpy_array.shape}")

                    return numpy_array, p2
                return None, p2
            except Exception as e:
                print("failed to get compressed data")
                raise e

        print("incompressed")
        print("start reading dicom pixel_array, uncompressed case uses apply_modality_lut")

        try:
            arr = ds.pixel_array
        except Exception as e:
            if transferSyntaxUID:
                raise e
            else:
                # http://dicom.nema.org/dicom/2013/output/chtml/part05/chapter_10.html
                print(
                    "read data fail may due to no TransferSyntaxUID, set it as most often used and default ImplicitVRLittleEndian and try read dicom again")
                ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
                arr = ds.pixel_array
        print(f"read dicom pixel_array ok, shape:{arr.shape}")
        image2d = apply_modality_lut(arr, ds)
        return image2d, None

    def get_image2d_maxmin(self, image2d):
        print("start to get max/min")
        start = time.time()
        _min = image2d.min()
        end = time.time()
        # 0.0009999275207519531 / 0.0002989768981933594 (pyodide : local python)
        print(f"1. min time :{end-start}")
        start = time.time()
        _max = image2d.max()
        end = time.time()
        print(f"2. max time :{end-start}")  # 0.0 / 0.00027108192443847656
        print(f'pixel min:{_min}')
        print(f'pixel max:{_max}')  # 255
        return _max, _min

    def get_image2d_dimension(self, image2d):
        width = len(image2d[0])
        height = len(image2d)
        print(f'width:{width};height:{height}')
        return width, height

    def normalize_image2d(self, image2d, _max, _min):
        # width = len(image2d[0])
        # height = len(image2d)

        print("start to normalization")
        # step1: normalize
        start = time.time()
        # print(f"center pixel:{image2d[height//2][width//2]}")
        # step1: normalize
        # ref: https://towardsdatascience.com/normalization-techniques-in-python-using-numpy-b998aa81d754
        # or use sklearn.preprocessing.minmax_scale, https://stackoverflow.com/a/55526862
        # scale = np.frompyfunc(lambda x, min, max: (x - min) / (max - min), 3, 1)
        value_range = _max - _min
        # 0.003, if no astype, just 0.002. using // become 0.02
        # or using colormap is another fast way,
        image2d = (((image2d-_min)/value_range)*255).astype("uint8")
        print(f"normalize time:{time.time()-start}")
        # print(f"after normalize, center pixel:{image2d[height//2][width//2]}")
        return image2d

    def flatten_rgb_image2d_plan0_to_rgba_1d_image_array(self, image2d):

        # US-PAL-8-10x-echo.dcm
        # ValueError: all the input arrays must have same number of dimensions,
        # but the array at index 0 has 4 dimension(s) and the array at index 1 has 3 dimension(s)

        # color-by-pixel
        # Planar Configuration = 0 -> R1, G1, B1, R2, G2, B2, …
        # e.g. US-RGB-8-esopecho.dcm (120, 256, 3)
        width = len(image2d[0])
        height = len(image2d)
        alpha = np.full((height, width), 255)
        stacked = np.dstack((image2d, alpha))
        print(f"shape:{stacked.shape}")
        image = stacked.flatten()
        image = image.astype("uint8")
        return image

    def flatten_rgb_image2d_plan1_to_rgba_1d_image_array(self, image2d):
        # color by plane
        # Planar Configuration = 1 -> R1, R2, R3, …, G1, G2, G3, …, B1, B2, B3
        # e.g. US-RGB-8-epicard.dcm (480, 640, 3)

        # TODO/ISSUE:
        # The shape of testing DICOM file is like planar 0 and below just work
        # weird for RGB w/ planar 1 !!!

        # Originally I guess the shape is not correcct, found out the below link :
        # https://stackoverflow.com/questions/42650233/how-to-access-rgb-pixel-arrays-from-dicom-files-using-pydicom
        # image2d = image2d.reshape([image2d.shape[1], image2d.shape[2], 3]) <- not work

        # The final trial is just use the same function as planar 0
        # The only possible explanation is pydicom automatically read it as same shape for both cases

        return self.flatten_rgb_image2d_plan0_to_rgba_1d_image_array(image2d)

    def flatten_grey_image2d_to_rgba_1d_image_array(self, image2d):
        print("flatten_grey_image2d_to_rgba_1d_image_array")
        # 3 planes. R plane (z=0), G plane (z=1), B plane (z=2)
        width = len(image2d[0])
        height = len(image2d)

        # https://stackoverflow.com/questions/63783198/how-to-convert-2d-array-into-rgb-image-in-python
        # step2: 2D grey -> 2D RGBA -> Flatten to 1D RGBA
        start = time.time()
        alpha = np.full((height, width), 255)  # ~
        stacked = np.dstack((image2d, image2d, image2d, alpha))
        print(f"stacked shape:{stacked.shape}")  # 512x 512x 4
        image = stacked.flatten()
        print(f"final shape:{image.shape}, type:{image.dtype}")  # int32
        image = image.astype("uint8")
        print(f"flatten time:{time.time()-start}")  # 0.002s
        return image

    def flatten_grey_image2d_to_rgba_1d_image_array_non_numpy_way(image2d):
        ''' This is depreciated
        '''
        width = len(image2d[0])
        height = len(image2d)

        # 2d -> 1d -> 1d *4 (each array value -copy-> R+G+B+A)
        # NOTE: 1st memory copy/allocation
        image = np.zeros(4*width*height, dtype="uint8")
        print("allocated a 1d array, start to flatten 2d grey array to RGBA 1d array")
        # ISSUE: Below may takes 3~4s for a 512x512 image, Using JS is much faster: <0.5s !!
        # Also, the wired thing is image2d.min()/max() is fast. Need more study/measurement.
        delta1 = 0
        delta2 = 0
        delta3 = 0
        delta4 = 0
        delta5 = 0
        delta6 = 0
        delta7 = 0
        # local python: 0.65s
        # pyodide: 7.266s
        for i_row in range(0, height):
            for j_col in range(0, width):
                start = time.time()
                # 0.8350014686584473 / 0.06848788261413574
                store_value = image2d[i_row][j_col]
                # end = time.time()
                delta1 += time.time() - start
                start = time.time()
                # 4.2840001583099365 / 0.32952332496643066
                # Issue:  (store_value - min) * 255 / value_range <- normalization
                # 1. slow
                # 2. final image seems wrong
                value = store_value  #
                # value = store_value
                delta2 += time.time() - start
                start = time.time()
                # 0.41300106048583984 / 0.04794716835021973
                k = 4 * (i_row*width + j_col)
                delta3 += time.time() - start
                start = time.time()
                image[k] = value  # 0.4740023612976074 / 0.05642890930175781
                delta4 += time.time() - start
                start = time.time()
                # 0.44700074195861816 / 0.05257463455200195
                image[k + 1] = value
                delta5 += time.time() - start
                start = time.time()
                # 0.42699670791625977 / 0.048801422119140625
                image[k + 2] = value
                delta6 += time.time() - start
                start = time.time()
                image[k + 3] = 255  # 0.3860006332397461 / 0.04797720909118652
                delta7 += time.time() - start
        total = delta1 + delta2 + delta3 + delta4 + delta5 + delta6 + delta7
        print(
            f"2d grey array flattens to 1d RGBA array ok:{total}")
        print(f"{delta1}, {delta2}, {delta3}, {delta4}, {delta5}, {delta6}, {delta7}")

    def is_pyodide_env(self):
        if "pyodide" in sys.modules or "PYODIDE" in os.environ:
            return True
        return False

    def __init__(self, buffer: Any = None):
        print("__init__!!!!!!!!!!!!!")
        if self.is_pyodide_env():
            if buffer is None:
                print("buffer is None")
                from my_js_module import buffer  # pylint: disable=import-error
                # from my_js_module import decoder  # pylint: disable=import-error
                # from my_js_module import newDecoder

                ## test life cycle in pyodide ##
                # print(f"class22: {bb.a}")
                # global x
                # x.append(10)

                # ## testing if python can access JS' user defined objects' methods ##
                # from my_js_module import add, polygon
                # k2 = add(5)
                # polygon.addWidth()  # works
                # print(f"k2:{k2}")
            else:
                print("buffer is not None")
                from my_js_module import jpeg

            ds = self.get_pydicom_dataset_from_js_buffer(buffer.to_py())
        else:
            # deprecated, use plot.py to do local experiment
            # start to do some local Python stuff, e.g. testing
            ds = self.get_pydicom_dataset_from_local_file(
                "dicom/image-00000-ot.dcm")

        width = ds[0x0028, 0x0011].value
        height = ds[0x0028, 0x0010].value
        print(f'dimension: {width}; {height}')
        allocated_bits = ds[0x0028, 0x0100].value

        transferSyntaxUID = ""
        try:
            transferSyntaxUID = ds.file_meta.TransferSyntaxUID
            print(f"transferSyntax:{transferSyntaxUID}")
        except:
            print("no TransferSyntaxUID")
        try:
            photometric = ds.PhotometricInterpretation
            print(
                f"photometric:{photometric}")
        except:
            print("no photometric")
            photometric = ""
        self.photometric = photometric
        frame_number = getattr(ds, 'NumberOfFrames', 1)
        print(f"frame_number:{frame_number}")

        if photometric == "PALETTE COLOR":
            print("it is PALETTE COLOR")
            # https://pydicom.github.io/pydicom/stable/old/working_with_pixel_data.html
            # before: a grey 2d image
            image2d = apply_color_lut(ds.pixel_array, ds)
            # after: a RGB 2d image
            print(f"PALETTE after apply_color_lut shape:{image2d.shape}")

            # _max, _min = get_image2d_maxmin(image2d)
            # print(f'pixel (after color lut) min:{_min}')  # min same as before
            # print(f'pixel (after color lut) max:{_max}')  # max same as before
            # but still need normalization (workaround way?) !!! Undocumented part !!!!
            # Mabye it is because its max (dark) is 65536, 16bit
            # image2d = normalize_image2d(image2d, _max, _min)
        else:
            # https://github.com/pyodide/pyodide/discussions/1273
            image2d, compress_pixel_data = self.get_manufacturer_independent_pixel_image2d_array(
                ds, transferSyntaxUID, jpeg.lossless.Decoder.new())
            print(
                f"after get_manufacturer_independent_pixel_image2d_array")
            # todo: using image2d == None will throw a error which says some element is ambiguous
            if image2d is None and compress_pixel_data is not None:
                # return bytes data
                # TODO: how to add width, height ?
                print(
                    f"directly return compressed data")
                # Columns (0028,0011), Rows (0028,0010)

                # self.image = image
                self.compressed_pixel_bytes = compress_pixel_data
                self.width = width
                self.height = height
                # self.min = int(_min)
                # self.max = int(_max)
                # self.photometric = photometric
                self.transferSyntaxUID = transferSyntaxUID
                self.allocated_bits = allocated_bits
                return
                # compress_pixel_data is bytes
                # 0                           1     2        3      4      5            6                 7
                # return compress_pixel_data, width, height, None, None, photometric, transferSyntaxUID, allocated_bits
        ### multi frame case, workaround way to get its 1st frame, not consider switching case ###
        # TODO: only get 1st frame for multiple frame case and will improve later
        if frame_number > 1:
            print("only get the 1st frame image2d data")
            image2d = image2d[0]

        _max, _min = self.get_image2d_maxmin(image2d)
        print(f"uncompressed shape:{image2d.shape}")

        if photometric == "MONOCHROME1":
            print("invert color for monochrome1")
            # -100 ~ 300
            start = time.time()
            image2d = _max - image2d + _min
            print(f"invert monochrome1 time:{time.time()-start}")

        ### normalization ###
        if photometric != "RGB":
            # TODO: figure it later, RGB case does not need it really but PALETTE need?
            # Even PALETTE case, still need normalization (workaround way?) !!! Undocumented part !!!!
            # Mabye it is because its max (dark) is 65536, 16bit

            image2d = self.normalize_image2d(image2d, _max, _min)
        else:
            print("it is RGB photometric, skip normalization?")

        print(f"uncompressed shape2:{image2d.shape}")  # 1024*768

        ### flatten to 1 d array ###
        # afterwards, treat it as RGB image, the PALETTE file we tested has planar:1
        if photometric == "RGB" or photometric == "PALETTE COLOR":
            print("it is RGB or PALETTE COLOR")
            try:
                planar_config = ds[0x0028, 0x0006].value
                print(f"planar:{planar_config}")
            except:
                print("no planar value")

            # if planar_config == 0:
            image = self.flatten_rgb_image2d_plan0_to_rgba_1d_image_array(
                image2d)
            # else:
            #     image = flatten_rgb_image2d_plan1_to_rgba_1d_image_array(image2d)
        else:
            print("it is grey color")
            if compress_pixel_data != None:
                print("flatten_grey_image1d_to_rgba_1d_image_array")
                # todo: handle RGB compressed JPEG to RGBA case
                print("below: expand grey 1d array to rgba")
                rgb_array = np.repeat(image2d, 3)
                print(f"rgb:{rgb_array.shape}")  # 1024*768*3
                alpha = np.full_like(compress_pixel_data, 255)
                print(f"alpha:{alpha.shape}")  # ()
                indexes = np.arange(3, len(rgb_array)+3, step=3)
                print(f"indexes:{indexes.shape}")  # 1024*768
                image = np.insert(rgb_array, indexes, alpha)
                print(f"final:{image.shape}")  # 3145728
            else:
                image = self.flatten_grey_image2d_to_rgba_1d_image_array(
                    image2d)

        # width, height = get_image2d_dimension(image2d)

        # Issue: instead of v0.17.0a2, if using latest dev code, this numpy.uint16 value becomes empty in JS !!!
        # so we need to use int(min), int(max)
        print(f'min type is:{type(_min)}')  # numpy.uint16
        print(f'width type is:{type(width)}')
        self.uncompressed_ndarray = image

        self.width = width
        self.height = height
        self.min = int(_min)
        self.max = int(_max)
        self.transferSyntaxUID = transferSyntaxUID
        self.allocated_bits = allocated_bits
        #       0           1      2       3           4          5                   6
        # return image, width, height, int(_min), int(_max), transferSyntaxUID, allocated_bits


# result = None
# try:
#     import js
#     print("you are in pyodide")
#     result = main(True)
# except ModuleNotFoundError:

    # result


if __name__ == '__main__':
    print("it is in __main__")
    # will not be executed in pyodide context, after testing
    print("you are not in pyodide, just do local python stuff")
    import line_profiler
    profile = line_profiler.LineProfiler()
    # using @profile is another way
    # TODO: wrap @profile with is_pyodide_context so we can use it both in local python or pyodide
    dicom = PyodideDicom()
    main_wrap = profile(dicom.main)
    result = main_wrap(False)
    profile.print_stats()
