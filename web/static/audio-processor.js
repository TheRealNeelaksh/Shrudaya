class AudioProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const inputChannel = inputs[0][0];
    if (inputChannel) {
      this.port.postMessage(inputChannel.buffer, [inputChannel.buffer]);
    }
    return true;
  }
}
registerProcessor('audio-processor', AudioProcessor);