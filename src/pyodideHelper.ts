
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
    const result = await pyodide.runPythonAsync(pythonCode);
    const result2 = result.toJs(1);
    const pyBufferData = result2[0].getBuffer("u8clamped");
    const width = result2[3];
    const height = result2[4];
    result.destroy();
    return { data: pyBufferData.data, width, height };
});
