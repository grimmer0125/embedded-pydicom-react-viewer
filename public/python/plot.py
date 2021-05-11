import matplotlib.pyplot as plt
from pydicom import dcmread
from pydicom.data import get_testdata_file

from pydicom.uid import (
    UID, JPEG2000, JPEG2000Lossless, JPEGBaseline8Bit, JPEGExtended12Bit
)

from io import BytesIO


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


def render(fpath=""):
    if fpath == "":
        fpath = get_testdata_file('CT_small.dcm')
    ds = dcmread(fpath, force=True)

    check_pillow(ds)

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

    from pydicom.encaps import defragment_data, decode_data_sequence

    pixel_data = defragment_data(ds.PixelData)
    print(f"pixel_data:{len(pixel_data)}")
    # return None, pixel_data

    try:
        fio = BytesIO(pixel_data)  # pixel_data)
        image = Image.open(fio)
    except Exception as e:
        print(f"pillow error:{e}")

    print('pillow done')

    # plot the image using matplotlib
    plt.imshow(ds.pixel_array, cmap=plt.cm.gray)
    plt.show()
