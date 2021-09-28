import { useRef, useEffect, useState, useCallback } from "react";
import 'semantic-ui-css/semantic.min.css'

import {
  Dropdown,
  Checkbox,
  CheckboxProps,
  DropdownProps,
  Radio,
} from "semantic-ui-react";

import Slider from "rc-slider";
import "rc-slider/assets/index.css";

import { useDropzone } from "react-dropzone";
import { initPyodideAndLoadPydicom, loadPyodideDicomModule, loadDicomFileAsync } from "./pyodideHelper";
import { PyProxyBuffer, PyProxy } from '../public/pyodide/pyodide.d'
import canvasRender from "./canvasRenderer"
import decompressJPEG from "./jpegDecoder"
import { file } from "@babel/types";

type PyProxyObj = any

// image = daikon.Series.parseImage(new DataView(buffer));
// console.log("daikon:", daikon)
// console.log("daikon2:", JpegDecoder)

// const a = new daikon.Image()
// console.log("a:", a.decompressJPEG)

// const decompressJPEG = (jpg: any, isCompressedJPEGLossless: boolean, isCompressedJPEGBaseline: boolean, bitsAllocated: number) => {
//   if (isCompressedJPEGLossless) {
//     const decoder = new jpeg.lossless.Decoder();
//     return decoder.decode(jpg).buffer;
//   } else if (isCompressedJPEGBaseline) {
//     const decoder = new JpegDecoder();
//     decoder.parse(new Uint8Array(jpg));
//     const width = decoder.width;
//     const height = decoder.height;

//     let decoded;
//     if (bitsAllocated === 8) {
//       decoded = decoder.getData(width, height);
//     } else if (bitsAllocated === 16) {
//       decoded = decoder.getData16(width, height);
//     }
//     return decoded.buffer;
//   }
// }

enum SeriesMode {
  NoSeries,
  Series
}

enum NormalizationMode {
  PixelHUMaxMin, //start from 0 
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
    // console.log("not dicom file:", name);
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
  const myCanvasRefSagittal = useRef<HTMLCanvasElement>(null);
  const myCanvasRefCorona = useRef<HTMLCanvasElement>(null);

  const isValidMouseDown = useRef(false);
  const clientX = useRef<number>()
  const clientY = useRef<number>()
  const dicomObj = useRef<any>(null);
  const PyodideDicom = useRef<Function>()
  const files = useRef<File[]>([]);

  const [totalFiles, setTotalFiles] = useState<number>(0)
  const [totalCoronaFrames, setTotalCoronaFrames] = useState<number>(0)
  const [totalSagittalFrames, setTotalSagittalFrames] = useState<number>(0)
  const [currFileNo, setCurrFileNo] = useState<number>(0)
  const [currentSagittalNo, setCurrentSagittalNo] = useState<number>(0)
  const [currentCoronaNo, setCurrentCoronaNo] = useState<number>(0)

  const [ifShowSagittalCoronal, setIfShowSagittalCoronal] = useState<SeriesMode>(SeriesMode.NoSeries);
  const [isCommonAxialView, setIsCommonAxialView] = useState(false);

  // for testing 
  const fileBuffer = useRef<any>(null);

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
  const [numFrames, setNumFrames] = useState<number>(1)
  const [currFrameIndex, setCurrFrameIndex] = useState<number>(1)


  const onMouseMove = (event: any) => {
    const isGrey = photometric === "MONOCHROME1" || photometric === "MONOCHROME2"
    // console.log("onMouseMove1:", isGrey, isValidMouseDown.current, clientX.current, clientY.current, pixelMax, pixelMin)
    if (isGrey && isValidMouseDown.current && clientX.current != undefined && clientY.current != undefined && pixelMax != undefined && pixelMin != undefined) {

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

      if (ifShowSagittalCoronal === SeriesMode.Series) {
        dicomObj.current.redner_sag_view.callKwargs({
          normalize_window_center: newWindowCenter, normalize_window_width: newWindowWidth
        });
        dicomObj.current.redner_cor_view.callKwargs({
          normalize_window_center: newWindowCenter, normalize_window_width: newWindowWidth
        });
        dicomObj.current.render_axial_view.callKwargs({
          normalize_window_center: newWindowCenter, normalize_window_width: newWindowWidth
        });
      } else {
        dicomObj.current.render_frame_to_rgba_1d(newWindowCenter, newWindowWidth)
      }
      renderFrame()

      // processDicomBuffer(fileBuffer.current)
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
    // TODO: add parameters to specify which should be updated 
    const image: PyProxyObj = dicomObj.current;

    // todo: figure it out 
    // 1. x need destroy old (e.g. image.destroy()) when assign new image ? yes
    // 2. x how to get toJS(1) effect when assigning a python object instance to dicom.current?
    // 3. x /** TODO: need releasing pyBufferData? pyBufferData.release()
    // * ref: https://pyodide.org/en/stable/usage/type-conversions.html#converting-python-buffer-objects-to-javascript */
    // const render_rgba_1d_ndarray: any = image.render_rgba_1d_ndarray;
    // console.log("render_rgba_1d_ndarray:", render_rgba_1d_ndarray, typeof render_rgba_1d_ndarray)
    // const kk = image.toJs({ depth: 1 })
    // console.log("kk:", kk)

    const ax_ndarray = (image as any).get_ax_ndarray()
    if (ax_ndarray) {
      // console.log("ax_ndarray")
      const buffer = (ax_ndarray as PyProxyBuffer).getBuffer("u8clamped");
      (ax_ndarray as PyProxyBuffer).destroy();
      const uncompressedData = buffer.data as Uint8ClampedArray
      // console.log("uncompressedData:", uncompressedData, uncompressedData.length, uncompressedData.byteLength)
      canvasRender.renderUncompressedData(uncompressedData, image.width as number, image.height as number, myCanvasRef);
      buffer.release();
    } else {
      const ndarray_proxy = (image as any).get_rgba_1d_ndarray() //render_rgba_1d_ndarray
      if (ndarray_proxy) {
        // console.log("ndarray_proxy")
        const buffer = (ndarray_proxy as PyProxyBuffer).getBuffer("u8clamped");
        (ndarray_proxy as PyProxyBuffer).destroy();
        // console.log("pyBufferData data type1, ", typeof pyBufferData.data, pyBufferData.data) // Uint8ClampedArray
        const uncompressedData = buffer.data as Uint8ClampedArray
        canvasRender.renderUncompressedData(uncompressedData, image.width as number, image.height as number, myCanvasRef);
        buffer.release(); // Release the memory when we're done
      }
    }

    const sag_ndarray = (image as any).get_sag_ndarray()
    if (sag_ndarray) {
      // const shape = image.get_3d_shape().toJs();
      // console.log("sag_ndarray:", shape);

      const buffer = (sag_ndarray as PyProxyBuffer).getBuffer("u8clamped");
      (sag_ndarray as PyProxyBuffer).destroy();
      const uncompressedData = buffer.data as Uint8ClampedArray
      canvasRender.renderUncompressedData(uncompressedData, image.series_dim_y as number, image.series_dim_z as number, myCanvasRefSagittal, image.sag_aspect);
      buffer.release();
    }

    const cor_ndarray = (image as any).get_cor_ndarray()
    if (cor_ndarray) {
      // const shape = image.get_3d_shape().toJs();
      // console.log("cor_ndarray")
      const buffer = (cor_ndarray as PyProxyBuffer).getBuffer("u8clamped");
      (cor_ndarray as PyProxyBuffer).destroy();
      const uncompressedData = buffer.data as Uint8ClampedArray
      canvasRender.renderUncompressedData(uncompressedData, image.series_dim_x as number, image.series_dim_z as number, myCanvasRefCorona, image.cor_aspect);
      buffer.release();
    }

    // } else {
    //   // (ndarray as PyProxy).destroy()
    //   console.log("not render2")
    // }
    // render_rgba_1d_ndarray.destroy();
    // (image.render_rgba_1d_ndarray as PyProxyBuffer).destroy() // 沒用
    // total += 1;
    // } else if (image.has_compressed_data) {
    //   console.log("render compressedData");
    //   const compressed = (image as any).get_compressed_pixel() // compressed_pixel_bytes
    //   const pyBufferData = (compressed as PyProxyBuffer).getBuffer()
    //   compressed.destroy();
    //   // console.log("pyBufferData data type2, ", typeof pyBufferData.data, pyBufferData.data) // Uint8Array
    //   const compressedData = pyBufferData.data as Uint8Array;
    //   canvasRender.renderCompressedData(
    //     compressedData,
    //     image.width as number,
    //     image.height as number,
    //     image.transferSyntaxUID as string,
    //     image.photometric as string,
    //     image.bit_allocated as number,
    //     myCanvasRef
    //   );
    //   pyBufferData.release()
    // } else {
    //   console.log("no uncompressedData & no compressedData")
    // }
    // total += 1;
    // image.destroy();
  }


  const processDicomBuffer = (buffer?: ArrayBuffer, bufferList?: ArrayBuffer[]) => {
    if (PyodideDicom.current) {
      // console.log("has imported PyodideDicom class")
      dicomObj.current = PyodideDicom.current(buffer, bufferList, decompressJPEG)
      const image: PyProxyObj = dicomObj.current;
      // console.log(`image:${image}`) // print a lot of message: PyodideDicom(xxxx
      // console.log(`image max:${image.max}`)
      // console.log(`image center:${image.window_center}`) // works !!!

      setModality(image.modality)
      setPhotometric(image.photometric)
      setTransferSyntax(image.transferSyntaxUID)
      setResX(image.width)
      setResY(image.height)
      setNumFrames(image.frame_num)

      // normalization: using global series max in 3d 
      // but https://grimmer.io/dicom-web-viewer/ show axial plan's max on UI
      // now we correct this by using global max/min 
      setPixelMax(image.frame_max ?? image.max_3d)
      setPixelMin(image.frame_min ?? image.min_3d)

      // by default it is referring 1st dicom in series mode
      setWindowCenter(image.window_center)
      setWindowWidth(image.window_width)

      setCurrFrameIndex(1)
      if (currNormalizeMode === NormalizationMode.WindowCenter) {
        setUseWindowCenter(image.window_center)
        setUseWindowWidth(image.window_width)
      }

      /** original logic is to const res = await pyodide.runPythonAsync, then res.toJs(1) !! v0.18 use toJs({depth : n})
       * now changes to use a Python object instance in JS !!
       */

      // if (image.ds) {
      // console.log("image ds:", image.ds) // target: PyProxyClass
      // console.log(image.ds) // Proxy
      // console.log(typeof image.ds) // object
      // console.log(`PhotometricInterpretation: ${(image.ds as PyProxy).PhotometricInterpretation}`) // works
      // }

      if (bufferList) {
        setTotalFiles(image.series_dim_z)
        setTotalCoronaFrames(image.series_dim_y)
        setTotalSagittalFrames(image.series_dim_x)

        // might be duplicate set (if actively drage slider for first time and setup here for 2nd time 
        // but it is fine)  
        setCurrFileNo(image.series_z + 1)
        setCurrentCoronaNo(image.series_y + 1)
        setCurrentSagittalNo(image.series_x + 1)

        setIsCommonAxialView(image.is_common_axial_direction)

        // console.log(image.series_dim_y, image.series_dim_x, image.series_y, image.series_x)
        // TODO: setCurrFilePath ??????????
      }

      renderFrame()


    } else {
      console.log("has not imported PyodideDicom class, ignore")
    }

  }

  const loadFile = async (file: File) => {
    // if (!checkIfValidDicomFileName(file.name)) {
    //   return
    // }

    // setCurrFilePath(file.name)
    const buffer = await loadDicomFileAsync(file);
    fileBuffer.current = buffer
    // NOTE: besides getting return value (python code last line expression),
    // python data can be retrieved by accessing python global object:
    // pyodide.globals.get("image")
    // console.log("start to use python to parse parse dicom data");

    processDicomBuffer(buffer)
  }

  const resetUI = () => {
    canvasRender.resetCanvas(myCanvasRef.current)
    canvasRender.resetCanvas(myCanvasRefSagittal.current)
    canvasRender.resetCanvas(myCanvasRefCorona.current)

    if (dicomObj.current) {
      dicomObj.current.destroy()
    }

    setCurrFrameIndex(1)
    setNumFrames(1)
  };

  const renderFiles = async (files: File[], seriesMode: SeriesMode) => {

    resetUI();

    // console.log("ifShowSagittalCoronal:", ifShowSagittalCoronal)
    if (!files || files.length === 0) {
      return
    }
    if (seriesMode === SeriesMode.Series) {
      // console.log("3d mode1")
      /** ~ loadFile */
      const promiseList: any[] = [];
      files.forEach((file, index) => {
        // if (typeof file === "string") {
        //   // fetch
        // } else 
        promiseList.push(loadDicomFileAsync(file));
      });
      const bufferList = await Promise.all(promiseList);
      processDicomBuffer(undefined, bufferList)
    } else {
      // console.log("2d mode2")

      const file = files[0];
      setTotalFiles(files.length)
      setCurrFileNo(1)
      setCurrFilePath(file.name)
      loadFile(file);
    }
  }

  const onDropFiles = useCallback(async (acceptedFiles?: File[]) => {

    if (acceptedFiles && acceptedFiles.length > 0) {
      acceptedFiles.sort((a: any, b: any) => {
        return a.name.localeCompare(b.name);
      });

      files.current = acceptedFiles.filter((file) => {
        return checkIfValidDicomFileName(file.name);
      })
    }

    if (files.current.length > 0) {

      renderFiles(files.current, ifShowSagittalCoronal)
    }
    // Do something with the files
  }, [ifShowSagittalCoronal]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: onDropFiles,
  });

  const handleNormalizeModeChange = useCallback((
    e: React.FormEvent<HTMLInputElement>,
    data: CheckboxProps
  ) => {
    const { value } = data;

    const normalize_mode = value as number;
    setCurrNormalizeMode(normalize_mode)

    // if (normalize_mode === NormalizationMode.WindowCenter) {
    //   // console.log(`new is center:${windowCenter}`)
    //   setUseWindowCenter(windowCenter)
    //   setUseWindowWidth(windowWidth)

    //   const image: PyProxyObj = dicomObj.current
    //   if (ifShowSagittalCoronal === SeriesMode.Series) {
    //     dicomObj.current.render_axial_view.callKwargs({
    //       normalize_window_center: windowCenter, normalize_window_width: windowWidth,
    //       normalize_mode: NormalizationMode.WindowCenter
    //     });
    //     dicomObj.current.redner_sag_view.callKwargs({
    //       normalize_window_center: windowCenter, normalize_window_width: windowWidth,
    //       normalize_mode: NormalizationMode.WindowCenter
    //     });
    //     dicomObj.current.redner_cor_view.callKwargs({
    //       normalize_window_center: windowCenter, normalize_window_width: windowWidth,
    //       normalize_mode: NormalizationMode.WindowCenter
    //     });
    //   } else {
    //     image.render_frame_to_rgba_1d(windowCenter, windowWidth, NormalizationMode.WindowCenter)
    //   }
    // } else 

    const image: PyProxyObj = dicomObj.current

    let normalize_window_center = undefined;
    let normalize_window_width = undefined;

    if (normalize_mode === NormalizationMode.PixelHUMaxMin) {
      // console.log("new is maxmin")
      // if (ifShowSagittalCoronal === SeriesMode.Series) {
      //   image.render_axial_view.callKwargs({
      //     normalize_mode
      //   });
      //   image.redner_sag_view.callKwargs({
      //     normalize_mode
      //   });
      //   image.redner_cor_view.callKwargs({
      //     normalize_mode
      //   });
      // } else {
      //   image.render_frame_to_rgba_1d.callKwargs({ normalize_mode })
      // }
    } else {

      if (normalize_mode === NormalizationMode.WindowCenter) {
        normalize_window_center = windowCenter;
        normalize_window_width = windowWidth;
      } else {
        const data = WindowCenterWidthConst[normalize_mode];
        const tmpWindowCenter = data.L;
        const tmpWindowWidth = data.W;

        normalize_window_center = tmpWindowCenter;
        normalize_window_width = tmpWindowWidth;
      }

      setUseWindowCenter(normalize_window_center)
      setUseWindowWidth(normalize_window_width)
    }

    if (ifShowSagittalCoronal === SeriesMode.Series) {
      image.render_axial_view.callKwargs({
        normalize_window_center, normalize_window_width,
        normalize_mode
      });
      image.redner_sag_view.callKwargs({
        normalize_window_center, normalize_window_width,
        normalize_mode
      });
      image.redner_cor_view.callKwargs({
        normalize_window_center, normalize_window_width,
        normalize_mode
      });
    } else {
      image.render_frame_to_rgba_1d.callKwargs({
        normalize_window_center, normalize_window_width,
        normalize_mode
      })
    }
    renderFrame()



  }, [windowCenter, windowWidth]);

  let info = ""
  info += ` modality:${modality}; photometric:${photometric}; transferSyntax:${transferSyntax};`;
  info += ` resolution:${resX} x ${resY}`;

  const frameIndexes: any[] = Array.from({ length: numFrames }, (_, i) => i + 1)

  const options = Array.from({ length: 10 }, (_, i) => {
    return {
      key: i + 1,
      text: i + 1,
      value: i + 1
    }
  })

  const handleSwitchFrame = (
    e: React.SyntheticEvent<HTMLElement, Event>,
    obj: DropdownProps
  ) => {
    const value = obj.value as number;

    console.log("switch frame:", value, currFrameIndex);

    if (value !== currFrameIndex) {
      setCurrFrameIndex(value)
      const image: PyProxyObj = dicomObj.current
      image.render_frame_to_rgba_1d.callKwargs({ frame_index: value - 1 })
      setPixelMax(image.frame_max)
      setPixelMin(image.frame_min)
      renderFrame()
    }
  };

  const switchSagittal = (value: number) => {
    setCurrentSagittalNo(value)
    dicomObj.current.redner_sag_view(value - 1)
    renderFrame()
  }

  const switchCorona = (value: number) => {
    setCurrentCoronaNo(value)
    dicomObj.current.redner_cor_view(value - 1)
    renderFrame()
  }

  const switchFile = (value: number) => {
    // this.setState({
    //   currFileNo: value,
    // });

    if (ifShowSagittalCoronal === SeriesMode.NoSeries) {
      setCurrFileNo(value)

      // const { ifShowSagittalCoronal } = this.state;
      // // console.log("ifShowSagittalCoronal:", ifShowSagittalCoronal);
      // if (ifShowSagittalCoronal) {
      //   this.buildAxialView(
      //     this.currentSeries,
      //     this.currentSeriesImageObjects,
      //     value - 1
      //   );
      // } else {
      const newFile = files.current[value - 1];
      // console.log("switch to image:", value, newFile);
      // if (!this.isOnlineMode) {
      setCurrFilePath(newFile.name)
      loadFile(newFile);
      // } else {
      //   this.fetchFile(newFile);
      // }
      // }
    } else {
      setCurrFileNo(value)
      dicomObj.current.render_axial_view(value - 1)
      renderFrame()
    }
  };

  const handleSeriesModeChange = async (e: any, obj: any) => {
    const { value } = obj;
    console.log("handleSeriesModeChange:", value)

    let seriesMode;
    if (ifShowSagittalCoronal === SeriesMode.NoSeries) {
      seriesMode = SeriesMode.Series;
      console.log("to series:", value)
      setIfShowSagittalCoronal(seriesMode)

    } else {
      console.log("to no series", value)
      seriesMode = SeriesMode.NoSeries;


      setIfShowSagittalCoronal(SeriesMode.NoSeries)
      // if (files.current.length > 0) {
      //   const file = files.current[0];
      //   setTotalFiles(files.current.length)
      //   setCurrFileNo(1)
      //   // if (this.isOnlineMode) {
      //   setCurrFilePath(file.name)
      //   loadFile(file);
      // }
    }

    renderFiles(files.current, seriesMode)


    // onDropFiles()
  }

  const axisLabel = (char: string) => {
    return (isCommonAxialView ? <div>{char}</div> : <div>{" "}</div>)
  }

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
          </div>
          <div className="flex-container">
            {info}
            <br />
            {` current window center:${useWindowCenter} ; window width ${useWindowWidth} ;`}
            {` ${modality === "CT" ? "HU" : "pixel"} max:${pixelMax}, min:${pixelMin} ;`}
            {/* {` file: ${currFilePath} ;`} */}
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
              mode={NormalizationMode.PixelHUMaxMin}
              currNormalizeMode={currNormalizeMode}
              onChange={handleNormalizeModeChange}
            />
            <div>
              {numFrames > 1 ? (
                <Dropdown
                  placeholder="Switch Frame"
                  selection
                  onChange={handleSwitchFrame}
                  options={options}
                />) : null}
            </div>
          </div>
          <div className="flex-container">
            {modality === "CT" && (
              <>
                <NormalizationComponent
                  mode={NormalizationMode.AbdomenSoftTissues}
                  currNormalizeMode={currNormalizeMode}
                  onChange={handleNormalizeModeChange}
                />
                <NormalizationComponent
                  mode={NormalizationMode.SpineSoftTissues}
                  currNormalizeMode={currNormalizeMode}
                  onChange={handleNormalizeModeChange}
                />

                <NormalizationComponent
                  mode={NormalizationMode.SpineBone}
                  currNormalizeMode={currNormalizeMode}
                  onChange={handleNormalizeModeChange}
                />
                <NormalizationComponent
                  mode={NormalizationMode.Brain}
                  currNormalizeMode={currNormalizeMode}
                  onChange={handleNormalizeModeChange}
                />
                <NormalizationComponent
                  mode={NormalizationMode.Lungs}
                  currNormalizeMode={currNormalizeMode}
                  onChange={handleNormalizeModeChange}
                />
              </>)}
          </div>
          <div className="flex-container">
            <Radio
              toggle
              value={SeriesMode[ifShowSagittalCoronal]}
              checked={ifShowSagittalCoronal === SeriesMode.Series}
              onChange={handleSeriesModeChange}
            />
            {"  Series mode"}
          </div>
        </div>
        {totalFiles > 0 ? (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
            }}
          >
            <div style={{ width: 600 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                }}
              >
                {`${currFilePath}. ${currFileNo}/${totalFiles}`}
              </div>
              <div className="flex-container">
                {axisLabel("S")}
                <Slider
                  value={currFileNo}
                  step={1}
                  min={1}
                  max={totalFiles}
                  onChange={switchFile}
                />
                {axisLabel("I")}
              </div>
              {ifShowSagittalCoronal === SeriesMode.Series && (
                <>
                  <div className="flex-container">
                    {axisLabel("R")}
                    <Slider
                      value={currentSagittalNo}
                      step={1}
                      min={1}
                      max={totalSagittalFrames}
                      onChange={switchSagittal}
                    />
                    {axisLabel("L")}
                  </div>
                  <div className="flex-container">
                    {axisLabel("A")}
                    <Slider
                      value={currentCoronaNo}
                      step={1}
                      min={1}
                      max={totalCoronaFrames}
                      onChange={switchCorona}
                    />
                    {axisLabel("P")}
                  </div>
                </>
              )}
            </div>
          </div>) : null}
        <div className="flex-container">
          <div className="flex-column-justify-align-center">
            {axisLabel("A")}
            <div className="flex-column_align-center">
              {axisLabel("R")}
              {/* Axial */}
              <canvas
                ref={myCanvasRef}
                onMouseDown={onMouseCanvasDown}
                onMouseMove={onMouseMove}
                // onMouseUp={onMouseUp}
                width={MAX_WIDTH_SERIES_MODE}
                height={MAX_HEIGHT_SERIES_MODE}
                style={{ backgroundColor: "black" }}
              />
              {axisLabel("L")}
            </div>
            {axisLabel("P")}
          </div>
          {ifShowSagittalCoronal === SeriesMode.Series && (
            <>
              <div className="flex-column-justify-align-center">
                {axisLabel("S")}
                <div className="flex-column_align-center">
                  {axisLabel("A")}
                  {/* Sagittal */}
                  <canvas
                    ref={myCanvasRefSagittal}
                    onMouseDown={onMouseCanvasDown}
                    onMouseMove={onMouseMove}
                    width={MAX_WIDTH_SERIES_MODE}
                    height={MAX_HEIGHT_SERIES_MODE}
                    style={{ backgroundColor: "yellow" }}
                  />
                  {axisLabel("P")}
                </div>
                {axisLabel("I")}
              </div>
              <div className="flex-column-justify-align-center">
                {axisLabel("S")}
                <div className="flex-column_align-center">
                  {/* Corona */}
                  {axisLabel("R")}
                  <canvas
                    ref={myCanvasRefCorona}
                    onMouseDown={onMouseCanvasDown}
                    onMouseMove={onMouseMove}
                    width={MAX_WIDTH_SERIES_MODE}
                    height={MAX_HEIGHT_SERIES_MODE}
                    style={{ backgroundColor: "green" }}
                  />
                  {axisLabel("L")}
                </div>
                {axisLabel("I")}
              </div>
            </>)}
        </div>
      </div>
    </div>
  );
}

export default App;
