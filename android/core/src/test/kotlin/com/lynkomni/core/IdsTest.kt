package com.lynkomni.core

import org.json.JSONObject
import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class IdsTest {
    private val root = File("../../contract")
    private val reg = Registry(File(root, "identifier-registry.v1.json").readText())
    private val vectors = JSONObject(File(root, "vectors/identifiers.v1.json").readText())

    @Test fun registryHasTheApprovedTypes() = assertEquals(48, reg.size)

    @Test fun vectorsFromThePythonReference() {
        val valid = vectors.getJSONArray("valid"); for (i in 0 until valid.length()) { val v = valid.getJSONObject(i); assertEquals(v.getString("payload"), parseId(reg, v.getString("id")).second) }
        val invalid = vectors.getJSONArray("invalid"); for (i in 0 until invalid.length()) assertFailsWith<IllegalArgumentException> { parseId(reg, invalid.getJSONObject(i).getString("id")) }
    }

    @Test fun offlineWindows() { assertEquals(7, maxOfflineDays("owner")); assertEquals(14, maxOfflineDays("cashier")) }
}
