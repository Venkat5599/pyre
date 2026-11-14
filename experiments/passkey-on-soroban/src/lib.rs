#![no_std]
//! Day-one check for Pyre: can a Soroban contract verify a real WebAuthn passkey
//! signature whose challenge is a ceremony contribution hash?

use soroban_sdk::{contract, contracterror, contractimpl, panic_with_error, Bytes, BytesN, Env};

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum Error {
    ChallengeMismatch = 1,
    NotAnAssertion = 2,
}

const B64URL: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

/// base64url (no padding) of a 32-byte hash: always 43 characters.
fn b64url_32(h: &[u8; 32]) -> [u8; 43] {
    let mut out = [0u8; 43];
    let mut o = 0;
    let mut i = 0;
    while i + 3 <= 30 {
        let n = ((h[i] as u32) << 16) | ((h[i + 1] as u32) << 8) | (h[i + 2] as u32);
        out[o] = B64URL[((n >> 18) & 63) as usize];
        out[o + 1] = B64URL[((n >> 12) & 63) as usize];
        out[o + 2] = B64URL[((n >> 6) & 63) as usize];
        out[o + 3] = B64URL[(n & 63) as usize];
        o += 4;
        i += 3;
    }
    // last 2 bytes -> 3 chars
    let n = ((h[30] as u32) << 16) | ((h[31] as u32) << 8);
    out[o] = B64URL[((n >> 18) & 63) as usize];
    out[o + 1] = B64URL[((n >> 12) & 63) as usize];
    out[o + 2] = B64URL[((n >> 6) & 63) as usize];
    out
}

fn contains(hay: &Bytes, needle: &[u8]) -> bool {
    let n = needle.len() as u32;
    if hay.len() < n {
        return false;
    }
    let mut i = 0;
    while i + n <= hay.len() {
        let mut ok = true;
        let mut j = 0;
        while j < n {
            if hay.get_unchecked(i + j) != needle[j as usize] {
                ok = false;
                break;
            }
            j += 1;
        }
        if ok {
            return true;
        }
        i += 1;
    }
    false
}

#[contract]
pub struct PasskeyCheck;

#[contractimpl]
impl PasskeyCheck {
    /// Accepts only if `sig` is the passkey `pk` signing a WebAuthn assertion whose
    /// challenge is exactly `contribution_hash`. Panics otherwise.
    pub fn verify(
        env: Env,
        contribution_hash: BytesN<32>,
        pk: BytesN<65>,
        auth_data: Bytes,
        client_data_json: Bytes,
        sig: BytesN<64>,
    ) -> bool {
        if !contains(&client_data_json, b"\"type\":\"webauthn.get\"") {
            panic_with_error!(&env, Error::NotAnAssertion);
        }
        let mut needle = [0u8; 13 + 43 + 1];
        needle[..13].copy_from_slice(b"\"challenge\":\"");
        needle[13..56].copy_from_slice(&b64url_32(&contribution_hash.to_array()));
        needle[56] = b'"';
        if !contains(&client_data_json, &needle) {
            panic_with_error!(&env, Error::ChallengeMismatch);
        }
        let cdh = env.crypto().sha256(&client_data_json);
        let mut msg = auth_data.clone();
        msg.append(&Bytes::from_array(&env, &cdh.to_array()));
        let digest = env.crypto().sha256(&msg);
        env.crypto().secp256r1_verify(&pk, &digest, &sig);
        true
    }
}

#[cfg(test)]
mod test;
