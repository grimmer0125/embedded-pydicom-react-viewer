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
    const { data, width, height } = await parseByPython(buffer);
    console.log('parsing dicom done')
    renderFrameByPythonData(data, width, height);
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
