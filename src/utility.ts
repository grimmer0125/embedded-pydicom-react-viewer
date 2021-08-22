export async function loadDicomAsync(file: File): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const fileContent = reader.result;
      resolve(fileContent as ArrayBuffer);
    };
    reader.onabort = () => console.log("file reading was aborted");
    reader.onerror = () => console.log("file reading has failed");
    reader.readAsArrayBuffer(file);
  });
}

export default {};
