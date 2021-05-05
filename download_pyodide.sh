#!/bin/bash

BASEDIR=$(dirname "$0")
curl -JL https://github.com/grimmer0125/embedded-python-dicom-visualization-reactapp/releases/download/v0.2/pyodide.zip > $BASEDIR/pyodide.zip
unzip $BASEDIR/pyodide.zip -d $BASEDIR/public
rm -r $BASEDIR//public/__MACOSX
rm $BASEDIR/pyodide.zip