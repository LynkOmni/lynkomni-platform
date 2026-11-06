package com.lynkomni.core

import org.json.JSONObject

/** Input and display validation for LynkOmni identifiers on Android. The authoritative engine is the Rust core (called through JNI). */
class Registry(json: String) {
    private val codes: Set<String> = JSONObject(json).getJSONArray("types").let { a -> (0 until a.length()).map { a.getJSONObject(it).getString("code") }.toSet() }
    fun has(code: String) = code in codes
    val size get() = codes.size
}

fun luhnDigit(p11: String): Char {
    var s = 0
    p11.reversed().forEachIndexed { i, ch -> var d = ch.digitToInt() * (if (i % 2 == 0) 2 else 1); if (d > 9) d -= 9; s += d }
    return ((10 - s % 10) % 10).digitToChar()
}

fun luhnOk(p12: String): Boolean {
    var s = 0
    p12.reversed().forEachIndexed { i, ch -> if (!ch.isDigit()) return false; var d = ch.digitToInt() * (if (i % 2 == 1) 2 else 1); if (d > 9) d -= 9; s += d }
    return s % 10 == 0
}

/** Format check only: a well-formed identifier proves nothing about existence or access. */
fun parseId(reg: Registry, id: String): Pair<String, String> {
    val m = Regex("^LO([A-Z]{2,4})-(\\d{4})-(\\d{4})-(\\d{4})$").matchEntire(id) ?: throw IllegalArgumentException("not a LynkOmni identifier")
    val code = m.groupValues[1]; val payload = m.groupValues[2] + m.groupValues[3] + m.groupValues[4]
    require(reg.has(code)) { "unregistered type" }
    require(luhnOk(payload)) { "check digit does not match" }
    return code to payload
}

/** Privileged roles re-authenticate sooner. Selling pauses, data stays safe. */
fun maxOfflineDays(role: String) = if (role == "owner" || role == "manager") 7 else 14
