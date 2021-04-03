import { useRef, useEffect } from 'react'

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

const MAX_WIDTH_SINGLE_MODE = 1280;
const MAX_HEIGHT_SINGLE_MODE = 1000;
const MAX_WIDTH_SERIES_MODE = 400;
const MAX_HEIGHT_SERIES_MODE = 400;

function App() {

  const my_js_module = useRef<any>({});
  const myCanvasRef = useRef<HTMLCanvasElement>(null);

  // NOTE: do some initialization
  useEffect(() => {
    initPyodide();
  }, []); // [] means only 1 time, if no [], means every update


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
    const pythonCode = `
      import setuptools
      import micropip
      import io
      await micropip.install('pydicom')
      print("install pydicom ok")        
    `;

    console.log("start to use python code, initialize Pyodide")
    await languagePluginLoader;
    await pyodide.loadPackage(['numpy', 'micropip']);
    await pyodide.runPythonAsync(pythonCode);
  
    pyodide.registerJsModule("my_js_module", my_js_module.current);


    console.log("finish initializing Pyodide")
  }

  const parseByPython = async (buffer:ArrayBuffer) =>{

    const pythonCode = `
      import pydicom
      from pydicom.pixel_data_handlers.util import apply_modality_lut
      from my_js_module import buffer 
      print("get buffer")
      # print(buffer) #  memoryview object.
      ds = pydicom.dcmread(io.BytesIO(buffer))
      name = ds.PatientName
      print("family name:"+name.family_name)
      arr = ds.pixel_array
      image = apply_modality_lut(arr, ds)
      min = image.min() 
      max = image.max() 
      print(min)
      print(max)
      name2 = name.family_name
      image, min, max # use image, name will result [data, proxy] after toJS <- not happen anymore
    `;

    my_js_module.current["buffer"] = buffer;


    console.log("start to use python to parse parse dicom data")
    const result = await pyodide.runPythonAsync(pythonCode);

    const result2 = result.toJs();
    const image2dUnit8Array = result2[0];
    const min = result2[1];
    const max = result2[2]
    result.destroy();
    console.log('done')
    return { data: image2dUnit8Array, min, max} ;
  }

  const renderFrameByPythonData = async (image2dUnit8Array: Array<Uint8Array>, min: number, max: number) => {

    // ignore 
    // 1. possible window center & width mode (need work with rescale equation)
    // 2. RGB mode1, RGB mode2
    // 3. MONOCHROME1 inverted color 
    // 4. multiple frame 
    // 5. corona & sagittal views
    // 6. scale (shrink to viewer size )
    // 7. get (optional) stored max/min from dicom ?? 

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
            DICOM Image Viewer
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
            {/* {isCommonAxialView ? <div>{"A"}</div> : null}{" "} */}
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
              }}
            >
              {/* {isCommonAxialView ? <div>{"R"}</div> : null}{" "} */}
              <canvas
                // onMouseDown={this.onMouseCanvasDown}
                ref={myCanvasRef}
                width={MAX_WIDTH_SERIES_MODE}
                height={MAX_HEIGHT_SERIES_MODE}
                style={{ backgroundColor: "black" }}
              />
              {/* {isCommonAxialView ? <div>{"L"}</div> : null}{" "} */}
            </div>
            {/* {isCommonAxialView ? <div>{"P"}</div> : null}{" "} */}
          </div>
        </div>

      </div>
    </div>  
  );
}

export default App;
