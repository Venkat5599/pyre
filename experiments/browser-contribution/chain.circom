pragma circom 2.1.6;
include "node_modules/circomlib/circuits/poseidon.circom";

// ~2^16-constraint test circuit: a chain of Poseidon hashes (about 240 constraints each).
template Chain(n) {
    signal input secret;
    signal output out;
    component h[n];
    signal acc[n + 1];
    acc[0] <== secret;
    for (var i = 0; i < n; i++) {
        h[i] = Poseidon(2);
        h[i].inputs[0] <== acc[i];
        h[i].inputs[1] <== i;
        acc[i + 1] <== h[i].out;
    }
    out <== acc[n];
}

component main = Chain(250);
