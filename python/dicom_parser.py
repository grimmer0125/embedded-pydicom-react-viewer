from dataclasses import dataclass
from typing import Optional
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
from pydicom.encaps import defragment_data, decode_data_sequence


compressed_list = [
    "1.2.840.10008.1.2.4.50",
    "1.2.840.10008.1.2.4.51",
    "1.2.840.10008.1.2.4.57",
    "1.2.840.10008.1.2.4.70",
    "1.2.840.10008.1.2.4.80",
    "1.2.840.10008.1.2.4.81",
    "1.2.840.10008.1.2.4.90",
    "1.2.840.10008.1.2.4.91",
]


handling_list = [
    # "1.2.840.10008.1.2.4.50", <- this decoder can not handle
    "1.2.840.10008.1.2.4.57",
    "1.2.840.10008.1.2.4.70",
]

from enum import IntEnum, auto


class NormalizeMode(IntEnum):
    window_center_mode = auto()
    max_min_mode = auto()


@dataclass
class PyodideDicom:

    ## todo:
    # 1. pillow for 50 https://pydicom.github.io/pydicom/dev/old/image_data_handlers.html
    # 2. multi files
    # 3. multi frame in 1 file

    render_rgba_1d_ndarray: Optional[np.ndarray] = None
    image: Optional[np.ndarray] = None
    width: Optional[int] = None
    height: Optional[int] = None
    max: Optional[int] = None
    min: Optional[int] = None
    modality: Optional[str] = None
    photometric: Optional[str] = None
    transferSyntaxUID: Optional[str] = None
    bit_allocated: Optional[int] = None
    pixel_representation: Optional[int] = None
    ds: Optional[Union[FileDataset, DicomDir]] = None
    compressed_pixel_bytes: Optional[bytes] = None
    normalize_mode: NormalizeMode = NormalizeMode.window_center_mode
    color_planar: Optional[str] = None

    @property
    def window_center(self):
        # 0028,1050, width: 0028,1051
        # ref: https://radiopaedia.org/articles/windowing-ct
        if self.ds:
            # if isinstance(self.ds, DicomDir):
            el = self.ds.get((0x0028, 0x1050))
            if el:
                return el.value  # elf.ds[0x0028, 0x1050].value
            # print(f"b2:{b2}")
            # c = self.ds.get([0x9999, 0x9999]) # None
            # print(f"c:{c}")
            # b = self.ds.get([0x0028, 0x1050]).value
            # a = self.ds[0x9999, 0x9999]
        return None

    @property
    def window_width(self):
        if self.ds:
            el = self.ds.get((0x0028, 0x1051))
            if el:
                return el.value
        return None

    def get_pydicom_dataset_from_js_buffer(self, buffer_memory: memoryview):
        print(
            f"get buffer from javascript, copied memory to wasm heap, start to read dicom:{type(buffer_memory)}"
        )
        # file_name = "image-00000-ot.dcm"
        ds = pydicom.dcmread(BytesIO(buffer_memory), force=True)
        print("read dicom ok")
        # patient_name = ds.PatientName
        # print("patient family name:"+patient_name.family_name)
        return ds

    def get_pydicom_dataset_from_local_file(self, path: str):
        ds = pydicom.dcmread(path, force=True)
        print("read dicom ok")
        return ds

    def get_manufacturer_independent_pixel_image2d_array(
        self, ds, transferSyntaxUID: str, jpeg_lossless_decoder: Any = None
    ):
        print(f"get_manufacturer_independent_pixel_image2d_array")

        # '1.2.840.10008.1.2.4.90'  #
        # ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.4.99'  # '1.2.840.10008.1.2.1.99'
        # has_TransferSyntax = True
        # print(f"syntax:{ds.file_meta.TransferSyntaxUID}")
        # RLE 1.2.840.10008.1.2.5:  US-PAL-8-10x-echo.dcm is automatically handled as uncompressed case
        if transferSyntaxUID and transferSyntaxUID in compressed_list:
            print("compressed case !!!!!!!!!")

            # return None, ds.PixelData
            # ref: https://github.com/pydicom/pydicom/blob/master/pydicom/pixel_data_handlers/pillow_handler.py
            print(
                "try to get compressed dicom's pixel data manually, can not handle by pydicom in pyodide, lack of some pyodide extension"
            )
            try:
                print(f"pixeldata:{len(ds.PixelData)}")  # 2126020

                # TODO: only get 1st frame for multiple frame case and will improve later
                if getattr(ds, "NumberOfFrames", 1) > 1:
                    print("multi frame")
                    # j2k_precision, j2k_sign = None, None
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
                    # p2 = pixel_data
                else:
                    print("single frame")
                    # working case but browser can not render :
                    # - JPGLosslessP14SV1_1s_1f_8b.dcm,  DICOM made JPEG Lossless, 1.2.840.10008.1.2.4.70. 1024x768. local mac is able to view.
                    # - JPEG57-MR-MONO2-12-shoulder.dcm from https://barre.dev/medical/samples/, JPEG Lossless, 1.2.840.10008.1.2.4.57.
                    #   https://products.groupdocs.app/viewer/jpg can be used to view. local mac seeme not able to view (all black)
                    # - JPEG-lossy.dcm 1.2.840.10008.1.2.4.51 from https://github.com/pydicom/pydicom/blob/master/pydicom/data/test_files/JPEG-lossy.dcm,
                    #   https://products.groupdocs.app/viewer/jpg can be used to view, local mac seems not able to view (all black)

                    pixel_data = defragment_data(ds.PixelData)
                    # p2 = pixel_data
                print(f"pixel_data:{len(pixel_data)}, {type(pixel_data)}")  # bytes
                # return None, pixel_data
                # numpy_array = None
                if (
                    jpeg_lossless_decoder is not None
                    and transferSyntaxUID in handling_list
                ):

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
                    b = jpeg_lossless_decoder.decompress(
                        pixel_data
                    )  # ArrayBuffer's JsProxy
                    # print(type(b))  # <class 'pyodide.JsProxy'> #
                    # print(f"b:{b}")  # b:[object ArrayBuffer]
                    # print(f"b2:{b2}")  # <memory at 0x20adfe8> memoryview
                    b2 = b.to_py()
                    print(f"b2 size:{len(b2)}")

                    # numpy_array = np.asarray(b2, dtype=np.uint8)
                    # dt = np.dtype(np.uint16)
                    # https://numpy.org/doc/stable/reference/generated/numpy.frombuffer.html?highlight=frombuffer#numpy.frombuffer
                    # https://numpy.org/doc/stable/reference/generated/numpy.dtype.byteorder.html
                    # print(f"order:{dt.byteorder}") # native. guess probably is big endian
                    # todo: handle PR=1(signed number)
                    if self.bit_allocated == 16:
                        if self.pixel_representation == 0:
                            numpy_array: np.ndarray = np.frombuffer(b2, dtype=np.uint16)
                        else:
                            numpy_array: np.ndarray = np.frombuffer(b2, dtype=np.int16)
                    else:
                        if self.pixel_representation == 0:
                            numpy_array: np.ndarray = np.frombuffer(b2, dtype=np.uint8)
                        else:
                            numpy_array: np.ndarray = np.frombuffer(b2, dtype=np.int8)
                    # print(f"numpy:{numpy_array}")
                    # 1024*1024*2 or 1024*768
                    print(f"numpy shape after using jpeg decoder:{numpy_array.shape}")

                    print(
                        f"get_manufacturer_independent_pixel_image2d_array:type:{type(numpy_array)}, {type(pixel_data)} "
                    )
                    return numpy_array, pixel_data
                return None, pixel_data
            except Exception as e:
                print("failed to get compressed data")
                raise e

        print("uncompressed case")
        print(
            "start reading dicom pixel_array, uncompressed case uses apply_modality_lut"
        )

        try:
            arr = ds.pixel_array
        except Exception as e:
            if transferSyntaxUID:
                # pass
                raise e
            else:
                # http://dicom.nema.org/dicom/2013/output/chtml/part05/chapter_10.html
                print("read data fail may due to no TransferSyntaxUID")
                ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
                arr = ds.pixel_array
                # raise e

        print(f"read dicom pixel_array ok, shape:{arr.shape}")
        image2d = apply_modality_lut(arr, ds)
        return image2d, None

    def get_image_maxmin(self, image2d: np.ndarray):
        print(f"start to get max/min")
        start = time.time()
        _min = image2d.min()
        end = time.time()
        # 0.0009999275207519531 / 0.0002989768981933594 (pyodide : local python)
        print(f"1. min time :{end-start}")
        start = time.time()
        _max = image2d.max()
        end = time.time()
        print(f"2. max time :{end-start}")  # 0.0 / 0.00027108192443847656
        print(f"pixel min:{_min}, type:{type(_min)}")  # e.g. np.uint8
        print(f"pixel max:{_max}")  # 255
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

        ## step1: saturation
        if normalize_min != self.min or normalize_max != self.max:
            # print("clip the outside value")
            start = time.time()
            image = np.clip(image, normalize_min, normalize_max)
            # print(f"clip time:{time.time()-start}")  # 0.003

        # step2: normalize

        # print(f"center pixel:{image2d[height//2][width//2]}")
        # step1: normalize
        # ref: https://towardsdatascience.com/normalization-techniques-in-python-using-numpy-b998aa81d754
        # or use sklearn.preprocessing.minmax_scale, https://stackoverflow.com/a/55526862
        # scale = np.frompyfunc(lambda x, min, max: (x - min) / (max - min), 3, 1)
        value_range = normalize_max - normalize_min
        # 0.003, if no astype, just 0.002. using // become 0.02
        # or using colormap is another fast way,
        image = (((image - normalize_min) / value_range) * 255).astype("uint8")
        # print(f"normalize time:{time.time()-start0}")  # 0.009 or 0.02
        # print(f"after normalize, center pixel:{image2d[height//2][width//2]}")
        return image

        # 原本 JPGLosslessP14SV1_1s_1f_8b: 0.007s

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
        print(f"shape:{stacked.shape}")
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

    def flatten_grey_image_to_rgba_1d_image_array(self, image2d: np.ndarray):
        # 3 planes. R plane (z=0), G plane (z=1), B plane (z=2)
        # width = len(image2d[0])
        # height = len(image2d)

        # https://stackoverflow.com/questions/63783198/how-to-convert-2d-array-into-rgb-image-in-python
        # step2: 2D grey -> 2D RGBA -> Flatten to 1D RGBA
        start_time = time.time()
        alpha = np.full(image2d.shape, 255)  # ~
        stacked = np.dstack((image2d, image2d, image2d, alpha))
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
    ):
        start = time.time()  ## 0.13s !!!!

        # print("render_frame_to_rgba_1d !!!")
        if normalize_mode is not None:
            self.normalize_mode = normalize_mode

        if self.image is None:
            # TODO: jpeg 50 case, add it later
            print("not handle jpeg 50 in-py uncompress case")
            return

        if (
            self.ds is None
            or self.max is None
            or self.min is None
            or self.width is None
            or self.height is None
        ):
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
        if normalize_mode == NormalizeMode.max_min_mode:
            normalize_image = self.normalize_image(self.image, self.max, self.min)
        else:
            if normalize_window_center and normalize_window_width:
                min = normalize_window_center - math.floor(normalize_window_width / 2)
                max = normalize_window_center + math.floor(normalize_window_width / 2)
                normalize_image = self.normalize_image(self.image, max, min)
            elif self.window_center and self.window_width:
                min = self.window_center - math.floor(self.window_width / 2)
                max = self.window_center + math.floor(self.window_width / 2)
                normalize_image = self.normalize_image(self.image, max, min)
            else:
                normalize_image = self.normalize_image(self.image, self.max, self.min)

        # else:
        #     print("it is RGB photometric, skip normalization?")

        # print(f"uncompressed shape2:{normalize_image.shape}")  # 1024*768

        ## dicom-viewer: https://github.com/grimmer0125/dicom-web-viewer
        # 0. every time need render image, decompress everytime
        # 1. original is 1d array
        # 2. obj.max gotten earily
        # 3. using 255 to normaizle + truncate when expand grey to rgba
        # 4. 3 modes. a. 1d b. rgb 1d (rgbrgb) c. rgb 1d (rrr...ggg...bbb...) <- Planar = 1
        # 5. assume RGB is 8 bit or daikon already downsize to 8 bit?
        # 6. not sure if handle floating data or not
        # 7. no mosue to adjust window center/width when no stored window center/width by default
        # 8. no windoe center mode on RGB

        ### flatten to 1 d array ###
        # afterwards, treat it as RGB image, the PALETTE file we tested has planar:1
        if self.photometric == "RGB" or self.photometric == "PALETTE COLOR":
            print("it is RGB or PALETTE COLOR")

            if normalize_image.ndim == 1:
                print("flatten_jpeg_RGB_image1d_to_rgba_1d_image_array")
                # http://medistim.com/wp-content/uploads/2016/07/ttfm.dcm 1.2.840.10008.1.2.4.70
                # alpha = np.full_like(compress_pixel_data, 255)
                # print(f"alpha1:{alpha.shape}")  # ()
                # indexes: sometimes it will throw error, e.g. http://medistim.com/wp-content/uploads/2016/07/bmode.dcm
                # TypeError: object of type 'numpy.uint8' has no len()
                start = time.time()
                normalize_image2 = normalize_image.reshape(
                    (self.width, self.height, 3)
                )  # ~ 0s
                self.render_rgba_1d_ndarray = (
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
                # uncompress case
                # if planar_config == 0:
                # US-RGB-8-esopecho # 0.025s
                print("flatten_rgb_image2d_plan0_to_rgba_1d_image_array!!")
                self.render_rgba_1d_ndarray = (
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

            self.render_rgba_1d_ndarray = (
                self.flatten_grey_image_to_rgba_1d_image_array(normalize_image)
            )

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
        print(f"render time:{time.time()-start}")  # 0.009

    def __init__(
        self,
        buffer: Any = None,
        jpeg_lossless_decoder: Any = None,
        normalize_mode=NormalizeMode.window_center_mode,
    ):
        ## TODO: handle BitsAllocated 32,64 case

        # buffer: pyodide.JsProxy
        # decoder: pyodide.JsProxy
        print(
            f"__init__!!!!!!!!!!!!! buffer:{type(buffer)} decoder:{type(jpeg_lossless_decoder)}"
        )
        if self.is_pyodide_env():
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
            ds = self.get_pydicom_dataset_from_local_file("dicom/image-00000-ot.dcm")

        self.ds = ds
        width: int = ds[0x0028, 0x0011].value
        height: int = ds[0x0028, 0x0010].value
        print(f"dimension: {width}; {height}")
        self.width = width
        self.height = height
        modality: str = ds[0x0008, 0x0060].value
        print(f"Modality:{modality}")
        self.modality = modality

        self.bit_allocated = ds[0x0028, 0x0100].value
        print(f"bit_allocated:{self.bit_allocated}")

        self.pixel_representation = ds[0x0028, 0x0103].value
        print(f"pr:{self.pixel_representation}")

        # 8,8 or 16,12
        # bit_allocated = ds[0x0028, 0x0100].value
        bites_stored = ds[0x0028, 0x0101].value
        print(f"stored_bites:{bites_stored}")

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
            print(f"transferSyntax:{transferSyntaxUID}")
        except:
            print("no TransferSyntaxUID")
        try:
            photometric: str = ds.PhotometricInterpretation
            print(f"photometric:{photometric}")
        except:
            print("no photometric")
            photometric = ""
        self.photometric = photometric
        self.transferSyntaxUID = transferSyntaxUID
        frame_number = getattr(ds, "NumberOfFrames", 1)
        print(f"frame_number:{frame_number}")

        compress_pixel_data = None
        if photometric == "PALETTE COLOR":
            print("it is PALETTE COLOR")
            # https://pydicom.github.io/pydicom/stable/old/working_with_pixel_data.html
            # before: a grey 2d image
            image = apply_color_lut(ds.pixel_array, ds)
            # after: a RGB 2d image
            print(f"PALETTE after apply_color_lut shape:{image.shape}")

            # _max, _min = get_image2d_maxmin(image2d)
            # print(f'pixel (after color lut) min:{_min}')  # min same as before
            # print(f'pixel (after color lut) max:{_max}')  # max same as before
            # but still need normalization (workaround way?) !!! Undocumented part !!!!
            # Mabye it is because its max (dark) is 65536, 16bit
            # image2d = normalize_image2d(image2d, _max, _min)
        else:
            # https://github.com/pyodide/pyodide/discussions/1273
            # previous: jpeg.lossless.Decoder.new()
            (
                image,
                compress_pixel_data,
            ) = self.get_manufacturer_independent_pixel_image2d_array(
                ds, transferSyntaxUID, jpeg_lossless_decoder
            )
            print(f"after get_manufacturer_independent_pixel_image2d_array")
            # NOTE: using image2d == None will throw a error which says some element is ambiguous
            self.compressed_pixel_bytes = compress_pixel_data
            if image is None:
                # return bytes data
                # TODO: how to add width, height ?
                print(f"directly return compressed data")
                # Columns (0028,0011), Rows (0028,0010)

                # self.image = image

                # self.min = int(_min)
                # self.max = int(_max)
                # self.photometric = photometric
                # self.transferSyntaxUID = transferSyntaxUID
                # self.bit_allocated = bit_allocated
                return
                # compress_pixel_data is bytes
                # 0                           1     2        3      4      5            6                 7
                # return compress_pixel_data, width, height, None, None, photometric, transferSyntaxUID, bit_allocated
        ### multi frame case, workaround way to get its 1st frame, not consider switching case ###
        # TODO: only get 1st frame for multiple frame case and will improve later
        if frame_number > 1:
            print("only get the 1st frame image2d data")
            image = image[0]

        _max, _min = self.get_image_maxmin(image)
        print(f"uncompressed shape:{image.shape}")
        self.min = int(_min)
        self.max = int(_max)
        print(f"max:{self.max};{self.min}")

        if photometric == "MONOCHROME1":
            print("invert color for monochrome1")
            # -100 ~ 300
            start = time.time()
            image = _max - image + _min
            print(f"invert monochrome1 time:{time.time()-start}")

        self.image = image
        self.normalize_mode = normalize_mode
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
