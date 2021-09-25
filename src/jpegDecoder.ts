
const JpegDecoder = require("./jpeg-baseline").JpegImage
const jpeg = require("jpeg-lossless-decoder-js");

// borrow from https://github.com/rii-mango/daikon/blob/master/src/image.js#L706
const decompressJPEG = (jpg: any, isCompressedJPEGLossless: boolean, isCompressedJPEGBaseline: boolean, bitsAllocated: number) => {
  // console.log("jpg:", jpg, typeof jpg) // PyProxyClass !!
  if (isCompressedJPEGLossless) {
    const decoder = new jpeg.lossless.Decoder();
    return decoder.decode(jpg).buffer;
  } else if (isCompressedJPEGBaseline) {
    const decoder = new JpegDecoder();
    decoder.parse(new Uint8Array(jpg));
    const width = decoder.width;
    const height = decoder.height;

    let decoded;
    if (bitsAllocated === 8) {
      decoded = decoder.getData(width, height);
    } else if (bitsAllocated === 16) {
      decoded = decoder.getData16(width, height);
    }
    return decoded.buffer;
  }
}

export default decompressJPEG;


