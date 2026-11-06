//! Offline session policy. Privileged roles re-authenticate sooner so a removed manager cannot sell for weeks. Data stays safe either way.
pub fn max_offline_days(role: &str) -> u32 { match role { "owner" | "manager" => 7, _ => 14 } }

/// Selling pauses (data stays safe and syncs after re-authentication) once the window has passed.
pub fn selling_allowed(role: &str, days_since_signin: u32) -> bool { days_since_signin <= max_offline_days(role) }
