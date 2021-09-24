import { useRef, useEffect, useState, useCallback } from "react";

import {
  Dropdown,
  Checkbox,
  CheckboxProps,
  DropdownProps,
  Radio,
} from "semantic-ui-react";

import { useDropzone } from "react-dropzone";
import { initPyodideAndLoadPydicom, loadPyodideDicomModule, loadDicomFileAsync } from "./pyodideHelper";
import { PyProxyBuffer, PyProxy } from '../public/pyodide/pyodide.d'
import canvasRender from "./canvasRenderer"


// import * as daikon from "daikon";

const JpegDecoder = require("./jpeg-baseline").JpegImage
const jpeg = require("jpeg-lossless-decoder-js");
type PyProxyObj = any

// image = daikon.Series.parseImage(new DataView(buffer));
// console.log("daikon:", daikon)
// console.log("daikon2:", JpegDecoder)

// const a = new daikon.Image()
// console.log("a:", a.decompressJPEG)

const decompressJPEG = (jpg: any, isCompressedJPEGLossless: boolean, isCompressedJPEGBaseline: boolean, bitsAllocated: number) => {
  if (isCompressedJPEGLossless) {
    const decoder = new jpeg.lossless.Decoder();
    return decoder.decode(jpg).buffer;
  } else if (isCompressedJPEGBaseline) {
    const decoder = new JpegDecoder();
    decoder.parse(new Uint8Array(jpg));
    const width = decoder.width;
    const height = decoder.height;

    let decoded;
    if (bitsAllocated === 8) {
      decoded = decoder.getData(width, height);
    } else if (bitsAllocated === 16) {
      decoded = decoder.getData16(width, height);
    }
    return decoded.buffer;
  }
}

enum NormalizationMode {
  PixelHUMaxMin,
  WindowCenter,
  // below are for CT,   // https://radiopaedia.org/articles/windowing-ct
  AbdomenSoftTissues, //W:400 L:50
  SpineSoftTissues, // W:250 L:50
  SpineBone, // W:1800 L:400
  Brain, // W:80 L:40
  Lungs, // W:1500 L:-600. chest
}

interface WindowItem {
  W: number;
  L: number;
}

interface NormalizationProps {
  disable?: boolean;
  mode: NormalizationMode;
  windowItem?: WindowItem;
  currNormalizeMode: NormalizationMode;
  onChange?: (
    e: React.FormEvent<HTMLInputElement>,
    data: CheckboxProps
  ) => void;
}

interface IWindowDictionary {
  [id: number]: WindowItem;
}

const WindowCenterWidthConst: IWindowDictionary = {
  [NormalizationMode.AbdomenSoftTissues]: {
    W: 400,
    L: 50,
  },
  [NormalizationMode.SpineSoftTissues]: {
    W: 250,
    L: 50,
  },
  [NormalizationMode.SpineBone]: {
    W: 1800,
    L: 400,
  },
  [NormalizationMode.Brain]: {
    W: 80,
    L: 40,
  },
  [NormalizationMode.Lungs]: {
    W: 1500,
    L: -600,
  },
};

function NormalizationComponent(props: NormalizationProps) {
  const { mode, windowItem, currNormalizeMode, onChange, disable } = props;
  const data = windowItem ?? WindowCenterWidthConst[mode] ?? null;
  return (
    <>
      <Checkbox
        radio
        disabled={disable}
        label={NormalizationMode[mode]}
        name="checkboxRadioGroup"
        value={mode}
        checked={currNormalizeMode === mode}
        onChange={onChange}
      // checked={ifWindowCenterMode}
      // onChange={this.handleNormalizeModeChange}
      />
      {data ? ` c:${data.L}, w:${data.W}  ` : `  `}
    </>
  );
}

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

let total = 0;

function App() {
  const myCanvasRef = useRef<HTMLCanvasElement>(null);
  const isValidMouseDown = useRef(false);
  const clientX = useRef<number>()
  const clientY = useRef<number>()
  const dicomObj = useRef<any>(null);
  const PyodideDicom = useRef<Function>()

  const [isPyodideLoading, setPyodideLoading] = useState(true);
  const [modality, setModality] = useState("")
  const [photometric, setPhotometric] = useState("")
  const [transferSyntax, setTransferSyntax] = useState("")
  const [currFilePath, setCurrFilePath] = useState("")
  const [resX, setResX] = useState<number>()
  const [resY, setResY] = useState<number>()
  const [pixelMax, setPixelMax] = useState<number>()
  const [pixelMin, setPixelMin] = useState<number>()
  const [windowCenter, setWindowCenter] = useState<number>()
  const [windowWidth, setWindowWidth] = useState<number>()
  const [useWindowCenter, setUseWindowCenter] = useState<number>()
  const [useWindowWidth, setUseWindowWidth] = useState<number>()
  // todo: define a clear interface/type instead of any 
  const [currNormalizeMode, setCurrNormalizeMode] = useState<NormalizationMode>(NormalizationMode.WindowCenter)

  const onMouseMove = (event: any) => {
    if (isValidMouseDown.current && clientX.current != undefined && clientY.current != undefined && pixelMax != undefined && pixelMin != undefined) {

      let deltaX = event.clientX - clientX.current;
      let deltaY = clientY.current - event.clientY;

      let newWindowWidth, newWindowCenter;

      let previousWindowWidth = useWindowWidth ?? windowWidth;
      if (previousWindowWidth) {
        newWindowWidth = previousWindowWidth + deltaX;
        if (newWindowWidth <= 1) {
          newWindowWidth = 2;
          deltaX = newWindowWidth - newWindowWidth;
        }
      } else {
        newWindowWidth = Math.floor((pixelMax - pixelMin) / 2);
      }

      if (deltaX === 0 && deltaY === 0) {
        // console.log(" delta x = y = 0")
        return;
      }

      let previousWindowCenter = useWindowCenter ?? windowCenter;
      if (previousWindowCenter) {
        newWindowCenter = previousWindowCenter + deltaY;
      } else {
        newWindowCenter = Math.floor((pixelMin + pixelMax) / 2);
      }

      setUseWindowCenter(newWindowCenter)
      setUseWindowWidth(newWindowWidth)

      const image: PyProxyObj = dicomObj.current
      // console.log("trigger new frame")
      image.render_frame_to_rgba_1d(newWindowCenter, newWindowWidth)
      renderFrame()
    } else {
      // console.log("not valid move")
    }
    clientX.current = event.clientX;
    clientY.current = event.clientY;
  }

  const onMouseCanvasDown = useCallback((event: any) => {
    console.log("onMouseDown:", event, typeof event);

    clientX.current = event.clientX;
    clientY.current = event.clientY;
    isValidMouseDown.current = true;
    // window.addEventListener("mousemove", onMouseMove);
  }, []);

  const onMouseUp = useCallback((event: any) => {
    console.log("onMouseUp:", event);
    isValidMouseDown.current = false;
    // window.removeEventListener("mousemove", onMouseMove);
  }, []);

  useEffect(() => {
    async function init() {
      console.log("initialize Pyodide, python browser runtime");
      // todo: sometimes App will be reloaded due to CRA hot load and hrow exception due to 2nd load pyodide
      if (isPyodideLoading) {
        try {
          initPyodideAndLoadPydicom(); // do some initialization
          PyodideDicom.current = await loadPyodideDicomModule();
          setPyodideLoading(false);
          console.log("finish initializing Pyodide");
        } catch {
          console.log("init pyodide error, probably duplicate loading it");
        }
      }
    }
    init();
    console.log("register mouseup")
    window.addEventListener("mouseup", onMouseUp);

  }, []); // [] means only 1 time, if no [], means every update this will be called

  const renderFrame = () => {
    const image: PyProxyObj = dicomObj.current;
    // if (total != 0) {
    //   console.log("not render33")
    //   return
    // }
    // todo: figure it out 
    // 1. need destroy old (e.g. image.destroy()) when assign new image ? yes
    // 2. how to get toJS(1) effect when assigning a python object instance to dicom.current?
    // 3. /** TODO: need releasing pyBufferData? pyBufferData.release()
    // * ref: https://pyodide.org/en/stable/usage/type-conversions.html#converting-python-buffer-objects-to-javascript */
    // const render_rgba_1d_ndarray: any = image.render_rgba_1d_ndarray;
    // console.log("render_rgba_1d_ndarray:", render_rgba_1d_ndarray, typeof render_rgba_1d_ndarray)
    // const kk = image.toJs({ depth: 1 })
    // console.log("kk:", kk)


    if (image.has_uncompressed_data) {
      // console.log("render uncompressedData");

      // if (true) {

      const ndarray_proxy = (image as any).get_rgba_1d_ndarray() //render_rgba_1d_ndarray
      const buffer = (ndarray_proxy as PyProxyBuffer).getBuffer("u8clamped");
      (ndarray_proxy as PyProxyBuffer).destroy();

      // if (true) {
      // const ndarray = image.render_rgba_1d_ndarray // <- memory leak !!!
      // const pyBufferData = (ndarray as PyProxyBuffer).getBuffer("u8clamped");
      // (ndarray as PyProxy).destroy()
      // kk.destroy()
      // console.log("pyBufferData data type1, ", typeof pyBufferData.data, pyBufferData.data) // Uint8ClampedArray
      const uncompressedData = buffer.data as Uint8ClampedArray
      canvasRender.renderUncompressedData(uncompressedData, image.width as number, image.height as number, myCanvasRef);
      // pyBufferData.release()
      // }

      buffer.release(); // Release the memory when we're done

      // } else {
      //   // (ndarray as PyProxy).destroy()
      //   console.log("not render2")
      // }
      // render_rgba_1d_ndarray.destroy();
      // (image.render_rgba_1d_ndarray as PyProxyBuffer).destroy() // 沒用
      total += 1;
    } else if (image.has_compressed_data) {
      console.log("render compressedData");
      const compressed = (image as any).get_compressed_pixel() // compressed_pixel_bytes
      const pyBufferData = (compressed as PyProxyBuffer).getBuffer()
      compressed.destroy();
      // console.log("pyBufferData data type2, ", typeof pyBufferData.data, pyBufferData.data) // Uint8Array
      const compressedData = pyBufferData.data as Uint8Array;
      canvasRender.renderCompressedData(
        compressedData,
        image.width as number,
        image.height as number,
        image.transferSyntaxUID as string,
        image.photometric as string,
        image.bit_allocated as number,
        myCanvasRef
      );
      pyBufferData.release()
    } else {
      console.log("no uncompressedData & no compressedData")
    }
    total += 1;

    // image.destroy();
  }

  const loadFile = async (file: File) => {
    setCurrFilePath(file.name)
    const buffer = await loadDicomFileAsync(file);
    // NOTE: besides getting return value (python code last line expression),
    // python data can be retrieved by accessing python global object:
    // pyodide.globals.get("image")
    console.log("start to use python to parse parse dicom data");

    if (PyodideDicom.current) {
      console.log("has imported PyodideDicom class")
      dicomObj.current = PyodideDicom.current(buffer, decompressJPEG)
      const image: PyProxyObj = dicomObj.current;
      // console.log(`image:${image}`) // print a lot of message: PyodideDicom(xxxx
      console.log(`image max:${image.max}`)
      console.log(`image center:${image.window_center}`) // works !!!

      setModality(image.modality)
      setPhotometric(image.photometric)
      setTransferSyntax(image.transferSyntaxUID)
      setResX(image.width)
      setResY(image.height)
      setPixelMax(image.max)
      setPixelMin(image.min)
      setWindowCenter(image.window_center)
      setWindowWidth(image.window_width)


      /** original logic is to const res = await pyodide.runPythonAsync, then res.toJs(1) !! v0.18 use toJs({depth : n})
       * now changes to use a Python object instance in JS !!
       */

      if (image.ds) {
        // console.log("image ds:", image.ds) // target: PyProxyClass
        // console.log(image.ds) // Proxy
        // console.log(typeof image.ds) // object
        console.log(`PhotometricInterpretation: ${(image.ds as PyProxy).PhotometricInterpretation}`) // works
      }

      renderFrame()


    } else {
      console.log("has not imported PyodideDicom class, ignore")
    }
  }

  const resetUI = () => {
    const canvas = myCanvasRef.current;
    canvasRender.resetCanvas(canvas)
    if (dicomObj.current) {
      dicomObj.current.destroy()
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

  const handleNormalizeModeChange = useCallback((
    e: React.FormEvent<HTMLInputElement>,
    data: CheckboxProps
  ) => {
    console.log("handleNormalizeModeChange")
    const { value } = data;

    const newMode = value as number;
    setCurrNormalizeMode(newMode)
  }, []);

  let info = ""
  info += ` modality:${modality}; photometric:${photometric}; transferSyntax:${transferSyntax};`;
  info += ` resolution:${resX} x ${resY}`;

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
          <div>
            {info}
            <br />
            {` current window center:${useWindowCenter} ; window width ${useWindowWidth} ;`}
            {` pixel/HU max:${pixelMax}, min:${pixelMin} ;`}
            {` file: ${currFilePath} ;`}
          </div>
          <div className="flex-container">
            <NormalizationComponent
              mode={NormalizationMode.WindowCenter}
              windowItem={
                (windowCenter !== undefined && windowWidth !== undefined)
                  ? { L: windowCenter, W: windowWidth }
                  : undefined
              }
              currNormalizeMode={currNormalizeMode}
              onChange={handleNormalizeModeChange}
            />
            <NormalizationComponent
              disable={true}
              mode={NormalizationMode.PixelHUMaxMin}
              currNormalizeMode={currNormalizeMode}
              onChange={handleNormalizeModeChange}
            />
          </div>
        </div>
        <div className="flex-container">
          <div className="flex-column-justify-align-center">
            <div className="flex-column_align-center">
              {/* <img style={{width:500, height:250}} ref={myImg} /> */}
              <canvas
                ref={myCanvasRef}
                onMouseDown={onMouseCanvasDown}
                onMouseMove={onMouseMove}
                // onMouseUp={onMouseUp}
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
