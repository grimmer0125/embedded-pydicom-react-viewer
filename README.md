# Embedded Python DICOM visualization ReactApp

This is a demo project and only can show a part of DICOM files. 

## Why to make this

Besides it is an interesting thing to use Python in browser, using Python DICOM parser has some advantanges. 
1. Although my another Chrome extension/Web project, https://github.com/grimmer0125/dicom-web-viewer uses 3-party JavaScript DICOM parser library but it seems not manintained. The other JavaScript/TypeScript DICOM parser library might be too heavy to use. 
2. Scientists usually use Python DICOM parser library, and using the same language is a good thing. 

## Python Browser runtime - Pyodide

https://github.com/pyodide/pyodide

### Other similar github repos using Pyodide + Pydicom
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
