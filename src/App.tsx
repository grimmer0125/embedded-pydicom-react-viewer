import { useRef, useEffect, useState } from 'react'

import Dropzone from "react-dropzone";
import { loadDicomAsync } from "./utility";
const { fromEvent } = require("file-selector");

declare var pyodide:any;
declare var loadPyodide:any;

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
    // NOTE: besides get return value (python code last line expression), 
    // python data can be retrieved by accessing python global object:
    // pyodide.globals.get("image")<-dev version (but stable v0.17.0a2 can use), pyodide.pyimport('sys')<-stable version; 
    const { data, width, height}  = await parseByPython(buffer);
    renderFrameByPythonData(data, width, height);    
  }

  const initPyodide = async () =>{
    console.log("initialize Pyodide, python browser runtime")
    // await loadPyodide({ indexURL : "https://cdn.jsdelivr.net/pyodide/dev/full/" });
    await loadPyodide({ indexURL : "pyodide/" }); 

    await pyodide.loadPackage(['numpy', 'micropip']);
    
    // NOTE
    // https://pyodide.org/en/0.17.0a2/usage/faq.html
    // pyodide.runPython(await fetch('https://some_url/...')) <- doc seems missing .text() part
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

    const result2 = result.toJs(1);
    const pyBufferData = result2[0].getBuffer("u8clamped");
    const width = result2[3];
    const height = result2[4];
    result.destroy();
    console.log('parsing dicom done')
    return { data: pyBufferData.data, width, height} ;
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
    const imgData = new ImageData(imageUnit8Array,rawDataWidth,rawDataHeight);
    ctx.putImageData(imgData, 0, 0);
  }

  return (
    <div className="flex-container">
      <div>
        <div className="flex-container">
          <div>
            DICOM Image Viewer {isPyodideLoading?"loading python runtime, do not upload file now":""} 
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
        </div>      
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
