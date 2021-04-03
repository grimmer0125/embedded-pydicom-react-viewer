import { useRef, useEffect, useState } from 'react'

import Dropzone from "react-dropzone";
import { loadDicomAsync } from "./utility";
const { fromEvent } = require("file-selector");

declare var languagePluginLoader:any;
declare var pyodide:any;

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

  const my_js_module = useRef<any>({});
  const myCanvasRef = useRef<HTMLCanvasElement>(null);

  const [isPyodideLoading, setPyodideLoading] = useState(true);


  // NOTE: do some initialization
  useEffect(() => {
    initPyodide();
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
    const { data, min, max}  = await parseByPython(buffer);
    renderFrameByPythonData(data, min, max);    
  }

  const initPyodide = async () =>{
    console.log("initialize Pyodide, python browser runtime")
    await languagePluginLoader;
    await pyodide.loadPackage(['numpy', 'micropip']);
    const pythonCode = await (await fetch('python/pyodide_init.py')).text();
    await pyodide.runPythonAsync(pythonCode);
    pyodide.registerJsModule("my_js_module", my_js_module.current);
    console.log("finish initializing Pyodide")
    setPyodideLoading(false);
  }

  const parseByPython = async (buffer:ArrayBuffer) =>{

    my_js_module.current["buffer"] = buffer;

    console.log("start to use python to parse parse dicom data")
    const pythonCode = await (await fetch('python/dicom_parser.py')).text();
    const result = await pyodide.runPythonAsync(pythonCode);

    const result2 = result.toJs();
    const image2dUnit8Array = result2[0];
    const min = result2[1];
    const max = result2[2]
    result.destroy();
    console.log('parsing dicom done')
    return { data: image2dUnit8Array, min, max} ;
  }

  const renderFrameByPythonData = async (image2dUnit8Array: Array<Uint8Array>, min: number, max: number) => {
    //** extra step
    const rawDataWidth  = image2dUnit8Array[0].length;
    const rawDataHeight = image2dUnit8Array.length; 
    
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
    const imgData = ctx.createImageData(rawDataWidth, rawDataHeight);
    const { data } = imgData;     

    for (let i = 0, k = 0; i < data.byteLength; i += 4, k += 1) {
      let row = Math.floor(k/rawDataWidth);
      let column = k% rawDataWidth; 
      let value = image2dUnit8Array[row][column];

      if (max && min) {
        const delta = max - min;

        value = ((value - min) * 255) / delta;
      }

      data[i] = value;
      data[i + 1] = value;
      data[i + 2] = value;
      data[i + 3] = 255;
    } 
    
    ctx.putImageData(imgData, 0, 0);
  }

  return (
    <div className="flex-container">
      <div>
        <div className="flex-container">
          <div>
            DICOM Image Viewer, {isPyodideLoading?"loading python runtime, do not upload file now":""} 
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
                style={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <div>
                  <p>
                    {" "}
                    Try dropping DICOM image file here, <br />
                    or click here to select file to view. <br />                  
                  </p>
                </div>
              </div>
            </Dropzone>                        
          </div>
          {/* optional some UI */}
        </div>      
        {/* optional some UI */}

        {/* canvas part */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
              }}
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
