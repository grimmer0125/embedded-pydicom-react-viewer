# Embedded Pydicom React Viewer

This experimental project demonstrates

1. How to use Python in browser, working with ReactApp.
2. Use Python to parse DICOM files (only supprot some kind of DICOM) and pass data to JS, then draw it on Canvas.

Tested on macOS Big Sur (intel/M1), Chrome 89.

Its usage is simple. Just drag a DICOM file into the panel to view.

Download from [DICOM sample file](#dicom-sample-file)

## Motivation

Besides it is an interesting thing to use Python in browser, using Python DICOM parser has some advantages.

1. Although my another Chrome extension/Web project, https://github.com/grimmer0125/dicom-web-viewer uses 3-party JavaScript DICOM parser library but it seems not manintained. The other JavaScript/TypeScript DICOM parser library might be too heavy to use.
2. Scientists usually use Python DICOM parser library, and using the same language/library is a good thing.

## Screenshot

OT-MONO2-8-hip.dcm from https://barre.dev/medical/samples/

![alt tag](https://raw.githubusercontent.com/grimmer0125/embedded-pydicom-react-viewer/master/public/screenshot.png)

## Python 3.8.2 Browser runtime - Pyodide

ref:

1. https://github.com/pyodide/pyodide
2. https://pyodide.org/en/latest/development/new-packages.html

I opened a issue here, https://github.com/pyodide/pyodide/issues/1426 about how to properly re-use python object.

### Other GitHub repos using Pyodide + Pydicom

1. [https://github.com/Fincap/onko-pyodide](https://github.com/Fincap/onko-pyodide), draw canvas in Pyodide runtime
2. [https://github.com/pymedphys/pymedphys](https://github.com/pymedphys/pymedphys), mainly for DICOM-RT

## Development

Please use VS Code and bulit-in TypeScript/Python formatter setting. Please install Python autopep8 out of thie project environment and mare sure the VS Code setting. Also, you can enable "format on save".

### Setup Pyodide

The current code uses local built Pyodide 0.17.0 version to speed up loading instead of CDN, just download it once. The zip file is https://github.com/grimmer0125/embedded-python-dicom-visualization-reactapp/releases/download/v0.2/pyodide.zip and you can just execute

`$ sh download_pyodide.sh`

in terminal which will download+unzip+move to `public/pyodide`. These Pyodide fiels were download from `https://cdn.jsdelivr.net/`, not built from scratch.

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

#### Why use 0.17.0 Pyodide version

Since we need to use `getBuffer` method which is added in `v0.17.0` to eliminate memory allocation/copy, that method only exists in the latest dev. During flattening a 2D grey array to 1D RGBA array, we need to allocate 1D RGBA arrray, we have moved this operation into Python Pyoidie side, so we need to avoid extra memory allocation due to `new Uint8ClampedArray` in the previous JS code.

### Install Python, Node.js and their dependencies for intel and Mac M1 (arm) machines

https://github.com/nvm-sh/nvm January 2021: there are no pre-compiled NodeJS binaries for versions prior to 15.x for Apple's new M1 chip (arm64 architecture). v14.16 supports M1 but need compilation (auto done by nvm). p.s. nvm seems to still build 15.14.0

Make sure you have Node.js (v15.14.0+), Python (3.9.2+) and [Poetry](https://python-poetry.org/) installed first. (Optional) [pyenv](https://github.com/pyenv/pyenv) is recommended to switch different Python and it will automatically switch to 3.9.2 since .python-version is created.

Then

1. `npm install --global yarn`
2. `yarn set version berry`
3. `yarn install`
4. `poetry install`

### Start coding

Just `yarn start`

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

## Docker images - another testing way

### Build a docker image to run (either on amd64 or arm64)

1. `docker build --progress=plain -t pyodide-react-dicom-viewer .`
2. `docker run -p 8000:8000 -d pyodide-react-dicom-viewer`
3. open http://localhost:8000/ and drag a DICOM file to view.

### Build a universal docker image (supporting amd64/arm64)

Cross compliation for intel/m1 takes much more time than normal `docker build`. Building + Pushing to docker hub takes 20~30min. Several times.

1. `docker buildx create --use --name m1_builder`
2. `docker buildx use m1_builder`
3. `docker buildx inspect --bootstrap`
4. `docker buildx build --platform linux/amd64,linux/arm64 --push -t grimmer0125/pyodide-react-dicom-viewer:0.4 .`

### Use remote docker image to run

Image: https://hub.docker.com/repository/docker/grimmer0125/pyodide-react-dicom-viewer

1. `docker run -p 8000:8000 grimmer0125/pyodide-react-dicom-viewer:0.4`
2. open http://localhost:8000/ and drag a DICOM file to view.

## DICOM sample file sites

- https://barre.dev/medical/samples/ contains jpeg 57, 70 (MR-MONO2-12-shoulder, CT-MONO2-16-chest)
- pydicom lib
  - https://github.com/pydicom/pydicom-data/tree/master/data_store/data JPGLosslessP14SV1_1s_1f_8b.dcm 1.2.840.10008.1.2.4.70 JPEG Lossless
  - https://github.com/pydicom/pydicom/blob/master/pydicom/data/test_files/JPEG-lossy.dcm: jpeg 51
- Daikon lib https://github.com/rii-mango/Daikon/tree/master/tests
- http://www.rubomedical.com/dicom_files/, some (multi-frame) `DICOM jpeg 1.2.840.10008.1.2.4.50`
- https://medistim.com/dicom/
  - http://medistim.com/wp-content/uploads/2016/07/ttfm.dcm 1.2.840.10008.1.2.4.70
  - http://medistim.com/wp-content/uploads/2016/07/bmode.dcm ultra sound, 70, multi frame

### Tested sample files

They are archived on https://github.com/grimmer0125/embedded-pydicom-react-viewer/releases/download/v0.2/dicom_samples.zip

- CT-MONO2-16-ort: 1.2.840.10008.1.2, MONOCHROME2
- JPEG57-MR-MONO2-12-shoulder: 1.2.840.10008.1.2.4.57 MONOCHROME2
- US-PAL-8-10x-echo: 1.2.840.10008.1.2.5 (RLE Lossless), PALETTE COLOR, multi-frame
- CR-MONO1-10-chest: 1.2.840.10008.1.2.4.50 (raw, need specified), MONOCHROME1
- [color3d_jpeg_baseline](https://github.com/pydicom/pydicom-data/tree/master/data_store/data): 1.2.840.10008.1.2.4.50, YBR_FULL_422 (not handled YBR part), multi-frame
- JPGLosslessP14SV1_1s_1f_8b: 1.2.840.10008.1.2.4.70, MONOCHROME2
- US-RGB-8-esopecho.dcm: 1.2.840.10008.1.2.1, RGB, planar:0
- US-RGB-8-epicard.dcm: 1.2.840.10008.1.2.2, RRB, planar = 1

## DICOM medical files - not handle cases

Below non handled items are done in another project https://github.com/grimmer0125/dicom-web-viewer (canvas operation is borrowed from this)

- DICOM FILE
  - Transfer Syntax:
    - ~~51 (supported)~~, 57, 70 JPEG DICOM. They are parsed but browser needs extra JPEG decoder to render, [Daikon][https://github.com/rii-mango/daikon] has done this.
    - ~~1.2.840.10008.1.2.5 RLE Lossless ~~
    - 1.2.840.10008.1.2.1.99 Deflated Explicit VR Little Endian (not tested)
    - 1.2.840.10008.1.2.4.90 JPEG2000 Lossless (not tested)
    - 1.2.840.10008.1.2.4.91 JPEG2000 (not tested)
  - [done] Photometric: MONOCHROME1, inverted color
  - [done] Photometric: RGB with planar 0, 1
  - [done] Photometric: PALETTE
  - 1.2.840.10008.1.2.1 Explicit VR, Little Endian (not testd)
  - ~~1.2.840.10008.1.2.2 Explicit VR, Big Endian (testd)~~
- possible window center & width mode (need work with rescale equation)
- multiple frame
- coronal & sagittal views & judge if current is AxialView or not
- scale (resize to viewer size)
- get width & height of compressed DICOM before rendering
- PhotometricInterpretation: YBR case

## Issues

1. [Solved][performance] Using Python numpy in browser is slow, it takes `3~4s` for 1 512\*512 array operation. Using pure JavaScript takes less than 0.5s. Ref: https://github.com/pyodide/pyodide/issues/112 (the author said WebAssembly may takes `3~5x` slow). The solution might be

   1. (can rollback to git commit: `219299f9adec489134206faf0cfab79d8345a7df`), using pydicom to parse DICOM files, sending pixel data to JS, then use JS to flatten 2D grey data to 1D RGBA canvas image data.~~
   2. [Use this way, solved] Or is there any quick way in numpy for flattening a 2D grey array to 1D RGBA array with normalization? Such as https://stackoverflow.com/questions/59219210/extend-a-greyscale-image-to-fit-a-rgb-image? Also image2D.min()/max() is fast. Need more study/profiling.

Speed (using above sample file to test, file: `OT-MONO2-8-hip.dcm` on https://barre.dev/medical/samples/):

1. numpy array + manual iteration calculation in local python ~= numpy array + numpy array operation ~= JS ArrayBuffer/int8ClampedArray + manual iteration calculation (very fast) >>
2. Python list + manual iteration calculation > (5s)
3. numpy array + manual iteration calculation in pyodide. (7s)

p.s.

1. I did not record JS accurate time cost but it is fast.
2. Local Python is much faster than Pyodide Python in browser.

## todo list

Besides adding back above medical file cases/features, there are some optional things we can do

1. [Done] Host these on your server. Check https://pyodide.org/en/0.17.0a2/usage/serving-pyodide-packages.html & https://pyodide.org/en/0.17.0a2/usage/loading-packages.html#
   1. pyodide.wasm (WebAssembly, 10MB), pyodide.asm.js (3.8MB), and pyodide.asm.data(5MB) files
   2. pyodide packages. e.g. numpy.js (159KB) and numpy.data (7.3MB <-used by WebAssembly). (By contrast, a numpy wheel package is about 16MB)
   3. non pyodide built-in pure python packages (which needs to be a wheel package and we use `pyodide micropip` to install them from PyPI). e.g. pydicom-2.1.2-py3-none-any.whl (1.9MB)
2. Move python code to a browser webworker, https://pyodide.org/en/0.17.0a2/usage/webworker.html#.
3. [Done] Dockerization
4. Bundle some testing DICOM files
5. Introduction to medical files and pyodide
6. Make a Python package
7. 3D visualization
8. Help to improve Pyodide
9. Refactor
10. Add tests
11. Fix [DICOM medical files - Not handle/test cases](#dicom-medical-files---not-handletest-cases)

## Misc

This project is using my another TypeScript npm library, [d4c-queue](https://www.npmjs.com/package/d4c-queue), and code is on https://github.com/grimmer0125/d4c-queue/. You can take a look.
