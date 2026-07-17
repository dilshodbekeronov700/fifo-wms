package com.example.pm84scanner

import android.util.Log
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * WMS backend bilan ishlash uchun HTTP client.
 * Endpoints:
 *   POST /api/v1/auth/login        — JWT olish
 *   POST /api/v1/putaway/tsd-scan  — GTIN → tavsiya + task_id
 *   POST /api/v1/putaway/confirm   — task_id + location_id → tasdiqlash
 */
class WmsApiClient(
    private val baseUrl: String,
    private var accessToken: String = "",
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    // ── Auth ─────────────────────────────────────────────────────────────────

    /**
     * Email va password bilan login qilish.
     * @return access_token yoki null (xatolik bo'lsa)
     */
    fun login(email: String, password: String): String? {
        val body = JSONObject().apply {
            put("email", email)
            put("password", password)
        }.toString().toRequestBody(jsonMedia)

        val request = Request.Builder()
            .url("${baseUrl.trimEnd('/')}/api/v1/auth/login")
            .post(body)
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    Log.e(TAG, "Login failed: ${response.code}")
                    return null
                }
                val json = JSONObject(response.body?.string().orEmpty())
                json.optString("access_token").takeIf { it.isNotBlank() }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Login exception: ${e.message}")
            null
        }
    }

    // ── TSD Putaway ───────────────────────────────────────────────────────────

    data class PutawaySuggestion(
        val locationId: String,
        val locationCode: String,
        val zoneName: String,
        val score: Float,
        val reason: String,
    )

    data class TsdScanResult(
        val taskId: String,
        val productId: String,
        val productName: String,
        val suggestions: List<PutawaySuggestion>,
    )

    /**
     * GTIN bo'yicha mahsulot topib, joylash tavsiyalarini olish.
     * @return TsdScanResult yoki null
     */
    fun tsdScan(gtin: String, warehouseId: String, qty: Int = 1): TsdScanResult? {
        val body = JSONObject().apply {
            put("gtin", gtin)
            put("warehouse_id", warehouseId)
            put("qty", qty)
        }.toString().toRequestBody(jsonMedia)

        val request = Request.Builder()
            .url("${baseUrl.trimEnd('/')}/api/v1/putaway/tsd-scan")
            .header("Authorization", "Bearer $accessToken")
            .post(body)
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                if (response.code == 401) {
                    Log.w(TAG, "tsdScan: 401 Unauthorized")
                    return null
                }
                val text = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    Log.e(TAG, "tsdScan error ${response.code}: $text")
                    return null
                }
                parseTsdScanResult(JSONObject(text))
            }
        } catch (e: Exception) {
            Log.e(TAG, "tsdScan exception: ${e.message}")
            null
        }
    }

    private fun parseTsdScanResult(json: JSONObject): TsdScanResult {
        val arr: JSONArray = json.optJSONArray("suggestions") ?: JSONArray()
        val suggestions = (0 until arr.length()).map { i ->
            val s = arr.getJSONObject(i)
            PutawaySuggestion(
                locationId = s.optString("location_id"),
                locationCode = s.optString("location_code"),
                zoneName = s.optString("zone_name"),
                score = s.optDouble("score", 0.0).toFloat(),
                reason = s.optString("reason"),
            )
        }
        return TsdScanResult(
            taskId = json.optString("task_id"),
            productId = json.optString("product_id"),
            productName = json.optString("product_name"),
            suggestions = suggestions,
        )
    }

    /**
     * Operátor yacheykaga mahsulotni qo'ygach tasdiqlash.
     * @return true = muvaffaqiyatli
     */
    fun confirmPutaway(taskId: String, locationId: String): Boolean {
        val body = JSONObject().apply {
            put("task_id", taskId)
            put("location_id", locationId)
        }.toString().toRequestBody(jsonMedia)

        val request = Request.Builder()
            .url("${baseUrl.trimEnd('/')}/api/v1/putaway/confirm")
            .header("Authorization", "Bearer $accessToken")
            .post(body)
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    Log.e(TAG, "confirmPutaway error ${response.code}: ${response.body?.string()}")
                    false
                } else true
            }
        } catch (e: Exception) {
            Log.e(TAG, "confirmPutaway exception: ${e.message}")
            false
        }
    }

    // ── Generic JSON POST/GET (used by new flows + offline replay) ─────────────

    /** Result of a raw call: HTTP code + body text. code<0 means network error. */
    data class HttpResult(val code: Int, val body: String) {
        val ok: Boolean get() = code in 200..299
    }

    fun postJson(path: String, payload: JSONObject): HttpResult {
        val body = payload.toString().toRequestBody(jsonMedia)
        val request = Request.Builder()
            .url("${baseUrl.trimEnd('/')}$path")
            .header("Authorization", "Bearer $accessToken")
            .post(body)
            .build()
        return execRaw(request)
    }

    fun getJson(path: String): HttpResult {
        val request = Request.Builder()
            .url("${baseUrl.trimEnd('/')}$path")
            .header("Authorization", "Bearer $accessToken")
            .get()
            .build()
        return execRaw(request)
    }

    private fun execRaw(request: Request): HttpResult {
        return try {
            client.newCall(request).execute().use { r ->
                HttpResult(r.code, r.body?.string().orEmpty())
            }
        } catch (e: Exception) {
            Log.e(TAG, "HTTP exception ${request.url}: ${e.message}")
            HttpResult(-1, e.message.orEmpty())
        }
    }

    // ── Transport-code scan → directed slotting → reserve → confirm-by-scan ─────
    //
    //   1) scanSuggest()  — scan the 20-digit transport code (00…); the backend
    //      resolves it through Asl Belgisi (ownership, GTIN, batch, box/unit
    //      counts, child codes) and returns ranked slots WITH a per-factor
    //      breakdown so the operator sees *why* a slot was chosen.
    //   2) reserve()      — operator accepts a slot (suggested or manual) → the
    //      slot is held (bron). No stock moves yet.
    //   3) confirm()      — operator physically scans the slot's QR/DataMatrix →
    //      stock is placed. Wrong barcode is rejected by the server.

    /** Full resolved Asl Belgisi detail for the scanned transport code. */
    data class ResolvedCode(
        val code: String,
        val ownershipOk: Boolean,
        val reason: String?,
        val packageType: String?,
        val gtin: String?,
        val expiryDate: String?,
        val productionDate: String?,
        val boxCount: Int,
        val unitCount: Int,
        val countingMethod: String,
        val productId: String?,
        val productName: String,
        val batchId: String?,
        val children: List<String>,
    )

    /** One ranked slot, with the weighted factor contributions that produced it. */
    data class SlotCandidate(
        val locationId: String,
        val locationCode: String,
        val zoneType: String,
        val score: Float,
        val reason: String,
        val factors: Map<String, Float>,
        val remainingBoxes: Int,
    )

    data class ScanSuggestResult(
        val resolved: ResolvedCode,
        val candidates: List<SlotCandidate>,
    )

    /** A location returned from the manual search/override. */
    data class LocationOption(
        val locationId: String,
        val code: String,
        val barcode: String?,
        val zoneType: String,
        val status: String,
        val remainingBoxes: Int,
        val canPlace: Boolean,
        val note: String?,
    )

    private fun productNameOf(o: JSONObject): String {
        val n = o.optJSONObject("product_name") ?: return o.optString("gtin", "—")
        return n.optString("uz").takeIf { it.isNotBlank() }
            ?: n.optString("ru").takeIf { it.isNotBlank() }
            ?: n.optString("en").takeIf { it.isNotBlank() }
            ?: o.optString("gtin", "—")
    }

    // org.json quirk: JSON null → optString "null" satrini qaytaradi. Bu helper
    // haqiqiy null / bo'sh / "null" satrini bir xil — null deb qaytaradi.
    private fun JSONObject.optStrOrNull(key: String): String? =
        if (isNull(key)) null else optString(key).takeIf { it.isNotBlank() && it != "null" }

    private fun parseResolved(r: JSONObject): ResolvedCode {
        val childArr = r.optJSONArray("children") ?: JSONArray()
        return ResolvedCode(
            code = r.optString("code"),
            ownershipOk = r.optBoolean("ownership_ok"),
            reason = r.optStrOrNull("reason"),
            packageType = r.optStrOrNull("package_type"),
            gtin = r.optStrOrNull("gtin"),
            expiryDate = r.optStrOrNull("expiry_date"),
            productionDate = r.optStrOrNull("production_date"),
            boxCount = r.optInt("box_count"),
            unitCount = r.optInt("unit_count"),
            countingMethod = r.optString("counting_method"),
            productId = r.optStrOrNull("product_id"),
            productName = productNameOf(r),
            batchId = r.optStrOrNull("batch_id"),
            children = (0 until childArr.length()).map { childArr.optString(it) },
        )
    }

    private fun parseCandidate(s: JSONObject): SlotCandidate {
        val fObj = s.optJSONObject("factors") ?: JSONObject()
        val factors = LinkedHashMap<String, Float>()
        fObj.keys().forEach { k -> factors[k] = fObj.optDouble(k, 0.0).toFloat() }
        return SlotCandidate(
            locationId = s.optString("location_id"),
            locationCode = s.optString("location_code"),
            zoneType = s.optString("zone_type"),
            score = s.optDouble("score", 0.0).toFloat(),
            reason = s.optString("reason"),
            factors = factors,
            remainingBoxes = s.optInt("remaining_boxes"),
        )
    }

    /** Oxirgi scanSuggest xatosi (HTTP kod + backend detali) — UI'da ko'rsatish uchun. */
    var lastScanError: String? = null
        private set

    fun scanSuggest(transportCode: String, warehouseId: String, topN: Int = 5): ScanSuggestResult? {
        lastScanError = null
        val payload = JSONObject().apply {
            put("code", transportCode); put("warehouse_id", warehouseId); put("top_n", topN)
        }
        val res = postJson("/api/v1/putaway/scan-suggest", payload)
        if (!res.ok) {
            Log.e(TAG, "scanSuggest ${res.code}: ${res.body}")
            val detail = try { JSONObject(res.body).optString("detail") } catch (_: Exception) { "" }
            lastScanError = "HTTP ${res.code}" + if (detail.isNotBlank()) ": $detail" else ": ${res.body.take(120)}"
            return null
        }
        val json = JSONObject(res.body)
        val resolved = parseResolved(json.optJSONObject("resolved") ?: JSONObject())
        val arr = json.optJSONArray("candidates") ?: JSONArray()
        val candidates = (0 until arr.length()).map { parseCandidate(arr.getJSONObject(it)) }
        return ScanSuggestResult(resolved, candidates)
    }

    /** Hold a slot for the scanned code. Returns the reservation id, or null. */
    fun reserve(
        warehouseId: String,
        resolved: ResolvedCode,
        locationId: String,
        manual: Boolean,
        score: Float?,
        reason: String?,
        force: Boolean = false,
        qty: Int? = null,
    ): HttpResult {
        val payload = JSONObject().apply {
            put("warehouse_id", warehouseId)
            put("code", resolved.code)
            put("location_id", locationId)
            put("product_id", resolved.productId)
            resolved.batchId?.let { put("batch_id", it) }
            put("qty", qty ?: maxOf(1, resolved.boxCount))
            put("unit_count", resolved.unitCount)
            resolved.packageType?.let { put("package_type", it) }
            score?.let { put("score", it.toDouble()) }
            reason?.let { put("reason", it) }
            put("manual", manual)
            put("force", force)
            put("payload", JSONObject().apply {
                put("children", JSONArray(resolved.children))
                resolved.gtin?.let { put("gtin", it) }
                resolved.expiryDate?.let { put("expiry_date", it) }
            })
        }
        return postJson("/api/v1/putaway/reserve", payload)
    }

    /** Confirm placement by the slot barcode the operator physically scanned. */
    fun confirmReservation(reservationId: String, locationBarcode: String): HttpResult =
        postJson("/api/v1/putaway/confirm", JSONObject().apply {
            put("reservation_id", reservationId)
            put("location_barcode", locationBarcode)
        })

    fun cancelReservation(reservationId: String): HttpResult =
        postJson("/api/v1/putaway/cancel", JSONObject().put("reservation_id", reservationId))

    fun searchLocations(
        warehouseId: String, query: String, productId: String?, batchId: String?, qty: Int,
    ): List<LocationOption> {
        val enc = { s: String -> java.net.URLEncoder.encode(s, "UTF-8") }
        var path = "/api/v1/putaway/locations/search?warehouse_id=$warehouseId&qty=$qty"
        if (query.isNotBlank()) path += "&q=${enc(query)}"
        if (!productId.isNullOrBlank()) path += "&product_id=$productId"
        if (!batchId.isNullOrBlank()) path += "&batch_id=$batchId"
        val res = getJson(path)
        if (!res.ok) return emptyList()
        val arr = JSONArray(res.body)
        return (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            LocationOption(
                locationId = o.optString("location_id"),
                code = o.optString("code"),
                barcode = o.optString("barcode").takeIf { it.isNotBlank() },
                zoneType = o.optString("zone_type"),
                status = o.optString("status"),
                remainingBoxes = o.optInt("remaining_boxes"),
                canPlace = o.optBoolean("can_place"),
                note = o.optString("note").takeIf { it.isNotBlank() },
            )
        }
    }

    // ── Tasks (assignment / monitoring) ─────────────────────────────────────────

    data class WmsTask(
        val id: String, val type: String, val status: String,
        val priority: Int, val payload: JSONObject,
    )

    fun getTasks(warehouseId: String, status: String? = null): List<WmsTask> {
        var path = "/api/v1/tasks/?warehouse_id=$warehouseId"
        if (!status.isNullOrBlank()) path += "&status=$status"
        val res = getJson(path)
        if (!res.ok) return emptyList()
        val arr = JSONArray(res.body)
        return (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            WmsTask(
                id = o.optString("id"),
                type = o.optString("task_type"),
                status = o.optString("status"),
                priority = o.optInt("priority"),
                payload = o.optJSONObject("payload") ?: JSONObject(),
            )
        }
    }

    // ── Product lookup (inventory flow) ─────────────────────────────────────────

    data class WmsProduct(val id: String, val name: String, val gtin: String, val unitsPerBox: Int)

    fun productByGtin(gtin: String): WmsProduct? {
        val res = getJson("/api/v1/products/by-gtin?gtin=$gtin")
        if (!res.ok) return null
        val o = JSONObject(res.body)
        val nameObj = o.optJSONObject("name")
        val name = nameObj?.optString("uz")?.takeIf { it.isNotBlank() }
            ?: nameObj?.optString("ru") ?: o.optString("id")
        return WmsProduct(
            id = o.optString("id"), name = name, gtin = o.optString("gtin"),
            unitsPerBox = o.optInt("units_per_box", 1),
        )
    }

    // ── Shipment / picking ──────────────────────────────────────────────────────

    data class ShipOrder(val dealId: String, val number: String, val status: String)

    fun getShipmentOrders(warehouseId: String): List<ShipOrder> {
        // statuses YUBORILMAYDI → backend ochiq buyurtmalarni (A/B#N/B#S) qaytaradi.
        // (Ilgari statuses=B#W edi — bunday status yo'q, ro'yxat bo'sh kelardi.)
        val res = getJson("/api/v1/shipment/orders?warehouse_id=$warehouseId")
        if (!res.ok) return emptyList()
        val arr = JSONArray(res.body)
        return (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            ShipOrder(o.optString("deal_id"), o.optString("order_number"), o.optString("status"))
        }
    }

    /** Create a pick task from a Smartup deal. Returns the WMS document id, or null. */
    fun createPickTask(warehouseId: String, dealId: String): String? {
        val res = postJson("/api/v1/shipment/pick-task",
            JSONObject().put("warehouse_id", warehouseId).put("smartup_deal_id", dealId))
        if (!res.ok) {
            Log.e(TAG, "createPickTask ${res.code}: ${res.body}")
            return null
        }
        return JSONObject(res.body).optString("document_id").takeIf { it.isNotBlank() }
    }

    fun confirmShipmentDoc(documentId: String): Boolean =
        postJson("/api/v1/shipment/confirm/$documentId", JSONObject()).ok

    // ── Labels (ZPL) ────────────────────────────────────────────────────────────

    fun locationLabelZpl(locationId: String): String? {
        val res = getJson("/api/v1/labels/location/$locationId")
        return if (res.ok) JSONObject(res.body).optString("zpl") else null
    }

    fun palletLabelZpl(markingCode: String): String? {
        val res = getJson("/api/v1/labels/pallet/${java.net.URLEncoder.encode(markingCode, "UTF-8")}")
        return if (res.ok) JSONObject(res.body).optString("zpl") else null
    }

    fun setToken(token: String) {
        accessToken = token
    }

    companion object {
        private const val TAG = "WmsApiClient"

        // SharedPreferences kalitlari
        const val PREFS = "enasai_settings"
        const val KEY_WMS_URL = "wms_base_url"
        const val KEY_WMS_EMAIL = "wms_email"
        const val KEY_WMS_PASSWORD = "wms_password"
        const val KEY_WMS_TOKEN = "wms_token"
        const val KEY_WMS_WAREHOUSE_ID = "wms_warehouse_id"

        /**
         * Prefs'dagi token yaroqliligini ta'minlaydi.
         * Token bo'sh yoki muddati o'tgan bo'lsa (errorIs401=true) — qayta login qilib
         * prefs'ga yangi token saqlaydi.
         *
         * @param context      SharedPreferences uchun
         * @param errorIs401   Oxirgi so'rovda 401 xatosi bo'ldimi (qayta login majburiy)
         * @return Yaroqli token yoki null (login muvaffaqiyatsiz / hisob yo'q)
         */
        fun ensureToken(context: android.content.Context, errorIs401: Boolean = false): String? {
            val p = context.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE)
            val url   = p.getString(KEY_WMS_URL,      "").orEmpty()
            val email = p.getString(KEY_WMS_EMAIL,    "").orEmpty()
            val pass  = p.getString(KEY_WMS_PASSWORD, "").orEmpty()
            val saved = p.getString(KEY_WMS_TOKEN,    "").orEmpty()

            if (url.isBlank() || email.isBlank() || pass.isBlank()) return null

            // Token bor va 401 bo'lmagan — mavjud tokenni ishlatamiz
            if (saved.isNotBlank() && !errorIs401) return saved

            // Token yo'q yoki muddati o'tgan — qayta login
            val newToken = WmsApiClient(url).login(email, pass) ?: return null
            p.edit().putString(KEY_WMS_TOKEN, newToken).apply()
            return newToken
        }
    }
}
