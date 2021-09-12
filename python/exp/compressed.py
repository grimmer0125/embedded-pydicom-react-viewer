from pydicom.encaps import defragment_data, decode_data_sequence


def parse_comppressed(ds):
    try:
        print(f"pixeldata:{len(ds.PixelData)}")

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
                print(f"frame i:{frame_count}, len:{len(frame)}")
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
            # working case but browser can not render DICOM made JPEG Lossless :
            # JPGLosslessP14SV1_1s_1f_8b.dcm, 70. 1024x768
            pixel_data = defragment_data(ds.PixelData)
            p2 = pixel_data
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
    except Exception as e:
        print("failed to get compressed data")
        raise e
