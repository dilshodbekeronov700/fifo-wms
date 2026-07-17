package com.example.pm84scanner

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

/**
 * Persistent offline operation queue (TZ §8 — offline-first TSD).
 *
 * Operations performed while offline are appended here as JSON and replayed by
 * [SyncManager] once connectivity returns. File-backed (atomic rewrite) so no
 * extra Gradle dependency (Room) is needed.
 *
 * Each entry: { id, type, path, method, payload, created_at, attempts }
 *   type    — logical op name (putaway_confirm, inventory_count, movement, ...)
 *   path    — WMS API path relative to base (e.g. /api/v1/putaway/confirm)
 *   payload — JSON body to POST
 */
class OfflineQueue(context: Context) {

    private val file = File(context.filesDir, FILE_NAME)
    private val lock = Any()

    data class Op(
        val id: String,
        val type: String,
        val path: String,
        val method: String,
        val payload: JSONObject,
        val createdAt: Long,
        var attempts: Int,
    )

    fun enqueue(type: String, path: String, payload: JSONObject, method: String = "POST"): Op {
        synchronized(lock) {
            val op = Op(
                id = UUID.randomUUID().toString(),
                type = type,
                path = path,
                method = method,
                payload = payload,
                createdAt = System.currentTimeMillis(),
                attempts = 0,
            )
            val arr = readArray()
            arr.put(op.toJson())
            writeArray(arr)
            return op
        }
    }

    fun all(): List<Op> {
        synchronized(lock) {
            val arr = readArray()
            return (0 until arr.length()).map { fromJson(arr.getJSONObject(it)) }
        }
    }

    fun size(): Int = synchronized(lock) { readArray().length() }

    fun remove(id: String) {
        synchronized(lock) {
            val arr = readArray()
            val kept = JSONArray()
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                if (o.optString("id") != id) kept.put(o)
            }
            writeArray(kept)
        }
    }

    fun bumpAttempts(id: String) {
        synchronized(lock) {
            val arr = readArray()
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                if (o.optString("id") == id) {
                    o.put("attempts", o.optInt("attempts") + 1)
                }
            }
            writeArray(arr)
        }
    }

    // ── persistence ───────────────────────────────────────────────────────────

    private fun readArray(): JSONArray {
        if (!file.exists()) return JSONArray()
        return try {
            JSONArray(file.readText())
        } catch (_: Exception) {
            JSONArray()
        }
    }

    private fun writeArray(arr: JSONArray) {
        val tmp = File(file.parentFile, "$FILE_NAME.tmp")
        tmp.writeText(arr.toString())
        tmp.renameTo(file)
    }

    private fun Op.toJson() = JSONObject().apply {
        put("id", id); put("type", type); put("path", path); put("method", method)
        put("payload", payload); put("created_at", createdAt); put("attempts", attempts)
    }

    private fun fromJson(o: JSONObject) = Op(
        id = o.optString("id"),
        type = o.optString("type"),
        path = o.optString("path"),
        method = o.optString("method", "POST"),
        payload = o.optJSONObject("payload") ?: JSONObject(),
        createdAt = o.optLong("created_at"),
        attempts = o.optInt("attempts"),
    )

    companion object {
        private const val FILE_NAME = "wms_offline_queue.json"
        const val MAX_ATTEMPTS = 8
    }
}
