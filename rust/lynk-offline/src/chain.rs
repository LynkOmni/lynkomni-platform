//! Contract v1 canonical serialization and hash chain. Byte-for-byte equal to the Python reference.
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

/// Canonical form: keys sorted, no whitespace, UTF-8 not escaped, integers only.
/// serde_json keeps object keys sorted (BTreeMap) unless the `preserve_order` feature is enabled: never enable it here.
pub fn canonical(v: &Value) -> Result<String, &'static str> {
    if let Value::Number(n) = v { if !(n.is_i64() || n.is_u64()) { return Err("floating point numbers are not allowed in events"); } }
    match v {
        Value::Array(a) => { for x in a { canonical(x)?; } Ok(serde_json::to_string(v).unwrap()) }
        Value::Object(o) => { for x in o.values() { canonical(x)?; } Ok(serde_json::to_string(v).unwrap()) }
        _ => Ok(serde_json::to_string(v).unwrap()),
    }
}

pub fn signing_bytes(evt: &Value, stamp_keys: &[String]) -> Result<String, &'static str> {
    let mut body = Map::new();
    for (k, v) in evt.as_object().ok_or("event must be an object")? {
        if k != "signature" && !stamp_keys.iter().any(|s| s == k) { body.insert(k.clone(), v.clone()); }
    }
    canonical(&Value::Object(body))
}

pub fn event_hash(evt: &Value, stamp_keys: &[String]) -> Result<String, &'static str> {
    Ok(hex::encode(Sha256::digest(signing_bytes(evt, stamp_keys)?.as_bytes())))
}

/// Index of the first event that breaks the chain, or None if the stream is intact.
pub fn verify_chain(events: &[Value], stamp_keys: &[String]) -> Result<Option<usize>, &'static str> {
    let mut prev = "GENESIS".to_string();
    for (i, e) in events.iter().enumerate() {
        if e["device_seq"].as_u64() != Some(i as u64 + 1) || e["prev_hash"].as_str() != Some(prev.as_str()) { return Ok(Some(i)); }
        prev = event_hash(e, stamp_keys)?;
    }
    Ok(None)
}
