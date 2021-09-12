declare const self: Worker;
export default {} as typeof Worker & { new (): Worker };

postMessage("I\'m working before postMessage(\'ali\').");
onmessage = function (oEvent) {
  postMessage("Hi " + oEvent.data);
};
