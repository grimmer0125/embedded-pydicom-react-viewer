const jpeg = require("jpeg-lossless-decoder-js");

function resetCanvas(canvas: HTMLCanvasElement | null) {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

function renderUncompressedData(
  imageUnit8Array: Uint8ClampedArray,
  rawDataWidth: number,
  rawDataHeight: number,
  myCanvasRef: React.RefObject<HTMLCanvasElement>
) {
  if (!myCanvasRef.current) {
    console.log("canvasRef is not ready, return");
    return;
  }

  const c = myCanvasRef.current;
  c.width = rawDataWidth;
  c.height = rawDataHeight;

  const ctx = c.getContext("2d");
  if (!ctx) {
    return;
  }
  // const a = imageUnit8Array.byteLength; // width*height*4
  // no allocate new memory
  // console.log(rawDataWidth, rawDataHeight, imageUnit8Array.byteLength);
  const imgData = new ImageData(imageUnit8Array, rawDataWidth, rawDataHeight);
  ctx.putImageData(imgData, 0, 0);
};

// todo: know width, height, color_bit first ?????
// 1. JPGLosslessP14SV1_1s_1f_8b:70 works 1024x768x1 Uint8Array
// 2. JPEG57-MR-MONO2-12-shoulder: 57, 1024x1024, 2byteColor: Uint16Array
function renderNonBaselineJPEG(
  input: ArrayBuffer,
  rawDataWidth: number,
  rawDataHeight: number,
  transferSyntaxUID: string,
  photometric: string,
  allocated_bits: number,
  myCanvasRef: React.RefObject<HTMLCanvasElement>
) {
  if (
    transferSyntaxUID !== "1.2.840.10008.1.2.4.57" &&
    transferSyntaxUID !== "1.2.840.10008.1.2.4.70"
  ) {
    console.log(`not supported transferSyntaxUID:${transferSyntaxUID}`);
    return;
    // renderNonBaselineJPEG(buffer2, rawDataWidth, rawDataHeight)
  } // photometric:MONOCHROME2

  if (photometric !== "MONOCHROME2") {
    return;
  }

  console.log(`allocated_bits:${allocated_bits}`);

  const decoder = new jpeg.lossless.Decoder();

  // {ArrayBuffer} output (size = cols * rows * bytesPerComponent * numComponents)
  const output: ArrayBuffer = decoder.decompress(input);
  console.log(`before decoded buffer: ${output.byteLength}`); // 1024x1024x2 每一pixel 2byte, grey color?. 1024*768*1
  // const WIDTH = 1024;
  // const HEIGHT = 768;
  let uint8View;
  if (allocated_bits === 16) {
    uint8View = new Uint16Array(output); // 會把 byte array 硬塞進去
  } else {
    uint8View = new Uint8Array(output); // 會把 byte array 硬塞進去
  }
  // = 1024*1024. 1024*768*1. 如果是用 unit16 for 1024x768 那張, 這裡會變成 1024*768*0.5
  console.log(`unitView got:${uint8View.length}`);
  // const uint8View2 = new Uint8ClampedArray(output);

  const pixel_size = rawDataWidth * rawDataHeight * 4; // 1024*1024*4 = 4194304
  console.log(`w*h*4:${pixel_size}`); //1024*768*1
  // const kkk = uint8View.length; // = output.byteLength
  const arrayBuffer = new ArrayBuffer(pixel_size);
  const pixels = new Uint8ClampedArray(arrayBuffer);
  let max = 0;
  let min = 0;
  for (let i = 0; i < uint8View.length; i++) {
    //  一個value 同時是兩個 pixel.
    const value = uint8View[i];
    if (value > max) {
      max = value;
    }
    if (value < min) {
      min = value;
    }
    const j = i * 4;
    pixels[j] = value / 2; // divided 2 & Uint16Array is needed for JPEG57-MR-MONO2-12-shoulder
    pixels[j + 1] = value / 2;
    pixels[j + 2] = value / 2;
    pixels[j + 3] = 255;
  }
  console.log(`max:${max}`); // 595 !!!!!
  console.log(`min:${min}`); // 0
  // for (let y = 0; y < HEIGHT; y++) {
  //   for (let x = 0; x < WIDTH; x++) {
  //     const i = (y * WIDTH + x) * 4; // 0, 1, 2,3
  //     pixels[i] = uint8View[i]; // red
  //     pixels[i + 1] = uint8View[i]; // green
  //     pixels[i + 2] = uint8View[i]; // blue
  //     pixels[i + 3] = 255; // alpha
  //   }
  // }
  renderUncompressedData(pixels, rawDataWidth, rawDataHeight, myCanvasRef);
};

function renderCompressedData(
  imageUnit8Array: Uint8Array,
  rawDataWidth: number,
  rawDataHeight: number,
  transferSyntaxUID: string,
  photometric: string,
  allocated_bits: number,
  myCanvasRef: React.RefObject<HTMLCanvasElement>
) {
  // console.log("renderFrameByPythonCompressedData");

  const myImg = new Image();
  const buffer = imageUnit8Array.buffer;

  // works for myImg.current.src
  // https://stackoverflow.com/questions/37228285/uint8array-to-arraybuffer
  function typedArrayToBuffer(array: Uint8Array): ArrayBuffer {
    return array.buffer.slice(
      array.byteOffset,
      array.byteLength + array.byteOffset
    );
  }
  const buffer2 = typedArrayToBuffer(imageUnit8Array);
  // console.log(
  //   "len:",
  //   imageUnit8Array.length,
  //   buffer.byteLength,
  //   buffer2.byteLength
  // ); //   718924, 75366400 (buffer.byteLength is more than actual size), 718924

  // console.log(`transferSyntaxUID:${transferSyntaxUID}`);
  if (transferSyntaxUID !== "1.2.840.10008.1.2.4.50") {
    // except 50, 57, 70. e.g. 80, 81 will go into here
    renderNonBaselineJPEG(
      buffer2,
      rawDataWidth,
      rawDataHeight,
      transferSyntaxUID,
      photometric,
      allocated_bits,
      myCanvasRef,
    );
    return;
  }

  if (!myCanvasRef.current) {
    console.log("canvasRef is not ready, return");
    return;
  }
  const c = myCanvasRef.current;
  c.width = rawDataWidth;
  c.height = rawDataHeight;
  const ctx = c.getContext("2d");
  if (!ctx) {
    return;
  }

  // works for myImg.current.src
  /** uint8 -> base64: https://stackoverflow.com/questions/21434167/how-to-draw-an-image-on-canvas-from-a-byte-array-in-jpeg-or-png-format */
  // var i = imageUnit8Array.length;
  // var binaryString = new Array(i);// [i];
  // while (i--) {
  //     binaryString[i] = String.fromCharCode(imageUnit8Array[i]);
  // }
  // var data = binaryString.join('');
  // var base64 = window.btoa(data);
  // const url2 =  "data:image/jpeg;base64," + base64;

  // works => become not work
  //****** testing svg rendering */
  // const my_svg = `<svg version="1.1" xmlns="http://www.w3.org/2000/svg"></svg>`;
  // const my_svg_blob = new Blob([my_svg], {
  //   type: "image/svg+xml;charset=utf-8",
  // });
  // const url4 = URL.createObjectURL(my_svg_blob);
  //****** testing svg rendering */

  ////****** testing manually make a mock data */
  // works for myImg.current.src
  // const content = new Uint8Array([
  //   137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 5,
  //   0, 0, 0, 5, 8, 6, 0, 0, 0, 141, 111, 38, 229, 0, 0, 0, 28, 73, 68, 65, 84,
  //   8, 215, 99, 248, 255, 255, 63, 195, 127, 6, 32, 5, 195, 32, 18, 132, 208,
  //   49, 241, 130, 88, 205, 4, 0, 14, 245, 53, 203, 209, 142, 14, 31, 0, 0, 0,
  //   0, 73, 69, 78, 68, 174, 66, 96, 130,
  // ]);
  // const url3 = URL.createObjectURL(
  //   new Blob([content.buffer], { type: "image/png" } /* (1) */)
  // );
  ////****** testing manually make a mock data */

  const blob = new Blob([buffer2], { type: "image/jpeg" });
  const url = URL.createObjectURL(blob);

  if (myImg) {
    myImg.onload = function () {
      /// draw image to canvas
      // console.log("on load:", myImg.width, myImg.height);
      c.width = myImg.width;
      c.height = myImg.height;
      ctx.drawImage(myImg as any, 0, 0, myImg.width, myImg.height);
    };
    myImg.src = url; //"https://raw.githubusercontent.com/grimmer0125/grimmer0125.github.io/master/images/bio.png";
  }
};

export default {
  renderCompressedData,
  renderUncompressedData,
  resetCanvas,
}