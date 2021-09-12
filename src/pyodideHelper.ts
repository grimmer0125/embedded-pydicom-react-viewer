
import * as Comlink from 'comlink';

import MyWorker,  {api}  from './Pyodide.worker';

const myWorkerInstance: Worker = new MyWorker();
// myWorkerInstance.onmessage = function (oEvent) {
//     console.log("Worker said : " + oEvent.data);
// };

// Call function in worker
const workrApi = Comlink.wrap<typeof api>(myWorkerInstance);
const initPyodideAndLoadPydicom = workrApi.initPyodideAndLoadPydicom
const loadPyodideDicomModule = workrApi.loadPyodideDicomModule
const newPyodideDicom = workrApi.newPyodideDicom

async function init(){    
    // const resp = await workrApi.remoteFunction('John Doe');
    // console.log(`remoteFunction:${resp}`)
}
init()

const loadDicomFileAsync = async (file: File): Promise<ArrayBuffer> =>{
  console.log("loadDicomFileAsync")
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
};

export {
    initPyodideAndLoadPydicom, 
    loadPyodideDicomModule,
    loadDicomFileAsync,
    newPyodideDicom,
}
