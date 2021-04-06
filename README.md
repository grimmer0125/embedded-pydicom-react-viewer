# Embedded Python DICOM visualization ReactApp

This is a demo project and only can show a part of DICOM files. 

## Why to make this

Besides it is an interesting thing to use Python in browser, using Python DICOM parser has some advantanges. 
1. Although my another Chrome extension/Web project, https://github.com/grimmer0125/dicom-web-viewer uses 3-party JavaScript DICOM parser library but it seems not manintained. The other JavaScript/TypeScript DICOM parser library might be too heavy to use. 
2. Scientists usually use Python DICOM parser library, and using the same language/library is a good thing. 

## Python Browser runtime - Pyodide

ref: 
1. https://github.com/pyodide/pyodide
2. https://pyodide.org/en/latest/development/new-packages.html

I opened a issue here, https://github.com/pyodide/pyodide/issues/1426 about 
1. how to properly re-use python object 
2. pyodide package vs using micropip load python normal package. Compare their performance & bundle size

### Other GitHub repos using Pyodide + Pydicom
1. [https://github.com/Fincap/onko-pyodide](https://github.com/Fincap/onko-pyodide)
2. [https://github.com/pymedphys/pymedphys](https://github.com/pymedphys/pymedphys)

## Not handle 

Below non handled items are done in another project https://github.com/grimmer0125/dicom-web-viewer (canvas operation is borrowed from this)

1. possible window center & width mode (need work with rescale equation)
2. RGB mode1, RGB mode2
3. MONOCHROME1 inverted color 
4. multiple frame 
5. coronal & sagittal views & judge if current is AxialView or not 
6. scale (resize to viewer size)

## For production usage

There are two more optional steps we can do 
1. host these on your server. Check https://pyodide.org/en/0.17.0a2/usage/serving-pyodide-packages.html & https://pyodide.org/en/0.17.0a2/usage/loading-packages.html#
    1. pyodide.wasm (WebAssembly, 10MB), pyodide.asm.js (3.8MB), and pyodide.asm.data(5MB) files 
    2. pyodide packages. e.g. numpy.js (159KB) and numpy.data (7.3MB <-used by WebAssembly). (By contrast, a numpy wheel package is about 16MB)
    3. non pyodide built-in pure python packages (which needs to be a wheel package and we use `pyodide micropip` to install them from PyPI). e.g. pydicom-2.1.2-py3-none-any.whl (1.9MB) 
3. move python code to a browser webworker, https://pyodide.org/en/0.17.0a2/usage/webworker.html#.  
