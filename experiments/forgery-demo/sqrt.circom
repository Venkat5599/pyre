pragma circom 2.0.0;
// Proves "I know a, with a * a = y". y is public.
template Sqrt() { signal input a; signal output y; y <== a * a; }
component main = Sqrt();
