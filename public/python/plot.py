from threading import local
import matplotlib.pyplot as plt
from pydicom import dcmread
from pydicom.data import get_testdata_file

from pydicom.uid import (
    UID, JPEG2000, JPEG2000Lossless, JPEGBaseline8Bit, JPEGExtended12Bit
)

from pydicom.encaps import defragment_data, decode_data_sequence

from io import BytesIO

from compressed import parse_comppressed

try:
    import PIL
    from PIL import Image, features
    HAVE_PIL = True
    HAVE_JPEG = features.check_codec("jpg")
    HAVE_JPEG2K = features.check_codec("jpg_2000")
    print("import pillow done")
except ImportError:
    HAVE_PIL = False
    HAVE_JPEG = False
    HAVE_JPEG2K = False

PillowJPEG2000TransferSyntaxes = [JPEG2000, JPEG2000Lossless]
PillowJPEGTransferSyntaxes = [JPEGBaseline8Bit, JPEGExtended12Bit]
PillowSupportedTransferSyntaxes = (
    PillowJPEGTransferSyntaxes + PillowJPEG2000TransferSyntaxes
)


def check_pillow(ds):
    transfer_syntax = "1.2.840.10008.1.2.4.51"  # ds.file_meta.TransferSyntaxUID

    if not HAVE_PIL:
        raise ImportError(
            f"The pillow package is required to use pixel_array for "
            f"this transfer syntax {transfer_syntax.name}, and pillow could "
            f"not be imported."
        )

    if not HAVE_JPEG and transfer_syntax in PillowJPEGTransferSyntaxes:
        raise NotImplementedError(
            f"The pixel data with transfer syntax {transfer_syntax.name}, "
            f"cannot be read because Pillow lacks the JPEG plugin"
        )

    if not HAVE_JPEG2K and transfer_syntax in PillowJPEG2000TransferSyntaxes:
        raise NotImplementedError(
            f"The pixel data with transfer syntax {transfer_syntax.name}, "
            f"cannot be read because Pillow lacks the JPEG 2000 plugin"
        )

    # if transfer_syntax == JPEGExtended12Bit:  # and ds.BitsAllocated != 8:
    #     raise NotImplementedError(
    #         f"{JPEGExtended12Bit} - {JPEGExtended12Bit.name} only supported "
    #         "by Pillow if Bits Allocated = 8")


# local_file = "dicom/JPEG-lossy.dcm"  # <-51,  70: CT-MONO2-16-chest.dcm"
# local_file = "dicom/JPGExtended.dcm" # 51 too, but miss some headers
# local_file = "dicom/SC_rgb_small_odd_jpeg.dcm"  # 50
# local_file = 'SC_jpeg_no_color_transform.dcm' 50 但我的 extension 也讀不到
folder_name = "dicom_samples/"

# local_file = 'JPGLosslessP14SV1_1s_1f_8b'  # jpeg_baseline_8bit.dcm'
# 'dwv-bbmri-53323131 (13)-mr'  # 'CT'  # 0020 CT-MONO2-16-chest'
# local_file = 'jpeg_ls' <-error # 'jpeg_baseline_8bit' # <-error  # 'itri'  # 'image-00000-ot'
# local_file = error : 'JPGExtended'  # 'JPEG57-MR-MONO2-12-shoulder'  # 'JPEG-lossy'
# local_file = error: 'SC_jpeg_no_color_transform'
# local_file = error: 'SC_rgb_small_odd_jpeg'
# local_file = 'JPGLosslessP14SV1_1s_1f_8b'  # '0002'  # 'tmp'
# local_file = 'JPEG-lossy'  # 'JPEG57-MR-MONO2-12-shoulder'
# local_file = "US-PAL-8-10x-echo"
# local_file = 'color3d_jpeg_baseline'
# local_file = 'CT-MONO2-16-ort'
local_file = 'JPEG2000'
local_file = folder_name + local_file

# TODO: duplicate


def get_pixel_data(ds):
    print(f"PixelData:{len(ds.PixelData)}")
    if getattr(ds, 'NumberOfFrames', 1) > 1:
        j2k_precision, j2k_sign = None, None
        # multiple compressed frames
        frame_count = 0
        for frame in decode_data_sequence(ds.PixelData):
            frame_count += 1
            print(f"frame i:{frame_count}, len:{len(frame)}")
            if frame_count == 1:
                pixel_data = frame
    else:
        pixel_data = defragment_data(ds.PixelData)
        print(f"pixel_data:{len(pixel_data)}")
    return pixel_data


def extract_compressed_data_to_save(fpath=""):
    print(f"{fpath}")
    if fpath == "":
        fpath = get_testdata_file('CT_small.dcm')
    ds = dcmread(fpath+".dcm", force=True)

    # check_pillow(ds)

    # Normal mode:
    # print()
    # print(f"File path........: {fpath}")
    # print(f"SOP Class........: {ds.SOPClassUID} ({ds.SOPClassUID.name})")
    # print()

    # pat_name = ds.PatientName
    # display_name = pat_name.family_name + ", " + pat_name.given_name
    # print(f"Patient's Name...: {display_name}")
    # print(f"Patient ID.......: {ds.PatientID}")
    # print(f"Modality.........: {ds.Modality}")
    # print(f"Study Date.......: {ds.StudyDate}")
    # print(f"Image size.......: {ds.Rows} x {ds.Columns}")
    # print(f"Pixel Spacing....: {ds.PixelSpacing}")

    # # use .get() if not sure the item exists, and want a default value if missing
    # print(f"Slice location...: {ds.get('SliceLocation', '(missing)')}")

    _, pixel_data = parse_comppressed(ds)

    # pixel_data = defragment_data(ds.PixelData)
    print(f"pixel_data:{len(pixel_data)}")
    b = pixel_data[len(pixel_data)-2]
    a = pixel_data[len(pixel_data)-1]
    p2 = pixel_data
    print(f"p2 data:{len(p2)}")

    f = open(fpath+".jpg", "wb")
    f.write(p2)
    f.close()


def render(fpath):
    # import matplotlib.pyplot as plt
    # import pydicom
    # from pydicom.data import get_testdata_files
    # filename = get_testdata_files("CT_small.dcm")[0]
    ds = dcmread(fpath+".dcm", force=True)
    pixel_data = ds.pixel_array
    # US-PAL-8-10x-echo, rle: 10, 430, 600 !!! multiple frame
    # color3d_jpeg_baseline, 120x480x640x3 !!
    shape = pixel_data.shape
    pixel_data2 = pixel_data[0]
    plt.imshow(pixel_data2, cmap=plt.cm.bone)
    plt.show()
    print("o")
    # return None, pixel_data

    # try:
    #     fio = BytesIO(pixel_data)  # pixel_data)
    #     image = Image.open(fio)
    # except Exception as e:
    #     print(f"pillow error:{e}")

    # print('pillow done')

    # # plot the image using matplotlib
    # plt.imshow(ds.pixel_array, cmap=plt.cm.gray)
    # plt.show()


extract_compressed_data_to_save(local_file)

# render(local_file)
