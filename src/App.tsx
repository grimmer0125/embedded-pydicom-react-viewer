import { useRef, useEffect, useState, useCallback } from "react";

import { useDropzone } from "react-dropzone";
import { initPyodideAndLoadPydicom, loadPyodideDicomModule, loadDicomFileAsync, newPyodideDicom } from "./pyodideHelper";

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
  // const PyodideDicom = useRef<Function>()

  const [isPyodideLoading, setPyodideLoading] = useState(true);

  useEffect(() => {
    async function init() {
      console.log("initialize Pyodide, python browser runtime");
      // todo: sometimes App will be reloaded due to CRA hot load and hrow exception due to 2nd load pyodide
      if (isPyodideLoading) {
        try {
          // 下面這個
          initPyodideAndLoadPydicom(); // do some initialization
          await loadPyodideDicomModule();
          setPyodideLoading(false);
          console.log("finish initializing Pyodide");
        } catch {
          console.log("init pyodide error, probably duplicate loading it");
        }
      }
    }
    init();
  }, []); // [] means only 1 time, if no [], means every update this will be called

  const loadFile = async (file: File) => {
    const buffer = await loadDicomFileAsync(file);
    // NOTE: besides getting return value (python code last line expression),
    // python data can be retrieved by accessing python global object:
    // pyodide.globals.get("image")
    console.log("start to use python to parse parse dicom data");

    // if (PyodideDicom.current) {
    console.log("has imported PyodideDicom class")
    const image: any = await newPyodideDicom(buffer); //PyodideDicom.current(buffer, decoder)

    console.log("await image", await image) // proxy

    console.log(image) // proxy 
    console.log(await image.max) // 255
    console.log((await image).max) // proxy
    console.log(await (await image).max) //255 

    // const max = await image.max;
    // const min = await image.min;
    const width = await image.width;
    const height = await image.height;
    console.log("image height:", height);

    const has_uncompressed = await image.has_uncompressed;
    const has_compressed = await image.has_compressed;

    // if ("compressed_pixel_bytes" in image) {
    //   console.log("exist compressed_pixel_bytes")
    // } else {
    //   console.log("no exist compressed_pixel_bytes")

    // }

    // if ("uncompressed_ndarray" in image) {
    //   console.log("exist uncompressed_ndarray")
    // } else {
    //   console.log("no exist uncompressed_ndarray")

    // }

    // Uncaught (in promise) DOMException: Failed to execute 'postMessage' on 'MessagePort': [object Object] could not be cloned.
    // console.log("image.uncompressed_ndarray:", await image.uncompressed_ndarray)
    // compressed_pixel_bytes is undefind 
    // if (image.compressed_pixel_bytes) {
    //   console.log("image.compressed_pixel_bytes:")

    //   const b = await (image.compressed_pixel_bytes.toJs())
    // } else {
    //   console.log("image.compressed_pixel_bytes is undefined ")
    // }

    // double Proxy (pyodide & comlink !!!!)
    // const uncompressed_ndarray0 = image.uncompressed_ndarray;
    // console.log(await uncompressed_ndarray0) //exception
    // console.log((await uncompressed_ndarray0).toJs()) //exception
    // console.log(uncompressed_ndarray0.toJs()) //promise pending 

    // https://github.com/grimmer0125/embedded-pydicom-react-viewer/blob/410d6519a7/src/pyodideHelper.ts
    /** original logic is to const  const res = await pyodide.runPythonAsync, then res.toJs(1) !! v0.18 use toJs({depth : n})
     * now changes to use a Python object instance in JS !!
     */

    // const bb = await (uncompressed_ndarray0.getBuffer("u8clamped"));
    // Uncaught (in promise) DOMException: Failed to execute 'postMessage' on 'MessagePort': ArrayBuffer is not detachable and could not be cloned.
    // uncompressed_ndarray0.getBuffer() <- has getBuffer method but not compatible with comlink !!!!!!!!!!!!!!!!!!!


    // todo: figure it out 
    // 1. need destroy old (e.g. image.destroy()) when assign new image ?
    // 2. how to get toJS(1) effect when assigning a python object instance to dicom.current?
    // 3. /** TODO: need releasing pyBufferData? pyBufferData.release()
    // * ref: https://pyodide.org/en/stable/usage/type-conversions.html#converting-python-buffer-objects-to-javascript */
    if (has_uncompressed) {
      console.log("render uncompressedData");
      const uncompressed_ndarray = await (image.uncompressed_ndarray.toJs());
      console.log("image uncompressed_ndarray:", uncompressed_ndarray) // Uint8Array(3145728) !!!!

      // console.log(`PhotometricInterpretation: ${PhotometricInterpretation}`); // works
      // const pyBufferData = uncompressed_ndarray.getBuffer("u8clamped");
      // console.log("buffer:", pyBufferData)
      const uncompressedData = new Uint8ClampedArray(uncompressed_ndarray.buffer)
      // console.log("uncompressedData:", uncompressedData)
      renderUncompressedData(uncompressedData, width, height, myCanvasRef);
    } else if (has_compressed) {
      console.log("render compressedData");
      const pyBufferData = await image.compressed_pixel_bytes.toJs()
      console.log("pyBufferData:", pyBufferData) //, pyBufferData.data)
      // const compressedData = pyBufferData.data
      renderCompressedData(
        pyBufferData,
        width,
        height,
        await image.transferSyntaxUID,
        await image.photometric,
        await image.allocated_bits,
        myCanvasRef
      );
    } else {
      console.log("no uncompressedData & no compressedData")
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

  const onDropFiles = useCallback(async (acceptedFiles: File[]) => {
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
