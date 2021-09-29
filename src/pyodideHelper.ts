
import { D4C } from "d4c-queue";

// const jpeg = require("jpeg-lossless-decoder-js");
// const decoder = new jpeg.lossless.Decoder();

declare var loadPyodide: any;
declare var pyodide: any;
declare var globalThis: any;
declare var self: any;

const baseURL = window.location.href ?? self.location.origin + "/"

// const test: number[] = []
// function add(x: number) {
//     test.push(x);
// }

// class Polygon {
//     height: number;
//     width: number;
//     constructor() {
//         this.height = 100;
//         this.width = 100;
//     }

//     addWidth() {
//         this.width += 100;
//     }
// }
// const polygon = new Polygon()

// // used for testing only
const my_js_module: any = {
    // decoder: decoder,
    // add,
    // polygon
    // jpeg,
    // newDecoder: function () {
    //     return new jpeg.lossless.Decoder();
    // }
};


const d4c = new D4C();
const initPyodideAndLoadPydicom = d4c.wrap(async () => {
    console.log("initPyodide:")

    globalThis.pyodide = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/dev/full/" });
    // globalThis.pyodide = await loadPyodide({ indexURL: "pyodide/" }); <- not work in 0.18, works in 0.17
    // globalThis.pyodide = await loadPyodide({ indexURL: baseURL + "pyodide/" });

    // await pyodide.loadPackage(['numpy', 'micropip']);
    const pythonCode = await (await fetch('python/pyodide_init.py')).text();
    await pyodide.loadPackagesFromImports(pythonCode);
    await pyodide.runPythonAsync(pythonCode);
    // pyodide.registerJsModule("my_js_module", my_js_module);
});


const loadPyodideDicomModule = d4c.wrap(async () => {
    console.log("loadPyodideDicomModule")
    const pythonCode = await (await fetch('python/dicom_parser.py')).text();
    await pyodide.loadPackagesFromImports(pythonCode);
    await pyodide.runPythonAsync(pythonCode);
    const PyodideDicom = pyodide.globals.get('PyodideDicom')
    return PyodideDicom
});

const loadDicomFileAsync = d4c.wrap(async (file: File): Promise<ArrayBuffer> => {
    // console.log("loadDicomFileAsync")
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const fileContent = reader.result;
            resolve(fileContent as ArrayBuffer);
        };
        reader.onabort = () => console.log("file reading was aborted");
        reader.onerror = () => console.log("file reading has failed");
        reader.readAsArrayBuffer(file);
    });
});

export {
    initPyodideAndLoadPydicom,
    loadPyodideDicomModule,
    loadDicomFileAsync
}


// ****** deprecated ******/
/** without d4c-queue, parseByPython will throw exception 
 * if it is called before initPyodide is finished */
export const parseByPython = d4c.wrap(async (buffer: ArrayBuffer) => {
    my_js_module["buffer"] = buffer;
    // this decoder shoulbe be re-newed everytime, 
    // otherwise 2nd decoding will use some internal temporary variables from 1st time and issues happen
    //my_js_module["decoder"] = new jpeg.lossless.Decoder();
    const pythonCode = await (await fetch('python/dicom_parser.py')).text();
    const res = await pyodide.runPythonAsync(pythonCode);

    // works !!    
    const x1 = pyodide.globals.get('x')
    console.log(`x1:${x1}`)
    const Test = pyodide.globals.get('Test')
    // works !!! can invoke Python constructor 
    const k2 = Test()
    console.log(`k2:${k2.a}`)


    // works !!! to access python global object instance
    const bb = pyodide.globals.get('bb')
    console.log(`bb:${bb.a}`)
    bb.test_a() // works !!!

    // console.log("after run python:", test) // yes !!!!
    // console.log("after run python:", polygon) // yes !!!!
    const data = res.toJs(1); //  v0.18 use toJs({depth : n})
    console.log("data:", data);
    console.log(`type:${typeof data}`)
    const width = data[1];
    const height = data[2];
    const photometric = data[5]
    const transferSyntaxUID = data[6]
    const allocated_bits = data[7]
    if (data[3] === undefined) {
        // python bytes -> uinit8 array 
        const data2 = data[0].getBuffer()

        //1048576
        // 718940
        console.log("it is compressed data:", data2.data)
        // return { data: 1, width: 2, height: 3 }
        return { compressedData: data2.data, width, height, photometric, transferSyntaxUID, allocated_bits }
    }

    const pyBufferData = data[0].getBuffer("u8clamped");

    res.destroy();
    /** TODO: need releasing buffer data? pyBufferData.release()
     * ref: https://pyodide.org/en/stable/usage/type-conversions.html#converting-python-buffer-objects-to-javascript */
    return { data: pyBufferData.data, width, height, photometric, transferSyntaxUID };
});
