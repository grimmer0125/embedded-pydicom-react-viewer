#!/bin/bash

BASEDIR=$(dirname "$0")
curl -JL https://github.com/grimmer0125/embedded-pydicom-react-viewer/releases/download/untagged-77e55ea5908aaad294e1/pyodide.zip > $BASEDIR/pyodide.zip
unzip $BASEDIR/pyodide.zip -d $BASEDIR/public
rm -r $BASEDIR//public/__MACOSX
rm $BASEDIR/pyodide.zip