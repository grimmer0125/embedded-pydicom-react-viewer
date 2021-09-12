#!/bin/bash

BASEDIR=$(dirname "$0")
curl -JL https://github.com/grimmer0125/embedded-pydicom-react-viewer/releases/download/untagged-4c8410552dae8d87d56b/pyodide.zip > $BASEDIR/pyodide.zip
unzip $BASEDIR/pyodide.zip -d $BASEDIR/public
rm -r $BASEDIR//public/__MACOSX
rm $BASEDIR/pyodide.zip