# Embedded Python DICOM visualization ReactApp

This experimental project demonstrates 
1. How to use Python in browser, working with ReactApp.   
2. Use Python to parse DICOM files (only supprot some kind of DICOM) and pass data to JS, then draw it on Canvas. 

Tested on macOS Big Sur (intel/M1), Chrome 89. 

## Why to make this

Besides it is an interesting thing to use Python in browser, using Python DICOM parser has some advantanges. 
1. Although my another Chrome extension/Web project, https://github.com/grimmer0125/dicom-web-viewer uses 3-party JavaScript DICOM parser library but it seems not manintained. The other JavaScript/TypeScript DICOM parser library might be too heavy to use. 
2. Scientists usually use Python DICOM parser library, and using the same language/library is a good thing. 

## Python Browser runtime - Pyodide

ref: 
1. https://github.com/pyodide/pyodide
2. https://pyodide.org/en/latest/development/new-packages.html

I opened a issue here, https://github.com/pyodide/pyodide/issues/1426 about how to properly re-use python object. 

### Setup Pyodide [do not ignore]

The current code alreasy uses local latest Pyodide dev version to speed up loading instead of CDN, just download it once, https://github.com/grimmer0125/embedded-python-dicom-visualization-reactapp/releases/download/untagged-93d9591f4af9212e43f1/pyodide.zip, unzip it, then move `pyoide` folder to `public/pyodide`. These Pyoide fiels are download from `https://cdn.jsdelivr.net/`, not built from scratch. 

Or you can comment these
```
<script src="pyodide/pyodide.js"></script>

await loadPyodide({ indexURL : "pyodide/" }); 

await micropip.install('pyodide/pydicom-2.1.2-py3-none-any.whl') 
```

and replace by below to fetch from CDN

```
<script src="https://cdn.jsdelivr.net/pyodide/dev/full/pyodide.js"></script>

await loadPyodide({ indexURL : "https://cdn.jsdelivr.net/pyodide/dev/full/" });

await micropip.install('pydicom') 

```

### Use latest dev instead of 0.17.0a2 Pyodide

Since we need to use `getBuffer` method to eliminate memory allocation/copy, that method only exists in the latest dev. During flattening a 2d grey array to 1d RGBA array, we need to allocate 1d RGBA arrray, we have moved this operation into Python Pyoidie side, so we need to avoid extra memory allocation due to `new Uint8ClampedArray` in the previous JS code. 

### Other GitHub repos using Pyodide + Pydicom
1. [https://github.com/Fincap/onko-pyodide](https://github.com/Fincap/onko-pyodide), draw canvas in Pyodide runtime
2. [https://github.com/pymedphys/pymedphys](https://github.com/pymedphys/pymedphys), mainly for DICOM-RT

## Not handle cases on medical files

Below non handled items are done in another project https://github.com/grimmer0125/dicom-web-viewer (canvas operation is borrowed from this)

1. possible window center & width mode (need work with rescale equation)
2. RGB mode1, RGB mode2
3. MONOCHROME1 inverted color 
4. multiple frame 
5. coronal & sagittal views & judge if current is AxialView or not 
6. scale (resize to viewer size)

##  todo list

Besides above medical file cases, there are some optional things we can do 
1. [Done] host these on your server. Check https://pyodide.org/en/0.17.0a2/usage/serving-pyodide-packages.html & https://pyodide.org/en/0.17.0a2/usage/loading-packages.html#
    1. pyodide.wasm (WebAssembly, 10MB), pyodide.asm.js (3.8MB), and pyodide.asm.data(5MB) files 
    2. pyodide packages. e.g. numpy.js (159KB) and numpy.data (7.3MB <-used by WebAssembly). (By contrast, a numpy wheel package is about 16MB)
    3. non pyodide built-in pure python packages (which needs to be a wheel package and we use `pyodide micropip` to install them from PyPI). e.g. pydicom-2.1.2-py3-none-any.whl (1.9MB) 
3. move python code to a browser webworker, https://pyodide.org/en/0.17.0a2/usage/webworker.html#.  
4. Dockerization
5. Bundle some testing DICOM files

## Install dependencies for intel and Mac M1 (arm) machines

https://github.com/nvm-sh/nvm January 2021: there are no pre-compiled NodeJS binaries for versions prior to 15.x for Apple's new M1 chip (arm64 architecture). v14.16 supports M1 but need compilation (auto done by nvm).

Make sure you have Node.js (v15.14.0+), [Yarn](https://yarnpkg.com/), Python (3.9.2+) and [Poetry](https://python-poetry.org/) installed. (Optional) [pyenv](https://github.com/pyenv/pyenv) is recommended to switch different Python and it will automatically switch to 3.9.2 since .python-version is created. 

1. `yarn install`
2. `poetry install`

## Production - Use Python FastAPI to host React app 

1. `yarn build` to build reactapp 

2. To launch FastAPI, 

either 
```
$ poetry shell
$ uvicorn main:app
```
or 
```
$ poetry run uvicorn main:app
```

Using `uvicorn main:app --reload` is for development but we already have create react app built-in development live server.

## Issues 

1. [Performance] Using Python numpy in browser is slow, it takes `3~4s` for 1 512*512 array operation. Using pure JavaScript/TypeScript takes less than 0.5s. Ref: https://github.com/pyodide/pyodide/issues/112 (the author said WebAssembly may takes `3~5x` slow). The better way might be 
    1. (can rollback to git commit: `219299f9adec489134206faf0cfab79d8345a7df`), using pydicom to parse DICOM files, sending pixel data to JS, then use JS to flatten 2d grey data to 1d RGBA canvas image data.
    2. Or is there any quick way in numpy for flattening a 2d grey array to 1d RGBA array? Such as https://stackoverflow.com/questions/59219210/extend-a-greyscale-image-to-fit-a-rgb-image + flatten?
