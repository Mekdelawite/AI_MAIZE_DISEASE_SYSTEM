import fs from 'node:fs';
import path from 'node:path';
import * as tf from '@tensorflow/tfjs';

const modelJsonPath = process.argv[2];
if (!modelJsonPath) throw new Error('Usage: node compare_tfjs_predictions.mjs <model.json>');

await tf.setBackend('cpu');
await tf.ready();
const artifacts = JSON.parse(fs.readFileSync(modelJsonPath, 'utf8'));
const modelDir = path.dirname(modelJsonPath);
const groups = artifacts.weightsManifest;
const shards = groups.flatMap((group) => group.paths.map((shardPath) => fs.readFileSync(path.join(modelDir, shardPath))));
const weightData = Buffer.concat(shards);
const model = await tf.loadLayersModel(tf.io.fromMemory({
  modelTopology: artifacts.modelTopology,
  weightSpecs: groups.flatMap((group) => group.weights),
  weightData: weightData.buffer.slice(weightData.byteOffset, weightData.byteOffset + weightData.byteLength),
  format: 'layers-model',
}));

const samples = JSON.parse(fs.readFileSync(0, 'utf8'));
const predictions = [];
for (const sample of samples) {
  const input = tf.tensor4d(sample.input, [1, 224, 224, 3]);
  const output = model.predict(input);
  predictions.push(Array.from(await output.data()));
  input.dispose();
  output.dispose();
}
model.dispose();
process.stdout.write(JSON.stringify(predictions));
