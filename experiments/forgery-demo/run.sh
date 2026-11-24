#!/bin/sh
# Full forgery demonstration: build keys, forge, encode for Soroban, check with Stellar's BN254 host function.
set -e
npm ci --silent
npx circom2 sqrt.circom --r1cs --wasm -o .
node forge.mjs 2>&1 | grep -v '^\[INFO\]'
node encode.mjs
cp soroban-fixture.json soroban/
cd soroban && cargo test 2>&1 | grep -E '^test |^test result: ok. [1-9]'
