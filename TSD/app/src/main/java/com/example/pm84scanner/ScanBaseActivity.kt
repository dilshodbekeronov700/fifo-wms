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
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.Color
import com.example.pm84scanner.ui.scan.LogLine
import com.example.pm84scanner.ui.scan.ScanScreen
import com.example.pm84scanner.ui.theme.FlowReceipt
import com.example.pm84scanner.ui.theme.Pm84Theme

/**
 * Skan-ekranlari uchun umumiy baza (Receipt / Inventory / Picking).
 * UI endi Jetpack Compose (Material 3). APPARAT SKANER mantig'i — PM84 broadcast,
 * clipboard-paste va keyboard-wedge — O'ZGARMADI. Subklasslar onScan() ni amalga
 * oshiradi va logLine/setCounter/setButtons + onPrimary/onSecondary dan foydalanadi.
 */
abstract class ScanBaseActivity : AppCompatActivity() {

    // ── Compose holati (eski XML view'lar o'rniga) ───────────────────────────
    private val logState = mutableStateListOf<LogLine>()
    private val counterState = mutableStateOf("")
    private val hintState = mutableStateOf("")
    private val primaryLabel = mutableStateOf("OK")
    private val secondaryLabel = mutableStateOf("Tozalash")
    private val secondaryVisible = mutableStateOf(true)
    private val primaryEnabled = mutableStateOf(true)

    /** Subklass tugma ishlovchilarini shu yerga beradi. */
    protected var onPrimary: () -> Unit = {}
    protected var onSecondary: () -> Unit = {}

    protected var baseUrl = ""
    protected var token = ""
    protected var warehouseId = ""

    private var lastScan = ""
    private var lastScanAt = 0L

    private var clipboardManager: android.content.ClipboardManager? = null
    private val clipListener = android.content.ClipboardManager.OnPrimaryClipChangedListener {
        window?.decorView?.post { readClipboardIfFocused() }
    }

    private fun readClipboardIfFocused() {
        if (!hasWindowFocus()) return
        val text = clipboardManager?.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty()
        deliverScan(text)
    }

    private val scanReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val action = intent?.action ?: return
            if (!DecodeBroadcastReceiver.SUPPORTED_ACTIONS.contains(action)) return
            deliverScan(extractRaw(intent))
        }
    }

    /** Broadcast va klaviatura yo'llari shu yerga keladi — debounce + onScan. */
    private fun deliverScan(raw: String) {
        val data = raw.trim()
        if (data.isBlank()) return
        val now = SystemClock.elapsedRealtime()
        if (data == lastScan && now - lastScanAt < 700) return
        lastScan = data; lastScanAt = now
        onScan(data)
    }

    // ── Keyboard-wedge rejimi ────────────────────────────────────────────────
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
                    if (data.isNotBlank()) { deliverScan(data); return true }
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

    /** Screen-specific: called once per (de-duplicated) scan. */
    protected abstract fun onScan(raw: String)

    protected abstract fun screenTitle(): String
    protected open fun initialHint(): String = ""

    /** Ekran accent rangi (Receipt/Inventory/Picking har biri o'zinikini beradi). */
    protected open fun accent(): Color = FlowReceipt

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        clipboardManager = getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
        hintState.value = initialHint()
        loadPrefs()
        setContent {
            Pm84Theme {
                ScanScreen(
                    title = screenTitle(),
                    hint = hintState.value,
                    accent = accent(),
                    counter = counterState.value,
                    log = logState,
                    primaryLabel = primaryLabel.value,
                    secondaryLabel = secondaryLabel.value,
                    secondaryVisible = secondaryVisible.value,
                    primaryEnabled = primaryEnabled.value,
                    onPrimary = { onPrimary() },
                    onSecondary = { onSecondary() },
                    onBack = { finish() },
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        loadPrefs()
        SyncManager.syncAsync(this)
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

    protected fun loadPrefs() {
        val p = getSharedPreferences(WmsApiClient.PREFS, Context.MODE_PRIVATE)
        baseUrl = p.getString(WmsApiClient.KEY_WMS_URL, "").orEmpty()
        token = p.getString(WmsApiClient.KEY_WMS_TOKEN, "").orEmpty()
        warehouseId = p.getString(WmsApiClient.KEY_WMS_WAREHOUSE_ID, "").orEmpty()
    }

    protected fun client() = WmsApiClient(baseUrl, token)

    // ── UI yordamchilari (eski nomlar saqlandi — Compose state'ga yozadi) ─────
    protected fun logLine(text: String, color: Int = 0xFF333333.toInt()) {
        val argb = color.toLong() and 0xFFFFFFFFL
        runOnUiThread { logState.add(0, LogLine(text, argb)) }
    }

    protected fun clearLog() { runOnUiThread { logState.clear() } }

    protected fun setCounter(text: String) { runOnUiThread { counterState.value = text } }

    protected fun toastUi(msg: String) =
        runOnUiThread { android.widget.Toast.makeText(this, msg, android.widget.Toast.LENGTH_SHORT).show() }

    protected fun setButtons(primary: String, secondary: String, secondaryVisible: Boolean = true) {
        runOnUiThread {
            primaryLabel.value = primary
            secondaryLabel.value = secondary
            this.secondaryVisible.value = secondaryVisible
        }
    }

    /** Eski `btnPrimary.isEnabled = ...` o'rniga. */
    protected fun setPrimaryEnabled(enabled: Boolean) {
        runOnUiThread { primaryEnabled.value = enabled }
    }

    // GS1 DataMatrix kod turi
    enum class CodeKind { TRANSPORT, BOX, UNIT, UNKNOWN }

    protected fun classifyCode(raw: String): CodeKind {
        val c = raw.trim()
        if (c.length >= 20 && c.startsWith("00") && c.substring(0, 20).all { it.isDigit() })
            return CodeKind.TRANSPORT
        if (c.startsWith("01") && c.length >= 16 && c.substring(2, 16).all { it.isDigit() })
            return if (c[2] == '0') CodeKind.UNIT else CodeKind.BOX
        return CodeKind.UNKNOWN
    }

    protected fun extractGtin(raw: String): String? {
        val c = raw.trim()
        if (c.startsWith("01") && c.length >= 16) {
            val g = c.substring(2, 16)
            if (g.all { it.isDigit() }) return g
        }
        val idx = c.indexOf("01")
        if (idx >= 0 && c.length >= idx + 16) {
            val g = c.substring(idx + 2, idx + 16)
            if (g.all { it.isDigit() }) return g
        }
        return null
    }

    protected fun vibrateOk() {
        val v = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager).defaultVibrator
        } else {
            @Suppress("DEPRECATION") getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            v.vibrate(VibrationEffect.createOneShot(60, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION") v.vibrate(60)
        }
    }

    private fun extractRaw(intent: Intent): String {
        val keys = listOf(
            "EXTRA_DATA",
            DecodeBroadcastReceiver.EXTRA_DATA,
            "barcode_string",
            "data",
            "DATA",
        )
        keys.forEach { k ->
            intent.getStringExtra(k)?.trim()?.takeIf { it.isNotEmpty() }?.let { return it }
        }
        keys.forEach { k ->
            intent.getByteArrayExtra(k)?.takeIf { it.isNotEmpty() }?.let { return String(it, Charsets.UTF_8) }
        }
        return ""
    }
}
