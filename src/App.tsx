import { useRef, useEffect, useState } from 'react'

import Dropzone from "react-dropzone";
import { loadDicomAsync } from "./utility";
import {initPyodide, parseByPython} from "./pyodideHelper"
const { fromEvent } = require("file-selector");


const dropZoneStyle = {
  borderWidth: 2,
  borderColor: "#666",
  borderStyle: "dashed",
  borderRadius: 5,
  width: 800,
  height: 150,
};

const MAX_WIDTH_SERIES_MODE = 400;
const MAX_HEIGHT_SERIES_MODE = 400;


function App() {
  const myCanvasRef = useRef<HTMLCanvasElement>(null);
  // const myImg = useRef<HTMLImageElement>(null);

  const [isPyodideLoading, setPyodideLoading] = useState(true);

  useEffect(() => {
    async function init(){
      console.log("initialize Pyodide, python browser runtime")
      await initPyodide(); // do some initialization
      setPyodideLoading(false);
      console.log("finish initializing Pyodide")
    }
    init();
  }, []); // [] means only 1 time, if no [], means every update this will be called

  const onDropFiles = async (acceptedFiles: any[]) => {
    if (acceptedFiles.length > 0) {
      acceptedFiles.sort((a, b) => {
        return a.name.localeCompare(b.name);
      });

      loadFile(acceptedFiles[0]);
    }
  };

  const loadFile = async (file: any) => {
    const buffer = await loadDicomAsync(file);
    // NOTE: besides get return value (python code last line expression), 
    // python data can be retrieved by accessing python global object:
    // pyodide.globals.get("image")<-dev version (but stable v0.17.0a2 can use), pyodide.pyimport('sys')<-stable version; 
    console.log("start to use python to parse parse dicom data")
    const { compressedData, data, width, height } = await parseByPython(buffer);
    console.log('parsing dicom done')
    if (compressedData){
      renderFrameByPythonCompressedData(compressedData, width, height)
    } else {
      renderFrameByPythonData(data, width, height);
    }
  }

  const renderFrameByPythonCompressedData = async (imageUnit8Array: Uint8Array, rawDataWidth: number, rawDataHeight: number) => {
    console.log("renderFrameByPythonCompressedData")
    const canvasRef = myCanvasRef;
    if (!canvasRef.current) {
      console.log("canvasRef is not ready, return");
      return;
    }

    const c = canvasRef.current;
    c.width = rawDataWidth;
    c.height = rawDataHeight;

    const ctx = c.getContext("2d");
    if (!ctx) {
      return;
    }

    const myImg = new Image();

    // needs arrayBuffe, but feed unit8array
    const buffer = imageUnit8Array.buffer;
    // 1000000
    //  718940 
    // 75366400
    // JPEG Lossless

    // https://stackoverflow.com/questions/37228285/uint8array-to-arraybuffer
    function typedArrayToBuffer(array: Uint8Array): ArrayBuffer {
      return array.buffer.slice(array.byteOffset, array.byteLength + array.byteOffset)
    }
    const buffer2  = typedArrayToBuffer(imageUnit8Array)
    console.log("len:",imageUnit8Array.length, buffer.byteLength, buffer2.byteLength);
    const blob = new Blob([buffer2], {type: "image/jpeg"});

    const url = URL.createObjectURL(blob);

    /** uint8 -> base64: https://stackoverflow.com/questions/21434167/how-to-draw-an-image-on-canvas-from-a-byte-array-in-jpeg-or-png-format */
    var i = imageUnit8Array.length;
    var binaryString = new Array(i);// [i];
    while (i--) {
        binaryString[i] = String.fromCharCode(imageUnit8Array[i]);
    }
    var data = binaryString.join('');
    var base64 = window.btoa(data);
    const url2 =  "data:image/jpeg;base64," + base64;

    // 可能問題 1. jpeg codec 不是 baseline, 2. pyodide -> js 時那邊出了問題

    // works 
    // const my_svg = `<svg version="1.1" xmlns="http://www.w3.org/2000/svg"></svg>`; 
    // const blob = new Blob([my_svg], { type: 'image/svg+xml;charset=utf-8' })

    if (myImg) {
      myImg.onload = function() {
        /// draw image to canvas
        console.log("on load:")
        // ctx.drawImage((myImg as any), rawDataWidth, rawDataHeight);
      };
      myImg.src = url2;
    }
  }

  const renderFrameByPythonData = async (imageUnit8Array: Uint8ClampedArray, rawDataWidth: number, rawDataHeight: number) => {
    const canvasRef = myCanvasRef;
    if (!canvasRef.current) {
      console.log("canvasRef is not ready, return");
      return;
    }

    const c = canvasRef.current;
    c.width = rawDataWidth;
    c.height = rawDataHeight;

    const ctx = c.getContext("2d");
    if (!ctx) {
      return;
    }

    // no allocate new memory 
    const imgData = new ImageData(imageUnit8Array, rawDataWidth, rawDataHeight);
    ctx.putImageData(imgData, 0, 0);
  }

  return (
    <div className="flex-container">
      <div>
        <div className="flex-container">
          <div>
            DICOM Image Viewer {isPyodideLoading ? ", loading python runtime" : ""}
          </div>
        </div>
        <div>
          <div className="flex-container">
            <Dropzone
              preventDropOnDocument={false}
              style={dropZoneStyle}
              getDataTransferItems={(evt) => fromEvent(evt)}
              onDrop={onDropFiles}
            >
              <div
                className="flex-column-justify-align-center"
                style={{
                  height: "100%",
                }}
              >
                <div>
                  <p>
                    Try dropping DICOM image file here, <br />
                    or click here to select file to view. <br />
                  </p>
                </div>
              </div>
            </Dropzone>
          </div>
        </div>
        <div
          className="flex-container"
        >
          <div
            className="flex-column-justify-align-center"
          >
            <div
              className="flex-column_align-center"
            >
              {/* <img ref={myImg} /> */}
              <canvas
                ref={myCanvasRef}
                width={MAX_WIDTH_SERIES_MODE}
                height={MAX_HEIGHT_SERIES_MODE}
                style={{ backgroundColor: "black" }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
