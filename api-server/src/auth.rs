//! Authentication Module
//! 
//! Keypair-based authentication for AI Agents.

use ed25519_dalek::{Signature, VerifyingKey, Verifier};
use bs58;

/// Verify an agent's signature
pub fn verify_signature(
    pubkey: &str,
    message: &[u8],
    signature: &str,
) -> Result<bool, AuthError> {
    // Decode pubkey
    let pubkey_bytes = bs58::decode(pubkey)
        .into_vec()
        .map_err(|_| AuthError::InvalidPubkey)?;
    
    if pubkey_bytes.len() != 32 {
        return Err(AuthError::InvalidPubkey);
    }
    
    let verifying_key = VerifyingKey::from_bytes(
        &pubkey_bytes.try_into().unwrap()
    ).map_err(|_| AuthError::InvalidPubkey)?;
    
    // Decode signature
    let sig_bytes = bs58::decode(signature)
        .into_vec()
        .map_err(|_| AuthError::InvalidSignature)?;
    
    if sig_bytes.len() != 64 {
        return Err(AuthError::InvalidSignature);
    }
    
    let sig = Signature::from_bytes(
        &sig_bytes.try_into().unwrap()
    );
    
    // Verify
    verifying_key
        .verify(message, &sig)
        .map(|_| true)
        .map_err(|_| AuthError::VerificationFailed)
}

#[derive(Debug)]
pub enum AuthError {
    InvalidPubkey,
    InvalidSignature,
    VerificationFailed,
}

impl std::fmt::Display for AuthError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AuthError::InvalidPubkey => write!(f, "Invalid public key"),
            AuthError::InvalidSignature => write!(f, "Invalid signature"),
            AuthError::VerificationFailed => write!(f, "Signature verification failed"),
        }
    }
}

impl std::error::Error for AuthError {}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_verify_signature() {
        // TODO: Add tests with real keypairs
    }
}
