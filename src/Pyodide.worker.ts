// import { expose } from 'comlink';
import { D4C } from "d4c-queue";

import * as Comlink from 'comlink'
import { PyProxy } from '../public/pyodide/pyodide.d'
const jpeg = require("jpeg-lossless-decoder-js");
declare const self: DedicatedWorkerGlobalScope & {pyodide: any};
export default {} as typeof Worker & { new (): Worker };

const d4c = new D4C();

declare var loadPyodide: any;

// NOTE: 
// 1. micropip.install becomes to need specific base_url in worker case 
// they do not know current window url !!
// 2. d4c is not compatible with comlink !!!
//const baseURL = 'http://localhost:3000/'

const baseURL = self.location.origin +"/"
// console.log("self.location:", self.location)

importScripts(baseURL+"pyodide/pyodide.js");

// postMessage("I\'m working before postMessage(\'ali\').");
// onmessage = function (oEvent) {
//   postMessage("Hi " + oEvent.data);
// };

export async function remoteFunction(name: string): Promise<string> {
  console.log("executes async function in web worker ")
  return `Hello ${name}!`;
}

let PyodideDicomClass:any;

const initPyodideAndLoadPydicom = d4c.wrap(async () => {
  console.log("initPyodideAndLoadPydicom")
  
  // self.pyodide  = await loadPyodide({ indexURL : "https://cdn.jsdelivr.net/pyodide/v0.18.0/full/" });
  // globalThis.pyodide = await loadPyodide({ indexURL: "pyodide/" }); <- not work in 0.18, works in 0.17
  self.pyodide = await loadPyodide({ indexURL: baseURL+ "pyodide/" });
  console.log("inject base_url to pyodide globals:", baseURL )
  self.pyodide.globals.set("base_url", baseURL)

  const pythonCode = await (await fetch(baseURL+ 'python/pyodide_init.py')).text();
  await self.pyodide.loadPackagesFromImports(pythonCode);
  await self.pyodide.runPythonAsync(pythonCode);
  console.log("initPyodideAndLoadPydicom done")
});

const loadPyodideDicomModule = d4c.wrap(async () => {
  console.log("loadPyodideDicomModule")
  const pythonCode = await (await fetch(baseURL+'python/dicom_parser.py')).text();
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

// const init = async ()=> {
//   initPyodideAndLoadPydicom();
//   loadPyodideDicomModule();
// }

const newPyodideDicom = d4c.wrap((buffer:ArrayBuffer)=> {
  const decoder = new jpeg.lossless.Decoder()
  const dicomObj: PyProxy = PyodideDicomClass(buffer, decoder);
  // return dicomObj
  // console.log(`dicom:${dicomObj}`)
  // dicom:PyodideDicom(uncompressed_ndarray=array([  0,   0,   0, ...,   0,   0, 255], dtype=uint8), width=1024, height=1024, max=595, min=0, modality='MR', photometric='MONOCHROME2', transferSyntaxUID='1.2.840.10008.1.2.4.57', allocated_bits=16, ds=Dataset.file_meta -------------------------------
  // (0002, 0000) File Meta Information Group Length  UL: 150

  // console.log(`dicom max:${dicomObj.max}`)
  // postMessage({name:"testla"});

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


