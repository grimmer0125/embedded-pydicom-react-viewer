
import * as Comlink from 'comlink';
import MyWorker, { api } from './Pyodide.worker';
const myWorkerInstance: Worker = new MyWorker();

// Call function in worker
const workrApi = Comlink.wrap<typeof api>(myWorkerInstance);
const initPyodideAndLoadPydicom = workrApi.initPyodideAndLoadPydicom
const loadPyodideDicomModule = workrApi.loadPyodideDicomModule
const newPyodideDicom = workrApi.newPyodideDicom



// import { D4C } from "d4c-queue";
// declare var loadPyodide: any;
// declare var pyodide: any;
// declare var globalThis: any;
function baseURL() {
    let baseURL = ""
    const regex = /chrome-extension:\/\/.*(?=\/index.html)/;
    const matchExtensionURL = window.location.href.match(regex)
    if (matchExtensionURL) {
        baseURL = matchExtensionURL[0] + "/"
    } else {
        baseURL = window.location.href + "/"
    }
    return baseURL
}


// const d4c = new D4C();
// const initPyodideAndLoadPydicom = d4c.wrap(async () => {
//     console.log("initPyodide:")

//     // globalThis.pyodide = await loadPyodide({ indexURL : "https://cdn.jsdelivr.net/pyodide/v0.18.0/full/" });
//     // globalThis.pyodide = await loadPyodide({ indexURL: "pyodide/" }); <- not work in 0.18, works in 0.17
//     globalThis.pyodide = await loadPyodide({ indexURL: baseURL() + "pyodide/" });

//     // await pyodide.loadPackage(['numpy', 'micropip']);
//     const pythonCode = await (await fetch('python/pyodide_init.py')).text();
//     await pyodide.loadPackagesFromImports(pythonCode);
//     await pyodide.runPythonAsync(pythonCode);
//     // pyodide.registerJsModule("my_js_module", my_js_module);
// });

// const loadPyodideDicomModule = d4c.wrap(async () => {
//     // console.log("loadPyodideDicomModule")
//     const pythonCode = await (await fetch('python/dicom_parser.py')).text();
//     await pyodide.loadPackagesFromImports(pythonCode);
//     await pyodide.runPythonAsync(pythonCode);
//     const PyodideDicom = pyodide.globals.get('PyodideDicom')
//     return PyodideDicom
// });

const loadDicomFileAsync = async (file: File): Promise<ArrayBuffer> => {
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
}

const fetchDicomFileAsync = async (url: string): Promise<ArrayBuffer> => {
    return new Promise((resolve, reject) => {
        if (url.indexOf("file://") === 0) {
            const xhr = new XMLHttpRequest();
            xhr.open("GET", url, true);
            xhr.responseType = "arraybuffer";
            xhr.onload = () => {
                const arrayBuffer = xhr.response;
                resolve(arrayBuffer);
                // this.renderImage(arrayBuffer);
            };
            xhr.send();
        } else {
            // NOTE: copy from https://github.com/my-codeworks/tiff-viewer-extension/blob/master/background.js#L29
            // TODO: figure it out why using arraybuffer will fail
            console.log("Starting XHR request for", url);
            const request = new XMLHttpRequest();
            request.open("GET", url, false);
            request.overrideMimeType("text/plain; charset=x-user-defined");
            request.send();
            console.log("Finished XHR request");
            const data = request.responseText;
            let buffer;
            let view: DataView;
            let a_byte;
            buffer = new ArrayBuffer(data.length);
            view = new DataView(buffer);
            data.split("").forEach((c, i) => {
                a_byte = c.charCodeAt(0);
                view.setUint8(i, a_byte & 0xff);
            });
            const buffer2 = view.buffer;
            resolve(buffer2);
        }
    });
};

export {
    initPyodideAndLoadPydicom,
    loadPyodideDicomModule,
    loadDicomFileAsync,
    fetchDicomFileAsync,
    newPyodideDicom
}