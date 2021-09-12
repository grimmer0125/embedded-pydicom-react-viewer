import { expose } from 'comlink';
declare const self: Worker;
export default {} as typeof Worker & { new (): Worker };

// postMessage("I\'m working before postMessage(\'ali\').");
// onmessage = function (oEvent) {
//   postMessage("Hi " + oEvent.data);
// };

// Define API
const api = {
  doSomething: (name: string): string => {
    return `Hello ${name}!`;
  },
};

// Expose API
expose(api);
