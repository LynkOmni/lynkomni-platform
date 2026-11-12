use lynk_offline::{chain, ids, session};
use serde_json::Value;

fn read(p: &str) -> String { std::fs::read_to_string(format!("{}/../../contract/{}", env!("CARGO_MANIFEST_DIR"), p)).expect(p) }

#[test]
fn identifier_vectors() {
    let reg = ids::Registry::from_json(&read("identifier-registry.v1.json"));
    assert_eq!(reg.len(), 48);
    let v: Value = serde_json::from_str(&read("vectors/identifiers.v1.json")).unwrap();
    for c in v["valid"].as_array().unwrap() { assert_eq!(ids::parse(&reg, c["id"].as_str().unwrap()).unwrap().1, c["payload"].as_str().unwrap()); }
    for c in v["invalid"].as_array().unwrap() { assert!(ids::parse(&reg, c["id"].as_str().unwrap()).is_err()); }
}

#[test]
fn chain_vectors_match_the_python_reference() {
    let v: Value = serde_json::from_str(&read("vectors/chain.v1.json")).unwrap();
    let keys: Vec<String> = v["server_stamp_keys"].as_array().unwrap().iter().map(|k| k.as_str().unwrap().to_string()).collect();
    for (i, e) in v["events"].as_array().unwrap().iter().enumerate() {
        assert_eq!(chain::signing_bytes(e, &keys).unwrap(), v["signing_bytes"][i].as_str().unwrap());
        assert_eq!(chain::event_hash(e, &keys).unwrap(), v["hashes"][i].as_str().unwrap());
    }
    assert_eq!(chain::event_hash(&v["stamped_event"], &keys).unwrap(), v["stamped_hash"].as_str().unwrap());
    assert_eq!(chain::verify_chain(v["events"].as_array().unwrap(), &keys).unwrap(), None);
}

#[test]
fn privileged_roles_reauthenticate_sooner() {
    assert!(session::selling_allowed("cashier", 14) && !session::selling_allowed("cashier", 15));
    assert!(session::selling_allowed("owner", 7) && !session::selling_allowed("owner", 8));
}
