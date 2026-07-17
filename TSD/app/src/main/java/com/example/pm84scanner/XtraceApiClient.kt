package com.example.pm84scanner

import android.util.Base64
import android.util.Log
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder
import java.time.ZoneOffset
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeUnit

/**
 * Two-step reporting: Utilisation then Aggregation (Base64 documentBody).
 */
class XtraceApiClient(
    private val baseUrl: String,
    private val apiKey: String
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    /** yyyy-MM-dd'T'HH:mm:ss'Z' (UTC, millisoniyasiz) — utilisation talabi. */
    private val utilisationInstantFormatter: DateTimeFormatter =
        DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss'Z'").withZone(ZoneOffset.UTC)

    private val utilisationSeriesDateFormatter: DateTimeFormatter =
        DateTimeFormatter.ofPattern("uuuuMMdd").withZone(ZoneOffset.UTC)

    private fun authHeader(): String = "Bearer $apiKey"

    /** Partiya raqami: "TSD-" + UTC sana (yyyyMMdd); masalan TSD-20260411 (12 belgi, ≤20). */
    private fun utilisationSeriesNumber(nowUtc: ZonedDateTime): String =
        "TSD-" + nowUtc.format(utilisationSeriesDateFormatter)

    private fun isoDateUtc(): String {
        return ZonedDateTime.now(ZoneOffset.UTC)
            .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
    }

    /** Utilisation `sntins`: `<GS>` → real GS (U+001D); faqat (01)(21)(93) atrofidagi qavslar olib tashlanadi. */
    private fun normalizeSntinForUtilisation(code: String): String {
        return code
            .replace("<GS>", "\u001D")
            .replace("(01)", "01")
            .replace("(21)", "21")
            .replace("(93)", "93")
            .trim()
    }

    /**
     * POST /api/utilisation?productGroup=...
     * @param sntinCodes GS1 SNTIN / serial strings: either box codes only, or box + unit codes per settings.
     * @return HTTP code and response body string (may be empty)
     */
    fun postUtilisation(
        productGroup: String,
        businessPlaceId: Int,
        manufacturerCountry: String,
        sntinCodes: List<String>,
        releaseType: String = AppConfig.RELEASE_TYPE
    ): Pair<Int, String> {
        val pg = URLEncoder.encode(productGroup, Charsets.UTF_8.name())
        val url = "${baseUrl.trimEnd('/')}/api/utilisation?productGroup=$pg"
        val sntinsJson = JSONArray()
        for (c in sntinCodes) {
            sntinsJson.put(normalizeSntinForUtilisation(c))
        }
        val nowUtc = ZonedDateTime.now(ZoneOffset.UTC)
        val prod = nowUtc.format(utilisationInstantFormatter)
        val exp = nowUtc.plusDays(360).format(utilisationInstantFormatter)
        val series = utilisationSeriesNumber(nowUtc)
        val bodyJson = JSONObject().apply {
            put("sntins", sntinsJson)
            put("businessPlaceId", businessPlaceId)
            put("manufacturerCountry", manufacturerCountry)
            put("releaseType", releaseType)
            put("productionDate", prod)
            put("expirationDate", exp)
            put("seriesNumber", series)
        }
        val body = bodyJson.toString().toRequestBody(jsonMedia)
        val request = Request.Builder()
            .url(url)
            .header("Authorization", authHeader())
            .header("Content-Type", "application/json")
            .post(body)
            .build()
        return execute(request)
    }

    /**
     * POST /public/api/v1/doc/aggregation
     * Outer JSON: { "documentBody": "<base64(inner)>" }
     */
    fun postAggregation(
        businessPlaceId: Int,
        boxLimit: Int,
        completedBoxes: List<BoxPayload>
    ): Pair<Int, String> {
        val aggregationUnits = JSONArray()
        for (box in completedBoxes) {
            val codes = JSONArray()
            for (u in box.units) {
                codes.put(truncateForAggregation(u))
            }
            aggregationUnits.put(
                aggregationUnitJson(
                    itemsCount = box.units.size,
                    capacity = boxLimit,
                    parentSerial = box.boxCode,
                    childCodesJson = codes
                )
            )
        }
        return postAggregationDocument(businessPlaceId, aggregationUnits)
    }

    /**
     * L2 bosqichi 2: Transport (ota) → quti kodlari (bolalar).
     */
    fun postAggregationTransportToBoxes(
        businessPlaceId: Int,
        transportCode: String,
        boxCodes: List<String>,
        palletCapacity: Int
    ): Pair<Int, String> {
        val codes = JSONArray()
        for (b in boxCodes) {
            codes.put(truncateForAggregation(b))
        }
        val aggregationUnits = JSONArray().put(
            aggregationUnitJson(
                itemsCount = boxCodes.size,
                capacity = palletCapacity,
                parentSerial = transportCode,
                childCodesJson = codes
            )
        )
        return postAggregationDocument(businessPlaceId, aggregationUnits)
    }

    /**
     * Bitta ota → bolalar bog‘lanishi (Import transport→unit, L3 transport→child kodlar).
     */
    fun postAggregationParentWithChildren(
        businessPlaceId: Int,
        parentSerial: String,
        children: List<String>,
        aggregationUnitCapacity: Int
    ): Pair<Int, String> {
        val codes = JSONArray()
        for (c in children) {
            codes.put(truncateForAggregation(c))
        }
        val aggregationUnits = JSONArray().put(
            aggregationUnitJson(
                itemsCount = children.size,
                capacity = aggregationUnitCapacity,
                parentSerial = parentSerial,
                childCodesJson = codes
            )
        )
        return postAggregationDocument(businessPlaceId, aggregationUnits)
    }

    private fun aggregationUnitJson(
        itemsCount: Int,
        capacity: Int,
        parentSerial: String,
        childCodesJson: JSONArray
    ): JSONObject {
        return JSONObject().apply {
            put("aggregationItemsCount", itemsCount)
            put("aggregationUnitCapacity", capacity)
            put("unitSerialNumber", truncateForAggregation(parentSerial))
            put("codes", childCodesJson)
        }
    }

    private fun postAggregationDocument(
        businessPlaceId: Int,
        aggregationUnits: JSONArray
    ): Pair<Int, String> {
        val inner = JSONObject().apply {
            put("aggregationUnits", aggregationUnits)
            put("businessPlaceId", businessPlaceId)
            put("documentDate", isoDateUtc())
        }
        val innerBytes = inner.toString().toByteArray(Charsets.UTF_8)
        val b64 = Base64.encodeToString(innerBytes, Base64.NO_WRAP)
        val outer = JSONObject().apply {
            put("documentBody", b64)
        }
        val url = "${baseUrl.trimEnd('/')}/public/api/v1/doc/aggregation"
        val body = outer.toString().toRequestBody(jsonMedia)
        val request = Request.Builder()
            .url(url)
            .header("Authorization", authHeader())
            .header("Content-Type", "application/json")
            .post(body)
            .build()
        return execute(request)
    }

    /**
     * COD private codes (check.py dagi `/public/api/cod/private/codes`).
     */
    fun postCodPrivateCodes(codes: List<String>, addCodeHistory: Boolean = true): Pair<Int, String> {
        if (codes.isEmpty()) return 400 to "{\"error\":\"empty codes\"}"
        val arr = JSONArray()
        for (c in codes) arr.put(c)
        val bodyJson = JSONObject().apply {
            put("codes", arr)
            put("addCodeHistory", addCodeHistory)
        }
        val url = "${baseUrl.trimEnd('/')}/public/api/cod/private/codes"
        val body = bodyJson.toString().toRequestBody(jsonMedia)
        val request = Request.Builder()
            .url(url)
            .header("Authorization", authHeader())
            .header("Content-Type", "application/json")
            .post(body)
            .build()
        return execute(request)
    }

    private fun execute(request: Request): Pair<Int, String> {
        client.newCall(request).execute().use { response ->
            val code = response.code
            val text = response.body?.string().orEmpty()
            Log.d(TAG, "${request.method} ${request.url} -> $code")
            return code to text
        }
    }

    companion object {
        private const val TAG = "XtraceApi"

        /** Aggregation: utilisation bilan mos — faqat (01)(21)(93) qavslari olib tashlanadi, keyin boshidan 31 belgi. */
        fun truncateForAggregation(s: String): String {
            val cleaned = s.trim()
                .replace("(01)", "01")
                .replace("(21)", "21")
                .replace("(93)", "93")
                .trim()
            return if (cleaned.length <= AppConfig.AGGREGATION_CODE_MAX_LEN) {
                cleaned
            } else {
                cleaned.substring(0, AppConfig.AGGREGATION_CODE_MAX_LEN)
            }
        }
    }
}
