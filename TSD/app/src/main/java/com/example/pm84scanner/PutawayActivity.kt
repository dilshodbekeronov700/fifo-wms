package com.example.pm84scanner

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.widget.EditText
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.runtime.mutableStateListOf
import com.example.pm84scanner.ui.putaway.PutawayCandidate
import com.example.pm84scanner.ui.putaway.PutawayPhase
import com.example.pm84scanner.ui.putaway.PutawayScreen
import com.example.pm84scanner.ui.theme.Pm84Theme
import org.json.JSONObject

/**
 * TSD "WMS joylash" (Compose + Material 3) — transport kod → bron → QR tasdiq.
 * APPARAT SKANER va oqim/API logikasi (Asl Belgisi resolve, ranjlangan joylar,
 * bron, tasdiq, qo'lda qidirish) O'ZGARMADI — faqat UI Compose'ga ko'chirildi.
 */
class PutawayActivity : AppCompatActivity() {

    // ── Compose holati ────────────────────────────────────────────────────────
    private val phaseState = mutableStateOf(PutawayPhase.SCAN)
    private val hintState = mutableStateOf("")
    private val scannedCodeState = mutableStateOf("")
    private val productState = mutableStateOf("")
    private val loadingState = mutableStateOf(false)
    private val candidatesState: SnapshotStateList<PutawayCandidate> = mutableStateListOf()
    private val qtyOptionsState = mutableStateOf<List<Int>>(emptyList())
    private val selectedQtyState = mutableStateOf(1)
    private val reservedLocState = mutableStateOf<String?>(null)

    // Flow state
    private var currentResult: WmsApiClient.ScanSuggestResult? = null
    private var reservationId: String? = null
    private var reservedLocationCode: String? = null
    private var inFlight = false
    private var selectedQty: Int = 1
    private var lastDedupe = ""
    private var lastDedupeAt = 0L

    private lateinit var wmsClient: WmsApiClient
    private var warehouseId = ""

    private val scanReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val action = intent?.action ?: return
            if (!DecodeBroadcastReceiver.SUPPORTED_ACTIONS.contains(action)) return
            val raw = extractRaw(intent)
            if (raw.isBlank()) return
            acceptScan(raw)
        }
    }

    private var clipboardManager: android.content.ClipboardManager? = null
    private val clipListener = android.content.ClipboardManager.OnPrimaryClipChangedListener {
        window?.decorView?.post {
            if (!hasWindowFocus()) return@post
            val text = clipboardManager?.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty()
            if (text.isNotBlank()) acceptScan(text)
        }
    }

    private val keyBuffer = StringBuilder()
    private var lastKeyAt = 0L

    override fun dispatchKeyEvent(event: android.view.KeyEvent): Boolean {
        if (currentFocus is android.widget.EditText) return super.dispatchKeyEvent(event)
        if (event.action == android.view.KeyEvent.ACTION_DOWN) {
            val now = SystemClock.elapsedRealtime()
            if (now - lastKeyAt > 300) keyBuffer.setLength(0)
            lastKeyAt = now
            when (event.keyCode) {
                android.view.KeyEvent.KEYCODE_ENTER,
                android.view.KeyEvent.KEYCODE_NUMPAD_ENTER,
                android.view.KeyEvent.KEYCODE_TAB -> {
                    val data = keyBuffer.toString()
                    keyBuffer.setLength(0)
                    if (data.isNotBlank()) { acceptScan(data); return true }
                    return super.dispatchKeyEvent(event)
                }
                else -> {
                    val ch = event.unicodeChar
                    if (ch != 0) { keyBuffer.append(ch.toChar()); return true }
                }
            }
        } else if (event.action == android.view.KeyEvent.ACTION_MULTIPLE) {
            val chars = event.characters
            if (!chars.isNullOrEmpty()) { keyBuffer.append(chars); return true }
        }
        return super.dispatchKeyEvent(event)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        clipboardManager = getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
        loadPrefs()
        resetScreen()
        setContent {
            Pm84Theme {
                PutawayScreen(
                    phase = phaseState.value,
                    hint = hintState.value,
                    scannedCode = scannedCodeState.value,
                    product = productState.value,
                    loading = loadingState.value,
                    candidates = candidatesState,
                    qtyOptions = qtyOptionsState.value,
                    selectedQty = selectedQtyState.value,
                    reservedLocation = reservedLocState.value,
                    onSelectQty = { selectedQty = it; selectedQtyState.value = it },
                    onReserve = ::reserveByLocation,
                    onManualSearch = ::openManualSearch,
                    onCancelReservation = ::cancelReservation,
                    onReset = ::resetScreen,
                    onBack = { finish() },
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        loadPrefs()
        val filter = IntentFilter().apply {
            DecodeBroadcastReceiver.SUPPORTED_ACTIONS.forEach { addAction(it) }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(scanReceiver, filter, Context.RECEIVER_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(scanReceiver, filter)
        }
        clipboardManager?.addPrimaryClipChangedListener(clipListener)
    }

    override fun onPause() {
        super.onPause()
        try { unregisterReceiver(scanReceiver) } catch (_: Exception) {}
        try { clipboardManager?.removePrimaryClipChangedListener(clipListener) } catch (_: Exception) {}
    }

    // ── Scan handling ─────────────────────────────────────────────────────────

    private fun acceptScan(raw: String) {
        val now = SystemClock.elapsedRealtime()
        if (raw == lastDedupe && now - lastDedupeAt < DEDUPE_MS) return
        lastDedupe = raw; lastDedupeAt = now
        onScanned(raw.trim())
    }

    private fun onScanned(raw: String) {
        if (inFlight) return
        if (reservationId != null) { confirm(raw); return }
        if (warehouseId.isBlank()) {
            Toast.makeText(this, getString(R.string.putaway_no_warehouse), Toast.LENGTH_LONG).show()
            return
        }
        if (classifyPutawayCode(raw) == PutawayCodeKind.UNIT) {
            vibrateOnce()
            Toast.makeText(this, "Unit (dona) kod joylashda qabul qilinmaydi — box yoki transport kodni skanlang", Toast.LENGTH_LONG).show()
            return
        }
        fetchSuggestions(raw)
    }

    private enum class PutawayCodeKind { TRANSPORT, BOX, UNIT, UNKNOWN }

    private fun classifyPutawayCode(raw: String): PutawayCodeKind {
        val c = raw.trim()
        if (c.length >= 20 && c.startsWith("00") && c.substring(0, 20).all { it.isDigit() })
            return PutawayCodeKind.TRANSPORT
        if (c.length >= 16 && c.startsWith("01") && c.substring(2, 16).all { it.isDigit() })
            return if (c[2] == '0') PutawayCodeKind.UNIT else PutawayCodeKind.BOX
        return PutawayCodeKind.UNKNOWN
    }

    private fun qtyOptions(boxCount: Int): List<Int> {
        if (boxCount <= 1) return listOf(1)
        val opts = linkedSetOf(1, Math.ceil(boxCount / 4.0).toInt(), Math.ceil(boxCount / 2.0).toInt(), boxCount)
        return opts.filter { it in 1..boxCount }.sorted()
    }

    // ── 1) Transport scan → resolve + directed slotting ─────────────────────────

    private fun fetchSuggestions(code: String) {
        inFlight = true
        loadingState.value = true
        hintState.value = getString(R.string.putaway_resolving)
        scannedCodeState.value = code
        candidatesState.clear()
        vibrateOnce()

        Thread {
            val token = WmsApiClient.ensureToken(this)
            if (token == null) {
                runOnUiThread {
                    inFlight = false; loadingState.value = false
                    hintState.value = getString(R.string.putaway_scan_transport)
                    Toast.makeText(this, getString(R.string.putaway_auth_error), Toast.LENGTH_LONG).show()
                }
                return@Thread
            }
            wmsClient.setToken(token)
            var result = wmsClient.scanSuggest(code, warehouseId)
            if (result == null && wmsClient.lastScanError?.contains("401") == true) {
                val fresh = WmsApiClient.ensureToken(this, errorIs401 = true)
                if (fresh != null) { wmsClient.setToken(fresh); result = wmsClient.scanSuggest(code, warehouseId) }
            }

            runOnUiThread {
                inFlight = false; loadingState.value = false
                if (result == null) {
                    hintState.value = getString(R.string.putaway_scan_transport)
                    val err = wmsClient.lastScanError
                    Toast.makeText(this, if (!err.isNullOrBlank()) err else getString(R.string.putaway_not_found), Toast.LENGTH_LONG).show()
                    return@runOnUiThread
                }
                if (!result.resolved.ownershipOk) {
                    hintState.value = getString(R.string.putaway_scan_transport)
                    Toast.makeText(this, getString(R.string.putaway_ownership_failed, result.resolved.reason ?: "?"), Toast.LENGTH_LONG).show()
                    return@runOnUiThread
                }
                if (result.resolved.productId.isNullOrBlank()) {
                    val g = result.resolved.gtin?.takeIf { it.isNotBlank() } ?: "—"
                    Toast.makeText(this, "Mahsulot aniqlanmadi (GTIN: $g) — joyni qo'lda tanlang", Toast.LENGTH_LONG).show()
                }
                currentResult = result
                selectedQty = result.resolved.boxCount.coerceAtLeast(1)
                selectedQtyState.value = selectedQty
                renderResolved(result.resolved)
                renderCandidates(result)
                phaseState.value = PutawayPhase.SUGGEST
            }
        }.start()
    }

    private fun renderResolved(r: WmsApiClient.ResolvedCode) {
        val displayName = r.productName?.takeIf { it.isNotBlank() && it != "null" }
            ?: ("Noma'lum mahsulot" + (r.gtin?.let { " (GTIN: $it)" } ?: ""))
        productState.value = getString(R.string.putaway_resolved_summary, displayName, r.boxCount, r.unitCount)
        val codeLine = StringBuilder(r.code)
        r.packageType?.let { codeLine.append(" · ").append(it) }
        r.expiryDate?.let { codeLine.append("\n").append(getString(R.string.putaway_expiry, it)) }
        if (r.children.isNotEmpty()) codeLine.append("\n").append("child: ${r.children.size}")
        scannedCodeState.value = codeLine.toString()
    }

    private fun renderCandidates(result: WmsApiClient.ScanSuggestResult) {
        val boxCount = result.resolved.boxCount.coerceAtLeast(1)
        qtyOptionsState.value = qtyOptions(boxCount)
        candidatesState.clear()
        result.candidates.forEachIndexed { index, c ->
            candidatesState.add(
                PutawayCandidate(
                    rank = index + 1,
                    code = c.locationCode,
                    zone = c.zoneType,
                    reason = factorLine(c),
                    score = c.score.toInt().coerceIn(0, 100),
                    locationId = c.locationId,
                )
            )
        }
        hintState.value = getString(R.string.putaway_scan_location)
    }

    private fun factorLine(c: WmsApiClient.SlotCandidate): String {
        val top = c.factors.entries.sortedByDescending { it.value }.take(3).joinToString(", ") { it.key }
        val parts = mutableListOf<String>()
        if (c.reason.isNotBlank() && c.reason != "standart") parts.add(c.reason)
        else if (top.isNotBlank()) parts.add(top)
        val extra = c.factors.size - 3
        if (extra > 0) parts.add(getString(R.string.putaway_factor_more, extra))
        parts.add(getString(R.string.putaway_remaining, c.remainingBoxes))
        return parts.joinToString(" · ")
    }

    /** Compose kartadan "Bron" — locationId bo'yicha candidate'ni topib reserve qiladi. */
    private fun reserveByLocation(locationId: String) {
        if (inFlight) return
        val c = currentResult?.candidates?.firstOrNull { it.locationId == locationId }
        reserve(locationId, manual = false, score = c?.score, reason = c?.reason)
    }

    private fun openManualSearch() {
        val r = currentResult?.resolved ?: return
        val input = EditText(this).apply {
            hint = getString(R.string.putaway_search_hint)
            setPadding(40, 30, 40, 30)
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.putaway_manual_search)
            .setView(input)
            .setPositiveButton(android.R.string.search_go) { _, _ -> runManualSearch(input.text.toString().trim(), r) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun runManualSearch(query: String, r: WmsApiClient.ResolvedCode) {
        inFlight = true; loadingState.value = true
        Thread {
            wmsClient.setToken(WmsApiClient.ensureToken(this).orEmpty())
            val opts = wmsClient.searchLocations(warehouseId, query, r.productId, r.batchId, maxOf(1, r.boxCount))
            runOnUiThread {
                inFlight = false; loadingState.value = false
                if (opts.isEmpty()) { Toast.makeText(this, R.string.putaway_no_suggestions, Toast.LENGTH_SHORT).show(); return@runOnUiThread }
                val labels = opts.map { o ->
                    val flag = if (o.canPlace) "✓" else "✕"
                    val note = o.note?.let { " ($it)" } ?: ""
                    "$flag ${o.code} · ${o.zoneType} · ${getString(R.string.putaway_remaining, o.remainingBoxes)}$note"
                }.toTypedArray()
                AlertDialog.Builder(this)
                    .setTitle(R.string.putaway_manual_search)
                    .setItems(labels) { _, which ->
                        val o = opts[which]
                        if (!o.canPlace && o.note == "bloklangan") {
                            Toast.makeText(this, "Slot bloklangan — joylash mumkin emas", Toast.LENGTH_SHORT).show()
                        } else if (!o.canPlace) {
                            val msg = o.note ?: getString(R.string.putaway_full)
                            AlertDialog.Builder(this)
                                .setTitle("Ogohlantirishga qaramay joylash?")
                                .setMessage("$msg\n\nBaribir bu joyga joylashtirilsinmi?")
                                .setPositiveButton("Ha, joylash") { _, _ ->
                                    reserve(o.locationId, manual = true, score = null, reason = "manual_force", force = true)
                                }
                                .setNegativeButton("Bekor qilish", null)
                                .show()
                        } else {
                            reserve(o.locationId, manual = true, score = null, reason = "manual")
                        }
                    }
                    .show()
            }
        }.start()
    }

    private fun reserve(locationId: String, manual: Boolean, score: Float?, reason: String?, force: Boolean = false) {
        val r = currentResult?.resolved ?: return
        inFlight = true; loadingState.value = true
        hintState.value = getString(R.string.putaway_reserving)
        Thread {
            wmsClient.setToken(WmsApiClient.ensureToken(this).orEmpty())
            val res = wmsClient.reserve(warehouseId, r, locationId, manual, score, reason, force, qty = selectedQty)
            runOnUiThread {
                inFlight = false; loadingState.value = false
                if (res.ok) {
                    val o = JSONObject(res.body)
                    reservationId = o.optString("id")
                    reservedLocationCode = findLocationCode(locationId)
                    enterConfirmState()
                    vibrateSuccess()
                    Toast.makeText(this, R.string.putaway_reserved_ok, Toast.LENGTH_LONG).show()
                } else {
                    hintState.value = getString(R.string.putaway_scan_location)
                    Toast.makeText(this, reserveErrorMessage(res.body), Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    private fun findLocationCode(locationId: String): String? =
        currentResult?.candidates?.firstOrNull { it.locationId == locationId }?.locationCode

    private fun reserveErrorMessage(body: String): String {
        val detail = try { JSONObject(body).optString("detail") } catch (_: Exception) { body }
        return when {
            detail.contains("location_blocked") -> "Slot bloklangan — joylash mumkin emas"
            detail.contains("location_full") -> "Slotda joy yetarli emas"
            detail.contains("mixing_not_allowed") -> "Bu zonada mahsulotlarni aralashtirish taqiqlangan"
            detail.contains("already_reserved") -> getString(R.string.putaway_already_reserved)
            detail.contains("product_not_found") -> "Mahsulot WMS da topilmadi"
            detail.contains("location_not_found") -> "Joy topilmadi"
            else -> getString(R.string.putaway_confirm_error)
        }
    }

    // ── 3) Confirm by scanning the slot QR/DataMatrix ───────────────────────────

    private fun enterConfirmState() {
        phaseState.value = PutawayPhase.CONFIRM
        reservedLocState.value = reservedLocationCode ?: "?"
        hintState.value = getString(R.string.putaway_reserved_ok)
        candidatesState.clear()
    }

    private fun confirm(scannedBarcode: String) {
        val resId = reservationId ?: return
        inFlight = true; loadingState.value = true
        hintState.value = getString(R.string.putaway_confirming)
        Thread {
            val res = WmsOps.confirmReservation(this, resId, scannedBarcode)
            runOnUiThread {
                inFlight = false; loadingState.value = false
                when (res.outcome) {
                    WmsOps.Outcome.SENT -> {
                        vibrateSuccess()
                        Toast.makeText(this, R.string.putaway_confirmed_ok, Toast.LENGTH_SHORT).show()
                        resetScreen()
                    }
                    WmsOps.Outcome.QUEUED -> {
                        vibrateSuccess()
                        Toast.makeText(this, R.string.putaway_queued_offline, Toast.LENGTH_SHORT).show()
                        resetScreen()
                    }
                    WmsOps.Outcome.FAILED -> {
                        if (res.detail.contains("wrong_location")) {
                            Toast.makeText(this, getString(R.string.putaway_wrong_location, reservedLocationCode ?: "?"), Toast.LENGTH_LONG).show()
                        } else {
                            Toast.makeText(this, R.string.putaway_confirm_error, Toast.LENGTH_SHORT).show()
                        }
                        hintState.value = getString(R.string.putaway_reserved_ok)
                    }
                }
            }
        }.start()
    }

    private fun cancelReservation() {
        val resId = reservationId ?: return
        inFlight = true; loadingState.value = true
        Thread {
            wmsClient.setToken(WmsApiClient.ensureToken(this).orEmpty())
            wmsClient.cancelReservation(resId)
            runOnUiThread {
                inFlight = false; loadingState.value = false
                Toast.makeText(this, R.string.putaway_reservation_cancelled, Toast.LENGTH_SHORT).show()
                resetScreen()
            }
        }.start()
    }

    private fun resetScreen() {
        currentResult = null
        reservationId = null
        reservedLocationCode = null
        inFlight = false
        phaseState.value = PutawayPhase.SCAN
        hintState.value = getString(R.string.putaway_scan_transport)
        scannedCodeState.value = ""
        productState.value = ""
        candidatesState.clear()
        qtyOptionsState.value = emptyList()
        reservedLocState.value = null
        loadingState.value = false
    }

    private fun loadPrefs() {
        val p = getSharedPreferences(WmsApiClient.PREFS, Context.MODE_PRIVATE)
        val url = p.getString(WmsApiClient.KEY_WMS_URL, "").orEmpty()
        val token = p.getString(WmsApiClient.KEY_WMS_TOKEN, "").orEmpty()
        warehouseId = p.getString(WmsApiClient.KEY_WMS_WAREHOUSE_ID, "").orEmpty()
        wmsClient = WmsApiClient(url, token)
    }

    private fun extractRaw(intent: Intent): String {
        listOf("EXTRA_DATA", "EXTRA_EVENT_DECODE_STRING_VALUE", "barcode_string", "data", "DATA")
            .forEach { k -> intent.getStringExtra(k)?.trim()?.takeIf { it.isNotEmpty() }?.let { return it } }
        return intent.getByteArrayExtra("EXTRA_DATA")?.let { String(it, Charsets.UTF_8) }.orEmpty()
    }

    private fun vibrateOnce() = vibrate(60)
    private fun vibrateSuccess() = vibrate(200)

    private fun vibrate(ms: Long) {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (getSystemService(VIBRATOR_MANAGER_SERVICE) as VibratorManager).defaultVibrator
        } else {
            @Suppress("DEPRECATION") getSystemService(VIBRATOR_SERVICE) as Vibrator
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION") vibrator.vibrate(ms)
        }
    }

    companion object {
        private const val DEDUPE_MS = 900L
    }
}
