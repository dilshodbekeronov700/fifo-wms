package com.example.pm84scanner

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Online/offline facade for WMS write operations.
 *
 * If online and the call succeeds → done immediately.
 * Otherwise the operation is appended to [OfflineQueue] and replayed later by
 * [SyncManager]. Returns an [OpResult] describing what happened.
 */
object WmsOps {

    enum class Outcome { SENT, QUEUED, FAILED }
    data class OpResult(val outcome: Outcome, val detail: String = "")

    private fun client(context: Context): WmsApiClient? {
        val prefs = context.getSharedPreferences(WmsApiClient.PREFS, Context.MODE_PRIVATE)
        val baseUrl = prefs.getString(WmsApiClient.KEY_WMS_URL, null) ?: return null
        val token = prefs.getString(WmsApiClient.KEY_WMS_TOKEN, "").orEmpty()
        return WmsApiClient(baseUrl, token)
    }

    private fun submit(context: Context, type: String, path: String, payload: JSONObject): OpResult {
        val queue = OfflineQueue(context)
        if (ConnectivityHelper.isOnline(context)) {
            val c = client(context)
            if (c != null) {
                val res = c.postJson(path, payload)
                if (res.ok) return OpResult(Outcome.SENT)
                // Network/server error (or 401) → queue for retry; hard validation drops happen in SyncManager.
                if (res.code < 0 || res.code >= 500 || res.code == 401 || res.code == 429) {
                    queue.enqueue(type, path, payload)
                    return OpResult(Outcome.QUEUED, "code=${res.code}")
                }
                return OpResult(Outcome.FAILED, "${res.code}: ${res.body}")
            }
        }
        queue.enqueue(type, path, payload)
        return OpResult(Outcome.QUEUED, "offline")
    }

    // ── Operations ──────────────────────────────────────────────────────────────

    /** Confirm a held putaway reservation by the slot barcode the operator scanned.
     *  Offline-aware: if the network drops mid-confirm the call is queued and
     *  replayed by [SyncManager] (the reservation already exists server-side). */
    fun confirmReservation(context: Context, reservationId: String, locationBarcode: String): OpResult =
        submit(context, "putaway_confirm", "/api/v1/putaway/confirm",
            JSONObject().put("reservation_id", reservationId).put("location_barcode", locationBarcode))

    /** Receipt: submit scanned transport codes (TZ §7.2). */
    fun receipt(
        context: Context, warehouseId: String,
        codes: List<Pair<String, String>>, notes: String? = null,
    ): OpResult {
        val arr = JSONArray()
        for ((code, pkg) in codes) {
            arr.put(JSONObject().put("code", code).put("package_type", pkg))
        }
        val payload = JSONObject().apply {
            put("warehouse_id", warehouseId); put("codes", arr)
            if (notes != null) put("notes", notes)
        }
        return submit(context, "receipt", "/api/v1/receipt", payload)
    }

    fun inventoryCount(
        context: Context, warehouseId: String, lines: List<Triple<String, String?, Int>>,
        notes: String? = null,
    ): OpResult {
        val arr = JSONArray()
        for ((productId, batchId, qty) in lines) {
            arr.put(JSONObject().apply {
                put("product_id", productId)
                if (batchId != null) put("batch_id", batchId)
                put("counted_qty", qty)
            })
        }
        val payload = JSONObject().apply {
            put("warehouse_id", warehouseId); put("lines", arr)
            if (notes != null) put("notes", notes)
        }
        return submit(context, "inventory_count", "/api/v1/inventory/count", payload)
    }

    fun movement(
        context: Context, warehouseId: String, fromLocationId: String, toLocationId: String,
        lines: List<Triple<String, String?, Int>>, reason: String? = null,
    ): OpResult {
        val arr = JSONArray()
        for ((productId, batchId, qty) in lines) {
            arr.put(JSONObject().apply {
                put("product_id", productId)
                if (batchId != null) put("batch_id", batchId)
                put("qty", qty)
            })
        }
        val payload = JSONObject().apply {
            put("warehouse_id", warehouseId)
            put("from_location_id", fromLocationId)
            put("to_location_id", toLocationId)
            put("lines", arr)
            if (reason != null) put("reason", reason)
        }
        return submit(context, "movement", "/api/v1/movement", payload)
    }
}
