from dataclasses import dataclass
from typing import Optional, List, Dict
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
import math
from pydicom.encaps import (
    defragment_data,
    decode_data_sequence,
    generate_pixel_data_frame,
)

import pyodide

compressed_list = [
    "1.2.840.10008.1.2.4.50",
    "1.2.840.10008.1.2.4.51",
    "1.2.840.10008.1.2.4.57",
    "1.2.840.10008.1.2.4.70",
    "1.2.840.10008.1.2.4.80",
    "1.2.840.10008.1.2.4.81",
    "1.2.840.10008.1.2.4.90",
    "1.2.840.10008.1.2.4.91",
    "1.2.840.10008.1.2.5",
]


handling_list = [
    "1.2.840.10008.1.2.4.50",
    "1.2.840.10008.1.2.4.51",
    "1.2.840.10008.1.2.4.57",
    "1.2.840.10008.1.2.4.70",
    "1.2.840.10008.1.2.4.90",  # not test/work yet
    "1.2.840.10008.1.2.4.91",
    "1.2.840.10008.1.2.4.80",
    "1.2.840.10008.1.2.4.81",
]

from enum import IntEnum, auto


class NormalizeMode(IntEnum):
    max_min_mode = 0  # start from 1 if using auto()
    window_center_mode = 1


@dataclass
class PyodideDicom:

    ## todo:
    # ** 1. pillow for 50 https://pydicom.github.io/pydicom/dev/old/image_data_handlers.html
    # x 2. multi files
    # x 3. multi frame in 1 file
    ds: Optional[Union[FileDataset]] = None
    jpeg_decoder: Any = None
    compressed_bytes: Optional[List[bytes]] = None
    decompressed_cache_dict: Optional[Dict[str, np.ndarray]] = None
    incompressed_image: Optional[np.ndarray] = None

    series_group: Optional[List[List[FileDataset]]] = None
    series_img3d_group: Optional[List[np.ndarray]] = None
    series_group_index: int = -1
    series_x: int = 0
    series_y: int = 0
    series_z: int = 0
    max_3d: Optional[int] = None
    min_3d: Optional[int] = None
    # valid_3d_files: Optional[int] = None
    ax_aspect: float = 1
    sag_aspect: float = 1
    cor_aspect: float = 1
    ax_ndarray: Optional[np.ndarray] = None
    sag_ndarray: Optional[np.ndarray] = None
    cor_ndarray: Optional[np.ndarray] = None
    is_common_axial_direction = False

    # image: Optional[np.ndarray] = None
    final_rgba_1d_ndarray: Optional[np.ndarray] = None
    current_frame: int = 0
    normalize_mode: NormalizeMode = NormalizeMode.window_center_mode

    # unused now
    # compressed_pixel_bytes: Optional[bytes] = None

    width: Optional[int] = None
    height: Optional[int] = None
    frame_max: Optional[int] = None
    frame_min: Optional[int] = None
    modality: Optional[str] = None
    photometric: Optional[str] = None
    transferSyntaxUID: Optional[str] = None
    bit_allocated: Optional[int] = None
    pixel_representation: Optional[int] = None
    color_planar: Optional[str] = None
    frame_num: int = 0
    numComponents: int = 1

    # numFrames
    # currFrameIndex
    # obj = image.getInterpretedData(false, true, frameIndex);

    @property
    def is_compressed(self):
        if self.transferSyntaxUID and self.transferSyntaxUID in compressed_list:
            return True
        return False

    @property
    def window_center(self):
        # 0028,1050, width: 0028,1051
        # ref: https://radiopaedia.org/articles/windowing-ct
        if self.ds:
            # if "WindowWidth" in self.ds:
            #     print(f"ds.WindowWidth: {self.ds.WindowWidth}")
            # if isinstance(self.ds, DicomDir):
            el = self.ds.get((0x0028, 0x1050))
            if el:
                # https://stackoverflow.com/questions/10088701/dicom-window-center-window-width/10090870
                if type(el.value) == pydicom.multival.MultiValue:
                    # multiple window center/width setting
                    return el.value[0]
                return el.value
            # print(f"b2:{b2}")
            # c = self.ds.get([0x9999, 0x9999]) # None
            # print(f"c:{c}")
            # b = self.ds.get([0x0028, 0x1050]).value
            # a = self.ds[0x9999, 0x9999]
        return None

    @property
    def window_width(self):
        if self.ds:
            #  width: [300, 1500], center [40, 300]
            el = self.ds.get((0x0028, 0x1051))
            if el:
                if type(el.value) == pydicom.multival.MultiValue:
                    return el.value[0]
                return el.value
        return None

    def get_pydicom_dataset_from_js_buffer(self, buffer_memory: memoryview):
        # print(
        #     f"get buffer from javascript, copied memory to wasm heap, start to read dicom:{type(buffer_memory)}"
        # )
        # file_name = "image-00000-ot.dcm"
        ## TODO: reading brain_001.dcm is so long, use stop_before_pixels?
        ds = pydicom.dcmread(BytesIO(buffer_memory), force=True)
        # print("read dicom ok")
        # patient_name = ds.PatientName
        # print("patient family name:"+patient_name.family_name)
        return ds

    def get_pydicom_dataset_from_local_file(self, path: str):
        ds = pydicom.dcmread(path, force=True)
        return ds

    def decompress_compressed_data(self, pixel_data: bytes):
        if self.jpeg_decoder is None:
            raise Exception("no jpeg decoder existing")
        jpeg_decoder = self.jpeg_decoder
        transferSyntaxUID = self.transferSyntaxUID
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

        ## TODO: might need reclaim pixel_data to release ???
        # https://pyodide.org/en/stable/usage/type-conversions.html#best-practices-for-avoiding-memory-leaks
        # jsobj = pyodide.create_proxy(pixel_data)
        # print("self.bit_allocated:" + str(self.bit_allocated))
        jsobj = pyodide.create_proxy(pixel_data)  # JsProxy
        # jsobj = pixel_data
        # jsobj = pyodide.to_js(pixel_data)
        # print(type(jsobj))  #
        # print("b")
        # if transferSyntaxUID == "1.2.840.10008.1.2.4.50":
        # b2 size: 262144, 512x512
        if (
            transferSyntaxUID == "1.2.840.10008.1.2.4.57"
            or transferSyntaxUID == "1.2.840.10008.1.2.4.70"
        ):
            b = jpeg_decoder.lossless(
                jsobj,
            )
        elif (
            transferSyntaxUID == "1.2.840.10008.1.2.4.50"
            or transferSyntaxUID == "1.2.840.10008.1.2.4.51"
        ):
            b = jpeg_decoder.baseline(
                jsobj,
                self.bit_allocated,
            )
        elif (
            transferSyntaxUID == "1.2.840.10008.1.2.4.90"
            or transferSyntaxUID == "1.2.840.10008.1.2.4.91"
        ):
            b = jpeg_decoder.jpeg2000(
                jsobj,
            )
        elif (
            transferSyntaxUID == "1.2.840.10008.1.2.4.80"
            or transferSyntaxUID == "1.2.840.10008.1.2.4.81"
        ):

            is_bytes_integer = False
            if (
                self.photometric != "RGB"
                and self.photometric != "PALETTE COLOR"
                and self.photometric != "YBR_FULL"
                and self.photometric != "YBR_FULL_422"
                and self.pixel_representation == 1
            ):
                is_bytes_integer = True

            b = jpeg_decoder.jpegls(jsobj, is_bytes_integer)
        else:
            raise ValueError(
                "not handle this compressed transferSyntaxUID yet1:"
                + str(self.transferSyntaxUID)
            )

        # b = decompressJPEG(
        #     jsobj, transferSyntaxUID, self.bit_allocated, is_bytes_integer
        # )
        # else:
        # 786432, 1024x768

        jsobj.destroy()

        # b = jpeg_lossless_decoder.decompress(
        #     pixel_data
        # )  # ArrayBuffer's JsProxy
        # print(type(b))  # <class 'pyodide.JsProxy'> #
        # print(f"b:{b}")  # b:[object ArrayBuffer]
        # print(f"b2:{b2}")  # <memory at 0x20adfe8> memoryview
        b2 = b.to_py()
        # print(f"b2 size:{len(b2)}")

        # numpy_array = np.asarray(b2, dtype=np.uint8)
        # dt = np.dtype(np.uint16)
        # https://numpy.org/doc/stable/reference/generated/numpy.frombuffer.html?highlight=frombuffer#numpy.frombuffer
        # https://numpy.org/doc/stable/reference/generated/numpy.dtype.byteorder.html
        # print(f"order:{dt.byteorder}") # native. guess probably is big endian
        # todo: handle PR=1(signed number)
        if self.bit_allocated == 16:
            if self.pixel_representation == 0:
                # print("111")
                # JPEG57-MR-MONO2-12-shoulder
                numpy_array: np.ndarray = np.frombuffer(b2, dtype=np.uint16)
            else:
                # print("222")
                # CT-MONO2-16-chest
                numpy_array: np.ndarray = np.frombuffer(b2, dtype=np.int16)

            ## TODO: use numComponents to detect 16/8 may be better?
            if self.width and self.height:
                numComponents = len(b2) // self.width // self.height // 2
                # print("numComponents:" + str(numComponents))
        else:  # 8
            if self.pixel_representation == 0:
                # print("333")
                # JPGLosslessP14SV1_1s_1f_8b
                numpy_array: np.ndarray = np.frombuffer(b2, dtype=np.uint8)
            else:
                # print("444")
                numpy_array: np.ndarray = np.frombuffer(b2, dtype=np.int8)

            if self.width and self.height:
                numComponents = len(b2) // self.width // self.height
                # print("numComponents:" + str(numComponents))

        return numpy_array
        # print(f"numpy:{numpy_array}")
        # 1024*1024*2 or 1024*768
        # print(f"numpy shape after using jpeg decoder:{numpy_array.shape}")

        # print(
        #     f"get_manufacturer_independent_pixel_image2d_array:type:{type(numpy_array)}, {type(pixel_data)} "
        # )
        # return numpy_array, pixel_data
        # else:
        #     raise ValueError(
        #         "not handle this compressed transferSyntaxUID yet2:"
        #         + transferSyntaxUID
        #     )

    def get_incompressed_or_uncompressed_pixel_data(
        self, ds, transferSyntaxUID: str, frame_num: int
    ):

        incompressed_image = None
        compressed_bytes = []
        # print(f"get_manufacturer_independent_pixel_image2d_array")

        # '1.2.840.10008.1.2.4.90'  #
        # ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.4.99'  # '1.2.840.10008.1.2.1.99'
        # has_TransferSyntax = True
        # print(f"syntax:{ds.file_meta.TransferSyntaxUID}")
        # RLE 1.2.840.10008.1.2.5:  US-PAL-8-10x-echo.dcm is automatically handled as uncompressed case
        if transferSyntaxUID and transferSyntaxUID in compressed_list:
            # print("compressed case !!!!!!!!!")

            # return None, ds.PixelData
            # ref: https://github.com/pydicom/pydicom/blob/master/pydicom/pixel_data_handlers/pillow_handler.py
            # print(
            #     "try to get compressed dicom's pixel data manually, can not handle by pydicom in pyodide, lack of some pyodide extension"
            # )
            try:
                # print(f"pixeldata:{len(ds.PixelData)}")  # 2126020

                compressed_bytes = []

                # TODO: only get 1st frame for multiple frame case and will improve later
                if frame_num > 1:
                    # print("multi frame compressed case")
                    # j2k_precision, j2k_sign = None, None
                    # multiple compressed frames
                    # working case (50):
                    # 1. 0002.dcm, some are [-5], [-4], [-6]. 512x512
                    # 2. color3d_jpeg_baseline , some frames needs [-1] but some do not need. size unknown?
                    try:
                        for frame in generate_pixel_data_frame(ds.PixelData):
                            compressed_bytes.append(frame)
                    except Exception as e:
                        print(f"e:{e}")
                        # some dicom can not find jpeg frame boundary
                        # e:Unable to determine the frame boundaries for the encapsulated pixel data as the Basic Offset Table is empty and `nr_frames` parameter is None
                        compressed_bytes = []
                        for frame in decode_data_sequence(ds.PixelData):
                            compressed_bytes.append(frame)

                    # TODO: what is the rule of -5/-1? But even not using pixel_data[:-1], pixel_data[:-5], still work
                    # p2 = pixel_data
                else:
                    # print("single frame")
                    # working case but browser can not render :
                    # - JPGLosslessP14SV1_1s_1f_8b.dcm,  DICOM made JPEG Lossless, 1.2.840.10008.1.2.4.70. 1024x768. local mac is able to view.
                    # - JPEG57-MR-MONO2-12-shoulder.dcm from https://barre.dev/medical/samples/, JPEG Lossless, 1.2.840.10008.1.2.4.57.
                    #   https://products.groupdocs.app/viewer/jpg can be used to view. local mac seeme not able to view (all black)
                    # - JPEG-lossy.dcm 1.2.840.10008.1.2.4.51 from https://github.com/pydicom/pydicom/blob/master/pydicom/data/test_files/JPEG-lossy.dcm,
                    #   https://products.groupdocs.app/viewer/jpg can be used to view, local mac seems not able to view (all black)

                    pixel_data = defragment_data(ds.PixelData)
                    compressed_bytes.append(pixel_data)
                    # p2 = pixel_data
                # print(f"pixel_data:{len(pixel_data)}, {type(pixel_data)}")  # bytes
                # return None, pixel_data
                # numpy_array = None

                # return None, pixel_data  # 1.2.5
            except Exception as e:
                print("failed to get compressed data")
                raise e
        else:
            # print("incompressed case")
            # print(
            #     "start reading dicom pixel_array, incompressed case uses apply_modality_lut"
            # )

            try:
                arr = ds.pixel_array
            except Exception as e:
                if transferSyntaxUID:
                    # pass
                    raise e
                else:
                    # http://dicom.nema.org/dicom/2013/output/chtml/part05/chapter_10.html
                    # print("read data fail may due to no TransferSyntaxUID")
                    ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
                    arr = ds.pixel_array
                    # raise e

            # print(f"read dicom pixel_array ok, shape:{arr.shape}")
            # image = apply_modality_lut(arr, ds)
            # print("ok")
            # if self.frame_num > 1:
            incompressed_image = arr
            # return image, None
        return incompressed_image, compressed_bytes

    def get_image_maxmin(self, image: np.ndarray):
        # print(f"start to get max/min")
        start = time.time()
        _min = image.min()
        end = time.time()
        # 0.0009999275207519531 / 0.0002989768981933594 (pyodide : local python)
        # print(f"1. min time :{end-start}")
        start = time.time()
        _max = image.max()
        end = time.time()
        # print(f"2. max time :{end-start}")  # 0.0 / 0.00027108192443847656
        # print(f"pixel min:{_min}, type:{type(_min)}")  # e.g. np.uint8
        # print(f"pixel max:{_max}")  # 255
        return _max, _min

    # def get_image2d_dimension(self, image2d):
    #     width = len(image2d[0])
    #     height = len(image2d)
    #     print(f'width:{width};height:{height}')
    #     return width, height

    def normalize_image(
        self,
        image: np.ndarray,
        normalize_max: int,
        normalize_min: int,
    ):
        # print("start to normalization")
        start0 = time.time()

        # print(f"shape:{image.shape}, type:{image.dtype}")
        ## step1: saturation
        if normalize_min != self.frame_min or normalize_max != self.frame_max:
            # print("clip the outside value")
            start = time.time()
            image = np.clip(image, normalize_min, normalize_max)  # in-place 0.004,0.005
            # print(f"clip time:{time.time()-start}")  # 0.003, 0.004
        # print(f"shape2:{image.shape}, type:{image.dtype}")

        # step2: normalize

        # print(f"center pixel:{image2d[height//2][width//2]}")
        # step1: normalize
        # ref: https://towardsdatascience.com/normalization-techniques-in-python-using-numpy-b998aa81d754
        # or use sklearn.preprocessing.minmax_scale, https://stackoverflow.com/a/55526862
        # scale = np.frompyfunc(lambda x, min, max: (x - min) / (max - min), 3, 1)
        value_range = normalize_max - normalize_min
        # 0.003, if no astype, just 0.002. using // become 0.02
        # or using colormap is another fast way,
        # MemoryError: Unable to allocate array with shape (786432,) and data type uint16
        # MemoryError: Unable to allocate array with shape (786432,) and data type float64
        # image2 = image = ((image - normalize_min) / value_range) * 255
        # print(f"shape3:{image2.shape}, type:{image2.dtype}")  # float64

        image = (((image - normalize_min) / value_range) * 255).astype("uint8")
        # print(f"normalize time:{time.time()-start0}")  # 0.009 or 0.02
        # print(f"after normalize, center pixel:{image2d[height//2][width//2]}")
        return image

        # original JPGLosslessP14SV1_1s_1f_8b: 0.007s

    def flatten_rgb_image2d_plan0_to_rgba_1d_image_array(self, image2d: np.ndarray):
        # US-PAL-8-10x-echo.dcm
        # ValueError: all the input arrays must have same number of dimensions,
        # but the array at index 0 has 4 dimension(s) and the array at index 1 has 3 dimension(s)

        # color-by-pixel
        # Planar Configuration = 0 -> R1, G1, B1, R2, G2, B2, …
        # e.g. US-RGB-8-esopecho.dcm (120, 256, 3)
        # print(f"shape0:{image2d.shape}")
        width = len(image2d[0])
        height = len(image2d)
        alpha = np.full((height, width), 255)
        stacked = np.dstack((image2d, alpha))
        # print(f"shape:{stacked.shape}")
        image = stacked.flatten()
        image = image.astype("uint8")
        return image

    def flatten_rgb_image2d_plan1_to_rgba_1d_image_array(self, image2d: np.ndarray):
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

    def flatten_grey_image_to_rgba_1d_image_array(self, image: np.ndarray):
        # 3 planes. R plane (z=0), G plane (z=1), B plane (z=2)
        # width = len(image2d[0])
        # height = len(image2d)

        # https://stackoverflow.com/questions/63783198/how-to-convert-2d-array-into-rgb-image-in-python
        # step2: 2D grey -> 2D RGBA -> Flatten to 1D RGBA
        start_time = time.time()
        alpha = np.full(image.shape, 255)  # ~
        stacked = np.dstack((image, image, image, alpha))
        # print(f"stacked shape:{stacked.shape}")  # 512x 512x 4
        image = stacked.flatten()
        # print(f"final shape:{image.shape}, type:{image.dtype}")  # int32
        image = image.astype("uint8")
        end_time = time.time()
        # print(f"flatten time:{time.time()-start}")  # 0.002s
        return image

    def flatten_grey_image2d_to_rgba_1d_image_array_non_numpy_way(
        self, image2d: np.ndarray
    ):
        """This is depreciated due to slow speed"""
        width = len(image2d[0])
        height = len(image2d)

        # 2d -> 1d -> 1d *4 (each array value -copy-> R+G+B+A)
        # NOTE: 1st memory copy/allocation
        image = np.zeros(4 * width * height, dtype="uint8")
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
                k = 4 * (i_row * width + j_col)
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
        print(f"2d grey array flattens to 1d RGBA array ok:{total}")
        print(f"{delta1}, {delta2}, {delta3}, {delta4}, {delta5}, {delta6}, {delta7}")

    def is_pyodide_env(self):
        if "pyodide" in sys.modules or "PYODIDE" in os.environ:
            return True
        return False

    def render_frame_to_rgba_1d(
        self,
        normalize_window_center: int = None,
        normalize_window_width: int = None,
        normalize_mode: NormalizeMode = None,
        frame_index: int = 0,
        ax_image: np.ndarray = None,
        sag_image: np.ndarray = None,
        cor_image: np.ndarray = None,
        _max: int = None,
        _min: int = None,
    ):
        start = time.time()  ## 0.13s !!!!
        if ax_image is not None:
            image = ax_image
            if _max is None or _min is None:
                raise ValueError("should pass _max _min along with ax_image")
        elif sag_image is not None:
            image = sag_image
            if _max is None or _min is None:
                raise ValueError("should pass _max _min along with sag_image")
        elif cor_image is not None:
            image = cor_image
            if _max is None or _min is None:
                raise ValueError("should pass _max _min along with cor_image")
        else:
            if frame_index >= self.frame_num:
                raise IndexError("frame index is over frame num")
            # print(
            #     f"render_frame_to_rgba_1d:{normalize_mode}, center:{normalize_window_center}, width:{normalize_window_width}"
            # )
            ### multi frame case, workaround way to get its 1st frame, not consider switching case ###
            # TODO: only get 1st frame for multiple frame case and will improve later
            if self.compressed_bytes is not None and len(self.compressed_bytes) > 0:
                if self.decompressed_cache_dict is None:
                    self.decompressed_cache_dict = {}

                if str(frame_index) in self.decompressed_cache_dict:
                    # print("use cache one")
                    image = self.decompressed_cache_dict[str(frame_index)]
                else:
                    # take some time
                    image = self.decompress_compressed_data(
                        self.compressed_bytes[frame_index]
                    )
                    if self.ds is not None:
                        # JPEG57-MR-MONO2-12-shoulder
                        image = apply_modality_lut(image, self.ds)
                self.decompressed_cache_dict[str(frame_index)] = image

            elif self.incompressed_image is not None:
                if self.frame_num > 1:
                    image: np.ndarray = self.incompressed_image[frame_index]
                else:
                    image = self.incompressed_image
            else:
                raise Exception("somehow no compressed/incompressed data")

            ## TODO: cache it
            _max, _min = self.get_image_maxmin(image)
            _max = int(_max)
            _min = int(_min)
            # print(f"uncompressed shape:{image.shape}")  # 空的?
            self.frame_max = _max
            self.frame_min = _min
        # print(f"setup frame_max:{int(_min)};{int(_max)};{self.photometric}")

        if self.photometric == "MONOCHROME1":
            # print("invert color for monochrome1")
            # -100 ~ 300
            start = time.time()
            image = _max - image + _min
            # print(f"invert monochrome1 time:{time.time()-start}")

        # print("render_frame_to_rgba_1d !!!")
        if normalize_mode is not None:
            self.normalize_mode = normalize_mode

        if self.ds is None or self.width is None or self.height is None:
            # should not happe, just make pylance warning disappeared
            print("self.ds/max/min/width/height is None, should not happen")
            return

        ### normalization ###
        # if True:  # photometric != "RGB":
        # TODO: figure it later, RGB case does not need it really (in previous cases) but PALETTE need?
        # Even PALETTE case, still need normalization (workaround way?) !!! Undocumented part !!!!
        # Mabye it is because its max (dark) is 65536, 16bit
        # I think previous RGB cases just use 8 bit RGB, so apply normalize on RGB (no harm)

        # center 127, width 254, max:255, min = 0
        # TODO: move back to JS side ?
        if self.normalize_mode == NormalizeMode.max_min_mode:
            # print(f"mode0:max_min_mode:{self.frame_max}")
            max = _max
            min = _min
            normalize_image = self.normalize_image(image, max, min)
        else:
            # print("mode:window_center_mode")
            if normalize_window_center and normalize_window_width:
                # print("mode2:")
                max = normalize_window_center + math.floor(normalize_window_width / 2)
                min = normalize_window_center - math.floor(normalize_window_width / 2)
                normalize_image = self.normalize_image(image, max, min)
            elif self.window_center and self.window_width:
                # print("mode3:")

                # print(f"mode3. max0: {self.window_width}, {self.window_center}")
                max = self.window_center + math.floor(self.window_width / 2)
                min = self.window_center - math.floor(self.window_width / 2)
                normalize_image = self.normalize_image(image, max, min)
                # print(
                #     f"mode3. max: {max}, {min}, {self.frame_max}, {self.frame_min}, {self.window_width}, {self.window_center}"
                # )
            else:
                max = _max
                min = _min
                # print("mode4:")
                normalize_image = self.normalize_image(image, max, min)
        # print(f"normalize max:{max};min:{min}")

        # else:
        #     print("it is RGB photometric, skip normalization?")

        # print(f"uncompressed shape2:{normalize_image.shape}")  # 1024*768

        ## dicom-viewer: https://github.com/grimmer0125/dicom-web-viewer
        # 0. every time need render image, decompress everytime
        # 1. original is 1d array
        # 2. obj.max gotten earily
        # 3. using 255 to normaizle + truncate when expand grey to rgba
        # 4. 3 modes. a. 1d b. rgb 1d (rgbrgb) c. rgb 1d (rrr...ggg...bbb...) <- Planar = 1
        # 5. assume RGB is 8 bit or decompressJPEG already downsize to 8 bit?
        # 6. not sure if handle floating data or not
        # 7. no mosue to adjust window center/width when no stored window center/width by default
        # 8. no windoe center mode on RGB

        ### flatten to 1 d array ###
        # afterwards, treat it as RGB image, the PALETTE file we tested has planar:1

        if (
            self.photometric == "RGB"
            or self.photometric == "PALETTE COLOR"
            or self.photometric == "YBR_FULL"
            # color3d_jpeg_baseline-broken-multi (0,243), 1.2.840.10008.1.2.4.50
            or self.photometric == "YBR_FULL_422"
        ):
            # print("it is RGB or PALETTE COLOR")

            if normalize_image.ndim == 1:
                # print("flatten_jpeg_RGB_image1d_to_rgba_1d_image_array")
                # http://medistim.com/wp-content/uploads/2016/07/ttfm.dcm 1.2.840.10008.1.2.4.70 (0,255)
                # alpha = np.full_like(compress_pixel_data, 255)
                # print(f"alpha1:{alpha.shape}")  # ()
                # indexes: sometimes it will throw error, e.g. http://medistim.com/wp-content/uploads/2016/07/bmode.dcm
                # TypeError: object of type 'numpy.uint8' has no len()
                start = time.time()
                normalize_image2 = normalize_image.reshape(
                    (self.width, self.height, 3)
                )  # ~ 0s
                final_rgba_1d_ndarray = (
                    self.flatten_rgb_image2d_plan0_to_rgba_1d_image_array(
                        normalize_image2
                    )
                )
                # print(f"time:{time.time()-start}")  # 0.03 ~ 0.035

                #### NOTE: this way is much slower than stack method !!!!!
                # indexes = np.arange(3, len(normalize_image) + 3, step=3)
                # # print(f"indexes:{indexes.shape}")  # 1024*768
                # self.render_rgba_1d_ndarray = np.insert(
                #     normalize_image, indexes, 255
                # )  # 0.06s
            else:
                # incompress case (such as PALETTE COLOR, US-PAL-8-10x-echo). (0,65280)
                # if planar_config == 0:
                # US-RGB-8-esopecho # 0.025s  (16,248)
                # print("flatten_rgb_image2d_plan0_to_rgba_1d_image_array!!")
                final_rgba_1d_ndarray = (
                    self.flatten_rgb_image2d_plan0_to_rgba_1d_image_array(
                        normalize_image
                    )
                )
                # else:
                #  US-RGB-8-epicard
                #     image = flatten_rgb_image2d_plan1_to_rgba_1d_image_array(image2d)
        else:
            # print("it is grey color")
            if normalize_image.ndim == 1:  # 0.15s !!!
                # rgb_array = np.repeat(normalize_image, 3) # 0.06s
                # indexes = np.arange(3, len(rgb_array) + 3, step=3)
                # self.render_rgba_1d_ndarray = np.insert(rgb_array, indexes, 255) # 0.06s
                pass
            else:
                pass
            # e.g. : JPGLosslessP14SV1_1s_1f_8b (US), CT-MONO2-16-chest
            # print("flatten_jpeg_grey_image1d_to_rgba_1d_image_array")

            # do truncate? + normalize before expand/append alpha https://radiopaedia.org/articles/windowing-ct
            # do we need to do truncate (window_center mode) on
            # - rgb <- no
            # - jpeg <- yes (CT-MONO2-16-chest has stored its window center/width) . if so, how about jpeg 50
            # - non ct?????? yes,
            #   (US) JPGLosslessP14SV1_1s_1f_8b has stored its window center/width
            #   CR-MONO1-10-chest has (1.2.840.10008.1.2, not jpeg )
            #   JPEG57-MR-MONO2-12-shoulder

            final_rgba_1d_ndarray = self.flatten_grey_image_to_rgba_1d_image_array(
                normalize_image
            )

        if ax_image is not None:
            self.ax_ndarray = final_rgba_1d_ndarray
        elif sag_image is not None:
            self.sag_ndarray = final_rgba_1d_ndarray
        elif cor_image is not None:
            self.cor_ndarray = final_rgba_1d_ndarray
        else:
            self.final_rgba_1d_ndarray = final_rgba_1d_ndarray

        # width, height = get_image2d_dimension(image2d)

        # Issue: instead of v0.17.0a2, if using latest dev code, this numpy.uint16 value becomes empty in JS !!!
        # so we need to use int(min), int(max)
        # print(f"min type is:{type(_min)}")  # numpy.uint8
        # print(f'width type is:{type(width)}') # int
        # self.uncompressed_ndarray = image
        # ref: https://grimmer.io/dicom-web-viewer/
        #   this.renderFrame({
        #     image: this.currentImage,
        #     frameIndex: currFrameIndex,
        #     currNormalizeMode: newMode,
        #     useWindowCenter: newWindowCenter,
        #     useWindowWidth: newWindowWidth,
        #   });
        # print(f"render time:{time.time()-start}")  # 0.009

    @property  ## memory leak !!!!
    def rgba_1d_ndarray(self):
        return self.final_rgba_1d_ndarray

    def get_rgba_1d_ndarray(self):
        return self.final_rgba_1d_ndarray

    def get_ax_ndarray(self):
        return self.ax_ndarray

    def get_sag_ndarray(self):
        return self.sag_ndarray

    def get_cor_ndarray(self):
        return self.cor_ndarray

    @property
    def series_dim_x(self):
        if self.img3d is not None:
            return self.img3d.shape[0]
        return 0

    @property
    def series_dim_y(self):
        if self.img3d is not None:
            return self.img3d.shape[1]
        return 0

    @property
    def series_dim_z(self):
        if self.img3d is not None:
            return self.img3d.shape[2]
        return 0

    @property
    def img3d(self):
        if self.series_img3d_group is not None and len(self.series_img3d_group) > 0:
            return self.series_img3d_group[self.series_group_index]
        return None

    @property
    def img3d_count(self):
        if self.series_img3d_group is not None:
            return len(self.series_img3d_group)
        return 0

    def get_image_after_all_transform_exclude_multi_frame(self, ds):
        photometric = ds.PhotometricInterpretation
        transferSyntaxUID = ds.file_meta.TransferSyntaxUID
        frame_num = getattr(ds, "NumberOfFrames", 1)
        (
            incompressed_image,
            compressed_bytes,
        ) = self.get_pixel_data_after_most_transform(
            ds, photometric, transferSyntaxUID, frame_num
        )
        if compressed_bytes is not None and len(compressed_bytes) > 0:
            image = self.decompress_compressed_data(compressed_bytes[0])
            image = apply_modality_lut(image, ds)
            return image
        elif incompressed_image is not None:
            return incompressed_image
        else:
            raise Exception(
                "no image, should not happen in get_image_after_all_transform_exclude_multi_frame"
            )

    def get_pixel_data_after_most_transform(
        self, ds, photometric: str, transferSyntaxUID: str, frame_num: int
    ):

        incompressed_image = None
        compressed_bytes = []

        if photometric == "PALETTE COLOR":
            print("it is PALETTE COLOR")
            # https://pydicom.github.io/pydicom/stable/old/working_with_pixel_data.html
            # before: a grey 2d image
            incompressed_image = apply_color_lut(ds.pixel_array, ds)
            # after: a RGB 2d image

            # NOTE: http://dicom.nema.org/dicom/2013/output/chtml/part04/sect_N.2.html still possible apply modality_lut first??

            # print(
            #     f"PALETTE after apply_color_lut shape:{self.incompressed_image.shape}"
            # )

            # _max, _min = get_image2d_maxmin(image2d)
            # print(f'pixel (after color lut) min:{_min}')  # min same as before
            # print(f'pixel (after color lut) max:{_max}')  # max same as before
            # but still need normalization (workaround way?) !!! Undocumented part !!!!
            # Mabye it is because its max (dark) is 65536, 16bit
            # image2d = normalize_image2d(image2d, _max, _min)
            # else:

        else:
            (
                incompressed_image,
                compressed_bytes,
            ) = self.get_incompressed_or_uncompressed_pixel_data(
                ds,
                transferSyntaxUID,
                frame_num,  # str is for eliminate warning
            )
            # self.incompressed_image = incompressed_image
            # self.compressed_bytes = compressed_bytes

            if incompressed_image is not None:

                # if self.incompressed_image is not None:
                # get_manufacturer_independent_pixel_image2d_array
                incompressed_image = apply_modality_lut(incompressed_image, ds)
            # print("ok")
            # if self.frame_num > 1:
            # self.incompressed_image = arr

            # if compress_pixel_data:
            #     self.has_compressed_data = True
            #     # print(f"after get_manufacturer_independent_pixel_image2d_array")
            #     # NOTE: using image2d == None will throw a error which says some element is ambiguous
            #     self.compressed_pixel_bytes = compress_pixel_data

            # if image is None:
            # return bytes data
            # TODO: how to add width, height ?
            # print(f"directly return compressed data")
            # Columns (0028,0011), Rows (0028,0010)

            # self.image = image

            # self.min = int(_min)
            # self.max = int(_max)
            # self.photometric = photometric
            # self.transferSyntaxUID = transferSyntaxUID
            # self.bit_allocated = bit_allocated
            # return
            # compress_pixel_data is bytes
            # 0                           1     2        3      4      5            6                 7
            # return compress_pixel_data, width, height, None, None, photometric, transferSyntaxUID, bit_allocated

        # self.has_uncompressed_data = True
        return incompressed_image, compressed_bytes

    def render_axial_view(self, z: int = None):
        if self.img3d is not None:
            if not z:
                self.series_z = self.img3d.shape[2] // 2
            else:
                self.series_z = z
            ax_image = self.img3d[:, :, self.series_z]
            self.render_frame_to_rgba_1d(
                ax_image=ax_image, _max=self.max_3d, _min=self.min_3d
            )

    def redner_sag_view(self, x: int = None):
        if self.img3d is not None:
            if not x:
                self.series_x = self.img3d.shape[1] // 2
            else:
                self.series_x = x
            sag_image = self.img3d[:, self.series_x, :].T
            # print(f"sag_image:{sag_image.shape}")
            self.render_frame_to_rgba_1d(
                sag_image=sag_image, _max=self.max_3d, _min=self.min_3d
            )

    def redner_cor_view(self, y: int = None):
        if self.img3d is not None:
            if not y:
                self.series_y = self.img3d.shape[0] // 2
            else:
                self.series_y = y
            cor_image = self.img3d[self.series_y, :, :].T
            # print(f"cor_image:{cor_image.shape}")
            self.render_frame_to_rgba_1d(
                cor_image=cor_image, _max=self.max_3d, _min=self.min_3d
            )

    def get_tag(self, ds, tag):
        el = ds.get(tag)
        if el:
            return str(el.value)
        else:
            return ""

    def get_series_id(self, ds):

        # https://pydicom.github.io/pydicom/stable/auto_examples/plot_dicom_difference.html
        # CT With/Without Contrast-Abdomen
        des = self.get_tag(
            ds, (0x0008, 0x1030)
        )  # .value  # this.getSeriesDescription();
        # print(f"series desc:{des}")

        # 1.3.12.2.1107.5.1.4.39722.30000013081301233446800000758
        uid = self.get_tag(
            ds, (0x0020, 0x000E)
        )  # .value  # this.getSeriesInstanceUID();
        # print(f"series id:{uid}")

        # 2
        num = self.get_tag(ds, (0x0020, 0x0011))  # ].value  # this.getSeriesNumber();
        # print(f"series num:{num}")  # 2

        # may empty
        echo = self.get_tag(ds, (0x0018, 0x0086))  # .value  # this.getEchoNumber();
        # print(f"echo:{echo}")

        # [1, 0, 0, 0, 1, 0]
        orientation = self.get_tag(
            ds, (0x0020, 0x0037)
        )  # ].value  # this.getOrientation();

        # 512
        cols = self.get_tag(ds, (0x0028, 0x0011))  # .value  # this.getCols();
        # width: int = ds[0x0028, 0x0011].value
        # print(f"width:{width}, {cols}")

        # 512
        rows = self.get_tag(ds, (0x0028, 0x0010))  # ].value  # this.getRows();

        id = ""

        if des:
            id += " " + des

        if uid:
            id += " " + uid

        if num:
            id += " " + num

        if echo:
            id += " " + echo

        if orientation:
            id += " " + orientation

        id += " (" + cols + " x " + rows + ")"
        return id

    def switch_series_group(self, new_index: int):
        if not self.series_group:
            return
        if self.series_group_index == new_index:
            return
        self.series_group_index = new_index

        slices = self.series_group[new_index]
        # if len(slices) > 0:
        ds = slices[0]
        direction = self.get_tag(ds, (0x0020, 0x0037))
        if direction == "[1, 0, 0, 0, 1, 0]":
            self.is_common_axial_direction = True
        self.fill_ds_meta(ds)
        # self.valid_3d_files = len(slices)
        # pixel aspects, assuming all slices are the same
        ps = ds.PixelSpacing
        ss = ds.SliceThickness
        self.ax_aspect = ps[1] / ps[0]
        self.sag_aspect = ss / ps[1]
        self.cor_aspect = ss / ps[0]
        print(f"ax:{self.ax_aspect}, sag:{self.sag_aspect}, cor:{self.cor_aspect}")

        if self.img3d is not None:
            print(f"switch_series_group self.img3d shape:{self.img3d.shape}")
            self.max_3d, self.min_3d = self.get_image_maxmin(self.img3d)
        else:
            print("switch_series_group no self.img3d")

    def handle_3d_projection_view(
        self,
        buffer_list: Any = None,
    ):
        if buffer_list is None:
            return

        files = []
        for buffer in buffer_list:
            ds = self.get_pydicom_dataset_from_js_buffer(buffer.to_py())
            # buffer.to_py()
            # print("glob: {}".format(sys.argv[1]))
            # path = "/Users/grimmer/git/embedded-pydicom-react-viewer/python/exp/CTSlicesWithTumor/*.dcm"
            # for fname in glob.glob(path, recursive=False):
            #     print("loading: {}".format(fname))
            files.append(ds)

        print("file count: {}".format(len(files)))
        # print(f"first:{self.get_series_id(files[0])}")
        # if len(files) > 0:
        #     seried_id = self.get_series_id(files[0])

        # skip files with no SliceLocation (eg scout views)
        series_dict: Dict[str, List[FileDataset]] = {}
        skipcount = 0
        for file in files:
            # frame_num = getattr(file, "NumberOfFrames", 1)
            # if frame_num > 1:
            #     raise Exception("every file should only have 1 frame")
            if file.get((0x0400, 0x0010)) is None:
                file.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

            # f.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
            if (
                hasattr(file, "SliceLocation")
                and getattr(file, "NumberOfFrames", 1) == 1
            ):

                # and self.get_series_id(file) == seried_id
                series_id = self.get_series_id(file)
                series = series_dict.get(series_id)
                if not series:
                    series = []
                    series_dict[series_id] = series
                series.append(file)
            else:
                ## usually the not match part is Series Instance UID
                # print(f"not matched tag:{self.get_series_id(file)}")
                skipcount = skipcount + 1

        print("skipped, no SliceLocation or is multi-frame: {}".format(skipcount))

        self.series_group = []
        for key, series in series_dict.items():
            # print("in series_dict dict")
            # ensure they are in the correct order
            series = sorted(series, key=lambda s: s.SliceLocation)
            series = list(reversed(series))
            self.series_group.append(series)
            # series_dict[key] = series
            # if not slices:
            #     slices = series
        # self.img3d_list = series_dict.values()
        print(f"series_group count:{len(self.series_group)}")
        self.series_img3d_group = []
        for series in self.series_group:
            # create 3D array
            # img = self.get_image_after_all_transform_exclude_multi_frame(slices[0])
            img_shape = list(
                self.get_image_after_all_transform_exclude_multi_frame(series[0]).shape
            )
            img_shape.append(len(series))
            img3d = np.zeros(img_shape)
            # fill 3D array with the images from the files
            for i, s in enumerate(series):
                img2d = self.get_image_after_all_transform_exclude_multi_frame(s)
                # img2d = s.pixel_array
                img3d[:, :, i] = img2d
            self.series_img3d_group.append(img3d)
        # print(f"img3d_group:{len(self.series_img3d_group)}")

        self.switch_series_group(0)

        self.render_axial_view()
        # ax_image = img3d[:, :, img_shape[2] // 2]
        # plot 3 orthogonal slices
        # a1 = plt.subplot(2, 2, 1)
        # plt.imshow(image1)
        # a1.set_aspect(ax_aspect)

        self.redner_sag_view()
        # sag_image = img3d[:, img_shape[1] // 2, :]
        # a2 = plt.subplot(2, 2, 2)
        # plt.imshow(image2)
        # a2.set_aspect(sag_aspect)

        self.redner_cor_view()
        # cor_image = img3d[img_shape[0] // 2, :, :].T
        # a3 = plt.subplot(2, 2, 3)
        # plt.imshow(image3)
        # a3.set_aspect(cor_aspect)

        # plt.show()

    def fill_ds_meta(self, ds):
        ###### DICOM meta fields #####
        self.ds = ds
        width: int = ds[0x0028, 0x0011].value
        height: int = ds[0x0028, 0x0010].value
        # print(f"dimension: {width}; {height}")
        self.width = width
        self.height = height
        modality: str = ds[0x0008, 0x0060].value
        # print(f"Modality:{modality}")
        self.modality = modality

        self.bit_allocated = ds[0x0028, 0x0100].value
        # print(f"bit_allocated:{self.bit_allocated}")

        self.pixel_representation = ds[0x0028, 0x0103].value
        # print(f"pr:{self.pixel_representation}")
        # k = ds[0x0028, 0x0107].value
        # print(f"store max:{k}")

        # 8,8 or 16,12
        # bit_allocated = ds[0x0028, 0x0100].value
        # bites_stored = ds[0x0028, 0x0101].value
        # print(f"stored_bites:{bites_stored}")

        # try:
        planar_config = ds.get((0x0028, 0x0006))
        if planar_config:
            self.color_planar = planar_config.value
        #     print(f"planar:{planar_config}")
        # except:
        #     print("no planar value")

        transferSyntaxUID = ""
        try:
            transferSyntaxUID: str = ds.file_meta.TransferSyntaxUID
            # print(f"transferSyntax:{transferSyntaxUID}")
        except:
            print("no TransferSyntaxUID")
        try:
            photometric: str = ds.PhotometricInterpretation
            # print(f"photometric:{photometric}")
        except:
            print("no photometric")
            photometric = ""
        self.photometric = photometric
        self.transferSyntaxUID = transferSyntaxUID
        self.frame_num = getattr(ds, "NumberOfFrames", 1)
        # print(f"frame_num:{frame_num}")
        ###### DICOM meta fields #####

    def __init__(
        self,
        buffer: Any = None,
        buffer_list: Any = None,
        decompressJPEG: Any = None,
        normalize_mode=None,
    ):
        self.jpeg_decoder = decompressJPEG
        if normalize_mode is not None:
            self.normalize_mode = normalize_mode
        ## TODO: handle BitsAllocated 32,64 case

        # buffer: pyodide.JsProxy
        # decoder: pyodide.JsProxy
        # print(f"__init__!!!!!!!!!!!!! buffer:{type(buffer)}")
        if self.is_pyodide_env():
            if buffer_list is not None:
                # print("3d")
                self.handle_3d_projection_view(buffer_list)
                return
            # print("2d")

            # if buffer is None:
            #     print("buffer is None")
            #     from my_js_module import buffer  # pylint: disable=import-error
            #     # from my_js_module import jpeg_lossless_decoder  # pylint: disable=import-error
            #     # from my_js_module import newDecoder
            #     ## test life cycle in pyodide ##
            #     # print(f"class22: {bb.a}")
            #     # global x
            #     # x.append(10)

            ##### only for testing if python can access JS' user defined objects' methods ##
            # from my_js_module import add, polygon
            # k2 = add(5)
            # polygon.addWidth()  # works
            # print(f"k2:{k2}")  # works
            # else:
            #     print("buffer is not None")
            # from my_js_module import jpeg
            #####

            ds = self.get_pydicom_dataset_from_js_buffer(buffer.to_py())
        else:
            # NOTE: its is possible to use jpeg decoders in https://pydicom.github.io/pydicom/dev/old/image_data_handlers.html
            # for local mode

            # deprecated, use plot.py to do local experiment
            # start to do some local Python stuff, e.g. testing
            ds = self.get_pydicom_dataset_from_local_file("dicom_samples/brain_001.dcm")

        self.fill_ds_meta(ds)

        (
            self.incompressed_image,
            self.compressed_bytes,
        ) = self.get_pixel_data_after_most_transform(
            ds, str(self.photometric), str(self.transferSyntaxUID), self.frame_num
        )

        self.render_frame_to_rgba_1d()


if __name__ == "__main__":
    print("it is in __main__")
    # will not be executed in pyodide context, after testing
    print("you are not in pyodide, just do local python stuff")

    # import line_profiler
    # profile = line_profiler.LineProfiler()
    # # using @profile is another way
    # # TODO: wrap @profile with is_pyodide_context so we can use it both in local python or pyodide
    dicom = PyodideDicom()
    # main_wrap = profile(dicom.main)
    # result = main_wrap(False)
    # profile.print_stats()
