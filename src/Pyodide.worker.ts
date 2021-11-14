import { D4C } from "d4c-queue";

import * as Comlink from 'comlink'
import { PyProxy } from '../public/pyodide/pyodide.d'
const jpegLossless = require("jpeg-lossless-decoder-js");
const JpegBaselineDecoder = require("./decoder/jpeg-baseline").JpegImage
// const Jpx2000Image = require('./decoder/jpx');
// const JpegLSDecoder = require('./decoder/jpeg-ls');

// import { expose } from 'comlink';

// const jpeg = require("jpeg-lossless-decoder-js");





// import decompressJPEG from "./jpegDecoder"
// console.log("jpegDecoder:", decompressJPEG)
// import NormalizationMode from "./App"

declare const self: DedicatedWorkerGlobalScope & { pyodide: any };
export default {} as typeof Worker & { new(): Worker };

const d4c = new D4C();

declare var loadPyodide: any;


const decompressJPEG = {
  lossless: (bytes: any) => {
    const buffer = bytes.getBuffer()
    const decoder = new jpegLossless.lossless.Decoder();
    const data = buffer.data;
    const decoded = decoder.decode(data, data.byteOffset, data.byteLength);
    buffer.release()
    return decoded.buffer
  },
  baseline: (bytes: any, bitsAllocated: number) => {
    // JPEGBaseline
    const buffer = bytes.getBuffer()
    const decoder = new JpegBaselineDecoder();
    decoder.parse(new Uint8Array(buffer.data));
    const width = decoder.width;
    const height = decoder.height;

    let decoded;
    if (bitsAllocated === 8) {
      decoded = decoder.getData(width, height);
    } else if (bitsAllocated === 16) {
      decoded = decoder.getData16(width, height);
    }
    buffer.release()
    return decoded.buffer;
  },
  // jpeg2000: (bytes: any) => {
  //   // JPEG_2000
  //   // remaining not tested yet: "1.2.840.10008.1.2.4.90"
  //   const buffer = bytes.getBuffer()
  //   const decoder = new Jpx2000Image();
  //   decoder.parse(new Uint8Array(buffer.data));
  //   const decoded = decoder.tiles[0].items;
  //   buffer.release()
  //   return decoded.buffer;
  // },
  // jpegls: (bytes: any, isBytesInteger: boolean) => {
  //   // JPEGLS
  //   const buffer = bytes.getBuffer()
  //   const decoder = new JpegLSDecoder();
  //   const decoded = decoder.decodeJPEGLS(new Uint8Array(buffer.data), isBytesInteger);
  //   buffer.release()
  //   return decoded.pixelData.buffer;
  // }
}

// NOTE: 
// 1. micropip.install becomes to need specific base_url in worker case 
// they do not know current window url !!
// 2. d4c is not compatible with comlink !!!
//const baseURL = 'http://localhost:3000/'

const baseURL = self.location.origin + "/"
// console.log("self.location:", self.location)

importScripts(baseURL + "pyodide/pyodide.js");

// var uint8 = new Uint8Array(2);
// uint8[0] = 42;

var buffer = new ArrayBuffer(8);
var uint8 = new Uint8Array(buffer);
uint8[0] = 42;

var uint82 = new Uint8Array(buffer);

console.log({ "d0:": uint8[0] })

console.log({ "d2:": uint82[0] })

postMessage(buffer);
// onmessage = function (oEvent) {
//   postMessage("Hi " + oEvent.data);
// };

let dicomGlobal: any = null;

// TODO: 看起來要可以把每次新的 ndarray 直接給當前 worker 再丟給 JS main app.tsx 的話
// 一開始就不能直接把整個 dicomObj 用 comlink.proxy 包起來 (不然就是要每次都臨時 unproxy, 得到 getBuffer 後 ui canvas copy 後再 proxy link!!)
// 不然 property 看起來之後每次都是自動也是 proxy 等級 (這樣就會看到 ArrayBuffer is not detachable and could not be cloned.) <-也不能在接收端指定要 return value 是 transfer 
//   如果在這邊 transfer, 如果上層 object 是 proxy, 就會遇到 Uncaught (in promise) DOMException: Failed to execute 'postMessage' on 'DedicatedWorkerGlobalScope': ArrayBuffer is not detachable and could not be cloned.
// NOTE: transfer 只能一次
// NOTE2: a.  (uint8,[uint8.buffer]) or uint8.buffer, [uint8.buffer]) works 
// b. Comlink.transfer(uint8, [uint8])  // Uncaught (in promise) TypeError: Failed to execute 'postMessage' on 'DedicatedWorkerGlobalScope': Value at index 0 does not have a transferable type.

// 下面失敗是因為已經是 proxy 的關係
// Comlink.transfer(data.buffer, [data.buffer]);
// Uncaught (in promise) DOMException: Failed to execute 'postMessage' on 'DedicatedWorkerGlobalScope': ArrayBuffer is not detachable and could not be cloned.

export async function remoteFunction(): Promise<any> {
  // const pyBuffer = dicomGlobal.final_rgba_1d_ndarray.getBuffer("u8clamped");;
  // 因為沒有 copy, 所以還是受限於之前就已經是 comlink proxy
  // const data = pyBuffer.data
  // console.log("try:")
  const ndarray = self.pyodide.globals.get("global_array")

  // const pyBuffer = ndarray.getBuffer("u8clamped");
  const uint8 = ndarray.toJs();

  const uncompressedData = new Uint8ClampedArray(uint8.buffer)
  // const uint8 = pyBuffer.data;
  // console.log("send:", { uncompressedData })
  // console.log("data:", { data: pyBuffer.data })
  // const start0 = new Date().getTime();
  // console.log("send:" + start0)

  return Comlink.transfer(uncompressedData, [uncompressedData.buffer])


  //postMessage(data2.data.buffer);

  // return "1"; //data;

  // return Comlink.transfer(uint8.buffer, [uint8.buffer]) // or uint8, [uint8.buffer] works 
  // return Comlink.transfer(uint8, [uint8])

  // return Comlink.transfer(data.buffer, [data.buffer]);
  // return Comlink.transfer(dicomGlobal, [dicomGlobal.final_rgba_1d_ndarray])
  // return Comlink.transfer(data, [data.buffer])

  // console.log("executes async function in web worker ")
  // return `Hello ${name}!`;
}

let PyodideDicomClass: any;



const initPyodideAndLoadPydicom = d4c.wrap(async () => {
  console.log("initPyodideAndLoadPydicom")

  // self.pyodide  = await loadPyodide({ indexURL : "https://cdn.jsdelivr.net/pyodide/v0.18.0/full/" });
  // globalThis.pyodide = await loadPyodide({ indexURL: "pyodide/" }); <- not work in 0.18, works in 0.17


  self.pyodide = await loadPyodide({ indexURL: baseURL + "pyodide/" });
  console.log("inject base_url to pyodide globals:", baseURL)
  self.pyodide.globals.set("base_url", baseURL)

  const pythonCode = await (await fetch(baseURL + 'python/pyodide_init.py')).text();
  await self.pyodide.loadPackagesFromImports(pythonCode);
  await self.pyodide.runPythonAsync(pythonCode);
  console.log("initPyodideAndLoadPydicom done")
});

const loadPyodideDicomModule = d4c.wrap(async () => {
  console.log("loadPyodideDicomModule")
  const pythonCode = await (await fetch(baseURL + 'python/dicom_parser.py')).text();
  // console.log(`code:${pythonCode}`) // without baseURL, it becomes html,  need baseURL !!
  // if (self.pyodide) {
  //   console.log("has pyodide")
  // }
  // await self.pyodide.loadPackagesFromImports(pythonCode);
  // self.pyodide.registerComlink(comlink)
  await self.pyodide.loadPackagesFromImports(pythonCode);
  await self.pyodide.runPythonAsync(pythonCode);
  PyodideDicomClass = self.pyodide.globals.get('PyodideDicom')
  console.log("loadPyodideDicomModule done")
});


const newPyodideDicom = d4c.wrap((buffer: ArrayBuffer, useWindowCenter?: number, useWindowWidth?: number, currNormalizeMode?: number) => {
  // const decoder = new jpeg.lossless.Decoder()
  const dicomObj: any = PyodideDicomClass(buffer, undefined, decompressJPEG, useWindowCenter, useWindowWidth, currNormalizeMode);
  // return dicomObj
  // console.log(`dicom:${dicomObj}`)
  // dicom:PyodideDicom(uncompressed_ndarray=array([  0,   0,   0, ...,   0,   0, 255], dtype=uint8), width=1024, height=1024, max=595, min=0, modality='MR', photometric='MONOCHROME2', transferSyntaxUID='1.2.840.10008.1.2.4.57', allocated_bits=16, ds=Dataset.file_meta -------------------------------
  // (0002, 0000) File Meta Information Group Length  UL: 150

  // console.log(`dicom max:${dicomObj.max}`)
  // postMessage({name:"testla"});

  dicomGlobal = dicomObj;

  return Comlink.proxy(dicomObj)
});

// Define API
export const api = {
  initPyodideAndLoadPydicom,
  loadPyodideDicomModule,
  newPyodideDicom,
  remoteFunction
};

Comlink.expose(api);


