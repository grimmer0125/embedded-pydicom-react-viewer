import { useRef, useEffect, useState, useCallback } from "react";

import { useDropzone } from "react-dropzone";
import { initPyodideAndLoadPydicom, loadPyodideDicomModule, loadDicomFileAsync } from "./pyodideHelper";

import {
  renderCompressedData,
  renderUncompressedData
} from "./canvasRenderer"

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

function checkIfValidDicomFileName(name: string) {
  if (
    name.toLowerCase().endsWith(".dcm") === false &&
    name.toLowerCase().endsWith(".dicom") === false
  ) {
    console.log("not dicom file:", name);
    return false;
  }
  return true;
}

// interface PyodideDicomObject {
//   SayHi: () => void
// }

function App() {
  const myCanvasRef = useRef<HTMLCanvasElement>(null);
  // todo: define a clear interface/type instead of any 
  const dicomObj = useRef<any>(null);
  const PyodideDicom = useRef<Function>()

  const [isPyodideLoading, setPyodideLoading] = useState(true);

  useEffect(() => {
    async function init() {
      console.log("initialize Pyodide, python browser runtime");
      // todo: sometimes App will be reloaded due to CRA hot load and hrow exception due to 2nd load pyodide
      try {
        initPyodideAndLoadPydicom(); // do some initialization
        PyodideDicom.current = await loadPyodideDicomModule();
        setPyodideLoading(false);
        console.log("finish initializing Pyodide");
      } catch {
        console.log("init pyodide error, probably duplicate loading it");
      }
    }
    init();
  }, []); // [] means only 1 time, if no [], means every update this will be called

  const loadFile = async (file: File) => {
    const buffer = await loadDicomFileAsync(file);
    // NOTE: besides getting return value (python code last line expression),
    // python data can be retrieved by accessing python global object:
    // pyodide.globals.get("image")<-dev version (but stable v0.17.0a2 can use), pyodide.pyimport('sys')<-stable version;
    console.log("start to use python to parse parse dicom data");

    if (PyodideDicom.current) {
      console.log("has imported PyodideDicom class")
      dicomObj.current = PyodideDicom.current(buffer)
      const image =  dicomObj.current; 
      console.log(`image:${image}`)
      console.log(`image max:${image.max}`)
      /** original logic is to const  const res = await pyodide.runPythonAsync, then res.toJs(1) !! 
       * now changes to use a Python object instance in JS !!
       */

      // todo: figure it out 
      // 1. need destroy old (e.g. image.destroy()) when assign new image ?
      // 2. how to get toJS(1) effect when assigning a python object instance to dicom.current?
      // 3. /** TODO: need releasing pyBufferData? pyBufferData.release()
      // * ref: https://pyodide.org/en/stable/usage/type-conversions.html#converting-python-buffer-objects-to-javascript */
      if (image.compressedData) {
        console.log("render compressedData");
        const pyBufferData = image.compressed_pixel_bytes.getBuffer()
        const compressedData = pyBufferData.data
        renderCompressedData(
              compressedData,
              image.width,
              image.height,
              image.transferSyntaxUID,
              image.photometric,
              image.allocated_bits,
              myCanvasRef
          );
      } else {
        console.log("render uncompressedData");
        const pyBufferData = image.uncompressed_ndarray.getBuffer("u8clamped");
        const uncompressedData = pyBufferData.data
        renderUncompressedData(uncompressedData, image.width, image.height, myCanvasRef);
      }    
    } else{
      console.log("has not imported PyodideDicom class, ignore")
    }
  }

  const resetUI = () => {
    const canvas = myCanvasRef.current;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  const onDropFiles = useCallback( async (acceptedFiles: File[]) => {
    console.log("acceptedFiles");

    if (acceptedFiles.length > 0) {
      acceptedFiles.sort((a: any, b: any) => {
        return a.name.localeCompare(b.name);
      });
      const file = acceptedFiles[0];
      resetUI();
      if (checkIfValidDicomFileName(file.name)) {
        await loadFile(file);
      }
    }

    // Do something with the files
  }, []);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: onDropFiles,
  });

  return (
    <div className="flex-container">
      <div>
        <div className="flex-container">
          <div>
            DICOM Image Viewer{" "}
            {isPyodideLoading ? ", loading python runtime" : ""}
          </div>
        </div>
        <div>
          <div className="flex-container">
            <div style={dropZoneStyle} {...getRootProps()}>
              <input {...getInputProps()} />
              {isDragActive ? (
                <p>Drop the files here ...</p>
              ) : (
                <p>Drag 'n' drop some files here, or click to select files</p>
              )}
            </div>

            {/* <Dropzone
              // style={dropZoneStyle}
              // getDataTransferItems={(evt) => fromEvent(evt)}
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
            </Dropzone> */}
          </div>
        </div>
        <div className="flex-container">
          <div className="flex-column-justify-align-center">
            <div className="flex-column_align-center">
              {/* <img style={{width:500, height:250}} ref={myImg} /> */}
              <canvas
                ref={myCanvasRef}
                width={MAX_WIDTH_SERIES_MODE}
                height={MAX_HEIGHT_SERIES_MODE}
              // style={{ backgroundColor: "black" }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
