import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_color_lut
import numpy as np
import time
from io import BytesIO

# try:
#     import PIL
#     from PIL import Image, features
#     HAVE_PIL = True
#     HAVE_JPEG = features.check_codec("jpg")
#     HAVE_JPEG2K = features.check_codec("jpg_2000")
#     print("import pillow done")
# except ImportError:
#     HAVE_PIL = False
#     HAVE_JPEG = False
#     HAVE_JPEG2K = False


from pydicom.encaps import defragment_data, decode_data_sequence


def get_pydicom_dataset_from_js_buffer(buffer_memory):
    print("get buffer from javascript, copied memory to wasm heap, start to read dicom")
    # print(buffer) #  memoryview object.
    # file_name = "image-00000-ot.dcm"
    ds = pydicom.dcmread(BytesIO(buffer_memory), force=True)
    print("read dicom ok")
    # patient_name = ds.PatientName
    # print("patient family name:"+patient_name.family_name)
    return ds


def get_pydicom_dataset_from_local_file(path):
    ds = pydicom.dcmread(path, force=True)
    print("read dicom ok")
    return ds


def get_manufacturer_independent_pixel_image2d_array(ds):
    print("start reading dicom pixel_array")

    try:
        print(f"check its transferSyntax:{ds.file_meta.TransferSyntaxUID}")
        transfer = ds.file_meta.TransferSyntaxUID
        has_TransferSyntax = True

        if (transfer in ["1.2.840.10008.1.2.4.50", "1.2.840.10008.1.2.4.51", "1.2.840.10008.1.2.4.57", "1.2.840.10008.1.2.4.70", "1.2.840.10008.1.2.4.80", "1.2.840.10008.1.2.4.81", "1.2.840.10008.1.2.4.90", "1.2.840.10008.1.2.4.91", "1.2.840.10008.1.2.5"]):
            print(
                "can not handle by pydicom in pyodide, lack of some pyodide extension")
            # return None, ds.PixelData
        # ref: https://github.com/pydicom/pydicom/blob/master/pydicom/pixel_data_handlers/pillow_handler.py
        print(f"pixeldata:{len(ds.PixelData)}")

        if getattr(ds, 'NumberOfFrames', 1) > 1:
            print("multi frame")
            j2k_precision, j2k_sign = None, None
            # multiple compressed frames
            frame_count = 0
            for frame in decode_data_sequence(ds.PixelData):
                frame_count += 1
                print(f"frame i:{frame_count}, len:{len(frame)}")
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
            # TODO: what is the rule of -5, and is it always ?
            p2 = pixel_data[:-5]
        else:
            print("single frame")
            pixel_data = defragment_data(ds.PixelData)
            # TODO: 1. in some file, its ending is [-1], why?
            #       2. does
            p2 = pixel_data  # [:-1]
        print(f"pixel_data:{len(pixel_data)}")
        # return None, pixel_data

        # try:
        #     fio = BytesIO(ds.PixelData)  # pixel_data)
        #     image = Image.open(fio)
        # except Exception as e:
        #     print(f"pillow error:{e}")

        # print('pillow done')
        # JPEG57-MR-MONO2-12-shoulder data:718940 -> data:718924
        return None, p2

    except:
        print("no TransferSyntaxUID")
        has_TransferSyntax = False
    try:
        arr = ds.pixel_array
    except Exception as e:
        if has_TransferSyntax == True:
            raise e
        else:
            print(
                "read data fail may due to no TransferSyntaxUID, set it as ImplicitVRLittleEndian and try read dicom again")
            ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
            arr = ds.pixel_array
    print(f"read dicom pixel_array ok, shape:{arr.shape}")
    image2d = apply_modality_lut(arr, ds)
    return image2d, None


def get_image2d_maxmin(image2d):
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
    print(f'pixel (after modality lut) min:{_min}')
    print(f'pixel (after modality lut) max:{_max}')  # 255
    return _max, _min


def get_image2d_dimension(image2d):
    width = len(image2d[0])
    height = len(image2d)
    print(f'width:{width};height:{height}')
    return width, height


def normalize_image2d(image2d, _max, _min):
    width = len(image2d[0])
    height = len(image2d)

    print("start to flatten 2d grey array to RGBA 1d array + normalization")
    # step1: normalize
    start = time.time()
    print(f"center pixel:{image2d[height//2][width//2]}")
    # step1: normalize
    # ref: https://towardsdatascience.com/normalization-techniques-in-python-using-numpy-b998aa81d754
    # or use sklearn.preprocessing.minmax_scale, https://stackoverflow.com/a/55526862
    # scale = np.frompyfunc(lambda x, min, max: (x - min) / (max - min), 3, 1)
    value_range = _max - _min
    # 0.003, if no astype, just 0.002. using // become 0.02
    # or using colormap is another fast way,
    image2d = (((image2d-_min)/value_range)*255).astype("uint8")
    print(f"normalize time:{time.time()-start}")
    print(f"after normalize, center pixel:{image2d[height//2][width//2]}")
    return image2d


def flatten_rgb_image2d_plan0_to_rgba_1d_image_array(image2d):
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


def flatten_rgb_image2d_plan1_to_rgba_1d_image_array(image2d):
    # color by plane
    # Planar Configuration = 1 -> R1, R2, R3, …, G1, G2, G3, …, B1, B2, B3
    # e.g. US-RGB-8-epicard.dcm (480, 640, 3)

    # ISSUE:
    # The shape of testing DICOM file is like planar 0 and below just work
    # weird for RGB w/ planar 1 !!!

    # Originally I guess the shape is not correcct, found out the below link :
    # https://stackoverflow.com/questions/42650233/how-to-access-rgb-pixel-arrays-from-dicom-files-using-pydicom
    # image2d = image2d.reshape([image2d.shape[1], image2d.shape[2], 3]) <- not work

    # The final trial is just use the same function as planar 0
    # The only possible explanation is pydicom automatically read it as same shape for both cases

    return flatten_rgb_image2d_plan0_to_rgba_1d_image_array(image2d)


def flatten_grey_image2d_to_rgba_1d_image_array(image2d):
    # 3 planes. R plane (z=0), G plane (z=1), B plane (z=2)
    width = len(image2d[0])
    height = len(image2d)

    # https://stackoverflow.com/questions/63783198/how-to-convert-2d-array-into-rgb-image-in-python
    # step2: 2D grey -> 2D RGBA -> Flattn to 1D RGBA
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
            image[k + 1] = value  # 0.44700074195861816 / 0.05257463455200195
            delta5 += time.time() - start
            start = time.time()
            image[k + 2] = value  # 0.42699670791625977 / 0.048801422119140625
            delta6 += time.time() - start
            start = time.time()
            image[k + 3] = 255  # 0.3860006332397461 / 0.04797720909118652
            delta7 += time.time() - start
    total = delta1 + delta2 + delta3 + delta4 + delta5 + delta6 + delta7
    print(
        f"2d grey array flattens to 1d RGBA array ok:{total}")
    print(f"{delta1}, {delta2}, {delta3}, {delta4}, {delta5}, {delta6}, {delta7}")


def main(is_pyodide_context: bool):
    if is_pyodide_context:
        from my_js_module import buffer  # pylint: disable=import-error
        ds = get_pydicom_dataset_from_js_buffer(buffer.to_py())
    else:
        # start to do some local Python stuff, e.g. testing
        ds = get_pydicom_dataset_from_local_file(
            "dicom/image-00000-ot.dcm")
    image2d, compress_pixel_data = get_manufacturer_independent_pixel_image2d_array(
        ds)
    print("after get_manufacturer_independent_pixel_image2d_array")
    photometric = ds[0x28, 0x04].value
    if compress_pixel_data != None:
        # return bytes data
        # TODO: add width, height ?
        print(f"photometric:{photometric}")
        return compress_pixel_data, None, None, None, None,
    _max, _min = get_image2d_maxmin(image2d)
    width, height = get_image2d_dimension(image2d)

    print(f"photometric:{photometric};shape:{image2d.shape}")

    if photometric == "MONOCHROME1":
        print("invert color for monochrome1")
        # -100 ~ 300
        start = time.time()
        image2d = _max - image2d + _min
        print(f"invert monochrome1 time:{time.time()-start}")

    if photometric == "PALETTE COLOR":
        # https://pydicom.github.io/pydicom/stable/old/working_with_pixel_data.html
        # before: a grey 2d image
        image2d = apply_color_lut(ds.pixel_array, ds)
        # after: a RGB 2d image
        print(f"PALETTE after apply_color_lut shape:{image2d.shape}")

        _max, _min = get_image2d_maxmin(image2d)
        print(f'pixel (after color lut) min:{_min}')  # min same as before
        print(f'pixel (after color lut) max:{_max}')  # max same as before
        # but still need normalization (workaround way?) !!! Undocumented part !!!!
        # Mabye it is because its max (dark) is 65536, 16bit
        image2d = normalize_image2d(image2d, _max, _min)

        # afterwards, treat it as RGB image, the PALETTE file we tested has planar:1
    if photometric == "RGB" or photometric == "PALETTE COLOR":
        planar_config = ds[0x0028, 0x0006].value
        print(f"planar:{planar_config}. dimension:{image2d.shape}")  # 0 or 1

        if planar_config == 0:
            image = flatten_rgb_image2d_plan0_to_rgba_1d_image_array(image2d)
        else:
            image = flatten_rgb_image2d_plan1_to_rgba_1d_image_array(image2d)
    else:
        image2d = normalize_image2d(image2d, _max, _min)
        image = flatten_grey_image2d_to_rgba_1d_image_array(image2d)

    # Issue: instead of v0.17.0a2, if using latest dev code, this numpy.uint16 value becomes empty in JS !!!
    # so we need to use int(min), int(max)
    print(f'min type is:{type(_min)}')  # numpy.uint16
    print(f'width type is:{type(width)}')
    return image, width, height, int(_min), int(_max)


result = None
try:
    import js
    print("you are in pyodide")
    result = main(True)
except ModuleNotFoundError:
    is_pyodide_context = False
    print("you are not in pyodide, just do local python stuff")
    import line_profiler
    profile = line_profiler.LineProfiler()
    # using @profile is another way
    # TODO: wrap @profile with is_pyodide_context so we can use it both in local python or pyodide
    main_wrap = profile(main)
    result = main_wrap(False)
    profile.print_stats()
result


# if __name__ == '__main__':
#   will not be executed in pyodide context, after testing
#   print("it is in __main__")
