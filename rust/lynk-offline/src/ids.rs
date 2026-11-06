//! LO + TYPE + "-XXXX-XXXX-XXXX": 12 digits, the last one a Luhn check digit.
use serde_json::Value;

pub struct Registry(Vec<String>);

impl Registry {
    pub fn from_json(json: &str) -> Registry {
        let v: Value = serde_json::from_str(json).expect("registry json");
        Registry(v["types"].as_array().expect("types").iter().map(|t| t["code"].as_str().expect("code").to_string()).collect())
    }
    pub fn has(&self, code: &str) -> bool { self.0.iter().any(|c| c == code) }
    pub fn len(&self) -> usize { self.0.len() }
}

pub fn luhn_digit(p11: &str) -> char {
    let mut s = 0;
    for (i, ch) in p11.chars().rev().enumerate() {
        let mut d = ch.to_digit(10).expect("digit") * if i % 2 == 0 { 2 } else { 1 };
        if d > 9 { d -= 9; }
        s += d;
    }
    char::from_digit((10 - s % 10) % 10, 10).unwrap()
}

pub fn luhn_ok(p12: &str) -> bool {
    let mut s = 0;
    for (i, ch) in p12.chars().rev().enumerate() {
        let mut d = match ch.to_digit(10) { Some(d) => d * if i % 2 == 1 { 2 } else { 1 }, None => return false };
        if d > 9 { d -= 9; }
        s += d;
    }
    s % 10 == 0
}

/// Format check only. A well-formed identifier proves nothing about existence or access.
pub fn parse(reg: &Registry, id: &str) -> Result<(String, String), &'static str> {
    let rest = id.strip_prefix("LO").ok_or("missing LO namespace")?;
    let (code, digits) = rest.split_once('-').ok_or("missing separator")?;
    if code.len() < 2 || code.len() > 4 || !code.chars().all(|c| c.is_ascii_uppercase()) || !reg.has(code) { return Err("unregistered type"); }
    let groups: Vec<&str> = digits.split('-').collect();
    if groups.len() != 3 || groups.iter().any(|g| g.len() != 4 || !g.chars().all(|c| c.is_ascii_digit())) { return Err("payload must be 3 groups of 4 digits"); }
    let payload = groups.concat();
    if !luhn_ok(&payload) { return Err("check digit does not match"); }
    Ok((code.to_string(), payload))
}
