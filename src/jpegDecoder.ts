
const JpegDecoder = require("./jpeg-baseline").JpegImage
const jpeg = require("jpeg-lossless-decoder-js");
const JpxImage = require('./jpx');
const JpegLSDecoder = require('./jpeg-ls');

// borrow from https://github.com/rii-mango/daikon/blob/master/src/image.js#L706
const decompressJPEG = (jpg: any, transferSyntaxUID: string, bitsAllocated: number, isBytesInteger: boolean) => {
  // 1. PyProxyClass 
  // 2. Uint8Array (if use pyodide.to_js first)
  // 3. PyProxyClass (is use pyodide.create_proxy)
  if (transferSyntaxUID === "1.2.840.10008.1.2.4.57" || transferSyntaxUID === "1.2.840.10008.1.2.4.70") {
    // JPEGLossless
    // console.log("jpg:", jpg, typeof jpg)
    const decoder = new jpeg.lossless.Decoder();
    const decoded = decoder.decode(jpg);
    return decoded.buffer
  } else if (transferSyntaxUID === "1.2.840.10008.1.2.4.50" || transferSyntaxUID === "1.2.840.10008.1.2.4.51") { // 50, 51
    // JPEGBaseline
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
    const buffer = decoded.buffer;
    return buffer;
  } else if (transferSyntaxUID === "1.2.840.10008.1.2.4.90" || transferSyntaxUID === "1.2.840.10008.1.2.4.91") {
    // JPEG_2000
    // remaining not tested yet: "1.2.840.10008.1.2.4.90"

    const decoder = new JpxImage();
    decoder.parse(new Uint8Array(jpg));
    const decoded = decoder.tiles[0].items;
    return decoded.buffer;
  } else if (transferSyntaxUID === "1.2.840.10008.1.2.4.80" || transferSyntaxUID === "1.2.840.10008.1.2.4.81") {
    // JPEGLS
    const decoder = new JpegLSDecoder();
    const decoded = decoder.decodeJPEGLS(new Uint8Array(jpg), isBytesInteger);
    return decoded.pixelData.buffer;
  }

}

export default decompressJPEG;


