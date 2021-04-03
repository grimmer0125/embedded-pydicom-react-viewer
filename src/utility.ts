// copy from https://github.com/grimmer0125/dicom-web-viewer/blob/develop/src/utility.ts
export async function loadDicomAsync(file: any): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const fileContent = reader.result;
        resolve(fileContent as ArrayBuffer);
        //   this.renderImage(fileContent);
      };
      reader.onabort = () => console.log("file reading was aborted");
      // e.g. "drag a folder" will fail to read
      reader.onerror = () => console.log("file reading has failed");
      reader.readAsArrayBuffer(file);
    });
  }
  
  export async function fetchDicomAsync(url: string) {
    return new Promise((resolve, reject) => {
      if (url.indexOf("file://") === 0) {
        const xhr = new XMLHttpRequest();
        xhr.open("GET", url, true);
        xhr.responseType = "arraybuffer";
        xhr.onload = () => {
          const arrayBuffer = xhr.response;
          resolve(arrayBuffer);
          // this.renderImage(arrayBuffer);
        };
        xhr.send();
      } else {
        // NOTE: copy from https://github.com/my-codeworks/tiff-viewer-extension/blob/master/background.js#L29
        // TODO: figure it out why using arraybuffer will fail
        console.log("Starting XHR request for", url);
        const request = new XMLHttpRequest();
        request.open("GET", url, false);
        request.overrideMimeType("text/plain; charset=x-user-defined");
        request.send();
        console.log("Finished XHR request");
        const data = request.responseText;
        let buffer;
        let view: DataView;
        let a_byte;
        buffer = new ArrayBuffer(data.length);
        view = new DataView(buffer);
        data.split("").forEach((c, i) => {
          a_byte = c.charCodeAt(0);
          view.setUint8(i, a_byte & 0xff);
        });
        const buffer2 = view.buffer;
        // this.renderImage(buffer2);
        resolve(buffer2);
      }
    });
  
    //   const promise = new Promise((resolve, reject) => {
    //     this.commandDict[pipelineUrl] = { resolve, reject };
    //   });
  }
  
  export default {};
  