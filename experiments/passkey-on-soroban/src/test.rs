extern crate std;
use super::*;
use p256::ecdsa::Signature;
use soroban_sdk::{Bytes, BytesN, Env};
use std::vec::Vec;

struct Fixture {
    hash: [u8; 32],
    pk: [u8; 65],
    auth: Vec<u8>,
    cdj: Vec<u8>,
    sig: [u8; 64],
}

/// Loads the assertion a real Chrome WebAuthn stack produced (virtual authenticator).
fn fixture() -> Fixture {
    let raw = std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/webauthn.json")).unwrap();
    let v: serde_json::Value = serde_json::from_str(&raw).unwrap();
    let h = |k: &str| hex::decode(v[k].as_str().unwrap()).unwrap();
    let spki = h("spki");
    let pk: [u8; 65] = spki[spki.len() - 65..].try_into().unwrap(); // uncompressed point at the end of the SPKI
    let der = Signature::from_der(&h("sig")).unwrap();
    let low_s = der.normalize_s().unwrap_or(der); // Soroban requires low-S form
    Fixture {
        hash: h("challenge_hex").try_into().unwrap(),
        pk,
        auth: h("authData"),
        cdj: h("cdj"),
        sig: low_s.to_bytes().into(),
    }
}

fn call(env: &Env, f: &Fixture, hash: [u8; 32], pk: [u8; 65], cdj: &[u8], sig: [u8; 64]) -> bool {
    let id = env.register(PasskeyCheck, ());
    let c = PasskeyCheckClient::new(env, &id);
    c.verify(
        &BytesN::from_array(env, &hash),
        &BytesN::from_array(env, &pk),
        &Bytes::from_slice(env, &f.auth),
        &Bytes::from_slice(env, cdj),
        &BytesN::from_array(env, &sig),
    )
}

#[test]
fn a_real_passkey_signature_over_the_contribution_hash_verifies() {
    let env = Env::default();
    env.cost_estimate().budget().reset_unlimited();
    let f = fixture();
    assert!(call(&env, &f, f.hash, f.pk, &f.cdj, f.sig));
    std::println!("cpu instructions: {}", env.cost_estimate().budget().cpu_instruction_cost());
}

#[test]
#[should_panic]
fn the_same_signature_cannot_be_reused_for_another_contribution() {
    let env = Env::default();
    let f = fixture();
    let mut other = f.hash;
    other[0] ^= 1;
    call(&env, &f, other, f.pk, &f.cdj, f.sig);
}

#[test]
#[should_panic]
fn a_tampered_signature_is_refused() {
    let env = Env::default();
    let f = fixture();
    let mut sig = f.sig;
    sig[10] ^= 1;
    call(&env, &f, f.hash, f.pk, &f.cdj, sig);
}

#[test]
#[should_panic]
fn a_different_passkey_is_refused() {
    let env = Env::default();
    let f = fixture();
    let other = p256::SecretKey::from_slice(&[7u8; 32]).unwrap().public_key();
    let enc = p256::elliptic_curve::sec1::ToEncodedPoint::to_encoded_point(&other, false);
    let pk: [u8; 65] = enc.as_bytes().try_into().unwrap();
    call(&env, &f, f.hash, pk, &f.cdj, f.sig);
}

#[test]
#[should_panic]
fn edited_client_data_is_refused() {
    let env = Env::default();
    let f = fixture();
    let mut cdj = f.cdj.clone();
    let n = cdj.len();
    cdj[n - 3] = b'X'; // change a byte outside the challenge: the signature no longer matches
    call(&env, &f, f.hash, f.pk, &cdj, f.sig);
}
