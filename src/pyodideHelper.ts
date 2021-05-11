
import { D4C } from "d4c-queue";
declare var loadPyodide: any;
declare var pyodide: any;

const my_js_module: any = {};
const d4c = new D4C();
export const initPyodide = d4c.wrap(async () => {
    await loadPyodide({ indexURL: "pyodide/" });
    await pyodide.loadPackage(['numpy', 'micropip']);
    const pythonCode = await (await fetch('python/pyodide_init.py')).text();
    await pyodide.runPythonAsync(pythonCode);
    pyodide.registerJsModule("my_js_module", my_js_module);
});

/** without d4c-queue, parseByPython will throw exception 
 * if it is called before initPyodide is finished */
export const parseByPython = d4c.wrap(async (buffer: ArrayBuffer) => {
    my_js_module["buffer"] = buffer;
    const pythonCode = await (await fetch('python/dicom_parser.py')).text();
    const res = await pyodide.runPythonAsync(pythonCode);
    console.log("after run python")
    const data = res.toJs(1);
    console.log("data:", data);
    console.log(`type:${typeof data}`)
    if (data[3] === undefined) {
        // python bytes -> uinit8 array 
        const data2 = data[0].getBuffer()

        //1048576
        // 718940
        console.log("it is compressed data:", data2.data)
        // return { data: 1, width: 2, height: 3 }
        return { compressedData: data2.data, width: 1024, height: 1024 }
    }

    const pyBufferData = data[0].getBuffer("u8clamped");
    const width = data[1];
    const height = data[2];
    res.destroy();
    /** TODO: need releasing buffer data? pyBufferData.release()
     * ref: https://pyodide.org/en/stable/usage/type-conversions.html#converting-python-buffer-objects-to-javascript */
    return { data: pyBufferData.data, width, height };
});
