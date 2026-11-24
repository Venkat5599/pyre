#![no_std]
//! Checks the Groth16 equation with Soroban's own BN254 host function (bn254_multi_pairing_check):
//! e(-A, B) * e(alpha, beta) * e(IC(x), gamma) * e(C, delta) == 1
//! Test-only harness for the forgery demonstration; Pyre ships no verifier.
use soroban_sdk::{crypto::bn254::{Bn254G1Affine, Bn254G2Affine}, vec, Env};

pub fn groth16_holds(env: &Env, neg_a: Bn254G1Affine, b: Bn254G2Affine, c: Bn254G1Affine,
                     alpha: Bn254G1Affine, beta: Bn254G2Affine, icx: Bn254G1Affine,
                     gamma: Bn254G2Affine, delta: Bn254G2Affine) -> bool {
    env.crypto().bn254().pairing_check(vec![env, neg_a, alpha, icx, c], vec![env, b, beta, gamma, delta])
}

#[cfg(test)]
mod test {
    extern crate std;
    use super::*;
    use soroban_sdk::BytesN;
    use std::string::String;

    fn field(json: &str, obj: &str, key: &str) -> String {
        let o = json.find(&std::format!("\"{}\"", obj)).unwrap();
        let k = o + json[o..].find(&std::format!("\"{}\"", key)).unwrap();
        let s = k + json[k..].find(": \"").unwrap() + 3;
        let e = s + json[s..].find('"').unwrap();
        String::from(&json[s..e])
    }
    fn bytes<const N: usize>(hex: &str) -> [u8; N] {
        let mut out = [0u8; N];
        for i in 0..N { out[i] = u8::from_str_radix(&hex[2 * i..2 * i + 2], 16).unwrap(); }
        out
    }
    fn g1(env: &Env, h: &str) -> Bn254G1Affine { Bn254G1Affine::from_bytes(BytesN::from_array(env, &bytes::<64>(h))) }
    fn g2(env: &Env, h: &str) -> Bn254G2Affine { Bn254G2Affine::from_bytes(BytesN::from_array(env, &bytes::<128>(h))) }

    fn check(key: &str) -> bool { check_with("proof", key) }

    fn check_with(proof: &str, key: &str) -> bool {
        let env = Env::default();
        let j = include_str!("../soroban-fixture.json");
        groth16_holds(&env,
            g1(&env, &field(j, proof, "neg_a")), g2(&env, &field(j, proof, "b")), g1(&env, &field(j, proof, "c")),
            g1(&env, &field(j, key, "alpha")), g2(&env, &field(j, key, "beta")), g1(&env, &field(j, key, "icx")),
            g2(&env, &field(j, key, "gamma")), g2(&env, &field(j, key, "delta")))
    }

    #[test]
    fn an_honest_proof_of_a_true_statement_passes_with_the_contributed_key() { assert!(check_with("honest", "B9")); }

    #[test]
    fn forged_proof_of_a_false_statement_passes_on_a_key_with_no_phase_2() { assert!(check("A")); }

    #[test]
    fn the_same_forgery_fails_after_one_honest_contribution() { assert!(!check("B")); }

    #[test]
    fn a_one_person_key_lets_its_maker_forge_a_proof_of_a_false_statement() { assert!(check_with("proofC", "C")); }
}
