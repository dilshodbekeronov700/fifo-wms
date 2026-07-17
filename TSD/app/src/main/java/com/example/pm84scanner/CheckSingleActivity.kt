package com.example.pm84scanner

import android.content.BroadcastReceiver
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.widget.Button
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.progressindicator.LinearProgressIndicator
import org.json.JSONArray
import org.json.JSONObject
import java.util.regex.Pattern

/**
 * COD private codes API (check.py) bo‘yicha tekshiruv: skan → ierarxiya (daraxt), qatorni bosish → batafsil / yana bosish → yig‘iladi.
 */
class CheckSingleActivity : AppCompatActivity() {

    // ── Compose holati ────────────────────────────────────────────────────────
    private val hintState = androidx.compose.runtime.mutableStateOf("")
    private val bufferState = androidx.compose.runtime.mutableStateOf<List<String>>(emptyList())
    private val rowsState =
        androidx.compose.runtime.mutableStateOf<List<com.example.pm84scanner.ui.check.UiTreeRow>>(emptyList())
    private val loadingState = androidx.compose.runtime.mutableStateOf(false)

    private var checkKind: CheckKind = CheckKind.ANY
    private var apiKey = ""
    private var baseUrl = ""
    private var inFlight = false

    private var lastDedupe = ""
    private var lastDedupeAt = 0L

    /** Skanerlangan identifikatorlar (API va ro‘yxatda shu ko‘rinadi). */
    private val pendingCodes = mutableListOf<String>()

    private var clipboardManager: ClipboardManager? = null

    private val clipListener = ClipboardManager.OnPrimaryClipChangedListener {
        window?.decorView?.post { readClipboardIfFocused() }
    }

    private val scanReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val action = intent?.action ?: return
            if (!DecodeBroadcastReceiver.SUPPORTED_ACTIONS.contains(action)) return
            val raw = extractRawBarcodeData(intent)
            val normalized = normalizeGs(raw)
            if (normalized.isBlank()) return
            acceptIncomingScan(normalized)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        checkKind = CheckKind.fromRaw(intent.getStringExtra(ScanIntentExtras.CHECK_KIND))
        loadPrefs()
        hintState.value = getString(R.string.check_scan_hint)
        clipboardManager = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        setContent {
            com.example.pm84scanner.ui.theme.Pm84Theme {
                com.example.pm84scanner.ui.check.CheckScreen(
                    hint = hintState.value,
                    buffer = bufferState.value,
                    rows = rowsState.value,
                    loading = loadingState.value,
                    onSend = { runCodQuery() },
                    onClear = { clearBuffer() },
                    onBack = { finish() },
                )
            }
        }
    }

    private fun clearBuffer() {
        if (pendingCodes.isEmpty()) {
            Toast.makeText(this, "Bufer allaqachon bo'sh", Toast.LENGTH_SHORT).show()
            return
        }
        val count = pendingCodes.size
        pendingCodes.clear()
        rowsState.value = emptyList()
        renderBuffer()
        Toast.makeText(this, "$count kod tozalandi", Toast.LENGTH_SHORT).show()
    }

    override fun onResume() {
        super.onResume()
        loadPrefs()
        val filter = IntentFilter().apply { DecodeBroadcastReceiver.SUPPORTED_ACTIONS.forEach { addAction(it) } }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(scanReceiver, filter, Context.RECEIVER_EXPORTED)
        } else {
            registerReceiver(scanReceiver, filter)
        }
        clipboardManager?.addPrimaryClipChangedListener(clipListener)
    }

    override fun onPause() {
        super.onPause()
        clipboardManager?.removePrimaryClipChangedListener(clipListener)
        unregisterReceiver(scanReceiver)
    }

    /** MainActivity bilan bir xil: skaner ba’zan clipboard orqali beradi. */
    private fun readClipboardIfFocused() {
        if (!hasWindowFocus()) return
        val text = clipboardManager?.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty()
        val normalized = normalizeGs(text)
        if (normalized.isBlank()) return
        acceptIncomingScan(normalized)
    }

    private fun acceptIncomingScan(normalized: String) {
        val now = SystemClock.elapsedRealtime()
        if (normalized == lastDedupe && now - lastDedupeAt < DEDUPE_MS) return
        lastDedupe = normalized
        lastDedupeAt = now
        onScanned(normalized)
    }

    private fun loadPrefs() {
        val p = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        apiKey = p.getString(KEY_API, AppConfig.DEFAULT_API_KEY).orEmpty()
        baseUrl = p.getString(KEY_URL, AppConfig.DEFAULT_BASE_URL).orEmpty()
    }

    private fun onScanned(raw: String) {
        if (inFlight) return
        if (apiKey.isBlank() || baseUrl.isBlank()) {
            Toast.makeText(this, R.string.missing_api_key, Toast.LENGTH_SHORT).show()
            return
        }
        val compact = extractFirstCode(raw) ?: run {
            Toast.makeText(this, R.string.toast_invalid_format, Toast.LENGTH_SHORT).show()
            return
        }
        val ident = stripCryptoTail(compact)
        if (!acceptsKind(ident, checkKind)) {
            Toast.makeText(this, R.string.check_kind_reject, Toast.LENGTH_SHORT).show()
            return
        }
        if (pendingCodes.contains(ident)) {
            Toast.makeText(this, R.string.toast_duplicate_unit, Toast.LENGTH_SHORT).show()
            return
        }
        pendingCodes.add(ident)
        renderBuffer()
        updateSendEnabled()
        vibrateSuccess()
    }

    private fun renderBuffer() { bufferState.value = pendingCodes.toList() }

    /** Compose CheckScreen tugmani buffer+loading bo'yicha o'zi hisoblaydi. */
    private fun updateSendEnabled() { /* no-op (Compose) */ }

    private fun runCodQuery() {
        if (apiKey.isBlank() || baseUrl.isBlank()) {
            Toast.makeText(this, R.string.missing_api_key, Toast.LENGTH_SHORT).show()
            return
        }
        if (pendingCodes.isEmpty()) {
            Toast.makeText(this, R.string.check_buffer_empty, Toast.LENGTH_SHORT).show()
            return
        }
        if (inFlight) return
        inFlight = true
        loadingState.value = true
        hintState.value = getString(R.string.check_loading)
        val identsSnapshot = pendingCodes.toList()
        Thread {
            try {
                val client = XtraceApiClient(baseUrl, apiKey)
                val (http, body) = client.postCodPrivateCodes(identsSnapshot)
                if (http in 401..403) {
                    runOnUiThread {
                        finishQueryUi()
                        Toast.makeText(this, "COD API: $http", Toast.LENGTH_LONG).show()
                    }
                    return@Thread
                }
                if (http !in 200..299) {
                    runOnUiThread {
                        finishQueryUi()
                        Toast.makeText(this, getString(R.string.check_error_api, http), Toast.LENGTH_LONG).show()
                    }
                    return@Thread
                }
                val merged = mergeExpandedCod(JSONObject(body), client)
                val forbidden = forbiddenCodesList(merged.optJSONArray("forbiddenCodes"))
                val index = buildIndex(formatInfoItems(merged))
                val roots = identsSnapshot.mapNotNull { buildTreeNode(it, index, mutableSetOf()) }
                val flat = mutableListOf<TreeRow>()
                flatten(roots, flat)
                runOnUiThread {
                    inFlight = false
                    loadingState.value = false
                    hintState.value = getString(R.string.check_scan_hint)
                    pendingCodes.clear()
                    renderBuffer()
                    rowsState.value = flat.map {
                        com.example.pm84scanner.ui.check.UiTreeRow(it.code, it.status, it.depth, buildDetailLines(it.entry))
                    }
                    if (forbidden.isNotEmpty()) {
                        val preview = forbidden.take(8).joinToString(", ")
                        Toast.makeText(this, getString(R.string.check_forbidden, preview), Toast.LENGTH_LONG).show()
                    }
                }
            } catch (e: Throwable) {
                runOnUiThread {
                    finishQueryUi()
                    Toast.makeText(this, e.message ?: "xato", Toast.LENGTH_SHORT).show()
                }
            }
        }.start()
    }

    private fun finishQueryUi() {
        inFlight = false
        loadingState.value = false
        hintState.value = getString(R.string.check_scan_hint)
    }

    private fun vibrateSuccess() {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (getSystemService(VIBRATOR_MANAGER_SERVICE) as VibratorManager).defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(VIBRATOR_SERVICE) as Vibrator
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(100)
        }
    }

    private data class TreeRow(
        val code: String,
        val status: String,
        val depth: Int,
        val entry: JSONObject?,
        var detailExpanded: Boolean = false
    )

    private class TreeAdapter(
        private val items: List<TreeRow>,
        private val onToggle: (Int) -> Unit,
        private val detailLines: (JSONObject?) -> String
    ) : RecyclerView.Adapter<TreeAdapter.VH>() {

        class VH(itemView: View) : RecyclerView.ViewHolder(itemView) {
            val root: View = itemView.findViewById(R.id.rootRow)
            val main: TextView = itemView.findViewById(R.id.tvMain)
            val detail: TextView = itemView.findViewById(R.id.tvDetail)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
            val v = LayoutInflater.from(parent.context).inflate(R.layout.item_check_tree_row, parent, false)
            return VH(v)
        }

        override fun getItemCount(): Int = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val r = items[position]
            val pad = (8 + r.depth * 18) * holder.itemView.resources.displayMetrics.density
            holder.root.setPaddingRelative(pad.toInt(), holder.root.paddingTop, holder.root.paddingEnd, holder.root.paddingBottom)
            holder.main.text = "${r.code}\n${r.status}"
            if (r.detailExpanded) {
                holder.detail.visibility = View.VISIBLE
                holder.detail.text = detailLines(r.entry)
            } else {
                holder.detail.visibility = View.GONE
            }
            holder.itemView.setOnClickListener {
                val pos = holder.bindingAdapterPosition
                if (pos != RecyclerView.NO_POSITION) onToggle(pos)
            }
        }
    }

    private fun forbiddenCodesList(arr: JSONArray?): List<String> {
        if (arr == null) return emptyList()
        val out = mutableListOf<String>()
        for (i in 0 until arr.length()) {
            arr.optString(i).trim().takeIf { it.isNotEmpty() }?.let { out.add(it) }
        }
        return out
    }

    private fun formatDetailBlock(entry: JSONObject?): String = buildDetailLines(entry)

    companion object {
        private const val PREFS = "enasai_settings"
        private const val KEY_API = "api_key"
        private const val KEY_URL = "base_url"
        private const val DEDUPE_MS = 900L
        private val CODE_IN_TEXT: Pattern = Pattern.compile("(00|01)[A-Za-z0-9]+")

        private fun normalizeGs(raw: String): String = raw.replace(Regex("[\\u001D]"), "<GS>").trim()

        private fun normalizeForRule(code: String): String =
            code.replace("<GS>", "").replace(" ", "").trimStart { !it.isDigit() }

        private fun stripCryptoTail(c: String): String {
            val x = c.replace(" ", "")
            return if (x.startsWith("01") && x.length > AppConfig.AGGREGATION_CODE_MAX_LEN) {
                x.substring(0, AppConfig.AGGREGATION_CODE_MAX_LEN)
            } else {
                x
            }
        }

        private fun extractFirstCode(text: String): String? {
            val lines = text.lines().map { it.trim() }.filter { it.isNotEmpty() }
            val line = lines.firstOrNull() ?: return null
            val compact = normalizeForRule(line)
            if (compact.startsWith("00") || compact.startsWith("01")) return compact
            val m = CODE_IN_TEXT.matcher(compact)
            return if (m.find()) m.group(0) else null
        }

        private fun acceptsKind(compact: String, kind: CheckKind): Boolean {
            return when (kind) {
                CheckKind.ANY -> compact.startsWith("00") || compact.startsWith("01")
                CheckKind.UNIT -> compact.startsWith("010")
                CheckKind.BOX ->
                    (compact.startsWith("01") && compact.length > 2 && compact[2] != '0') ||
                        (compact.startsWith("00000") && compact.length >= 25 &&
                            compact.take(25).all { it.isDigit() })
                CheckKind.TRANSPORT ->
                    compact.length == 20 && compact.startsWith("00") && compact.all { it.isDigit() }
            }
        }

        private fun extractRawBarcodeData(intent: Intent): String {
            val keys = listOf(
                DecodeBroadcastReceiver.EXTRA_DATA,
                "EXTRA_EVENT_DECODE_STRING_VALUE",
                "barcode_string",
                "data",
                "DATA"
            )
            keys.forEach { k ->
                intent.getStringExtra(k)?.trim()?.takeIf { it.isNotEmpty() }?.let { return it }
            }
            val rawBytes = intent.getByteArrayExtra(DecodeBroadcastReceiver.EXTRA_DATA)
            if (rawBytes != null && rawBytes.isNotEmpty()) {
                return String(rawBytes, Charsets.UTF_8)
            }
            return ""
        }

        private fun formatInfoItems(data: JSONObject?): List<JSONObject> {
            if (data == null) return emptyList()
            for (k in listOf("results", "codes", "items", "data", "result")) {
                val arr = data.optJSONArray(k) ?: continue
                val out = ArrayList<JSONObject>(arr.length())
                for (i in 0 until arr.length()) {
                    arr.optJSONObject(i)?.let { out.add(it) }
                }
                if (out.isNotEmpty()) return out
            }
            return emptyList()
        }

        private fun entryCode(e: JSONObject): String? {
            val c = e.optJSONObject("codeData")?.optString("code")?.trim().orEmpty()
                .ifBlank { e.optString("code", "").trim() }
            return c.takeIf { it.isNotBlank() }?.let { stripCryptoTail(it) }
        }

        private fun entryStatus(e: JSONObject): String {
            return e.optJSONObject("codeData")?.optString("status")?.trim().orEmpty()
                .ifBlank { e.optString("status", "").trim() }
        }

        private fun extractParentCode(entry: JSONObject): String? {
            val p = entry.optJSONObject("packageData")?.optString("parentCode")?.trim().orEmpty()
            return p.takeIf { it.isNotBlank() }?.let { stripCryptoTail(it) }
        }

        private fun extractChildCodes(entry: JSONObject): List<String> {
            val arr = entry.optJSONObject("packageData")?.optJSONArray("children") ?: return emptyList()
            val out = LinkedHashSet<String>()
            for (i in 0 until arr.length()) {
                when (val v = arr.opt(i)) {
                    is JSONObject -> {
                        val c = v.optString("code", "").trim()
                        if (c.isNotBlank()) out.add(stripCryptoTail(c))
                    }
                    is String -> if (v.isNotBlank()) out.add(stripCryptoTail(v.trim()))
                }
            }
            return out.toList()
        }

        private fun collectRelated(entries: Collection<JSONObject>): Set<String> {
            val s = mutableSetOf<String>()
            for (e in entries) {
                extractParentCode(e)?.let { s.add(it) }
                s.addAll(extractChildCodes(e))
            }
            return s
        }

        private fun buildIndex(entries: List<JSONObject>): Map<String, JSONObject> {
            val m = linkedMapOf<String, JSONObject>()
            for (e in entries) {
                val c = entryCode(e) ?: continue
                m[c] = e
            }
            return m
        }

        private fun mergeExpandedCod(initial: JSONObject, client: XtraceApiClient): JSONObject {
            val forbidden = initial.optJSONArray("forbiddenCodes") ?: JSONArray()
            val codeIndex = linkedMapOf<String, JSONObject>()
            for (e in formatInfoItems(initial)) {
                entryCode(e)?.let { codeIndex[it] = e }
            }
            var toFetch = collectRelated(codeIndex.values).filter { it !in codeIndex }.toMutableSet()
            var depth = 0
            var fetched = 0
            while (toFetch.isNotEmpty() && depth < 2 && fetched < 400) {
                val chunk = toFetch.take(100)
                toFetch = (toFetch - chunk.toSet()).toMutableSet()
                val (st, text) = client.postCodPrivateCodes(chunk)
                if (st in 401..403) break
                if (st !in 200..299) break
                val data = runCatching { JSONObject(text) }.getOrNull() ?: break
                val batch = formatInfoItems(data)
                for (e in batch) {
                    val c = entryCode(e) ?: continue
                    if (c !in codeIndex) codeIndex[c] = e
                }
                fetched += chunk.size
                val more = collectRelated(batch).filter { it !in codeIndex }
                toFetch = (toFetch + more).toMutableSet()
                depth++
            }
            val arr = JSONArray()
            codeIndex.values.forEach { arr.put(it) }
            return JSONObject().apply {
                put("results", arr)
                put("forbiddenCodes", forbidden)
            }
        }

        private data class TreeNode(
            val code: String,
            val status: String,
            val entry: JSONObject?,
            val children: List<TreeNode>
        )

        private fun buildTreeNode(code: String, index: Map<String, JSONObject>, visiting: MutableSet<String>): TreeNode? {
            if (!visiting.add(code)) return null
            return try {
                val entry = index[code]
                val status = entry?.let { entryStatus(it) }?.takeIf { it.isNotBlank() } ?: "—"
                val childCodes = entry?.let { extractChildCodes(it) } ?: emptyList()
                val children = childCodes.mapNotNull { buildTreeNode(it, index, visiting) }
                TreeNode(code, status, entry, children)
            } finally {
                visiting.remove(code)
            }
        }

        private fun flatten(nodes: List<TreeNode>, out: MutableList<TreeRow>) {
            for (n in nodes) {
                appendFlat(n, 0, out)
            }
        }

        private fun appendFlat(n: TreeNode, depth: Int, out: MutableList<TreeRow>) {
            out.add(TreeRow(n.code, n.status, depth, n.entry, false))
            for (c in n.children) appendFlat(c, depth + 1, out)
        }

        private fun buildDetailLines(entry: JSONObject?): String {
            if (entry == null) return "—"
            val sb = StringBuilder()
            val cd = entry.optJSONObject("codeData")
            val pd = entry.optJSONObject("packageData")
            val td = entry.optJSONObject("turnoverData")?.optJSONObject("ownerInfo")
            val pr = entry.optJSONObject("productData")
            val md = entry.optJSONObject("markingData")
            sb.append("Status: ").append(cd?.optString("status").orEmpty()).append('\n')
            sb.append("Package type: ").append(pd?.optString("packageType").orEmpty()).append('\n')
            sb.append("Parent: ").append(pd?.optString("parentCode").orEmpty()).append('\n')
            sb.append("Actually packed: ").append(pd?.opt("actuallyPacked")?.toString().orEmpty()).append('\n')
            sb.append("Owner TIN: ").append(td?.optString("ownerTin").orEmpty()).append('\n')
            sb.append("Production date: ").append(pr?.optString("productionDate").orEmpty()).append('\n')
            sb.append("Emission: ").append(md?.optString("emissionDate").orEmpty())
                .append("  Issue: ").append(md?.optString("issueDate").orEmpty())
            return sb.toString().trim()
        }
    }
}
